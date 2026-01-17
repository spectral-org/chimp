"""
Chimp Server - FastAPI Main Application

WebSocket-based real-time communication for the agentic language simulation.
Handles audio streaming, transcript processing, and world state updates.
"""

import json
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.config import config
from app.models import (
    WorldState, MissionState, ParsedAction,
    TranscriptMessage, ActionResultMessage, WorldStateMessage,
    ReasoningChainMessage, ErrorMessage, NPCAudioMessage
)
from app.memory import session_store
from app.agents.graph import process_speech
from app.agents.planner import planner_agent
from app.services.tts import synthesize_merchant_dialogue

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("🚀 Chimp Server starting up...")
    logger.info(f"   Debug mode: {config.DEBUG}")
    logger.info(f"   Gemini API configured: {'Yes' if config.GEMINI_API_KEY else 'No'}")
    yield
    logger.info("👋 Chimp Server shutting down...")
    session_store.cleanup_old_sessions(max_age_hours=0)


app = FastAPI(
    title="Chimp - Agentic Language Simulation",
    description="Real-time speech-controlled medieval bazaar using Gemini 3 and LangGraph",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# REST Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Health check."""
    return {
        "status": "ok",
        "service": "chimp-server",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session state."""
    world = session_store.get_world_state(session_id)
    mission = session_store.get_mission(session_id)
    
    return {
        "session_id": session_id,
        "world_state": world.model_dump(),
        "mission": mission.model_dump() if mission else None,
    }


@app.post("/api/session")
async def create_session():
    """Create a new session."""
    session_id = str(uuid.uuid4())
    session = session_store.get_or_create_session(session_id)
    
    # Generate initial mission
    mission = await planner_agent.generate_initial_mission(session_id)
    session_store.update_mission(session_id, mission)
    
    return {
        "session_id": session_id,
        "world_state": session["world_state"].model_dump(),
        "mission": mission.model_dump(),
    }


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    session_store.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


# =============================================================================
# WebSocket Handler
# =============================================================================

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_json(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)


manager = ConnectionManager()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time audio/text communication.
    
    Incoming messages:
    - {"type": "transcript", "text": "...", "is_final": true/false}
    - {"type": "audio_chunk", "data": "base64...", "end_of_turn": true/false}
    - {"type": "ping"}
    
    Outgoing messages:
    - {"type": "transcript", "text": "...", "is_final": true/false}
    - {"type": "action_result", ...}
    - {"type": "world_state", ...}
    - {"type": "reasoning", ...}
    - {"type": "error", ...}
    """
    await manager.connect(websocket, session_id)
    
    # Ensure session exists
    session = session_store.get_or_create_session(session_id)
    
    # Send initial mission if not set
    mission = session_store.get_mission(session_id)
    if not mission:
        mission = await planner_agent.generate_initial_mission(session_id)
        session_store.update_mission(session_id, mission)
    
    # Send initial world state
    world = session_store.get_world_state(session_id)
    await manager.send_json(session_id, WorldStateMessage(
        type="world_state",
        state=world,
    ).model_dump(mode='json'))
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "ping":
                await manager.send_json(session_id, {"type": "pong"})
                continue
            
            elif msg_type == "transcript":
                # Process text transcript through agent graph
                transcript = data.get("text", "")
                is_final = data.get("is_final", True)
                
                if not transcript.strip():
                    continue
                
                logger.info(f"[{session_id}] Received transcript: {transcript}")
                
                # Echo transcript back
                await manager.send_json(session_id, TranscriptMessage(
                    type="transcript",
                    text=transcript,
                    is_final=is_final,
                ).model_dump(mode='json'))
                
                if is_final:
                    # Get current state
                    world = session_store.get_world_state(session_id)
                    mission = session_store.get_mission(session_id)
                    
                    # Process through agent graph
                    result = await process_speech(
                        session_id=session_id,
                        transcript=transcript,
                        world_state=world,
                        mission=mission,
                    )
                    
                    # Send reasoning chain (for visibility)
                    for step in result.get("reasoning_chain", []):
                        await manager.send_json(session_id, ReasoningChainMessage(
                            type="reasoning",
                            agent=step.get("agent", "unknown"),
                            step=step.get("step", ""),
                            details=step,
                        ).model_dump(mode='json'))
                    
                    # Send action result
                    if result.get("parsed_action"):
                        parsed = ParsedAction(**result["parsed_action"])
                        verification = result.get("verification_result", {})
                        
                        await manager.send_json(session_id, ActionResultMessage(
                            type="action_result",
                            parsed_action=parsed,
                            validation_passed=verification.get("is_valid", False),
                            feedback=result.get("feedback", []),
                            world_diff=result.get("world_diff", {}),
                        ).model_dump(mode='json'))
                        
                        # Generate and send TTS audio for NPC dialogue
                        world_diff = result.get("world_diff", {})
                        npc_dialogue = world_diff.get("npc_dialogue")
                        if npc_dialogue:
                            # Get NPC mood from world state
                            npc_mood = "neutral"
                            if result.get("world_state"):
                                npcs = result["world_state"].get("npcs", [])
                                target = parsed.entities.target
                                for npc in npcs:
                                    if npc.get("id") == target:
                                        npc_mood = npc.get("mood", "neutral")
                                        break
                            
                            # Synthesize speech
                            audio_data = await synthesize_merchant_dialogue(
                                dialogue=npc_dialogue,
                                npc_name="Merchant",
                                mood=npc_mood,
                            )
                            
                            if audio_data:
                                await manager.send_json(session_id, NPCAudioMessage(
                                    type="npc_audio",
                                    audio_data=audio_data,
                                    npc_name="Merchant",
                                    dialogue=npc_dialogue,
                                    mood=npc_mood,
                                ).model_dump(mode='json'))
                    
                    # Update and send world state
                    if result.get("world_state"):
                        new_world = WorldState(**result["world_state"])
                        session_store.update_world_state(session_id, new_world)
                        
                        await manager.send_json(session_id, WorldStateMessage(
                            type="world_state",
                            state=new_world,
                        ).model_dump(mode='json'))
                    
                    # Update mission if changed
                    if result.get("mission"):
                        new_mission = MissionState(**result["mission"])
                        session_store.update_mission(session_id, new_mission)
            
            elif msg_type == "audio_chunk":
                # TODO: Implement Gemini Live API streaming
                # For now, we expect transcripts from the frontend
                logger.info(f"[{session_id}] Received audio chunk (not implemented yet)")
                await manager.send_json(session_id, ErrorMessage(
                    type="error",
                    message="Audio streaming not implemented yet. Please send transcript.",
                    recoverable=True,
                ).model_dump(mode='json'))
            
            else:
                logger.warning(f"Unknown message type: {msg_type}")
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
        await manager.send_json(session_id, ErrorMessage(
            type="error",
            message=str(e),
            recoverable=False,
        ).model_dump(mode='json'))
        manager.disconnect(session_id)


# =============================================================================
# Debug Endpoints (Development Only)
# =============================================================================

if config.DEBUG:
    @app.post("/api/debug/process")
    async def debug_process(session_id: str, transcript: str):
        """Debug endpoint to test transcript processing without WebSocket."""
        world = session_store.get_world_state(session_id)
        mission = session_store.get_mission(session_id)
        
        result = await process_speech(
            session_id=session_id,
            transcript=transcript,
            world_state=world,
            mission=mission,
        )
        
        # Update state
        if result.get("world_state"):
            new_world = WorldState(**result["world_state"])
            session_store.update_world_state(session_id, new_world)
        
        if result.get("mission"):
            new_mission = MissionState(**result["mission"])
            session_store.update_mission(session_id, new_mission)
        
        return result
