from typing import Dict, List, Any

class DualRAGPipeline:
    """
    Dual-RAG Pipeline combining:
    1. Legal Knowledge RAG (Statutes, IPC/BNS, Constitutional Rights)
    2. Case Example RAG (Precedents, High Court/Supreme Court Rulings)
    """
    def __init__(self):
        # In-memory index mock representations for dual retrieval
        self.legal_statutes_db = [
            {"id": "STAT_01", "title": "BNS Section 303 / IPC Section 378", "content": "Theft definition and punishment. Minimum sentence 3 years or fine."},
            {"id": "STAT_02", "title": "Consumer Protection Act 2019 Section 35", "content": "Filing a complaint before the District Consumer Commission for defective goods or service deficiency."},
            {"id": "STAT_03", "title": "Labour Code / Payment of Wages Act Section 15", "content": "Claims arising out of deductions from wages or delay in payment of wages."}
        ]
        self.case_examples_db = [
            {"id": "CASE_01", "title": "State of MH v. Sarita (2021)", "content": "Summary procedure for wage recovery in informal worker disputes."},
            {"id": "CASE_02", "title": "Gupta v. Electronics Ltd (2023)", "content": "Consumer court ordered full refund + compensation for non-functional appliances without warranty card."}
        ]

    def retrieve_legal_context(self, query: str) -> Dict[str, Any]:
        """
        Retrieves context from both Legal Knowledge RAG and Case Example RAG.
        """
        # Retrieve matching statutes
        matched_statutes = [
            item for item in self.legal_statutes_db
            if any(w.lower() in item["content"].lower() or w.lower() in item["title"].lower() for w in query.split())
        ] or [self.legal_statutes_db[0]]

        # Retrieve matching case precedents
        matched_cases = [
            item for item in self.case_examples_db
            if any(w.lower() in item["content"].lower() or w.lower() in item["title"].lower() for w in query.split())
        ] or [self.case_examples_db[0]]

        combined_context = f"LEGAL STATUTES: {matched_statutes[0]['title']} - {matched_statutes[0]['content']}\nCASE PRECEDENT: {matched_cases[0]['title']} - {matched_cases[0]['content']}"

        return {
            "statutes": matched_statutes,
            "cases": matched_cases,
            "combined_context_text": combined_context
        }

dual_rag_pipeline = DualRAGPipeline()
