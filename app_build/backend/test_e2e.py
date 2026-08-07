import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app.models.schemas import RAGRequest
from app.services.rag_service import dual_rag_pipeline
from app.services.action_handler import action_handler_engine

def main():
    phone = "test-session-123"
    query = "What is the punishment for theft under BNS?"
    
    print("\n" + "="*50)
    print("STAGE 1: Direct RAG Retrieval (Proving Output Contract)")
    print("="*50)
    req = RAGRequest(query=query, language="en", route_hint="knowledge")
    rag_res = dual_rag_pipeline.retrieve_context(req)
    print(rag_res.model_dump_json(indent=2))
    
    print("\n" + "="*50)
    print("STAGE 2: Action 1 (Full Pipeline - RAG + LLM Generation)")
    print("="*50)
    res1 = action_handler_engine.process_action(phone, action_code=1, payload=query)
    print(f"Action: {res1.action_name}")
    print(f"RAG Executed: {res1.rag_executed}")
    print(f"LLM Route: {res1.llm_route}")
    print(f"Answer:\n{res1.answer_text}")
    
    print("\n" + "="*50)
    print("STAGE 3: Action 3 (Repeat - Cache Only, Bypass RAG & LLM)")
    print("="*50)
    res3 = action_handler_engine.process_action(phone, action_code=3)
    print(f"Action: {res3.action_name}")
    print(f"RAG Executed: {res3.rag_executed}")
    print(f"LLM Route: {res3.llm_route}")
    print(f"Answer:\n{res3.answer_text}")

    print("\n" + "="*50)
    print("STAGE 4: Action 4 (Simplify - Cache to LLM, Bypass RAG)")
    print("="*50)
    res4 = action_handler_engine.process_action(phone, action_code=4)
    print(f"Action: {res4.action_name}")
    print(f"RAG Executed: {res4.rag_executed}")
    print(f"LLM Route: {res4.llm_route}")
    print(f"Simplified Answer:\n{res4.answer_text}")

    print("\n" + "="*50)
    print("STAGE 5: Action 5 (Follow-ups - Cache to LLM, Bypass RAG)")
    print("="*50)
    res5 = action_handler_engine.process_action(phone, action_code=5)
    print(f"Action: {res5.action_name}")
    print(f"RAG Executed: {res5.rag_executed}")
    print(f"LLM Route: {res5.llm_route}")
    print(f"Follow-ups Generated:\n")
    if res5.socratic_followups:
        for q in res5.socratic_followups:
            print(f"  - {q}")

if __name__ == "__main__":
    main()
