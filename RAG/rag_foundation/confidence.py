from typing import List, Dict
from models import ConfidenceTier

class ConfidenceScorer:
    """
    Evaluates the reranked candidate pool to determine a confidence tier.
    Thresholds are exposed for external UX tuning.
    """
    def __init__(self, high_threshold: float = 2.0, medium_threshold: float = 0.0):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def compute_confidence(self, candidates: List[Dict]) -> tuple[float, ConfidenceTier]:
        """
        Computes confidence based on the top candidate's MS-MARCO rerank score.
        Returns (raw_score, tier).
        """
        if not candidates:
            return 0.0, ConfidenceTier.NONE
            
        # Candidates are assumed to be sorted descending by rerank_score
        top_score = candidates[0].get("rerank_score", 0.0)
        
        if top_score >= self.high_threshold:
            tier = ConfidenceTier.HIGH
        elif top_score >= self.medium_threshold:
            tier = ConfidenceTier.MEDIUM
        else:
            tier = ConfidenceTier.LOW
            
        return top_score, tier
