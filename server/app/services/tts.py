"""
Text-to-Speech service using Gemini TTS.

Uses Gemini 2.5 Flash TTS model for NPC voice responses
with mood-based voice control using natural language prompts.
"""

import base64
import io
import wave
import logging
from typing import Optional

from google import genai
from app.config import config

logger = logging.getLogger(__name__)

# Initialize Gemini client
client = genai.Client(api_key=config.GEMINI_API_KEY)

# Mood-based voice prompts for Gemini TTS
MOOD_PROMPTS = {
    "friendly": "Speak in a warm, welcoming British merchant voice. Be cheerful and helpful.",
    "neutral": "Speak in a calm, professional British merchant voice. Be polite but businesslike.",
    "annoyed": "Speak in a slightly impatient British merchant voice. Sound a bit frustrated.",
    "angry": "Speak in a stern, gruff British merchant voice. Sound irritated and firm.",
}

# TTS model - Gemini 2.5 Flash TTS
TTS_MODEL = "gemini-2.5-flash-preview-tts"


def pcm16_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """Convert raw PCM16 audio to WAV format."""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)  # Mono
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_data)
    buffer.seek(0)
    return buffer.read()


async def synthesize_speech(
    text: str,
    mood: str = "neutral",
) -> Optional[str]:
    """
    Synthesize speech from text using Gemini TTS.
    
    Args:
        text: The text to speak
        mood: NPC mood (friendly, neutral, annoyed, angry)
    
    Returns:
        Base64-encoded WAV audio data, or None on error
    """
    try:
        # Get mood prompt
        mood_prompt = MOOD_PROMPTS.get(mood, MOOD_PROMPTS["neutral"])
        
        # Build the prompt with mood instruction
        full_prompt = f"{mood_prompt}\n\nSay this: \"{text}\""
        
        # Generate TTS audio
        response = client.models.generate_content(
            model=TTS_MODEL,
            contents=full_prompt,
            config={
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": "Kore"  # One of the available voices
                        }
                    }
                }
            }
        )
        
        # Extract audio data
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    audio_data = part.inline_data.data
                    mime_type = part.inline_data.mime_type
                    
                    # Convert PCM16 to WAV if needed
                    if "pcm" in mime_type.lower():
                        wav_data = pcm16_to_wav(audio_data)
                        audio_b64 = base64.b64encode(wav_data).decode("utf-8")
                    else:
                        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                    
                    logger.info(f"[TTS] Generated audio for mood={mood}, size={len(audio_data)} bytes")
                    return audio_b64
        
        logger.warning("[TTS] No audio data in response")
        return None
        
    except Exception as e:
        logger.error(f"[TTS] Error synthesizing speech: {e}")
        return None


async def synthesize_merchant_dialogue(
    dialogue: str,
    npc_name: str = "Merchant",
    mood: str = "neutral",
) -> Optional[str]:
    """
    Synthesize merchant dialogue with appropriate tone.
    
    Args:
        dialogue: What the merchant says
        npc_name: Name of the NPC (for future voice selection)
        mood: NPC mood
    
    Returns:
        Base64-encoded WAV audio data
    """
    return await synthesize_speech(dialogue, mood=mood)
