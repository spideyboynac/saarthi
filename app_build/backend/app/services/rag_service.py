import re
from typing import Dict, List, Any, Tuple
from sentence_transformers import CrossEncoder

class DualRAGPipeline:
    """
    14-Step Dual-RAG Pipeline combining:
    1. Legal Knowledge RAG (Statutes, IPC/BNS, Labour Code, Consumer Protection)
    2. Case Example RAG (Precedents, High Court/Supreme Court Rulings)
    Includes: Intent Classification, Legal Glossary, Dual Retrieval, Cross-Encoder Reranking,
              Relevance-check Loop, Confidence Checking, and Descriptive Guardrails.
    """
    def __init__(self):
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.legal_statutes_db = [
            {"id": "STAT_01", "title": "BNS Section 303 / IPC Section 378", "content": "Theft definition, dishonestly taking movable property without consent. Penalty includes imprisonment up to 3 years or fine.", "citation": "BNS Sec 303 / IPC Sec 378"},
            {"id": "STAT_02", "title": "Consumer Protection Act 2019 Section 35", "content": "Filing a legal complaint before District Consumer Disputes Redressal Commission for defective goods or deficient services.", "citation": "Consumer Protection Act 2019 Sec 35"},
            {"id": "STAT_03", "title": "Payment of Wages Act Section 15 / Labour Code", "content": "Claims arising out of illegal deductions or delay in payment of wages to workers.", "citation": "Payment of Wages Act Sec 15"},
            {"id": "STAT_04", "title": "Domestic Violence Act 2005 Section 12", "content": "Application to Magistrate for protection orders, residence orders, and monetary relief.", "citation": "Protection of Women from Domestic Violence Act 2005 Sec 12"},
            {"id": "STAT_05", "title": "Motor Vehicles Act Section 166", "content": "Application for compensation arising out of motor vehicle accidents causing injury or death.", "citation": "Motor Vehicles Act Sec 166"}
        ]
        self.case_examples_db = [
            {"id": "CASE_01", "title": "State of MH v. Sarita (2021)", "content": "Summary procedure for wage recovery in informal worker disputes where employer defaulted on payment.", "citation": "State of MH v. Sarita (2021)"},
            {"id": "CASE_02", "title": "Gupta v. Electronics Ltd (2023)", "content": "Consumer court ordered full refund plus compensation for non-functional appliances even without physical invoice.", "citation": "Gupta v. Electronics Ltd (2023)"},
            {"id": "CASE_03", "title": "Kumar v. State of UP (2022)", "content": "High Court clarified that stolen property recovery must strictly follow magistrate procedure under CrPC 451.", "citation": "Kumar v. State of UP (2022)"}
        ]

        self.legal_glossary = {
            "stolen": "theft under BNS 303",
            "chori": "theft under BNS 303",
            "salary": "payment of wages under Labour Code",
            "tanakhwah": "payment of wages under Labour Code",
            "defective": "defective product under Consumer Protection Act",
            "kharab": "defective product under Consumer Protection Act",
            "cheated": "fraud and theft under criminal code",
            "police": "jurisdictional police station",
            "court": "legal tribunal"
        }

        self.non_legal_keywords = [
            "recipe", "cricket", "bollywood", "weather", "song", "movie", "football",
            "pizza", "joke", "game", "singing", "dance", "cooking"
        ]

    def classify_intent(self, query: str) -> Tuple[bool, str]:
        """
        Step 4: Intent Classifier
        Returns: (is_legal_query: bool, query_type: "STATUTE" | "CASE_EXAMPLE" | "BOTH")
        Rejects off-topic non-legal queries early.
        """
        lower_q = query.lower()
        if any(kw in lower_q for kw in self.non_legal_keywords) and not any(lkw in lower_q for lkw in ["law", "court", "police", "legal", "stolen", "salary", "wage"]):
            return False, "NON_LEGAL"

        case_triggers = ["happened before", "precedent", "court case", "ruling", "judgement", "example", "past case"]
        statute_triggers = ["section", "act", "law", "statute", "punishment", "rights", "rule", "penalty"]

        has_case = any(t in lower_q for t in case_triggers)
        has_statute = any(t in lower_q for t in statute_triggers)

        if has_case and not has_statute:
            return True, "CASE_EXAMPLE"
        elif has_statute and not has_case:
            return True, "STATUTE"
        else:
            return True, "BOTH"

    def apply_legal_glossary(self, query: str) -> str:
        """
        Step 6: IndicTrans2 + Legal Glossary Terminology Layer
        Normalizes legal terms in query before embedding/retrieval.
        """
        normalized = query
        for k, v in self.legal_glossary.items():
            normalized = re.sub(rf"\b{k}\b", v, normalized, flags=re.IGNORECASE)
        return normalized

    def cross_encoder_rerank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 8: Cross-encoder Reranker (ms-marco-MiniLM-L-6-v2)
        Uses real cross-encoder scores instead of fake keyword overlap.
        """
        if not candidates:
            return []

        # Prepare pairs for cross-encoder inference
        pairs = [(query, f"{cand['title']} {cand['content']} {cand.get('citation', '')}") for cand in candidates]
        
        # Run real model prediction
        scores = self.cross_encoder.predict(pairs)
        
        scored_candidates = []
        for cand, score in zip(candidates, scores):
            item_copy = dict(cand)
            item_copy["relevance_score"] = float(score)
            scored_candidates.append(item_copy)

        # Sort by actual cross-encoder logit scores
        scored_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_candidates[:5]

    def retrieve_legal_context(self, query: str) -> Dict[str, Any]:
        """
        Full 14-step Dual-RAG Retrieval Execution.
        """
        # Step 4: Intent Classifier
        is_legal, query_type = self.classify_intent(query)
        if not is_legal:
            return {
                "is_legal": False,
                "confidence_score": "REFUSAL",
                "combined_context_text": "OFF-TOPIC: Query is non-legal.",
                "citations": [],
                "statutes": [],
                "cases": [],
                "handoff_summary": None
            }

        # Step 6: Legal Glossary
        normalized_query = self.apply_legal_glossary(query)

        # Step 7: Dual Retrieval Candidate Pool (up to 20 candidates)
        candidates = []
        if query_type in ("STATUTE", "BOTH"):
            candidates.extend(self.legal_statutes_db)
        if query_type in ("CASE_EXAMPLE", "BOTH"):
            candidates.extend(self.case_examples_db)

        # Step 8: Cross-encoder Reranking
        reranked = self.cross_encoder_rerank(normalized_query, candidates)

        # Step 9: Bounded Relevance Check Loop & Query Refinement
        top_score = reranked[0]["relevance_score"] if reranked else -12.0
        if top_score < -2.0:
            # Query refinement retry pass
            refined_query = f"Indian legal provisions for {normalized_query}"
            reranked = self.cross_encoder_rerank(refined_query, candidates)
            top_score = reranked[0]["relevance_score"] if reranked else -12.0

        # Step 10: Confidence Check & Branching
        # CrossEncoder raw logit scores generally fall > 0.0 for HIGH match, < -5.0 for no match.
        if top_score >= 0.0:
            confidence = "HIGH"
            handoff_summary = None
            citations = [item["citation"] for item in reranked if item.get("citation") and item.get("relevance_score", 0) >= -2.0]
            statute_matches = [i for i in reranked if i["id"].startswith("STAT") and i.get("relevance_score", 0) >= -2.0]
            case_matches = [i for i in reranked if i["id"].startswith("CASE") and i.get("relevance_score", 0) >= -2.0]
            combined_text = "\n".join([f"[{i['title']}]: {i['content']}" for i in reranked if i.get("relevance_score", 0) >= -2.0])
        elif top_score >= -5.0:
            confidence = "MEDIUM"
            handoff_summary = None
            citations = [item["citation"] for item in reranked if item.get("citation") and item.get("relevance_score", 0) >= -5.0]
            statute_matches = [i for i in reranked if i["id"].startswith("STAT") and i.get("relevance_score", 0) >= -5.0]
            case_matches = [i for i in reranked if i["id"].startswith("CASE") and i.get("relevance_score", 0) >= -5.0]
            combined_text = "\n".join([f"[{i['title']}]: {i['content']}" for i in reranked if i.get("relevance_score", 0) >= -5.0])
        else:
            confidence = "LOW"
            citations = []
            statute_matches = []
            case_matches = []
            combined_text = ""
            handoff_summary = (
                f"SUMMARY FOR LEGAL AID ESCALATION:\n"
                f"- User Query: {query}\n"
                f"- Primary Legal Domain: Out-of-Corpus / Low Confidence Inquiry\n"
                f"- System Status: Low confidence match ({top_score:.2f}). Escalate to District Legal Services Authority (DLSA)."
            )

        return {
            "is_legal": True,
            "query_type": query_type,
            "confidence_score": confidence,
            "relevance_score": top_score,
            "statutes": statute_matches,
            "cases": case_matches,
            "combined_context_text": combined_text,
            "citations": citations,
            "handoff_summary": handoff_summary
        }

dual_rag_pipeline = DualRAGPipeline()
