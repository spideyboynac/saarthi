import re
from transformers import AutoTokenizer

CHUNK_SIZE = 512
OVERLAP = 64

_tokenizer = None

def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-large-en-v1.5")
    return _tokenizer

def chunk_document(text: str, doc_id: str, extra_metadata: dict = None) -> list[dict]:
    """
    Splits text into strict 512-token chunks with a 64-token overlap.
    Returns chunks with attached metadata.
    """
    if extra_metadata is None:
        extra_metadata = {}
        
    tokenizer = get_tokenizer()
    tokens = tokenizer(text, add_special_tokens=False)["input_ids"]
    
    chunks = []
    chunk_index = 0
    start = 0
    
    if not tokens:
        return []
        
    while start < len(tokens):
        end = start + CHUNK_SIZE
        chunk_tokens = tokens[start:end]
        
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
        
        # Build metadata
        chunk_meta = {
            "doc_id": doc_id,
            "chunk_index": chunk_index,
            "text": chunk_text
        }
        # Attach additional citation info if provided
        chunk_meta.update(extra_metadata)
        
        chunks.append(chunk_meta)
        
        if end >= len(tokens):
            break
            
        start += (CHUNK_SIZE - OVERLAP)
        chunk_index += 1
        
    return chunks

def semantic_chunk_document(text: str, doc_id: str, extra_metadata: dict = None) -> list[dict]:
    """
    Semantically chunks the document by Chapter, Section, or Article.
    If a chunk exceeds the token limit, it applies the 512/64 overlapping chunker to that block.
    """
    if extra_metadata is None:
        extra_metadata = {}
        
    pattern = r'(?i)(\n\s*(?:Chapter|Section|Article)\s+[A-Za-z\dIVX]+[^\n]*)'
    parts = re.split(pattern, text)
    
    blocks = []
    if parts[0].strip():
        blocks.append(parts[0].strip())
        
    for i in range(1, len(parts), 2):
        header = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ""
        blocks.append((header + content).strip())
        
    all_chunks = []
    tokenizer = get_tokenizer()
    
    # We manage global chunk_index across blocks for this document
    global_chunk_index = 0
    for block in blocks:
        if not block:
            continue
            
        tokens = tokenizer(block, add_special_tokens=False)["input_ids"]
        if len(tokens) <= CHUNK_SIZE:
            chunk_meta = {
                "doc_id": doc_id,
                "chunk_index": global_chunk_index,
                "text": block
            }
            chunk_meta.update(extra_metadata)
            all_chunks.append(chunk_meta)
            global_chunk_index += 1
        else:
            # For long sections, use the robust 512/64 overlapping chunker
            sub_chunks = chunk_document(block, doc_id, extra_metadata)
            for sc in sub_chunks:
                sc["chunk_index"] = global_chunk_index
                all_chunks.append(sc)
                global_chunk_index += 1
                
    return all_chunks

