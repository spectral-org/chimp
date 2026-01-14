from typing import List, Dict, Any
from app.models import Mission

class MemoryStore:
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.missions: List[Mission] = []
        self.player_profile: Dict[str, Any] = {
            "grammar_weaknesses": [],
            "error_patterns": {},
            "relationship_state": {} # NPC ID -> relationship score
        }

    def add_interaction(self, input_text: str, action: Dict, validation: Dict, timestamp: float):
        """
        Logs a full turn of interaction.
        """
        entry = {
            "timestamp": timestamp,
            "input": input_text,
            "action": action,
            "validation": validation
        }
        self.history.append(entry)
        
        # Simple heuristic updates
        if not validation.get("valid", True):
            reason = validation.get("reason", "unknown")
            self.player_profile["error_patterns"][reason] = self.player_profile["error_patterns"].get(reason, 0) + 1

    def get_recent_history(self, limit: int = 5) -> List[Dict]:
        return self.history[-limit:]

    def get_profile_summary(self) -> str:
        return f"Errors: {self.player_profile['error_patterns']}, Relations: {self.player_profile['relationship_state']}"
