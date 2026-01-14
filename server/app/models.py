from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class InteractionEntities(BaseModel):
    item: Optional[str] = Field(None, description="The item involved in the interaction")
    quantity: Optional[int] = Field(None, description="The quantity of the item")
    target: Optional[str] = Field(None, description="The target NPC or object ID")

class GrammarFeatures(BaseModel):
    tense: Literal["present", "past", "conditional"] = Field(..., description="The grammatical tense used")
    politeness: Literal["neutral", "polite"] = Field(..., description="The politeness level")
    required_constructs_present: List[str] = Field(default_factory=list, description="List of required grammatical constructs found")

class ActionSchema(BaseModel):
    intent: Literal["buy_item", "negotiate", "ask_info", "give_item", "move", "interact"] = Field(..., description="The projected intent of the user")
    entities: InteractionEntities = Field(..., description="Entities extracted from the speech")
    grammar_features: GrammarFeatures = Field(..., description="Grammatical features analyzed")
    confidence: float = Field(..., description="Confidence score of the interpretation (0.0 to 1.0)")
    canonical_transcript: str = Field(..., description="The cleaned, canonical transcript of the user's speech")
    feedback_keys: List[str] = Field(default_factory=list, description="Keys for feedback messages based on errors")

class WorldState(BaseModel):
    # Placeholder for World State
    timestamp: float
    entities: dict
    mission_state: dict

class Mission(BaseModel):
    id: str
    description: str
    requirements: dict
