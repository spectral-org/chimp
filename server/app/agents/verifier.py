import os
import json
from google import genai
from google.genai import types
from app.models import ActionSchema, WorldState

VERIFIER_SYSTEM_INSTRUCT = """
You are the VERIFIER / CRITIC AGENT.
Your job is to validate a user's proposed action against the World State and Grammar Rules.

Input:
- Proposed Action (JSON)
- World State (JSON)
- Mission Requirements (JSON)

Output:
- JSON with `valid` (bool) and `reason` (string).

Rules:
1. If the action contradicts the world state (e.g. buying item not in shop), it is INVALID.
2. If the action misses required grammar (e.g. not polite when required), it is INVALID.
3. If the intent is unclear or low confidence, it is INVALID.

Output JSON Schema:
{
  "valid": boolean,
  "reason": "explanation of failure",
  "suggested_correction": "optional hint"
}
"""

class VerifierAgent:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key, http_options={"api_version": "v1alpha"})
        self.model = "gemini-2.0-flash-exp"

    async def verify_action(self, action: ActionSchema, world_state: WorldState, mission_reqs: dict) -> dict:
        prompt = f"""
        Proposed Action: {action.model_dump_json()}
        World State: {world_state.model_dump_json()}
        Mission Requirements: {json.dumps(mission_reqs)}
        """
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=VERIFIER_SYSTEM_INSTRUCT,
                response_mime_type="application/json"
            )
        )
        
        return json.loads(response.text)
