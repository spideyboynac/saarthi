import os
import sys
import time
import json
import httpx
import traceback

sys.stdout.reconfigure(encoding='utf-8')
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app.services.pipeline_logger import PipelineTracker
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service
from app.services.hybrid_router import hybrid_router
from app.services.rag_service import dual_rag_pipeline
from app.services.rag_core.router import QueryType, get_target_collections
from app.services.rag_core.confidence import ConfidenceScorer
from app.services.rag_core.models import ConfidenceTier
from app.services.session_service import session_service
from app.models.schemas import RAGRequest

TEST_QUERIES = [
    # --- Category 1: Clearly In-Domain (4 queries) ---
    {"id": "Call_01_InDomain", "query": "What is the punishment for theft under BNS?", "audio_file": None},
    {"id": "Call_02_InDomain", "query": "How can I file a consumer court complaint for a defective product?", "audio_file": None},
    {"id": "Call_03_InDomain", "query": "What are worker rights if an employer refuses to pay salaries?", "audio_file": None},
    {"id": "Call_04_InDomain", "query": "What is the legal procedure to file an FIR at a police station?", "audio_file": None},
    
    # --- Category 2: Borderline / Ambiguous (3 queries) ---
    {"id": "Call_05_Borderline", "query": "My neighbor's tree branches hang into my balcony.", "audio_file": None},
    {"id": "Call_06_Borderline", "query": "Can I break a house lease contract without paying penalty fee?", "audio_file": None},
    {"id": "Call_07_Borderline", "query": "Someone posted a bad review about my shop online.", "audio_file": None},
    
    # --- Category 3: Clearly Off-Topic (3 queries) ---
    {"id": "Call_08_OffTopic", "query": "What is the capital of France and how is the weather?", "audio_file": None},
    {"id": "Call_09_OffTopic", "query": "How do I bake a chocolate cake at home step by step?", "audio_file": None},
    {"id": "Call_10_OffTopic", "query": "Who won the cricket match yesterday?", "audio_file": None},
]

def simulate_twilio_audio_download(url: str = "https://api.twilio.com/2010-04-01/Accounts/ACmock/Recordings/REmock.mp3") -> bytes:
    """Simulates or executes Audio download from Twilio recording URL."""
    # If test_audio.mp3 exists locally, use its bytes to avoid fake URL network fail
    local_audio = os.path.join(base_dir, "test_audio.mp3")
    if os.path.exists(local_audio):
        with open(local_audio, "rb") as f:
            return f.read()
    # Fallback simulation bytes
    return b"SIMULATED_TWILIO_AUDIO_RECORDING_BYTES_" * 20

def run_single_call_diagnosis(call_id: str, query: str):
    tracker = PipelineTracker(call_id=call_id)
    
    transcription_text = query
    audio_bytes = None
    
    # -------------------------------------------------------------------------
    # STAGE 1: Audio Download from Twilio recording URL
    # -------------------------------------------------------------------------
    with tracker.track_stage(1, "Audio download from Twilio recording URL") as stg:
        try:
            audio_bytes = simulate_twilio_audio_download("https://api.twilio.com/mock_recording.mp3")
            stg.details["bytes_received"] = len(audio_bytes)
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 2: IndicASR / Deepgram STT Transcription
    # -------------------------------------------------------------------------
    with tracker.track_stage(2, "IndicASR / Deepgram Transcription") as stg:
        try:
            # If real audio bytes available, test Deepgram/STT call
            if audio_bytes and len(audio_bytes) > 500:
                res_stt = stt_service.transcribe_audio_deepgram(audio_bytes)
                stg.details["stt_result"] = res_stt[:80]
                if "error" in res_stt.lower() or "failed" in res_stt.lower():
                    stg.details["warning"] = "STT returned fallback message"
            else:
                stg.details["mode"] = "Direct input string supplied"
                stg.details["transcription"] = transcription_text[:80]
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 3: Intent Classifier (in-domain check)
    # -------------------------------------------------------------------------
    query_type = QueryType.MIXED
    with tracker.track_stage(3, "Intent Classifier (in-domain check)") as stg:
        try:
            collections = get_target_collections(query_type)
            stg.details["classified_intent"] = query_type.value
            stg.details["target_collections"] = collections
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 4: IndicTrans2 (native -> English)
    # -------------------------------------------------------------------------
    english_query = transcription_text
    with tracker.track_stage(4, "IndicTrans2 (native -> English)") as stg:
        try:
            # Hackathon build pass-through log
            stg.status = "PASS_THROUGH"
            stg.details["input_lang"] = "auto-detect"
            stg.details["output_english"] = english_query[:80]
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 5: Legal Knowledge RAG Retrieval
    # -------------------------------------------------------------------------
    legal_candidates = []
    with tracker.track_stage(5, "Legal Knowledge RAG retrieval") as stg:
        try:
            query_vec = dual_rag_pipeline.retriever.retriever.manager.search_collection(
                "legal_knowledge",
                # Embed query vector
                dual_rag_pipeline.retriever.retriever.manager.base_dir and 
                __import__("app.services.rag_core.embedder", fromlist=["embed_query"]).embed_query(english_query),
                k=20
            )
            legal_candidates = query_vec
            stg.details["passages_found"] = len(legal_candidates)
            if legal_candidates:
                stg.details["top_score"] = round(legal_candidates[0].get("score", 0.0), 4)
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 6: Case Example RAG Retrieval
    # -------------------------------------------------------------------------
    case_candidates = []
    with tracker.track_stage(6, "Case Example RAG retrieval") as stg:
        try:
            query_vec = dual_rag_pipeline.retriever.retriever.manager.search_collection(
                "case_examples",
                __import__("app.services.rag_core.embedder", fromlist=["embed_query"]).embed_query(english_query),
                k=20
            )
            case_candidates = query_vec
            stg.details["passages_found"] = len(case_candidates)
            if case_candidates:
                stg.details["top_score"] = round(case_candidates[0].get("score", 0.0), 4)
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # Merged candidates for reranking
    merged_candidates = legal_candidates + case_candidates

    # -------------------------------------------------------------------------
    # STAGE 7: Reranking
    # -------------------------------------------------------------------------
    reranked_top5 = []
    with tracker.track_stage(7, "Reranking (Cross-Encoder / Overlap)") as stg:
        try:
            if not merged_candidates:
                stg.details["passages_input"] = 0
                stg.details["reranked_count"] = 0
            else:
                ce = __import__("app.services.rag_core.retriever", fromlist=["get_cross_encoder"]).get_cross_encoder()
                if ce is not None:
                    stg.details["reranker_engine"] = "ms-marco-MiniLM-L-6-v2"
                    cross_inp = [[english_query, c["text"]] for c in merged_candidates]
                    scores = ce.predict(cross_inp)
                    for idx, s in enumerate(scores):
                        merged_candidates[idx]["rerank_score"] = float(s)
                else:
                    stg.details["reranker_engine"] = "word_overlap_fallback"
                    overlap_fn = __import__("app.services.rag_core.retriever", fromlist=["_word_overlap_score"])._word_overlap_score
                    for c in merged_candidates:
                        c["rerank_score"] = overlap_fn(english_query, c.get("text", ""))

                merged_candidates.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
                reranked_top5 = merged_candidates[:5]
                stg.details["passages_input"] = len(merged_candidates)
                stg.details["top_rerank_score"] = round(reranked_top5[0]["rerank_score"], 4) if reranked_top5 else None
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 8: Confidence / Sufficiency Check
    # -------------------------------------------------------------------------
    confidence_score = 0.0
    confidence_tier = ConfidenceTier.NONE
    rag_status = "abstain"
    with tracker.track_stage(8, "Confidence / Sufficiency check") as stg:
        try:
            scorer = ConfidenceScorer()
            confidence_score, confidence_tier = scorer.compute_confidence(reranked_top5)
            if confidence_tier == ConfidenceTier.HIGH:
                rag_status = "sufficient"
            elif confidence_tier in (ConfidenceTier.MEDIUM, ConfidenceTier.LOW):
                rag_status = "needs_clarification"
            else:
                rag_status = "abstain"
                
            stg.details["confidence_score"] = round(confidence_score, 4)
            stg.details["confidence_tier"] = confidence_tier.name
            stg.details["resulting_status"] = rag_status
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 9: Qwen 3 4B / Claude LLM Generation
    # -------------------------------------------------------------------------
    generated_text = ""
    llm_route = "NONE"
    with tracker.track_stage(9, "LLM Generation (Claude / Ollama)") as stg:
        try:
            if rag_status == "sufficient" and reranked_top5:
                context_blocks = "\n".join([f"[{p.get('source_file', 'Source')}] {p['text']}" for p in reranked_top5])
                system_prompt = f"You are Nyaya-Dhwani, an Indian legal literacy assistant. Ground your answer in context:\n{context_blocks}"
                prompt = f"User Question: {english_query}\nProvide a clear, legally accurate answer."
                generated_text, llm_route = hybrid_router.generate_llm_response(prompt, system_prompt)
                stg.details["mode"] = "Grounded RAG + Ollama (Llama 3.1)"
            else:
                system_prompt = "You are Nyaya-Dhwani, a helpful Indian legal literacy assistant. Answer directly using general legal knowledge."
                prompt = f"User Question: {english_query}\nProvide a clear, helpful legal answer."
                generated_text, raw_route = hybrid_router.generate_llm_response(prompt, system_prompt)
                llm_route = f"{raw_route}_DIRECT_LLM_NO_RAG_FALLBACK"
                stg.details["mode"] = "Direct Ollama LLM Fallback (NO RAG)"

            stg.details["llm_route"] = llm_route
            stg.details["response_length"] = len(generated_text)
            stg.details["preview"] = generated_text[:100]
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 10: IndicTrans2 (English -> native)
    # -------------------------------------------------------------------------
    with tracker.track_stage(10, "IndicTrans2 (English -> native)") as stg:
        try:
            stg.status = "PASS_THROUGH"
            stg.details["target_lang"] = "en"
            stg.details["text_preview"] = generated_text[:80] if generated_text else ""
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 11: ElevenLabs TTS call
    # -------------------------------------------------------------------------
    audio_b64 = ""
    with tracker.track_stage(11, "ElevenLabs TTS call") as stg:
        try:
            if generated_text:
                audio_b64 = tts_service.generate_tts_audio(generated_text[:150]) # cap for testing speed
                stg.details["audio_b64_len"] = len(audio_b64)
                if not audio_b64:
                    stg.details["warning"] = "ElevenLabs returned empty audio or failed"
            else:
                stg.details["warning"] = "No text provided to TTS"
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    # -------------------------------------------------------------------------
    # STAGE 12: Audio file write + Twilio <Play> / WS response
    # -------------------------------------------------------------------------
    with tracker.track_stage(12, "Audio file write + Twilio <Play> response") as stg:
        try:
            stg.details["payload_ready"] = bool(audio_b64 or generated_text)
            stg.details["delivery_channel"] = "TwiML XML / WebSocket JSON"
        except Exception as e:
            stg.status = "FAILURE"
            stg.error_type = type(e).__name__
            stg.error_message = str(e)
            stg.traceback_str = traceback.format_exc()

    tracker.print_pipeline_report(title=f"DIAGNOSIS REPORT — Query: '{query[:50]}...'")
    return tracker

def main():
    print("=" * 80)
    print(" STARTING 10-CALL PIPELINE DIAGNOSIS (ALL 12 STAGES INSTRUMENTED)")
    print("=" * 80)
    
    all_trackers = []
    for item in TEST_QUERIES:
        call_id = item["id"]
        query = item["query"]
        print(f"\n>>> Running Call Diagnosis: {call_id} | Query: '{query}'")
        tracker = run_single_call_diagnosis(call_id, query)
        all_trackers.append(tracker)
        
    print("\n" + "=" * 80)
    print(" COMPLETED ALL 10 TEST CALL DIAGNOSES")
    print("=" * 80)

if __name__ == "__main__":
    main()
