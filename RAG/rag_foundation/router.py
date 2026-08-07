from enum import Enum

class QueryType(Enum):
    STATUTE_LOOKUP = "statute_lookup"
    CASE_PRECEDENT = "case_precedent"
    MIXED = "mixed"
    UNCLEAR = "unclear"

def get_target_collections(query_type: QueryType) -> list[str]:
    """
    Explicitly routes a typed query intent to the correct FAISS collections.
    This serves as the narrow, obvious contract with the upstream classifier.
    """
    if query_type == QueryType.STATUTE_LOOKUP:
        return ["legal_knowledge"]
    elif query_type == QueryType.CASE_PRECEDENT:
        return ["case_examples"]
    elif query_type in (QueryType.MIXED, QueryType.UNCLEAR):
        # Route to BOTH collections
        return ["legal_knowledge", "case_examples"]
    else:
        # Failsafe default to broad search
        return ["legal_knowledge", "case_examples"]
