import os
import fitz  # PyMuPDF
from chunker import semantic_chunk_document
from embedder import embed_chunks
from index_manager import IndexManager

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts all text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = []
    for page in doc:
        text.append(page.get_text())
    return "\n".join(text)

def main():
    # Use absolute paths or assume running from project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "Knowledge RAg data")
    vector_store_dir = os.path.join(base_dir, "vector_store")
    collection_name = "legal_knowledge"
    
    manager = IndexManager(vector_store_dir)
    
    if not os.path.exists(data_dir):
        print(f"Error: Data directory not found at {data_dir}")
        return
        
    for file in os.listdir(data_dir):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(data_dir, file)
            doc_id = file.replace(".pdf", "").replace(" ", "_").lower()
            
            print(f"\nProcessing {file} (doc_id: {doc_id})...")
            
            # 1. Extract Text
            print("  Extracting text...")
            text = extract_text_from_pdf(pdf_path)
            
            # 2. Semantic Chunking
            print("  Semantically chunking text...")
            chunks = semantic_chunk_document(text, doc_id, extra_metadata={"source_file": file})
            print(f"  Generated {len(chunks)} chunks.")
            
            if not chunks:
                print("  No chunks generated, skipping.")
                continue
                
            # 3. Embed Chunks
            print("  Embedding chunks (this might take a moment)...")
            vectors = embed_chunks(chunks)
            
            # 4. Store in FAISS
            print("  Storing in IndexManager...")
            manager.add_chunks(collection_name, doc_id, chunks, vectors)
            
    print("\nIngestion complete!")

if __name__ == "__main__":
    main()
