from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any
from app.services.rag_core.router import QueryType

class ConfidenceTier(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

@dataclass
class RetrievalResult:
    """
    The strict, versioned output contract returned to the orchestration layer.
    No generative LLM outputs, Twilio instructions, or ASR data should ever be added here.
    """
    passages: List[Dict[str, Any]]
    collections_queried: List[str]
    confidence_score: float
    confidence_tier: ConfidenceTier
    is_retry: bool
    attempt_number: int
