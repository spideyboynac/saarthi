import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from router import QueryType
from refine import RefiningRetriever
from models import ConfidenceTier

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vector_store_dir = os.path.join(base_dir, "vector_store")
    
    # Initialize refining retriever with max 3 retries
    retriever = RefiningRetriever(vector_store_dir, max_retries=3)
    
    # Attempt 1: Broad, unclear query
    q1 = "give me cases about disputes"
    print(f"\n{'-'*40}\nATTEMPT 1\nQuery: '{q1}'\n{'-'*40}")
    res1 = retriever.retrieve(q1, QueryType.MIXED, attempt_number=1)
    
    print(f"Confidence Tier: {res1.confidence_tier.name} (Score: {res1.confidence_score:.2f})")
    print(f"Is Retry: {res1.is_retry}, Attempt: {res1.attempt_number}")
    print(f"Passages Found: {len(res1.passages)}")
    
    # Simulate LLM orchestration deciding it's insufficient
    if res1.confidence_tier in (ConfidenceTier.LOW, ConfidenceTier.NONE):
        print("\n[Orchestrator]: Result insufficient. Triggering refinement...")
        
        # Attempt 2: Refined, specific query
        q2 = "Has there been a case where a worker was unfairly dismissed without notice?"
        print(f"\n{'-'*40}\nATTEMPT 2\nRefined Query: '{q2}'\n{'-'*40}")
        res2 = retriever.retrieve(q2, QueryType.CASE_PRECEDENT, attempt_number=2)
        
        print(f"Confidence Tier: {res2.confidence_tier.name} (Score: {res2.confidence_score:.2f})")
        print(f"Is Retry: {res2.is_retry}, Attempt: {res2.attempt_number}")
        
        print("\nTop 1 Result from Attempt 2:")
        if res2.passages:
            print(f"  Source: {res2.passages[0].get('source_file')}")
            print(f"  Preview: {res2.passages[0]['text'][:80].replace(chr(10), ' ')}...")
            
    # Attempt 4: Exceeding max retries
    print(f"\n{'-'*40}\nATTEMPT 4 (Exceeding max bounds)\n{'-'*40}")
    res4 = retriever.retrieve("Just trying again", QueryType.MIXED, attempt_number=4)
    print(f"Confidence Tier: {res4.confidence_tier.name}")
    print(f"Passages Found: {len(res4.passages)}")

if __name__ == "__main__":
    main()
