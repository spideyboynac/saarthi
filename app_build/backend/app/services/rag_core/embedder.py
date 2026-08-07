import numpy as np

# Lazy import — sentence_transformers is optional
try:
    from sentence_transformers import SentenceTransformer as _STClass
    _ST_AVAILABLE = True
except ImportError:
    _STClass = None
    _ST_AVAILABLE = False

_model = None
EMBEDDING_DIM = 1024  # bge-large-en-v1.5 output dimension

def get_model():
    global _model
    if not _ST_AVAILABLE:
        return None
    if _model is None:
        _model = _STClass("BAAI/bge-large-en-v1.5")
    return _model

def embed_chunks(chunks: list[dict], batch_size: int = 32) -> np.ndarray:
    """
    Takes a list of chunk dictionaries (which must contain a 'text' key),
    embeds the text using bge-large-en-v1.5, and returns the vectors as a NumPy array.
    Falls back to zero-vectors when sentence_transformers is unavailable.
    """
    if not chunks:
        return np.array([])
        
    model = get_model()
    if model is None:
        # Fallback: zero vectors (retrieval will score 0 but won't crash)
        return np.zeros((len(chunks), EMBEDDING_DIM), dtype='float32')

    texts = [chunk["text"] for chunk in chunks]
    # BGE models work best with normalized embeddings for cosine similarity.
    embeddings = model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
    return embeddings

def embed_query(query: str) -> np.ndarray:
    """
    Embeds a single query string.
    BGE models expect queries to be prefixed with an instruction for best retrieval.
    Falls back to a zero-vector when sentence_transformers is unavailable.
    """
    model = get_model()
    if model is None:
        return np.zeros(EMBEDDING_DIM, dtype='float32')
    # Official BGE query prefix
    query_text = f"Represent this sentence for searching relevant passages: {query}"
    embedding = model.encode([query_text], normalize_embeddings=True, show_progress_bar=False)[0]
    return embedding
