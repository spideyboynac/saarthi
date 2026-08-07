import os
from sentence_transformers import CrossEncoder
from app.services.rag_core.router import QueryType, get_target_collections
from app.services.rag_core.embedder import embed_query
from app.services.rag_core.index_manager import IndexManager

_cross_encoder = None

def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _cross_encoder

class UnifiedRetriever:
    def __init__(self, vector_store_dir: str):
        self.manager = IndexManager(vector_store_dir)
        
    def retrieve(self, query: str, query_type: QueryType) -> list[dict]:
        collections = get_target_collections(query_type)
        
        # 1. Embed query (using the shared bge-large-en-v1.5 wrapper)
        query_vec = embed_query(query)
        
        # 2. Retrieve top-20 from whichever collection(s) routing selected.
        # If 'mixed' routes to both, this retrieves 20 from each (40 total)
        # ensuring the cross-encoder has a rich, merged candidate pool to evaluate.
        candidates = []
        for col in collections:
            results = self.manager.search_collection(col, query_vec, k=20)
            candidates.extend(results)
            
        if not candidates:
            return []
            
        # 3. Cross-Encoder Reranking
        cross_encoder = get_cross_encoder()
        
        # Create (query, text) pairs for the cross-encoder
        cross_inp = [[query, candidate["text"]] for candidate in candidates]
        scores = cross_encoder.predict(cross_inp)
        
        # Attach rerank score to candidates
        for idx, score in enumerate(scores):
            candidates[idx]["rerank_score"] = float(score)
            
        # 4. Sort globally by cross-encoder score descending
        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # 5. Cut to top-5 post-rerank
        top_5 = candidates[:5]
        return top_5
