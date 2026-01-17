"""
Planner Agent - Long-context reasoning for mission generation and adaptation.

This agent handles:
1. Generating multi-step missions based on player history
2. Adjusting difficulty dynamically
3. Maintaining mission graphs across turns
4. Writing to long-term memory
"""

import logging
from typing import Optional
from google import genai
from google.genai import types

from app.config import config
from app.models import MissionState, WorldState, ParsedAction

logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """You are the Planner Agent for a medieval bazaar language learning game.

Your responsibilities:
1. Generate missions that teach English grammar through gameplay
2. Adapt difficulty based on player performance
3. Create engaging narrative scenarios
4. Track player progress and weaknesses

MISSION TYPES:
1. TRANSACTION: Practice quantity + politeness ("I would like to buy 3 apples, please")
2. NEGOTIATION: Practice conditionals ("If you lower the price, I will buy two")
3. CAUSAL REASONING: Practice because/if-then ("I need this because...")

OUTPUT FORMAT (JSON):
{
  "mission": {
    "id": "unique_id",
    "title": "Mission Title",
    "description": "What the player must do",
    "grammar_requirement": "specific grammar to use",
    "success_condition": "how to complete",
    "npc_behavior": "how NPC should react",
    "hints": ["hint1", "hint2"]
  },
  "reasoning": "why this mission was chosen"
}

Consider player history when generating missions:
- If they struggle with politeness, create missions requiring polite forms
- If they've mastered basic transactions, introduce negotiations
- Gradually increase complexity
"""


class PlannerAgent:
    """
    Long-context planner for mission generation and adaptation.
    Uses Gemini's extended context window for player history.
    """
    
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.player_history: dict[str, list[dict]] = {}
    
    async def generate_initial_mission(self, session_id: str) -> MissionState:
        """Generate the first mission for a new player."""
        return MissionState(
            id="mission_1_greeting",
            title="Greet the Merchant",
            description="Approach the apple merchant and greet them politely. Try saying 'Good morning' or 'Hello, how are you today?'",
            grammar_requirement="polite greeting",
            success_condition="Polite greeting detected with friendly tone",
            is_complete=False,
            attempts=0,
        )
    
    async def generate_next_mission(
        self,
        session_id: str,
        world_state: WorldState,
        last_action: Optional[ParsedAction] = None,
    ) -> MissionState:
        """Generate the next mission based on player progress."""
        # Get player history
        history = self.player_history.get(session_id, [])
        completed = world_state.completed_missions
        
        # Build context for Gemini
        history_str = "\n".join([
            f"- Action: {h.get('action', 'unknown')}, Success: {h.get('success', False)}, Feedback: {h.get('feedback', [])}"
            for h in history[-10:]  # Last 10 actions
        ])
        
        prompt = f"""Player session: {session_id}
Completed missions: {completed}
Recent action history:
{history_str}

Current world state: {world_state.world_time}, Player gold: {world_state.player.gold}

Generate the next appropriate mission. Consider what grammar the player needs to practice.
Output JSON only."""

        try:
            response = await self.client.aio.models.generate_content(
                model=config.GEMINI_TEXT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=PLANNER_SYSTEM_PROMPT,
                    temperature=0.7,  # Some creativity for missions
                )
            )
            
            if response.text:
                import json
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                
                data = json.loads(text)
                mission_data = data.get("mission", data)
                
                return MissionState(
                    id=mission_data.get("id", f"mission_{len(completed) + 1}"),
                    title=mission_data.get("title", "New Mission"),
                    description=mission_data.get("description", "Complete the objective"),
                    grammar_requirement=mission_data.get("grammar_requirement", "any"),
                    success_condition=mission_data.get("success_condition", "complete action"),
                    is_complete=False,
                    attempts=0,
                )
        except Exception as e:
            logger.error(f"Mission generation failed: {e}")
        
        # Fallback missions
        fallback_missions = [
            MissionState(
                id="mission_2_transaction",
                title="Buy Some Apples",
                description="Purchase apples from the merchant. Remember to be polite and specify the quantity. Try: 'I would like to buy three apples, please.'",
                grammar_requirement="quantity + politeness (please, would like)",
                success_condition="Buy item with polite form and quantity specified",
            ),
            MissionState(
                id="mission_3_negotiate",
                title="Negotiate a Better Price",
                description="The merchant's prices seem high. Try to negotiate using conditional language. Example: 'If you give me a discount, I will buy more.'",
                grammar_requirement="conditional clause (if...then, would...if)",
                success_condition="Use conditional to negotiate",
            ),
            MissionState(
                id="mission_4_causal",
                title="Explain Your Need",
                description="Tell the merchant why you need bread. Use 'because' or 'since' to explain. Example: 'I need bread because my family is hungry.'",
                grammar_requirement="causal connector (because, since, therefore)",
                success_condition="Use causal reasoning in speech",
            ),
        ]
        
        # Return next uncompleted mission
        for mission in fallback_missions:
            if mission.id not in completed:
                return mission
        
        # All done - generate random challenge
        return MissionState(
            id=f"challenge_{len(completed)}",
            title="Free Exploration",
            description="Explore the bazaar and interact with any NPC. Practice your English!",
            grammar_requirement="any",
            success_condition="successful interaction",
        )
    
    def record_action(
        self,
        session_id: str,
        action: ParsedAction,
        success: bool,
        feedback: list[str],
    ):
        """Record player action for history tracking."""
        if session_id not in self.player_history:
            self.player_history[session_id] = []
        
        self.player_history[session_id].append({
            "action": action.intent.value,
            "transcript": action.canonical_transcript,
            "confidence": action.confidence,
            "success": success,
            "feedback": feedback,
            "grammar": action.grammar_features.model_dump(),
        })
        
        # Keep last 50 actions
        if len(self.player_history[session_id]) > 50:
            self.player_history[session_id] = self.player_history[session_id][-50:]


# Global planner instance
planner_agent = PlannerAgent()
