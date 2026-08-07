from pydantic import BaseModel
from typing import Optional, List

class QueryRequest(BaseModel):
    phone_hash: str
    query_text: str
    literacy_tier: Optional[str] = "STANDARD"

class ActionRequest(BaseModel):
    phone_hash: str
    action_code: int  # 1 to 6
    payload: Optional[str] = None

class ActionResponse(BaseModel):
    action_code: int
    action_name: str
    answer_text: str
    literacy_tier: str
    rag_executed: bool
    llm_route: str  # CLAUDE_API or OLLAMA_LOCAL
    socratic_followups: Optional[List[str]] = None
    call_active: bool

class RAGPassage(BaseModel):
    """Represents a single retrieved chunk with citation."""
    text: str
    source_citation: str
    score: float

class RAGRequest(BaseModel):
    """The strict input contract for querying the RAG service."""
    query: str
    language: str
    route_hint: Optional[str] = None

class RAGResponse(BaseModel):
    """The strict output contract returned by the RAG service."""
    passages: List[RAGPassage]
    confidence: float
    status: str  # "sufficient" | "needs_clarification" | "abstain"
    retry_count: int
