import os
import json
from google import genai
from google.genai import types
from app.models import Mission

PLANNER_SYSTEM_INSTRUCT = """
You are the PLANNER AGENT for an Agentic Language Simulation.
Your goal is to generate dynamic missions for the user based on their history and current difficulty level.

Missions should be challenging but achievable.
You must output a JSON object representing the `Mission`.

Difficulty Levels:
1. Basic: Simple transactions, clear intent.
2. Intermediate: Negotiations, polite phrasing required.
3. Advanced: Causal reasoning, conditional logic, complex multi-step goals.

Output JSON Schema:
{
  "id": "mission_id",
  "description": "Short description",
  "requirements": {
    "intent": "required intent",
    "grammar": ["required grammar constructs"]
  }
}
"""

class PlannerAgent:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key, http_options={"api_version": "v1alpha"})
        self.model = "gemini-2.0-flash-exp"

    async def generate_mission(self, history: list, difficulty: str) -> Mission:
        prompt = f"History: {history}\nCurrent Difficulty: {difficulty}\nGenerate a new mission."
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=PLANNER_SYSTEM_INSTRUCT,
                response_mime_type="application/json",
                response_schema=Mission
            )
        )
        
        # Parse the response to Mission model
        mission_data = json.loads(response.text)
        return Mission(**mission_data)
