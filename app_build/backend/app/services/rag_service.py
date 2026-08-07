from app.models.schemas import RAGRequest, RAGResponse, RAGPassage
from app.services.rag_core.refine import RefiningRetriever
from app.services.rag_core.router import QueryType
from app.services.rag_core.models import ConfidenceTier
import os

class DualRAGPipeline:
    """
    Dual-RAG Pipeline combining:
    1. Legal Knowledge RAG (Statutes, IPC/BNS, Constitutional Rights)
    2. Case Example RAG (Precedents, High Court/Supreme Court Rulings)
    """
    def __init__(self):
        # The vector store is located in the RAG directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        vector_store_dir = os.path.join(base_dir, "RAG", "vector_store")
        
        # Initialize our real RefiningRetriever
        self.retriever = RefiningRetriever(vector_store_dir, max_retries=3)

    def retrieve_context(self, request: RAGRequest) -> RAGResponse:
        """
        Retrieves context using the new Dual-RAG foundation.
        """
        # Map route_hint to QueryType
        query_type = QueryType.MIXED
        if request.route_hint == "knowledge":
            query_type = QueryType.STATUTE_LOOKUP
        elif request.route_hint == "case":
            query_type = QueryType.CASE_PRECEDENT
            
        # Execute retrieval
        result = self.retriever.retrieve(request.query, query_type=query_type, attempt_number=1)
        
        # Map ConfidenceTier to requested string status
        # HIGH  (score >= 0.0)  → sufficient         → full LLM generation
        # MEDIUM (score >= -3.0) → needs_clarification → Socratic followup
        # LOW   (score < -3.0)  → needs_clarification → still try, but note uncertainty
        # NONE  (no passages)   → abstain             → human handoff
        if result.confidence_tier == ConfidenceTier.HIGH:
            status = "sufficient"
        elif result.confidence_tier in (ConfidenceTier.MEDIUM, ConfidenceTier.LOW):
            status = "needs_clarification"
        else:  # ConfidenceTier.NONE — zero passages returned
            status = "abstain"
            
        # Map passages
        rag_passages = []
        for p in result.passages:
            source = p.get("source_file", "Unknown Source")
            doc = p.get("doc_id", "")
            citation = f"{source} ({doc})"
            rag_passages.append(
                RAGPassage(
                    text=p["text"],
                    source_citation=citation,
                    score=p.get("rerank_score", 0.0)
                )
            )
            
        return RAGResponse(
            passages=rag_passages,
            confidence=result.confidence_score,
            status=status,
            retry_count=result.attempt_number
        )

# Instantiate singleton
dual_rag_pipeline = DualRAGPipeline()
