# AI Agent Handoff Document: Nyaya-Dhwani Backend Integration

**STATUS:** RAG Backend & LLM Orchestration (Routing) Complete.
**NEXT STAGE:** Generative LLM Wiring & Telephony (Audio) Integration.

This document serves as a direct handoff for the next AI agent picking up this repository. It outlines exactly what has been built, where the files live, and the exact entry points required for the remaining tasks.

---

## 1. What Has Been Completed

### A. The Dual-RAG Foundation
We have successfully built a production-ready Dual-RAG pipeline that queries both legal statutes and case precedents securely.
*   **Vector Store:** Uses `bge-large-en-v1.5` for embeddings and FAISS for indexing.
*   **Reranking:** Uses `MS-MARCO-MiniLM-L-6-v2` cross-encoder for top-5 extraction.
*   **Safety Loop:** Includes confidence scoring (High/Medium/Low tiers) and a bounded relevance-refinement retry loop (max 3 tries) to adjust queries if confidence is low.
*   **Strict Contracts:** Defined via Pydantic (`RAGRequest`, `RAGResponse`, `RAGPassage`).

### B. LLM Orchestration & RAG Integration
The RAG engine is fully wired into the main FastAPI application via the `ActionHandlerEngine` (`app_build/backend/app/services/action_handler.py`), which orchestrates the call flow:
*   **Action 1 & 2 (New Questions):** Calls the RAG pipeline.
    *   If `status == "sufficient"`: Injects the RAG passages securely into the system prompt and calls the LLM.
    *   If `status == "needs_clarification"`: Skips LLM, returns Socratic clarifying question.
    *   If `status == "abstain"`: Skips LLM, returns human-handoff trigger.
*   **Action 3 (Repeat):** Reads from session cache. **Bypasses RAG & LLM.**
*   **Action 4 (Simplify):** Feeds cached text to LLM to simplify. **Bypasses RAG.**
*   **Action 5 (Follow-ups):** Feeds cached text to LLM to generate questions. **Bypasses RAG.**

---

## 2. Where Everything Is Located

*   **RAG Engine Source:** `app_build/backend/app/services/rag_core/` (Chunker, Embedder, Retriever, Refiner, Confidence).
*   **RAG Wrapper API:** `app_build/backend/app/services/rag_service.py` (Exposes `DualRAGPipeline`).
*   **Data Contracts:** `app_build/backend/app/models/schemas.py`.
*   **LLM Orchestrator:** `app_build/backend/app/services/action_handler.py`.
*   **REST Endpoint:** `app_build/backend/app/api/query_routes.py` (Exposes `POST /query/retrieve`).
*   **Indices:** `RAG/vector_store/` *(Note: Make sure to copy this directory to the new laptop!)*
*   **End-to-End Test:** `app_build/backend/test_e2e.py` (Run this to verify the pipeline works locally).

---

## 3. Open Ends (Tasks for the Next Agent)

The next agent should tackle the following tracks. Do **NOT** modify the RAG routing logic in `action_handler.py`, as it has been heavily fortified.

### A. Wire the Generative LLM
**Target File:** `app_build/backend/app/services/hybrid_router.py`
*   Currently, `generate_llm_response()` is returning a **mocked string**.
*   **Task:** Connect the incoming `prompt` and `system_prompt` to actual API calls:
    1.  Primary: Claude 3.5 Sonnet (Cloud API).
    2.  Fallback: Llama 3.1 8B (Local via Ollama).

### B. Twilio Telephony & Audio Processing
**Target Layer:** `app_build/backend/app/api/` (likely `twilio_routes.py` or similar).
*   **Task:** Build the API endpoints that Twilio webhooks will hit during a call.
*   **ASR (Deepgram):** Convert incoming Indian language audio to English text.
*   **Translation (Bhashini):** (If required to bridge ASR and the English RAG pipeline).
*   **TTS (Sarvam/Bhashini):** Convert the English `answer_text` returned by `action_handler_engine` back to regional audio to stream to the caller.

### C. Implement the Upstream Intent Classifier
**Target Location:** Before `action_handler.py` is invoked.
*   Currently, the RAG defaults to querying `QueryType.MIXED` (both FAISS indices at once).
*   **Task:** Build an intent classifier that analyzes the user's transcript and sets the `route_hint` inside the `RAGRequest` to `"knowledge"` (statutes) or `"case"` (precedents) to optimize search latency.
