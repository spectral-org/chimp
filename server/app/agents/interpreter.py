"""
Interpreter Agent - Real-time audio to structured JSON using Gemini Live API.

This agent is the core of the speech-to-action pipeline:
1. Receives audio chunks via WebSocket
2. Streams to Gemini Live API for transcription + interpretation
3. Outputs strict JSON action schema
"""

import json
import logging
from typing import Any
from google import genai
from google.genai import types

from app.config import config
from app.models import ParsedAction, IntentType, Tense, Politeness, GrammarFeatures, ActionEntities

logger = logging.getLogger(__name__)


INTERPRETER_SYSTEM_PROMPT = """You are a real-time speech interpreter for a medieval bazaar language learning game.

Your ONLY job is to convert spoken English into a strict JSON action schema. You must analyze:
1. INTENT: What the player wants to do (buy, sell, negotiate, ask, move, greet, etc.)
2. ENTITIES: Items, quantities, NPC targets mentioned
3. GRAMMAR: Tense, politeness level, required constructs (conditionals, because-clauses)
4. CONFIDENCE: How certain you are about the interpretation (0.0-1.0)

CRITICAL RULES:
- Output ONLY valid JSON, no explanations or markdown
- If speech is unclear, set confidence < 0.7 and add feedback_keys
- Detect politeness markers: "please", "would you", "could I", "thank you"
- Detect conditionals: "if", "would", "could", "might"
- Detect causal: "because", "since", "therefore"

JSON SCHEMA (output EXACTLY this structure):
{
  "intent": "buy_item|negotiate|ask_info|give_item|move|interact|greet|unknown",
  "entities": {
    "item": "string or null",
    "quantity": "number or null",
    "target": "npc_id or null"
  },
  "grammar_features": {
    "tense": "present|past|conditional|future",
    "politeness": "neutral|polite|rude",
    "required_constructs_present": ["conditional_if", "because_reason", "please", "would_like", etc.]
  },
  "confidence": 0.0-1.0,
  "canonical_transcript": "the exact words spoken",
  "feedback_keys": ["missing_conditional", "wrong_tense", "unclear_intent", "be_more_polite", etc.]
}

EXAMPLES:
Input: "I would like to buy three apples please"
Output: {"intent":"buy_item","entities":{"item":"apple","quantity":3,"target":null},"grammar_features":{"tense":"conditional","politeness":"polite","required_constructs_present":["would_like","please"]},"confidence":0.95,"canonical_transcript":"I would like to buy three apples please","feedback_keys":[]}

Input: "Give me bread"
Output: {"intent":"buy_item","entities":{"item":"bread","quantity":1,"target":null},"grammar_features":{"tense":"present","politeness":"rude","required_constructs_present":[]},"confidence":0.85,"canonical_transcript":"Give me bread","feedback_keys":["be_more_polite"]}

Input: "If you lower the price I will buy two"
Output: {"intent":"negotiate","entities":{"item":null,"quantity":2,"target":null},"grammar_features":{"tense":"conditional","politeness":"neutral","required_constructs_present":["conditional_if"]},"confidence":0.9,"canonical_transcript":"If you lower the price I will buy two","feedback_keys":[]}
"""


def parse_json_response(text: str) -> ParsedAction:
    """Parse Gemini response into ParsedAction, handling malformed JSON."""
    try:
        # Try to extract JSON from response
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        data = json.loads(text)
        
        # Map to Pydantic model
        return ParsedAction(
            intent=IntentType(data.get("intent", "unknown")),
            entities=ActionEntities(
                item=data.get("entities", {}).get("item"),
                quantity=data.get("entities", {}).get("quantity"),
                target=data.get("entities", {}).get("target"),
            ),
            grammar_features=GrammarFeatures(
                tense=Tense(data.get("grammar_features", {}).get("tense", "present")),
                politeness=Politeness(data.get("grammar_features", {}).get("politeness", "neutral")),
                required_constructs_present=data.get("grammar_features", {}).get("required_constructs_present", []),
            ),
            confidence=float(data.get("confidence", 0.5)),
            canonical_transcript=data.get("canonical_transcript", ""),
            feedback_keys=data.get("feedback_keys", []),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Failed to parse JSON response: {e}\nText: {text}")
        return ParsedAction(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            canonical_transcript=text,
            feedback_keys=["json_parse_error", "retry_needed"],
        )


async def interpret_text(transcript: str) -> ParsedAction:
    """
    Interpret a text transcript using Gemini text model.
    Used as fallback when Live API returns text.
    """
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    response = await client.aio.models.generate_content(
        model=config.GEMINI_TEXT_MODEL,
        contents=f"Interpret this speech and output JSON only: {transcript}",
        config=types.GenerateContentConfig(
            system_instruction=INTERPRETER_SYSTEM_PROMPT,
            temperature=0.1,  # Low temperature for consistent JSON
        )
    )
    
    if response.text:
        return parse_json_response(response.text)
    
    return ParsedAction(
        intent=IntentType.UNKNOWN,
        confidence=0.0,
        feedback_keys=["no_response"],
    )


async def interpret_audio_stream(audio_data: bytes) -> tuple[str, ParsedAction]:
    """
    Stream audio to Gemini Live API for real-time interpretation.
    Returns (transcript, parsed_action).
    
    Note: Gemini Live API with native audio dialog model.
    """
    import base64
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    try:
        # Use the text model with audio for now (more reliable)
        # In production, usegemini-2.5-flash-native-audio-dialog with Live API
        logger.info(f"Interpreting audio chunk of {len(audio_data)} bytes")
        
        # For audio input, we need to use the multimodal approach
        # The audio should be base64 encoded
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        response = await client.aio.models.generate_content(
            model=config.GEMINI_TEXT_MODEL,
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type="audio/wav",
                                data=audio_data
                            )
                        ),
                        types.Part(text="Transcribe and interpret this audio. Output JSON only.")
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=INTERPRETER_SYSTEM_PROMPT,
                temperature=0.1,
            )
        )
        
        if response.text:
            parsed = parse_json_response(response.text)
            return parsed.canonical_transcript, parsed
            
    except Exception as e:
        logger.error(f"Audio interpretation failed: {e}")
    
    return "", ParsedAction(
        intent=IntentType.UNKNOWN,
        confidence=0.0,
        feedback_keys=["audio_processing_error"],
    )


class InterpreterAgent:
    """
    Stateful interpreter agent for managing audio sessions.
    Maintains context across audio chunks within a session.
    """
    
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.session_contexts: dict[str, list[str]] = {}
    
    async def process_transcript(self, session_id: str, transcript: str) -> ParsedAction:
        """Process a text transcript within a session context."""
        # Add to session context
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = []
        self.session_contexts[session_id].append(transcript)
        
        # Keep last 5 turns for context
        context = self.session_contexts[session_id][-5:]
        
        # Build context-aware prompt
        context_str = "\n".join([f"- {t}" for t in context[:-1]]) if len(context) > 1 else ""
        prompt = f"""Previous context:
{context_str}

Current speech to interpret: {transcript}

Output JSON only:"""
        
        response = await self.client.aio.models.generate_content(
            model=config.GEMINI_TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=INTERPRETER_SYSTEM_PROMPT,
                temperature=0.1,
            )
        )
        
        if response.text:
            return parse_json_response(response.text)
        
        return ParsedAction(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            canonical_transcript=transcript,
            feedback_keys=["no_response"],
        )
    
    def clear_session(self, session_id: str):
        """Clear session context."""
        if session_id in self.session_contexts:
            del self.session_contexts[session_id]


# Global interpreter instance
interpreter_agent = InterpreterAgent()
