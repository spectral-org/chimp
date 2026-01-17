import os
import asyncio
import json
import logging
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from google.genai import types

from app.models import ActionSchema, WorldState
from app.agents.interpreter import InterpreterAgent
from app.agents.verifier import VerifierAgent
from app.agents.planner import PlannerAgent
from app.world.executor import WorldExecutor
from app.memory import MemoryStore
from app.graph import SimulationGraph

load_dotenv()

# Hack: Unset GOOGLE_API_KEY if present to avoid conflicts with GEMINI_API_KEY
if "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.websocket("/ws/simulation")
async def simulation_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    try:
        # Initialize Components
        memory = MemoryStore()
        executor = WorldExecutor()
        verifier = VerifierAgent()
        planner = PlannerAgent()
        interpreter = InterpreterAgent()

        sim_graph = SimulationGraph(verifier, executor, planner, memory)

        # Temporary Mission Logic
        active_mission_reqs = {"intent": "buy_item", "grammar": ["polite"]}

        # Connect to Gemini Live
        logger.info("Connecting to Gemini Live...")
        async with await interpreter.connect() as session:
            logger.info("Connected to Gemini Live session")
            
            async def receive_from_client():
                """Reads audio/messages from client and sends to Gemini"""
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            # Forward audio bytes to Gemini Live
                            # Input must be properly formatted with proper MIME type for PCM 16kHz
                            # We use explicit types to ensure the SDK serializes it correctly.
                            # logger.info(f"Sending {len(data['bytes'])} bytes of audio") 
                            await session.send(
                                input=types.LiveClientRealtimeInput(
                                    media_chunks=[
                                        types.Blob(
                                            data=data["bytes"], 
                                            mime_type="audio/pcm;rate=16000"
                                        )
                                    ]
                                ),
                                end_of_turn=False
                            )
                        elif "text" in data:
                            # Might be control messages or text input fallback
                            text_payload = data["text"]
                            try:
                                parsed = json.loads(text_payload)
                                
                                # Handle Commit Signal (End of Turn)
                                # We use a single space text message to signal end of turn.
                                # This avoids 1007 errors associated with empty inputs or silence frame formatting issues.
                                if isinstance(parsed, dict) and parsed.get("type") == "commit":
                                    logger.info("Commit received")
                                    await session.send(input=" ", end_of_turn=True)
                                    logger.info("Sent commit signal to Gemini")
                                    continue

                                text_payload = parsed.get("text", text_payload)
                            except json.JSONDecodeError:
                                pass
                            await session.send(input=text_payload, end_of_turn=True)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.error(f"Client Receive Error: {e}")

            async def receive_from_gemini():
                """Reads tool calls from Gemini and executes graph"""
                logger.info("Starting receive_from_gemini loop")
                try:
                    logger.info("Waiting for session.receive()...")
                    async for response in session.receive():
                        logger.info(f"Raw Response: {response}")
                        # Check for tool calls in the response
                        tool_calls = []
                        
                        # Logic to extract tool_calls from LiveServerMessage
                        if hasattr(response, "server_content") and response.server_content:
                            model_turn = response.server_content.model_turn
                            if model_turn and model_turn.parts:
                                for part in model_turn.parts:
                                    if part.function_call:
                                        tool_calls.append(part.function_call)
                        
                        # Check for top-level tool_call (Common in Live API)
                        if hasattr(response, "tool_call") and response.tool_call:
                            for fc in response.tool_call.function_calls:
                                tool_calls.append(fc)
                        
                        if tool_calls:
                            for tool_call in tool_calls:
                                if tool_call.name == "submit_action":
                                    logger.info("Received Action from Interpreter")
                                    # Extract arguments
                                    args = tool_call.args
                                    # Convert to Pydantic
                                    try:
                                        action = ActionSchema(**args)
                                        
                                        # Run Simulation Graph
                                        result = await sim_graph.process_action(
                                            action, executor.state, active_mission_reqs
                                        )
                                        
                                        # Send Feedback/Updates to Client
                                        update = {
                                            "type": "world_update",
                                            "state": result["world_state"].model_dump(),
                                            "feedback": result["feedback"],
                                            "validation": result["validation"]
                                        }
                                        await websocket.send_json(update)
                                        
                                        # Log to memory
                                        memory.add_interaction(
                                            input_text=action.canonical_transcript, 
                                            action=action.model_dump(), 
                                            validation=result["validation"],
                                            timestamp=executor.state.timestamp
                                        )
                                        
                                        # Send result back to Gemini (Tool Output) so it knows it succeeded?
                                        # For Live, we often just proceed. 
                                        # Send result back to Gemini (Tool Output)
                                        # Use LiveClientRealtimeInput with function_responses
                                        # Using dict for function_response to ensure compatibility
                                        await session.send(
                                            input=types.LiveClientRealtimeInput(
                                                function_responses=[
                                                    {
                                                        "name": "submit_action",
                                                        "id": tool_call.id,
                                                        "response": {"status": "success", "feedback": result["feedback"]}
                                                    }
                                                ]
                                            ), 
                                            end_of_turn=True
                                        )
                                        
                                    except Exception as e:
                                        logger.error(f"Action Execution Error: {e}")
                                        await websocket.send_json({"type": "error", "message": str(e)})

                except Exception as e:
                    logger.error(f"Gemini Receive Error: {e}")

            # Run both loops
            await asyncio.gather(receive_from_client(), receive_from_gemini())

    except Exception as e:
        logger.error(f"Session Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
        await websocket.close()
