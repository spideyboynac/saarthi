# Dual-RAG Shared Foundation

This document outlines the architecture, integration contracts, and explicit exclusions of the `rag_foundation` module for the Dual-RAG Legal Literacy project. This documentation is written for the UX, Cloud/Twilio, and Offline Orchestration tracks to integrate against this layer seamlessly.

## Architecture & Two-Collection Design
The core engine utilizes FAISS operating on a **per-document sub-indexing** pattern. We maintain two strictly separated FAISS collections:
1. **`legal_knowledge`**: Contains official government acts, statutes, and FAQs. Chunked semantically by Chapter/Section.
2. **`case_examples`**: Contains synthetic/real case precedents. Chunked in fixed 512-token blocks and grouped into sub-indices by topic.

Both collections share the exact same `chunker.py`, `embedder.py` (`bge-large-en-v1.5`), and `IndexManager`.

## Integration Contract (Output)
The downstream LLM orchestration layer interacts exclusively with the `RefiningRetriever` in `refine.py`. 

Every retrieval action returns a strictly typed `RetrievalResult` data object (defined in `models.py`) containing:
- `passages`: A list of the top-5 reranked dictionary chunks, universally equipped with citation metadata (`doc_id`, `source_file`, `text`, etc.).
- `collections_queried`: A list of the FAISS namespaces searched (e.g., `["legal_knowledge"]`).
- `confidence_score`: The raw MS-MARCO cross-encoder float score of the top candidate.
- `confidence_tier`: A categorical `ConfidenceTier` Enum (`HIGH`, `MEDIUM`, `LOW`, `NONE`) calculated from tunable thresholds.
- `is_retry`: A boolean indicating if this was a refinement pass.
- `attempt_number`: The current retry attempt counter.

## Routing Contract
The module accepts a `QueryType` Enum from the upstream intent classifier. 
- `QueryType.STATUTE_LOOKUP`: Routes purely to the `legal_knowledge` index.
- `QueryType.CASE_PRECEDENT`: Routes purely to the `case_examples` index.
- `QueryType.MIXED` or `QueryType.UNCLEAR`: Triggers a parallel search across both indices, merging and re-ranking the combined candidates via the Cross-Encoder.

## 🛑 Explicit Exclusions (Integration Warning)
This module acts *strictly* as an information retrieval layer. The following functionalities have been explicitly banished from this codebase to preserve architectural purity:
1. **No LLM Generation**: This module retrieves text; it does not converse or generate answers.
2. **No Intent Classification**: The upstream engine must pass the typed `QueryType`. We do not classify raw strings here.
3. **No ASR / TTS / Cloud Telephony**: Twilio logic and voice streaming are handled by the Cloud track.
4. **No Translation Layer**: All inputs to this module must already be translated to English, and all outputs will be in English. The `IndicTrans2` layer resides downstream.
5. **No Call-flow Shortcuts**: Handling numpad keys (3/4/5 for repeat/simplify) is managed by the cache in the orchestrator.
6. **No Infinite Loops**: The refinement retry mechanism enforces a hard cap (`max_retries`) exposed during instantiation. The LLM must make the judgment of "is this sufficient"; this module merely executes the re-retrieval.
