import sys
import os
import json
sys.stdout.reconfigure(encoding='utf-8')

# Ensure we can import from app
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app.models.schemas import RAGRequest
from app.services.rag_service import dual_rag_pipeline

def main():
    print("Testing DualRAGPipeline standalone...\n")
    
    # 1. Statute Lookup Test
    print("-" * 50)
    print("TEST 1: Statute Lookup ('knowledge' hint)")
    req1 = RAGRequest(query="What is the punishment for theft under BNS?", language="en", route_hint="knowledge")
    res1 = dual_rag_pipeline.retrieve_context(req1)
    print(f"Status: {res1.status}")
    print(f"Confidence: {res1.confidence:.2f}")
    if res1.passages:
        print(f"Top Source: {res1.passages[0].source_citation}")
        print(f"Top Score: {res1.passages[0].score:.2f}")
    
    # 2. Case Example Test
    print("-" * 50)
    print("TEST 2: Case Precedent ('case' hint)")
    req2 = RAGRequest(query="Has there been a case where a worker was unfairly dismissed?", language="en", route_hint="case")
    res2 = dual_rag_pipeline.retrieve_context(req2)
    print(f"Status: {res2.status}")
    print(f"Confidence: {res2.confidence:.2f}")
    if res2.passages:
        print(f"Top Source: {res2.passages[0].source_citation}")
        print(f"Top Score: {res2.passages[0].score:.2f}")
    
    # 3. Mixed / Auto Test (JSON dump to prove contract)
    print("-" * 50)
    print("TEST 3: Full Pydantic Contract Dump (No hint)")
    req3 = RAGRequest(query="What does the law say about property disputes?", language="en")
    res3 = dual_rag_pipeline.retrieve_context(req3)
    
    print("\n[RAGResponse JSON Dump]")
    print(res3.model_dump_json(indent=2))
    
if __name__ == "__main__":
    main()
