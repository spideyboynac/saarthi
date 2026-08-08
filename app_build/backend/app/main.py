import os
from dotenv import load_dotenv

# Load environment variables BEFORE anything else initializes
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
from app.services.session_service import session_service

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

                # ════════════════════════════════════════════════════════════
                # STEP 1 — STT: Deepgram (Base64 → transcription text)
                # ════════════════════════════════════════════════════════════
                print("\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print("--- [STEP 1] STT — Decoding Base64 + Deepgram transcription ---")
                print(f"    audio_b64 length: {len(audio_b64)} chars")
                try:
                    transcription = stt_service.process_audio_b64(audio_b64)
                    print(f"--- [STEP 1] SUCCESS — Transcription: '{transcription[:120]}'")
                    logger.info(f"[WS] STT transcription: {transcription[:80]}")
                except Exception as e:
                    print(f"--- [STEP 1] FAILED — STT Error: {e}")
                    logger.error(f"[WS] STT Error: {e}")
                    await websocket.send_json({"error": f"STT Failed: {str(e)}"})
                    continue

                # ════════════════════════════════════════════════════════════
                # STEP 2–5 — IndicTrans2 (in) → Dual-RAG → LLM → IndicTrans2 (out)
                #   All handled inside action_handler.process_action()
                #   Individual step logs are printed inside action_handler.py
                # ════════════════════════════════════════════════════════════
                print("\n--- [STEP 2-5] Entering Action Handler (RAG + LLM pipeline) ---")
                print(f"    phone_hash: {phone_hash}")
                print(f"    transcription passed as payload: '{transcription[:120]}'")
                try:
                    response = action_handler_engine.process_action(
                        phone_identifier=phone_hash,
                        action_code=2,
                        payload=transcription
                    )
                    print(f"--- [STEP 2-5] SUCCESS — LLM answer ({len(response.answer_text)} chars): '{response.answer_text[:100]}'")
                    print(f"    llm_route: {response.llm_route} | rag_executed: {response.rag_executed}")
                except Exception as e:
                    print(f"--- [STEP 2-5] FAILED — Action Handler Error: {e}")
                    logger.error(f"[WS] LLM Error: {e}")
                    await websocket.send_json({"error": f"LLM Processing Failed: {str(e)}"})
                    continue

                # ════════════════════════════════════════════════════════════
                # STEP 6 — TTS: ElevenLabs (answer text → Base64 audio)
                # ════════════════════════════════════════════════════════════
                print("\n--- [STEP 6] TTS — ElevenLabs synthesis ---")
                print(f"    input text length: {len(response.answer_text)} chars")
                try:
                    audio_b64_response = tts_service.generate_tts_audio(response.answer_text)
                    if not audio_b64_response:
                        raise ValueError("ElevenLabs returned empty audio bytes")

                    print(f"--- [STEP 6] SUCCESS — audio_b64 length: {len(audio_b64_response)} chars")
                    logger.info(f"[WS] TTS audio generated: {len(audio_b64_response)} chars")

                    # Success path — spec §3.2 step 12: action=AUDIO_RESPONSE
                    await websocket.send_json({
                        "action": "AUDIO_RESPONSE",
                        "audio_b64": audio_b64_response,
                        "question": transcription,
                        "text": response.answer_text,
                        "sources": response.sources or [],
                        "literacy_tier": response.literacy_tier,
                        "rag_executed": response.rag_executed,
                        "llm_route": response.llm_route,
                    })
                    print("--- [STEP 6] AUDIO_RESPONSE sent to frontend ✓")
                    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

                except Exception as e:
                    print(f"--- [STEP 6] FAILED — TTS Error: {e}")
                    logger.error(f"[WS] TTS Error: {e}")
                    # Fallback path — spec §3.3: action=TTS_FALLBACK, NO audio_b64 field.
                    # Frontend must invoke window.speechSynthesis.speak() on this message.
                    await websocket.send_json({
                        "action": "TTS_FALLBACK",
                        "question": transcription,
                        "text": response.answer_text,
                        "sources": response.sources or [],
                        "literacy_tier": response.literacy_tier,
                        "rag_executed": response.rag_executed,
                        "llm_route": response.llm_route,
                        "error": "TTS_UNAVAILABLE",
                    })
                    print("--- [STEP 6] TTS_FALLBACK sent to frontend ✓")
                    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


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
                    
                    # TTS Generation for non-audio actions (3, 4, 5)
                    try:
                        audio_b64_response = tts_service.generate_tts_audio(response.answer_text)
                        if not audio_b64_response:
                            raise ValueError("Empty audio received from TTS API")

                        logger.info(f"[WS] TTS audio generated: {len(audio_b64_response)} chars")

                        # Success path — spec §3.2 step 12: action=AUDIO_RESPONSE
                        await websocket.send_json({
                            "action": "AUDIO_RESPONSE",
                            "audio_b64": audio_b64_response,
                            "text": response.answer_text,
                            "sources": response.sources or [],
                            "literacy_tier": response.literacy_tier,
                            "rag_executed": response.rag_executed,
                            "llm_route": response.llm_route,
                        })
                    except Exception as e:
                        logger.error(f"[WS] TTS Error: {e}")
                        # Fallback path — spec §3.3: action=TTS_FALLBACK, NO audio_b64 field.
                        # Frontend must invoke window.speechSynthesis.speak() on this message.
                        await websocket.send_json({
                            "action": "TTS_FALLBACK",
                            "text": response.answer_text,
                            "sources": response.sources or [],
                            "literacy_tier": response.literacy_tier,
                            "rag_executed": response.rag_executed,
                            "llm_route": response.llm_route,
                            "error": "TTS_UNAVAILABLE",
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