"""
Session-based memory store for player state persistence.

Manages:
- Player session state
- World state per session
- Mission progress
- Interaction history
"""

import logging
from datetime import datetime
from typing import Optional
from copy import deepcopy

from app.models import WorldState, PlayerState, NPCState, MissionState

logger = logging.getLogger(__name__)


def create_initial_world() -> WorldState:
    """Create the initial medieval bazaar world state."""
    return WorldState(
        timestamp=datetime.now(),
        player=PlayerState(
            position=(0, 0, 0),
            inventory={},
            gold=100,
            reputation=0.5,
        ),
        npcs=[
            NPCState(
                id="merchant_apple",
                name="Gregor the Apple Merchant",
                role="merchant",
                position=(5, 0, 0),
                mood="friendly",
                inventory={"apple": 50, "pear": 30},
                patience=1.0,
                dialogue_history=[],
            ),
            NPCState(
                id="merchant_bread",
                name="Martha the Baker",
                role="merchant",
                position=(-5, 0, 3),
                mood="neutral",
                inventory={"bread": 40, "pastry": 20},
                patience=0.8,
                dialogue_history=[],
            ),
            NPCState(
                id="merchant_meat",
                name="Boris the Butcher",
                role="merchant",
                position=(0, 0, -5),
                mood="neutral",
                inventory={"meat": 25, "fish": 15, "cheese": 30},
                patience=0.6,
                dialogue_history=[],
            ),
            NPCState(
                id="guard_1",
                name="Sir Roland",
                role="guard",
                position=(10, 0, 10),
                mood="neutral",
                inventory={},
                patience=0.5,
                dialogue_history=[],
            ),
        ],
        current_mission=None,
        completed_missions=[],
        world_time="morning",
    )


class SessionStore:
    """
    In-memory session store for development.
    In production, replace with Redis or database.
    """
    
    def __init__(self):
        self._sessions: dict[str, dict] = {}
    
    def get_or_create_session(self, session_id: str) -> dict:
        """Get existing session or create new one."""
        if session_id not in self._sessions:
            world = create_initial_world()
            self._sessions[session_id] = {
                "session_id": session_id,
                "world_state": world,
                "mission": None,
                "created_at": datetime.now(),
                "last_active": datetime.now(),
                "interaction_count": 0,
            }
            logger.info(f"Created new session: {session_id}")
        
        session = self._sessions[session_id]
        session["last_active"] = datetime.now()
        return session
    
    def get_world_state(self, session_id: str) -> WorldState:
        """Get world state for a session."""
        session = self.get_or_create_session(session_id)
        return deepcopy(session["world_state"])
    
    def update_world_state(self, session_id: str, world_state: WorldState):
        """Update world state for a session."""
        session = self.get_or_create_session(session_id)
        session["world_state"] = world_state
        session["interaction_count"] += 1
    
    def get_mission(self, session_id: str) -> Optional[MissionState]:
        """Get current mission for a session."""
        session = self.get_or_create_session(session_id)
        return session.get("mission")
    
    def update_mission(self, session_id: str, mission: Optional[MissionState]):
        """Update current mission for a session."""
        session = self.get_or_create_session(session_id)
        session["mission"] = mission
    
    def delete_session(self, session_id: str):
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
    
    def get_all_sessions(self) -> list[str]:
        """Get all active session IDs."""
        return list(self._sessions.keys())
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        now = datetime.now()
        to_delete = []
        
        for session_id, session in self._sessions.items():
            age = (now - session["last_active"]).total_seconds() / 3600
            if age > max_age_hours:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            self.delete_session(session_id)
        
        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old sessions")


# Global session store instance
session_store = SessionStore()
