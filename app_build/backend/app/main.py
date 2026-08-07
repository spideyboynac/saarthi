import os
from dotenv import load_dotenv

# CRITICAL FIX: Load environment variables BEFORE anything else initializes
load_dotenv() 

import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.twilio_routes import router as twilio_router
from app.api.query_routes import router as query_router
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service
from app.services.action_handler import action_handler_engine

logger = logging.getLogger("nyaya-dhwani")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs"
)

# Configure CORS for SPA React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST Routers
app.include_router(twilio_router, prefix=settings.API_PREFIX)
app.include_router(query_router, prefix=settings.API_PREFIX)

# ============================================================
# WebSocket Endpoint: /ws/audio
# Receives Base64-encoded browser microphone audio,
# decodes it via STT, and routes through the Dual-RAG pipeline.
# ============================================================
@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WS] Client connected to /ws/audio")
    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            action = message.get("action")
            phone_hash = message.get("phone_hash", "ws-user-default")

            if action == "PROCESS_AUDIO":
                audio_b64 = message.get("audio_b64")
                if not audio_b64:
                    await websocket.send_json({"error": "Missing audio_b64 field"})
                    continue

                # STT Transcription
                try:
                    transcription = stt_service.process_audio_b64(audio_b64)
                    logger.info(f"[WS] STT transcription: {transcription[:80]}...")
                except Exception as e:
                    logger.error(f"[WS] STT Error: {e}")
                    await websocket.send_json({"error": f"STT Failed: {str(e)}"})
                    continue

                # LLM / Dual-RAG Pipeline
                try:
                    response = action_handler_engine.process_action(
                        phone_identifier=phone_hash,
                        action_code=2,
                        payload=transcription
                    )
                    print("LLM Response:", response.answer_text)
                except Exception as e:
                    logger.error(f"[WS] LLM Error: {e}")
                    await websocket.send_json({"error": f"LLM Processing Failed: {str(e)}"})
                    continue
                
                # TTS Generation
                try:
                    audio_b64_response = tts_service.generate_tts_audio(response.answer_text)
                    if not audio_b64_response:
                        raise ValueError("Empty audio received from TTS API")
                    
                    print("TTS Audio Length:", len(audio_b64_response))
                    
                    await websocket.send_json({
                        "action": "PLAY_AUDIO",
                        "text": response.answer_text,
                        "audio_b64": audio_b64_response,
                        **response.model_dump()
                    })
                except Exception as e:
                    logger.error(f"[WS] TTS Error: {e}")
                    # CRITICAL: Send empty audio_b64 so UI unfreezes and shows text
                    await websocket.send_json({
                        "action": "PLAY_AUDIO",
                        "text": response.answer_text,
                        "audio_b64": "",
                        "error": "TTS Failed",
                        **response.model_dump()
                    })

            else:
                # Non-audio actions (3, 4, 5, 6)
                action_code = message.get("action_code")
                if action_code and isinstance(action_code, int):
                    try:
                        response = action_handler_engine.process_action(
                            phone_identifier=phone_hash,
                            action_code=action_code,
                            payload=message.get("payload")
                        )
                        print("LLM Response:", response.answer_text)
                    except Exception as e:
                        logger.error(f"[WS] LLM Error: {e}")
                        await websocket.send_json({"error": f"LLM Processing Failed: {str(e)}"})
                        continue
                    
                    # TTS Generation for Numpad Actions
                    try:
                        audio_b64_response = tts_service.generate_tts_audio(response.answer_text)
                        if not audio_b64_response:
                            raise ValueError("Empty audio received from TTS API")
                            
                        print("TTS Audio Length:", len(audio_b64_response))

                        await websocket.send_json({
                            "action": "PLAY_AUDIO",
                            "text": response.answer_text,
                            "audio_b64": audio_b64_response,
                            **response.model_dump()
                        })
                    except Exception as e:
                        logger.error(f"[WS] TTS Error: {e}")
                        # CRITICAL: Send empty audio_b64 so UI unfreezes
                        await websocket.send_json({
                            "action": "PLAY_AUDIO",
                            "text": response.answer_text,
                            "audio_b64": "",
                            "error": "TTS Failed",
                            **response.model_dump()
                        })
                else:
                    await websocket.send_json({"error": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected from /ws/audio")

@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    from app.services.hybrid_router import hybrid_router
    is_online = hybrid_router.check_internet_availability()
    return {
        "status": "healthy",
        "hybrid_route": "CLAUDE_CLOUD" if is_online else "OLLAMA_LOCAL",
        "force_offline_flag": settings.FORCE_OFFLINE
    }