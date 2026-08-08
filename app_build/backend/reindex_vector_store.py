"""
reindex_vector_store.py
-----------------------
Rebuilds ALL FAISS indexes from their existing _meta.json files using real
bge-large-en-v1.5 embeddings (now that sentence-transformers is installed).

Previously the indexes were built with zero-vectors because sentence-transformers
was missing at ingest time. This script re-embeds the stored text chunks and
overwrites only the .index files — the _meta.json files are kept as-is.

Run once from: app_build/backend/
  python reindex_vector_store.py
"""

import os, sys, json, time
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------- locate vector store ----------
from app.services.rag_service import dual_rag_pipeline
VECTOR_STORE = dual_rag_pipeline.retriever.retriever.manager.base_dir
print(f"Vector store: {VECTOR_STORE}\n")

# ---------- load embedding model ----------
print("Loading bge-large-en-v1.5 embedding model...")
t0 = time.perf_counter()
from sentence_transformers import SentenceTransformer
embed_model = SentenceTransformer("BAAI/bge-large-en-v1.5")
print(f"  Model loaded in {time.perf_counter()-t0:.1f}s\n")

# ---------- load FAISS ----------
try:
    import faiss
    FAISS_OK = True
except ImportError:
    FAISS_OK = False
    print("ERROR: faiss not available — cannot rebuild indexes.")
    sys.exit(1)

EMBED_DIM = 1024  # bge-large-en-v1.5 output dim
BGE_PREFIX = "Represent this sentence for searching relevant passages: "

def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    prefixed = [BGE_PREFIX + t for t in texts]
    vecs = embed_model.encode(
        prefixed,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return vecs.astype("float32")

total_rebuilt = 0
total_chunks  = 0

for collection in sorted(os.listdir(VECTOR_STORE)):
    col_path = os.path.join(VECTOR_STORE, collection)
    if not os.path.isdir(col_path):
        continue

    print(f"{'='*60}")
    print(f"Collection: {collection}")
    print(f"{'='*60}")

    for fname in sorted(os.listdir(col_path)):
        if not fname.endswith("_meta.json"):
            continue

        doc_id    = fname.replace("_meta.json", "")
        meta_path = os.path.join(col_path, fname)
        idx_path  = os.path.join(col_path, f"{doc_id}.index")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        if not meta:
            print(f"  [{doc_id}] 0 chunks — skipping")
            continue

        texts = [m.get("text", "") for m in meta]
        n     = len(texts)
        print(f"\n  [{doc_id}] {n} chunks — embedding...")

        t_start = time.perf_counter()
        vectors = embed_texts(texts)
        elapsed = time.perf_counter() - t_start
        print(f"  Embedded {n} chunks in {elapsed:.1f}s")

        # Rebuild FAISS index (Inner Product = cosine for normalized vecs)
        index = faiss.IndexFlatIP(EMBED_DIM)
        index.add(vectors)
        faiss.write_index(index, idx_path)
        print(f"  Wrote index → {idx_path} ({index.ntotal} vectors)")

        total_rebuilt += 1
        total_chunks  += n

print(f"\n{'='*60}")
print(f"REINDEX COMPLETE")
print(f"  Collections rebuilt : {total_rebuilt} sub-indexes")
print(f"  Total vectors stored: {total_chunks}")
print(f"{'='*60}\n")
print("Now re-run benchmark_rag.py to verify real cross-encoder scores.")
