from chunker import chunk_document
from embedder import embed_chunks, embed_query
from index_manager import IndexManager
import shutil
import os

def test_pipeline():
    print("Testing Pipeline...")
    # Clean up test dir if exists
    test_dir = "./test_vector_store"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        
    manager = IndexManager(test_dir)
    collection = "test_collection"
    
    # Document 1
    doc1 = "doc_001"
    text1 = "Apples are red and grow on trees. They are sweet and delicious."
    chunks1 = chunk_document(text1, doc1, {"type": "fruit"})
    vectors1 = embed_chunks(chunks1)
    manager.add_chunks(collection, doc1, chunks1, vectors1)
    
    # Document 2
    doc2 = "doc_002"
    text2 = "Carrots are orange root vegetables. They are crunchy."
    chunks2 = chunk_document(text2, doc2, {"type": "vegetable"})
    vectors2 = embed_chunks(chunks2)
    manager.add_chunks(collection, doc2, chunks2, vectors2)
    
    # Test Scoped Search
    q_vec = embed_query("What is orange?")
    res = manager.search_document(collection, doc2, q_vec, k=1)
    assert len(res) == 1
    assert "carrots" in res[0]["text"].lower()
    print("Scoped Search Passed!")
    
    # Test Global Search
    q_vec2 = embed_query("What is red?")
    res2 = manager.search_collection(collection, q_vec2, k=1)
    assert len(res2) == 1
    assert "apples" in res2[0]["text"].lower()
    assert res2[0]["doc_id"] == "doc_001"
    print("Global Search Passed!")
    
    print("All tests passed!")

if __name__ == "__main__":
    test_pipeline()
