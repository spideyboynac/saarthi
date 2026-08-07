from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    return _model

def embed_chunks(chunks: list[dict], batch_size: int = 32) -> np.ndarray:
    """
    Takes a list of chunk dictionaries (which must contain a 'text' key),
    embeds the text using bge-large-en-v1.5, and returns the vectors as a NumPy array.
    """
    if not chunks:
        return np.array([])
        
    model = get_model()
    texts = [chunk["text"] for chunk in chunks]
    
    # BGE models work best with normalized embeddings for cosine similarity.
    embeddings = model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
    return embeddings

def embed_query(query: str) -> np.ndarray:
    """
    Embeds a single query string.
    BGE models expect queries to be prefixed with an instruction for best retrieval.
    """
    model = get_model()
    # Official BGE query prefix
    query_text = f"Represent this sentence for searching relevant passages: {query}"
    embedding = model.encode([query_text], normalize_embeddings=True, show_progress_bar=False)[0]
    return embedding
