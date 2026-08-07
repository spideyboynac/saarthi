import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from router import QueryType
from retriever import UnifiedRetriever

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vector_store_dir = os.path.join(base_dir, "vector_store")
    
    # Initialize the retriever
    retriever = UnifiedRetriever(vector_store_dir)
    
    # Define our test queries
    queries = [
        ("What does the constitution say about fundamental rights?", QueryType.STATUTE_LOOKUP),
        ("Has there been a case where a worker was unfairly dismissed without notice?", QueryType.CASE_PRECEDENT),
        ("What does the law say about property disputes and are there cases on it?", QueryType.MIXED)
    ]
    
    for q, qt in queries:
        print(f"\n{'-'*60}\nQuery: '{q}'\nRouted as: {qt.name}\n{'-'*60}")
        
        # Execute retrieval
        results = retriever.retrieve(q, qt)
        
        print(f"Retrieved {len(results)} final candidates (Top-5 Cut).")
        for i, res in enumerate(results, 1):
            source = res.get("source_file", "Unknown")
            doc_id = res.get('doc_id', 'Unknown')
            score = res.get('rerank_score', 0)
            
            # Format preview text to be single-line
            preview = res['text'][:100].replace('\n', ' ').replace('\r', '')
            
            print(f"  {i}. [Score: {score:7.2f}] Source: {source} (Doc: {doc_id})")
            print(f"     Preview: {preview}...")

if __name__ == "__main__":
    main()
