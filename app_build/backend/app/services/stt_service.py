import base64
import os
import logging
import httpx

logger = logging.getLogger("nyaya-dhwani.stt")

class STTService:
    """
    Speech-to-Text Audio Decoder & Transcription Service using Deepgram.
    
    Receives Base64-encoded audio bytes from the WebSocket endpoint,
    decodes them, and produces a text transcription via Deepgram REST API.
    """

    def decode_audio_b64(self, audio_b64: str) -> bytes:
        """
        Decodes a Base64 audio string into raw audio bytes.
        Handles both plain Base64 and data-URI prefixed strings
        (e.g., 'data:audio/webm;codecs=opus;base64,...').
        """
        if "," in audio_b64:
            # Strip the data URI prefix: 'data:audio/webm;codecs=opus;base64,<payload>'
            audio_b64 = audio_b64.split(",", 1)[1]
        
        try:
            audio_bytes = base64.b64decode(audio_b64)
            logger.info(f"[STT] Decoded audio: {len(audio_bytes)} bytes")
            return audio_bytes
        except Exception as e:
            logger.error(f"[STT] Failed to decode Base64 audio: {e}")
            raise ValueError(f"Invalid Base64 audio data: {e}")

    def transcribe_audio_deepgram(self, audio_bytes: bytes, content_type: str = "audio/wav", language: str = "en-IN") -> str:
        """
        Transcribes raw audio bytes into text using the Deepgram REST API.
        """
        byte_count = len(audio_bytes)
        
        if byte_count < 100:
            logger.warning(f"[STT] Audio payload too small ({byte_count} bytes), likely empty recording")
            return "[STT: Audio too short — please speak clearly and try again]"
        
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            logger.error("[STT] DEEPGRAM_API_KEY environment variable not set.")
            return "[STT: Deepgram API key missing]"
        
        logger.info(f"[STT] Transcribing {byte_count} bytes using Deepgram (Language: {language})...")
        
        url = f"https://api.deepgram.com/v1/listen?model=nova-2&language={language}"
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": content_type
        }

        try:
            print(f"    [STT] Sending {byte_count} bytes to Deepgram API (timeout=10s)...")
            response = httpx.post(url, headers=headers, content=audio_bytes, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Extract transcription from Deepgram response
            transcription = data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
            
            if not transcription:
                logger.warning(f"[STT] Deepgram returned empty transcription. Raw response: {data}")
                return "[STT: Could not understand audio]"
            
            logger.info(f"[STT] Transcription result: {transcription[:80]}...")
            return transcription
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[STT] Deepgram API returned status {e.response.status_code}: {e.response.text}")
            raise RuntimeError(f"STT Deepgram API Error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"[STT] Deepgram API request failed: {e}")
            raise RuntimeError(f"STT Deepgram request failed: {e}")

    def process_audio_b64(self, audio_b64: str) -> str:
        """
        Full pipeline: decode Base64 → raw bytes → transcription text.
        Single entry point called by the WebSocket handler.
        """
        audio_bytes = self.decode_audio_b64(audio_b64)
        return self.transcribe_audio_deepgram(audio_bytes)

stt_service = STTService()
