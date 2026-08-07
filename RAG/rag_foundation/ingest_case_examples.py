import os
import pandas as pd
from chunker import chunk_document
from embedder import embed_chunks
from index_manager import IndexManager

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "synthetic_case_examples_rag_1000.csv")
    vector_store_dir = os.path.join(base_dir, "vector_store")
    collection_name = "case_examples"
    
    manager = IndexManager(vector_store_dir)
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV not found at {csv_path}")
        return
        
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Group by topic to create sub-indices
    grouped = df.groupby('topic')
    
    for topic, group in grouped:
        print(f"\nProcessing topic: {topic} ({len(group)} cases)...")
        
        all_chunks = []
        doc_id = topic  # Topic becomes the sub-index doc_id
        
        for _, row in group.iterrows():
            text = str(row.get('text', ''))
            case_id = str(row.get('case_id', ''))
            court_level = str(row.get('court_level', ''))
            decision = str(row.get('decision', ''))
            
            # Identical metadata schema to legal_knowledge:
            # We provide 'source_file' plus additional case-specific fields for citations later.
            extra_metadata = {
                "source_file": "synthetic_case_examples_rag_1000.csv",
                "case_id": case_id,
                "court_level": court_level,
                "decision": decision,
                "topic": topic
            }
            
            # Using the fixed 512/64 overlapping chunker for short case texts
            case_chunks = chunk_document(text, doc_id, extra_metadata=extra_metadata)
            all_chunks.extend(case_chunks)
            
        print(f"  Generated {len(all_chunks)} chunks for topic '{topic}'.")
        
        if not all_chunks:
            continue
            
        print(f"  Embedding chunks for '{topic}' (this may take a moment)...")
        vectors = embed_chunks(all_chunks)
        
        print(f"  Storing in IndexManager under collection '{collection_name}'...")
        manager.add_chunks(collection_name, doc_id, all_chunks, vectors)
        
    print("\nCase Example Ingestion complete!")

if __name__ == "__main__":
    main()
