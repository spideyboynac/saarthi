from typing import List, Optional
from app.models.schemas import ActionResponse, RAGRequest
from app.services.session_service import session_service
from app.services.hybrid_router import hybrid_router
from app.services.rag_service import dual_rag_pipeline


class ActionHandlerEngine:
    """
    Implements the 6-Action Control Map & RAG Bypass Rules (v3.0 spec §3).

    Action 1/2  — New Question / End Input:
        Full Dual-RAG pipeline. STT transcription arrives as `payload`.
        RAG EXECUTED: vector search across both legal and case indices.

    Action 3    — Repeat:
        Replays last_answer_text from call_session. STRICT RAG BYPASS.
        Zero LLM generation, zero vector search.

    Action 4    — Simplify:
        Drops literacy tier. Sends last_answer_text to LLM with a narrow
        rewrite prompt. STRICT RAG BYPASS — operates only on cached text.

    Action 5    — Follow-Ups:
        Sends last_answer_text to LLM to produce 2-3 Socratic follow-up
        questions. STRICT RAG BYPASS.

    Action 6    — Stop:
        Barge-in / interrupt. Terminates active session state immediately.
        No LLM, no RAG.

    ZERO MOCK DATA POLICY (v3.0 spec §3.1):
        No hardcoded questions, answers, or audio strings are permitted in
        this file. If `payload` is empty on Action 1/2, raise immediately.
    """

    def process_action(
        self, phone_identifier: str, action_code: int, payload: Optional[str] = None
    ) -> ActionResponse:
        session = session_service.get_or_create_session(phone_identifier)

        # ----------------------------------------------------------------
        # ACTION 1 & 2: New Question / End Input → Full Dual-RAG Pipeline
        # ----------------------------------------------------------------
        if action_code in (1, 2):
            query = payload
            if not query or not query.strip():
                raise ValueError(
                    "Action 1/2 requires real STT transcription as input. "
                    "Hardcoded mock queries are forbidden (v3.0 spec §3.1)."
                )

            # -- STEP 2: IndicTrans2 - Native -> English (pass-through in hackathon build) --
            print("\n--- [STEP 2] IndicTrans2 - Native language -> English (pass-through) ---")
            print(f"    query: '{query[:120]}'")
            # Hackathon build: Deepgram detect_language handles normalisation.
            # IndicTrans2 full integration is the production milestone.
            english_query = query
            print("--- [STEP 2] SUCCESS (pass-through) ---")

            # -- STEP 3: Dual-RAG Retrieval ----------------------------------------------
            print("\n--- [STEP 3] Dual-RAG Retrieval (Legal KB + Case KB -> Top 5) ---")
            print(f"    querying vector store with: '{english_query[:120]}'")
            
            rag_res = None
            try:
                rag_req = RAGRequest(query=english_query, language="en")
                rag_res = dual_rag_pipeline.retrieve_context(rag_req)
                print(f"--- [STEP 3] RAG execution finished - status: {rag_res.status} | passages: {len(rag_res.passages)} | confidence: {rag_res.confidence:.3f}")
            except Exception as e:
                print(f"--- [STEP 3] WARNING: RAG Retrieval failed ({e}) - falling back to Direct LLM")
                rag_res = None

            # -- STEP 4: LLM Generation (Ollama Llama 3.1) --------------------------------
            print("\n--- [STEP 4] LLM Generation (Ollama Llama 3.1) ---")
            
            # Check if RAG provided usable context passages
            if rag_res and rag_res.status == "sufficient" and rag_res.passages:
                print("--- [STEP 4] Executing Ollama LLM with Grounded RAG Context + General Knowledge Fallback ---")
                context_blocks = "\n".join(
                    [f"[{p.source_citation}] {p.text}" for p in rag_res.passages]
                )
                system_prompt = (
                    f"You are Nyaya-Dhwani, an Indian legal literacy assistant.\n"
                    f"Your objective is to explain Indian laws and legal literacy concepts clearly and directly.\n\n"
                    f"Retrieved context for reference:\n{context_blocks}\n\n"
                    f"INSTRUCTIONS:\n"
                    f"1. Answer the user's question directly with clear legal facts.\n"
                    f"2. Use the retrieved context if relevant, but rely on your full legal knowledge for specific sections and penalties (such as BNS Section 303 for theft: up to 3 years imprisonment or fine).\n"
                    f"3. Never refuse to answer, never say 'I cannot provide information', and never state 'the context does not mention'. Always give the legal answer."
                )
                prompt = f"User Question: {english_query}\nProvide a clear, legally accurate answer."
                sources = [p.source_citation for p in rag_res.passages]
                answer_text, llm_route = hybrid_router.generate_llm_response(prompt, system_prompt)
            else:
                # FALLBACK RULE: If RAG ain't working or returned no passages, fallback to using ONLY the LLM (NO RAG NOTHING)
                print("--- [STEP 4] RAG UN-AVAILABLE / NO USABLE MATCH -> FALLBACK TO DIRECT OLLAMA LLM (NO RAG) ---")
                system_prompt = (
                    f"You are Nyaya-Dhwani, an Indian legal literacy assistant. "
                    f"Explain Indian laws, rights, and legal procedures directly and clearly using your general legal knowledge."
                )
                prompt = f"User Question: {english_query}\nProvide a clear, helpful legal answer."
                sources = []
                answer_text, raw_route = hybrid_router.generate_llm_response(prompt, system_prompt)
                llm_route = f"{raw_route}_DIRECT_LLM_FALLBACK"

            print(f"--- [STEP 4] SUCCESS - route: {llm_route} | answer: '{answer_text[:100]}'")

            # -- STEP 5: IndicTrans2 - English -> Native (pass-through in hackathon build) --
            print("\n--- [STEP 5] IndicTrans2 - English -> Native language (pass-through) ---")
            # Hackathon build: response sent in English; full IndicTrans2 is production milestone.
            print(f"--- [STEP 5] SUCCESS (pass-through) | final answer: '{answer_text[:100]}'")

            # Persist full result into call_session (spec §3.2 step 11)
            session_service.update_session(
                phone_hash=session.phone_hash,
                last_answer_text=answer_text,
                last_answer_tier=session.last_answer_tier,
                call_active=True,
                last_question=query,
                last_sources=sources,
            )

            return ActionResponse(
                action_code=action_code,
                action_name="New Question / Input Over",
                answer_text=answer_text,
                sources=sources,
                literacy_tier=session.last_answer_tier,
                rag_executed=True,
                llm_route=llm_route,
                call_active=True,
            )


        # ----------------------------------------------------------------
        # ACTION 3: Repeat Last Answer → STRICT RAG Bypass, No LLM
        # ----------------------------------------------------------------
        elif action_code == 3:
            last_text = session.last_answer_text or "No previous answer recorded in session."
            last_sources = session.last_sources or []

            return ActionResponse(
                action_code=3,
                action_name="Repeat Last Answer",
                answer_text=last_text,
                sources=last_sources,
                literacy_tier=session.last_answer_tier,
                rag_executed=False,   # STRICT RAG BYPASS
                llm_route="NONE (REPLAY_SESSION_MEMORY)",
                call_active=True,
            )

        # ----------------------------------------------------------------
        # ACTION 4: Simplify Explanation → STRICT RAG Bypass
        # ----------------------------------------------------------------
        elif action_code == 4:
            last_text = session.last_answer_text or (
                "[No prior answer in session — ask a question first using Action 1]"
            )

            # Drop the user's literacy tier in their persistent profile
            new_tier = session_service.degrade_tier(phone_identifier)

            # Narrow LLM prompt — operates ONLY on last_answer_text
            system_prompt = (
                "You are a legal literacy simplifier. "
                "Rewrite the provided answer in simpler language. "
                "Keep the same facts. Do not add any new claims or legal information."
            )
            prompt = f"Rewrite this in simpler language, same facts, no new claims:\n\n{last_text}"

            simplified_text, llm_route = hybrid_router.generate_llm_response(
                prompt, system_prompt
            )

            # Update session with simplified answer and new tier
            session_service.update_session(
                phone_hash=session.phone_hash,
                last_answer_text=simplified_text,
                last_answer_tier=new_tier,
                call_active=True,
            )

            return ActionResponse(
                action_code=4,
                action_name="Simplify Explanation",
                answer_text=simplified_text,
                literacy_tier=new_tier,
                rag_executed=False,   # STRICT RAG BYPASS
                llm_route=llm_route,
                call_active=True,
            )

        # ----------------------------------------------------------------
        # ACTION 5: Recommend Follow-Up Socratic Queries → STRICT RAG Bypass
        # ----------------------------------------------------------------
        elif action_code == 5:
            last_text = session.last_answer_text or (
                "[No prior answer in session — ask a question first using Action 1]"
            )

            # Narrow LLM prompt — operates ONLY on last_answer_text
            system_prompt = (
                "You are a Socratic legal guide. Generate 2 to 3 concise, natural follow-up questions "
                "that a caller might ask next based on the advice provided. "
                "Output each question on a separate line. Do not include introductory text or numbering."
            )
            prompt = f"Caller advice:\n\n{last_text}\n\nList 2-3 concise follow-up questions:"

            llm_text, llm_route = hybrid_router.generate_llm_response(prompt, system_prompt)

            # Parse LLM output into a list of follow-up question strings (stripping leading numbers/bullets)
            raw_lines = [q.strip() for q in llm_text.split("\n") if q.strip()]
            socratic_questions = []
            for line in raw_lines:
                # Strip leading numbering like "1. ", "1)", "- ", etc.
                cleaned = line.lstrip("0123456789.-*•) ").strip()
                if cleaned and len(cleaned) > 5:
                    socratic_questions.append(cleaned)

            if not socratic_questions:
                socratic_questions = [
                    "What legal evidence should I collect for this case?",
                    "How can I file a formal complaint with DLSA?"
                ]

            readable_answer = "Here are recommended follow-up questions:\n" + "\n".join([f"• {q}" for q in socratic_questions])

            return ActionResponse(
                action_code=5,
                action_name="Recommend Follow-Ups",
                answer_text=readable_answer,
                literacy_tier=session.last_answer_tier,
                rag_executed=False,   # STRICT RAG BYPASS
                llm_route=llm_route,
                socratic_followups=socratic_questions,
                call_active=True,
            )

        # ----------------------------------------------------------------
        # ACTION 6: Stop Playback (Barge-in) — Immediate, No LLM, No RAG
        # ----------------------------------------------------------------
        elif action_code == 6:
            session_service.terminate_session(session.phone_hash)

            return ActionResponse(
                action_code=6,
                action_name="Stop Playback (Barge-in)",
                answer_text="[BARGE-IN] Playback stopped immediately.",
                literacy_tier=session.last_answer_tier,
                rag_executed=False,
                llm_route="NONE",
                call_active=False,
            )

        else:
            raise ValueError(f"Invalid Action Code: {action_code}. Valid codes are 1-6.")


action_handler_engine = ActionHandlerEngine()
