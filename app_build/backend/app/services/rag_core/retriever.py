import os
from app.services.rag_core.router import QueryType, get_target_collections
from app.services.rag_core.embedder import embed_query
from app.services.rag_core.index_manager import IndexManager

# Lazy import — sentence_transformers is optional; fall back to word-overlap
try:
    from sentence_transformers import CrossEncoder as _CEClass
    _CE_AVAILABLE = True
except ImportError:
    _CEClass = None
    _CE_AVAILABLE = False

_cross_encoder = None

def get_cross_encoder():
    global _cross_encoder
    if not _CE_AVAILABLE:
        return None
    if _cross_encoder is None:
        _cross_encoder = _CEClass('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _cross_encoder

def _word_overlap_score(query: str, text: str) -> float:
    """Fallback scorer when CrossEncoder is unavailable."""
    q_words = set(query.lower().split())
    t_words = set(text.lower().split())
    if not q_words:
        return 0.0
    return len(q_words & t_words) / len(q_words)

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

        # 3. Cross-Encoder Reranking (or word-overlap fallback)
        cross_encoder = get_cross_encoder()
        if cross_encoder is not None:
            cross_inp = [[query, candidate["text"]] for candidate in candidates]
            scores = cross_encoder.predict(cross_inp)
            for idx, score in enumerate(scores):
                candidates[idx]["rerank_score"] = float(score)
        else:
            for candidate in candidates:
                candidate["rerank_score"] = _word_overlap_score(query, candidate.get("text", ""))
            
        # 4. Sort globally by rerank score descending
        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # 5. Cut to top-5 post-rerank
        top_5 = candidates[:5]
        return top_5
