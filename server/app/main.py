import os
import asyncio
import json
import logging
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

from app.models import ActionSchema, WorldState
from app.agents.interpreter import InterpreterAgent
from app.agents.verifier import VerifierAgent
from app.agents.planner import PlannerAgent
from app.world.executor import WorldExecutor
from app.memory import MemoryStore
from app.graph import SimulationGraph

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.websocket("/ws/simulation")
async def simulation_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Initialize Components
    memory = MemoryStore()
    executor = WorldExecutor()
    verifier = VerifierAgent()
    planner = PlannerAgent()
    interpreter = InterpreterAgent()
    
    sim_graph = SimulationGraph(verifier, executor, planner, memory)

    # Temporary Mission Logic
    active_mission_reqs = {"intent": "buy_item", "grammar": ["polite"]} 
    
    try:
        # Connect to Gemini Live
        async with await interpreter.connect() as session:
            
            async def receive_from_client():
                """Reads audio/messages from client and sends to Gemini"""
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            # Forward audio bytes to Gemini Live
                            # Note: Google GenAI SDK method to send audio
                            await session.send(input=data["bytes"], end_of_turn=False)
                        elif "text" in data:
                            # Might be control messages or text input fallback
                             await session.send(input=data["text"], end_of_turn=True)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.error(f"Client Receive Error: {e}")

            async def receive_from_gemini():
                """Reads tool calls from Gemini and executes graph"""
                try:
                    async for response in session.receive():
                        # Check for tool calls
                        # This structure depends on the exact GenAI SDK version response format
                        # Assuming we get tool calls in the server events
                        
                        tool_calls = response.tool_calls
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
                                        await session.send(input=types.ToolResponse(
                                            name="submit_action",
                                            id=tool_call.id,
                                            content={"status": "success", "feedback": result["feedback"]}
                                        ))
                                        
                                    except Exception as e:
                                        logger.error(f"Action Execution Error: {e}")
                                        await websocket.send_json({"type": "error", "message": str(e)})

                except Exception as e:
                    logger.error(f"Gemini Receive Error: {e}")

            # Run both loops
            await asyncio.gather(receive_from_client(), receive_from_gemini())

    except Exception as e:
        logger.error(f"Session Error: {e}")
        await websocket.close()
