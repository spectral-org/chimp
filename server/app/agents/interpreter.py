import os
import json
import asyncio
from google import genai
from google.genai import types
from app.models import ActionSchema

# Define the tool using pydantic model schema if supported, or manual declaration
# For Live API, we often define tools manually in the config.

INTERPRETER_SYSTEM_INSTRUCT = """
You are an INTERPRETER AGENT in a high-stakes simulation.
Your ONLY job is to listen to the user's spoken audio and convert it into a STRICT JSON Action.

You do NOT speak. You do NOT answer questions. You only output actions.

Your output must use the `submit_action` tool.

The user is controlling a character in a 3D world.
Possible intents: buy_item, negotiate, ask_info, give_item, move, interact.

Grammar Rules:
- "if... then..." implies conditional tense.
- "Because..." implies reasoning.
- Polite phrases: "Could you", "Please", "May I".

If the input is gibberish or silent, do nothing or output low confidence.
"""

class InterpreterAgent:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")
        
        # Hack to prevent SDK from using GOOGLE_API_KEY if it exists in the system env
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]

        self.client = genai.Client(api_key=self.api_key, http_options={"api_version": "v1alpha"})
        self.model = "gemini-2.0-flash-exp" 

    async def connect(self):
        """
        Establishes a session with Gemini Live.
        Returns the session context manager.
        """
        # We need to define the tool for the model to call
        # We can extract schema from Pydantic, but explicit is safer for now.
        
        tool_decl = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="submit_action",
                    description="Submit the interpreted user action.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "intent": types.Schema(type="STRING", enum=["buy_item", "negotiate", "ask_info", "give_item", "move", "interact"]),
                            "entities": types.Schema(
                                type="OBJECT",
                                properties={
                                    "item": types.Schema(type="STRING"),
                                    "quantity": types.Schema(type="INTEGER"),
                                    "target": types.Schema(type="STRING"),
                                }
                            ),
                            "grammar_features": types.Schema(
                                type="OBJECT",
                                properties={
                                    "tense": types.Schema(type="STRING", enum=["present", "past", "conditional"]),
                                    "politeness": types.Schema(type="STRING", enum=["neutral", "polite"]),
                                    "required_constructs_present": types.Schema(type="ARRAY", items=types.Schema(type="STRING"))
                                },
                                required=["tense", "politeness"]
                            ),
                            "confidence": types.Schema(type="NUMBER"),
                            "canonical_transcript": types.Schema(type="STRING"),
                            "feedback_keys": types.Schema(type="ARRAY", items=types.Schema(type="STRING"))
                        },
                        required=["intent", "entities", "grammar_features", "confidence", "canonical_transcript"]
                    )
                )
            ]
        )

        config = types.LiveConnectConfig(
            response_modalities=["TEXT"], 
            system_instruction=types.Content(parts=[types.Part(text=INTERPRETER_SYSTEM_INSTRUCT)]),
            tools=[tool_decl]
        )
        
        return self.client.aio.live.connect(model=self.model, config=config)

