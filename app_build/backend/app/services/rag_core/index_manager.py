import os
import json
import numpy as np

# faiss is optional — fall back to in-memory metadata search when unavailable
try:
    import faiss as _faiss
    _FAISS_AVAILABLE = True
except ImportError:
    _faiss = None
    _FAISS_AVAILABLE = False


class IndexManager:
    def __init__(self, base_dir: str = "./vector_store"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        # 1024 is the embedding dimension for bge-large-en-v1.5
        self.embedding_dim = 1024
        
    def _get_collection_path(self, collection: str) -> str:
        path = os.path.join(self.base_dir, collection)
        os.makedirs(path, exist_ok=True)
        return path
        
    def _get_doc_paths(self, collection: str, doc_id: str):
        col_path = self._get_collection_path(collection)
        # Ensure the filename is safe
        safe_doc_id = "".join(c for c in doc_id if c.isalnum() or c in "._-")
        index_path = os.path.join(col_path, f"{safe_doc_id}.index")
        meta_path = os.path.join(col_path, f"{safe_doc_id}_meta.json")
        return index_path, meta_path

    def register_document(self, collection: str, doc_id: str):
        """Creates an empty sub-index for the document if it doesn't exist."""
        index_path, meta_path = self._get_doc_paths(collection, doc_id)
        if not os.path.exists(meta_path):
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump([], f)
        if _FAISS_AVAILABLE and not os.path.exists(index_path):
            # Inner Product (IndexFlatIP) is equivalent to cosine similarity for normalized vectors
            index = _faiss.IndexFlatIP(self.embedding_dim)
            _faiss.write_index(index, index_path)

    def add_chunks(self, collection: str, doc_id: str, chunks: list[dict], vectors: np.ndarray):
        """Adds embedded chunks to a specific document's sub-index."""
        self.register_document(collection, doc_id)

        index_path, meta_path = self._get_doc_paths(collection, doc_id)

        # Add to FAISS index (skip if faiss unavailable)
        if _FAISS_AVAILABLE and os.path.exists(index_path):
            index = _faiss.read_index(index_path)
            index.add(vectors.astype('float32'))
            _faiss.write_index(index, index_path)

        # Append metadata
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        metadata.extend(chunks)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def list_documents(self, collection: str) -> list[str]:
        """Lists all document IDs registered in a collection."""
        col_path = self._get_collection_path(collection)
        docs = []
        for file in os.listdir(col_path):
            if file.endswith(".index"):
                doc_id = file[:-6] 
                docs.append(doc_id)
        return docs

    def search_document(self, collection: str, doc_id: str, query_vector: np.ndarray, k: int = 5) -> list[dict]:
        """Scoped search against a single document's sub-index."""
        index_path, meta_path = self._get_doc_paths(collection, doc_id)

        if not os.path.exists(meta_path):
            return []

        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        if not metadata:
            return []

        # If FAISS is available and index file exists, use vector search
        if _FAISS_AVAILABLE and os.path.exists(index_path):
            index = _faiss.read_index(index_path)
            if index.ntotal == 0:
                return []
            actual_k = min(k, index.ntotal)
            query_vector = query_vector.reshape(1, -1).astype('float32')
            scores, indices = index.search(query_vector, actual_k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and idx < len(metadata):
                    res = dict(metadata[idx])
                    res["score"] = float(score)
                    results.append(res)
            return results

        # Fallback: return all metadata with score=0 (caller will rerank by word overlap)
        return [{**dict(m), "score": 0.0} for m in metadata[:k]]

    def search_collection(self, collection: str, query_vector: np.ndarray, k: int = 5) -> list[dict]:
        """Merged search across every sub-index in a collection."""
        docs = self.list_documents(collection)
        all_results = []
        
        for doc_id in docs:
            doc_results = self.search_document(collection, doc_id, query_vector, k)
            all_results.extend(doc_results)
            
        # Sort globally by score descending
        all_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return all_results[:k]
