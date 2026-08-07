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

            # ── STEP 2: IndicTrans2 — Native → English (pass-through in hackathon build) ──
            print("\n--- [STEP 2] IndicTrans2 — Native language → English (pass-through) ---")
            print(f"    query: '{query[:120]}'")
            # Hackathon build: Deepgram detect_language handles normalisation.
            # IndicTrans2 full integration is the production milestone.
            english_query = query
            print("--- [STEP 2] SUCCESS (pass-through) ---")

            # ── STEP 3: Dual-RAG Retrieval ──────────────────────────────────────────────
            print("\n--- [STEP 3] Dual-RAG Retrieval (Legal KB + Case KB → Top 5) ---")
            print(f"    querying vector store with: '{english_query[:120]}'")
            rag_req = RAGRequest(query=english_query, language="en")
            rag_res = dual_rag_pipeline.retrieve_context(rag_req)
            print(f"--- [STEP 3] SUCCESS — status: {rag_res.status} | passages: {len(rag_res.passages)} | confidence: {rag_res.confidence:.3f}")
            for i, p in enumerate(rag_res.passages):
                print(f"    passage[{i}]: score={p.score:.3f} source='{p.source_citation}' text='{p.text[:60]}...'")

            # Extract source citations for session storage and response
            sources = [p.source_citation for p in rag_res.passages]

            # ── STEP 4: LLM Generation ──────────────────────────────────────────────────
            print("\n--- [STEP 4] LLM Generation (Claude / Ollama) ---")
            if rag_res.status == "needs_clarification":
                answer_text = (
                    "I found some relevant information, but I need to be sure. "
                    "Could you clarify what exactly happened or who was involved?"
                )
                llm_route = "NONE (SOCRATIC_FALLBACK)"
                print(f"--- [STEP 4] SOCRATIC FALLBACK (RAG confidence insufficient)")

            elif rag_res.status == "abstain":
                answer_text = (
                    "I'm sorry, but I do not have enough specific legal context to "
                    "answer that safely. I am transferring you to a human legal aid "
                    "volunteer."
                )
                llm_route = "NONE (HUMAN_HANDOFF)"
                print(f"--- [STEP 4] HUMAN HANDOFF (RAG returned abstain)")

            else:
                # status == "sufficient" — generate grounded LLM answer
                context_blocks = "\n".join(
                    [f"[{p.source_citation}] {p.text}" for p in rag_res.passages]
                )

                system_prompt = (
                    f"You are Nyaya-Dhwani, a legal literacy conversational assistant. "
                    f"Ground your answer STRICTLY in the retrieved context:\n{context_blocks}\n"
                    f"You must answer ONLY using the provided context. "
                    f"Cite your claims using the [Source Document] names provided. "
                    f"Use descriptive language only ('the law states X', never 'you should X'). "
                    f"Target Literacy Tier: {session.last_answer_tier}."
                )

                prompt = f"User Question: {english_query}\nProvide a clear, legally accurate answer."
                print(f"    sending prompt to LLM ({len(prompt)} chars prompt, {len(system_prompt)} chars system)...")
                answer_text, llm_route = hybrid_router.generate_llm_response(
                    prompt, system_prompt
                )
                print(f"--- [STEP 4] SUCCESS — route: {llm_route} | answer: '{answer_text[:100]}'")

            # ── STEP 5: IndicTrans2 — English → Native (pass-through in hackathon build) ──
            print("\n--- [STEP 5] IndicTrans2 — English → Native language (pass-through) ---")
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
            system_prompt = "You are a Socratic legal guide."
            prompt = (
                f"Suggest 2-3 natural follow-up questions a caller might ask next, "
                f"based only on this advice:\n\n{last_text}"
            )

            llm_text, llm_route = hybrid_router.generate_llm_response(prompt, system_prompt)

            # Parse LLM output into a list of follow-up question strings
            socratic_questions = [q.strip() for q in llm_text.split("\n") if q.strip()]

            return ActionResponse(
                action_code=5,
                action_name="Recommend Follow-Ups",
                answer_text=llm_text,
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
