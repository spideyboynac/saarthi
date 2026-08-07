from typing import List, Optional, Dict, Any
from app.models.schemas import ActionResponse
from app.services.session_service import session_service
from app.services.hybrid_router import hybrid_router
from app.services.rag_service import dual_rag_pipeline

class ActionHandlerEngine:
    """
    Implements the 6-Action Control Map & RAG Bypass Rules:
    - Action 1/2 (New Question / End Input): Route through Dual-RAG pipeline.
    - Action 3 (Repeat): Replay last_answer_text, no LLM regeneration.
    - Action 4 (Simplify): Drop literacy tier. Pass last_answer_text to LLM with narrow rewrite prompt. STRICTLY bypass RAG.
    - Action 5 (Follow-Ups): Pass last_answer_text to LLM to suggest Socratic queries. STRICTLY bypass RAG.
    - Action 6 (Stop): Interrupt playback mid-response (barge-in).
    """

    def process_action(self, phone_identifier: str, action_code: int, payload: Optional[str] = None) -> ActionResponse:
        session = session_service.get_or_create_session(phone_identifier)

        # ----------------------------------------------------
        # ACTION 1 & 2: New Question / End Input -> Dual-RAG Pipeline
        # ----------------------------------------------------
        if action_code in (1, 2):
            query = payload
            if not query or not query.strip():
                raise ValueError("Action 1/2 requires real audio transcription input. Hardcoded mock queries are forbidden.")
            
            # Step 1: Retrieve context from Dual-RAG
            rag_context = dual_rag_pipeline.retrieve_legal_context(query)
            
            # Step 2: System prompt for legal literacy
            system_prompt = (
                f"You are Nyaya-Dhwani, a legal literacy conversational assistant. "
                f"Ground your answer STRICTLY in the retrieved context:\n{rag_context['combined_context_text']}\n"
                f"Target Literacy Tier: {session.last_answer_tier}."
            )
            
            prompt = f"User Question: {query}\nProvide a clear, legally accurate answer."
            
            # Step 3: LLM generation via Hybrid Router
            answer_text, llm_route = hybrid_router.generate_llm_response(prompt, system_prompt)
            
            # Update call_session state
            session_service.update_session(
                phone_hash=session.phone_hash,
                last_answer_text=answer_text,
                last_answer_tier=session.last_answer_tier,
                call_active=True
            )

            return ActionResponse(
                action_code=action_code,
                action_name="New Question / Input Over",
                answer_text=answer_text,
                literacy_tier=session.last_answer_tier,
                rag_executed=True,
                llm_route=llm_route,
                call_active=True
            )

        # ----------------------------------------------------
        # ACTION 3: Repeat Last Answer -> STRICT RAG Bypass & No LLM
        # ----------------------------------------------------
        elif action_code == 3:
            last_text = session.last_answer_text or "No previous answer recorded in call session."
            
            return ActionResponse(
                action_code=3,
                action_name="Repeat Last Answer",
                answer_text=f"[REPLAY] {last_text}",
                literacy_tier=session.last_answer_tier,
                rag_executed=False,  # STRICT RAG BYPASS
                llm_route="NONE (REPLAY_SESSION_MEMORY)",
                call_active=True
            )

        # ----------------------------------------------------
        # ACTION 4: Simplify Explanation -> STRICT RAG Bypass
        # ----------------------------------------------------
        elif action_code == 4:
            # Drop literacy tier
            new_tier = "SIMPLE"
            last_text = session.last_answer_text or "[No prior answer in session — ask a question first using Action 1]"
            
            # Narrow LLM prompt operating ONLY on last_answer_text
            system_prompt = "You are a legal literacy simplifier. Rewrite the given text using extremely simple terms, avoiding legal jargon."
            prompt = f"Rewrite this legal explanation for a caller needing SIMPLE literacy:\n\n{last_text}"
            
            simplified_text, llm_route = hybrid_router.generate_llm_response(prompt, system_prompt)
            
            # Update session state with simplified answer and tier
            session_service.update_session(
                phone_hash=session.phone_hash,
                last_answer_text=simplified_text,
                last_answer_tier=new_tier,
                call_active=True
            )

            return ActionResponse(
                action_code=4,
                action_name="Simplify Explanation",
                answer_text=simplified_text,
                literacy_tier=new_tier,
                rag_executed=False,  # STRICT RAG BYPASS
                llm_route=llm_route,
                call_active=True
            )

        # ----------------------------------------------------
        # ACTION 5: Recommend Follow-Up Socratic Queries -> STRICT RAG Bypass
        # ----------------------------------------------------
        elif action_code == 5:
            last_text = session.last_answer_text or "[No prior answer in session — ask a question first using Action 1]"
            
            # Narrow LLM prompt operating ONLY on last_answer_text
            system_prompt = "You are a Socratic legal guide. Suggest 3 short follow-up questions the caller should ask next."
            prompt = f"Based on this legal advice:\n{last_text}\n\nList 3 recommended follow-up questions."
            
            llm_text, llm_route = hybrid_router.generate_llm_response(prompt, system_prompt)
            
            socratic_questions = [
                "1. Where is the nearest Legal Services Authority (DLSA) office?",
                "2. What documents or payment receipts do I need to bring as evidence?",
                "3. How long does the consumer court or labour commission process take?"
            ]

            return ActionResponse(
                action_code=5,
                action_name="Recommend Follow-Ups",
                answer_text=llm_text,
                literacy_tier=session.last_answer_tier,
                rag_executed=False,  # STRICT RAG BYPASS
                llm_route=llm_route,
                socratic_followups=socratic_questions,
                call_active=True
            )

        # ----------------------------------------------------
        # ACTION 6: Stop Playback (Barge-in)
        # ----------------------------------------------------
        elif action_code == 6:
            session_service.update_session(
                phone_hash=session.phone_hash,
                last_answer_text=session.last_answer_text,
                last_answer_tier=session.last_answer_tier,
                call_active=False
            )

            return ActionResponse(
                action_code=6,
                action_name="Stop Playback (Barge-in)",
                answer_text="[BARGE-IN] Playback stopped immediately.",
                literacy_tier=session.last_answer_tier,
                rag_executed=False,
                llm_route="NONE",
                call_active=False
            )

        else:
            raise ValueError(f"Invalid Action Code: {action_code}")

action_handler_engine = ActionHandlerEngine()
