from typing import Optional
from router import QueryType, get_target_collections
from retriever import UnifiedRetriever
from confidence import ConfidenceScorer
from models import RetrievalResult, ConfidenceTier

class RefiningRetriever:
    """
    Wraps the unified retriever with bounded retry logic and confidence scoring.
    This exposes the final contract to the downstream orchestration layer.
    """
    def __init__(self, vector_store_dir: str, max_retries: int = 3, 
                 high_threshold: float = 2.0, medium_threshold: float = 0.0):
        self.retriever = UnifiedRetriever(vector_store_dir)
        self.scorer = ConfidenceScorer(high_threshold, medium_threshold)
        self.max_retries = max_retries
        
    def retrieve(self, query: str, query_type: QueryType, attempt_number: int = 1) -> RetrievalResult:
        """
        Executes a retrieval or a re-retrieval retry triggered externally.
        Bounded by max_retries. If exceeded, returns an empty/failsafe result.
        """
        collections_targeted = get_target_collections(query_type)
        
        if attempt_number > self.max_retries:
            return RetrievalResult(
                passages=[],
                collections_queried=collections_targeted,
                confidence_score=0.0,
                confidence_tier=ConfidenceTier.NONE,
                is_retry=True,
                attempt_number=attempt_number
            )
            
        # Perform core retrieval
        candidates = self.retriever.retrieve(query, query_type)
        
        # Calculate confidence
        score, tier = self.scorer.compute_confidence(candidates)
        
        return RetrievalResult(
            passages=candidates,
            collections_queried=collections_targeted,
            confidence_score=score,
            confidence_tier=tier,
            is_retry=(attempt_number > 1),
            attempt_number=attempt_number
        )
