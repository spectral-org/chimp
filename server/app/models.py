"""Pydantic models for action schemas and world state."""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum
from datetime import datetime


# =============================================================================
# Action Intent Types
# =============================================================================

class IntentType(str, Enum):
    """Valid action intents from speech interpretation."""
    BUY_ITEM = "buy_item"
    NEGOTIATE = "negotiate"
    ASK_INFO = "ask_info"
    GIVE_ITEM = "give_item"
    MOVE = "move"
    INTERACT = "interact"
    GREET = "greet"
    UNKNOWN = "unknown"


class Tense(str, Enum):
    """Grammar tense detection."""
    PRESENT = "present"
    PAST = "past"
    CONDITIONAL = "conditional"
    FUTURE = "future"


class Politeness(str, Enum):
    """Politeness level detection."""
    NEUTRAL = "neutral"
    POLITE = "polite"
    RUDE = "rude"


# =============================================================================
# Action Schema (Strict JSON from Interpreter)
# =============================================================================

class GrammarFeatures(BaseModel):
    """Grammar analysis from spoken input."""
    tense: Tense = Tense.PRESENT
    politeness: Politeness = Politeness.NEUTRAL
    required_constructs_present: list[str] = Field(default_factory=list)
    

class ActionEntities(BaseModel):
    """Entities extracted from speech."""
    item: Optional[str] = None
    quantity: Optional[int] = None
    target: Optional[str] = None  # NPC ID or object ID


class ParsedAction(BaseModel):
    """
    Strict JSON schema output from the Interpreter Agent.
    This is THE contract between audio input and world execution.
    """
    intent: IntentType = IntentType.UNKNOWN
    entities: ActionEntities = Field(default_factory=ActionEntities)
    grammar_features: GrammarFeatures = Field(default_factory=GrammarFeatures)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    canonical_transcript: str = ""
    feedback_keys: list[str] = Field(default_factory=list)
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "intent": "buy_item",
                    "entities": {"item": "apple", "quantity": 3, "target": "merchant_1"},
                    "grammar_features": {
                        "tense": "present",
                        "politeness": "polite",
                        "required_constructs_present": ["please", "would_like"]
                    },
                    "confidence": 0.95,
                    "canonical_transcript": "I would like to buy three apples, please.",
                    "feedback_keys": []
                }
            ]
        }
    }


# =============================================================================
# World State Models
# =============================================================================

class NPCState(BaseModel):
    """State of an NPC in the medieval bazaar."""
    id: str
    name: str
    role: str  # merchant, guard, villager
    position: tuple[float, float, float] = (0, 0, 0)
    mood: Literal["friendly", "neutral", "annoyed", "angry"] = "neutral"
    inventory: dict[str, int] = Field(default_factory=dict)
    patience: float = Field(ge=0.0, le=1.0, default=1.0)
    dialogue_history: list[str] = Field(default_factory=list)


class PlayerState(BaseModel):
    """State of the player."""
    position: tuple[float, float, float] = (0, 0, 0)
    inventory: dict[str, int] = Field(default_factory=dict)
    gold: int = 100
    reputation: float = Field(ge=0.0, le=1.0, default=0.5)


class MissionState(BaseModel):
    """Current mission/objective."""
    id: str
    title: str
    description: str
    grammar_requirement: str
    success_condition: str
    is_complete: bool = False
    attempts: int = 0


class WorldState(BaseModel):
    """Complete world state for the medieval bazaar."""
    timestamp: datetime = Field(default_factory=datetime.now)
    player: PlayerState = Field(default_factory=PlayerState)
    npcs: list[NPCState] = Field(default_factory=list)
    current_mission: Optional[MissionState] = None
    completed_missions: list[str] = Field(default_factory=list)
    world_time: str = "morning"  # morning, afternoon, evening, night
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "ser_json_timedelta": "iso8601",
    }


# =============================================================================
# WebSocket Message Models
# =============================================================================

class AudioChunkMessage(BaseModel):
    """Incoming audio chunk from client."""
    type: Literal["audio_chunk"] = "audio_chunk"
    data: str  # Base64 encoded audio
    end_of_turn: bool = False
    session_id: str


class TranscriptMessage(BaseModel):
    """Transcript update to client."""
    type: Literal["transcript"] = "transcript"
    text: str
    is_final: bool = False


class ActionResultMessage(BaseModel):
    """Action execution result to client."""
    type: Literal["action_result"] = "action_result"
    parsed_action: ParsedAction
    validation_passed: bool
    feedback: list[str] = Field(default_factory=list)
    world_diff: dict = Field(default_factory=dict)


class NPCAudioMessage(BaseModel):
    """NPC voice audio for client playback."""
    type: Literal["npc_audio"] = "npc_audio"
    audio_data: str  # Base64-encoded MP3
    npc_name: str
    dialogue: str
    mood: str = "neutral"


class WorldStateMessage(BaseModel):
    """World state update to client."""
    type: Literal["world_state"] = "world_state"
    state: WorldState


class ReasoningChainMessage(BaseModel):
    """Agent reasoning chain for visibility."""
    type: Literal["reasoning"] = "reasoning"
    agent: str  # planner, interpreter, verifier, executor
    step: str
    details: dict = Field(default_factory=dict)


class ErrorMessage(BaseModel):
    """Error message to client."""
    type: Literal["error"] = "error"
    message: str
    recoverable: bool = True
