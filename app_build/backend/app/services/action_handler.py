from typing import List, Optional, Dict, Any
from app.models.schemas import ActionResponse, RAGRequest
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
            rag_req = RAGRequest(query=query, language="en")
            rag_res = dual_rag_pipeline.retrieve_context(rag_req)
            
            # Step 2 & 3: Branch on RAG confidence status
            if rag_res.status == "needs_clarification":
                answer_text = "I found some information, but I need to be sure. Could you clarify what exactly happened or who was involved?"
                llm_route = "NONE (SOCRATIC_FALLBACK)"
            elif rag_res.status == "abstain":
                answer_text = "I'm sorry, but I do not have enough specific legal context to answer that safely. I am transferring you to a human legal aid volunteer."
                llm_route = "NONE (HUMAN_HANDOFF)"
            else:
                # status == "sufficient"
                context_blocks = "\n".join([f"[{p.source_citation}] {p.text}" for p in rag_res.passages])
                
                system_prompt = (
                    f"You are Nyaya-Dhwani, a legal literacy conversational assistant. "
                    f"Ground your answer STRICTLY in the retrieved context:\n{context_blocks}\n"
                    f"You must answer ONLY using the provided context. You must cite your claims using the [Source Document] names provided.\n"
                    f"Target Literacy Tier: {session.last_answer_tier}."
                )
                
                prompt = f"User Question: {query}\nProvide a clear, legally accurate answer."
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
            system_prompt = "You are a legal literacy simplifier."
            prompt = f"rewrite this in simpler language, same facts, no new claims:\n\n{last_text}"
            
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
            system_prompt = "You are a Socratic legal guide."
            prompt = f"suggest 2-3 natural follow-up questions based on this advice:\n\n{last_text}"
            
            llm_text, llm_route = hybrid_router.generate_llm_response(prompt, system_prompt)
            
            # Split the LLM output into a list of questions
            socratic_questions = [q.strip() for q in llm_text.split('\n') if q.strip()]

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
