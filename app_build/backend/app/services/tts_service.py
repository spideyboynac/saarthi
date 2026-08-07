import os
import base64
import logging
import httpx

logger = logging.getLogger("nyaya-dhwani.tts")

class TTSService:
    """
    Text-to-Speech Audio Generation Service using ElevenLabs.
    
    Receives generated text (Hindi) from the LLM and converts it to audio bytes.
    """
    
    def generate_tts_audio(self, text: str) -> str:
        """
        Converts text to speech using ElevenLabs API and returns Base64 encoded audio string.
        """
        if not text or not text.strip():
            logger.warning("[TTS] Empty text provided for TTS, skipping.")
            return ""
            
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            logger.error("[TTS] ELEVENLABS_API_KEY environment variable not set.")
            return ""
            
        logger.info(f"[TTS] Synthesizing {len(text)} characters to speech via ElevenLabs...")
        
        # We use the generic pre-trained voice "Rachel" for example, but any voice ID can be used
        voice_id = "21m00Tcm4TlvDq8ikWAM" 
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            
            audio_bytes = response.content
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            logger.info(f"[TTS] Successfully generated audio: {len(audio_bytes)} bytes")
            return audio_b64
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[TTS] ElevenLabs API returned status {e.response.status_code}: {e.response.text}")
            return ""
        except Exception as e:
            logger.error(f"[TTS] ElevenLabs API request failed: {e}")
            return ""

tts_service = TTSService()
