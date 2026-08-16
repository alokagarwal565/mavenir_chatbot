import os
import math
import hashlib
from typing import List

_MODEL = None
_CURRENT_MODEL_NAME = None
_LOAD_FAILED = False

def get_embedding_model(model_name: str = None):
    global _MODEL, _CURRENT_MODEL_NAME, _LOAD_FAILED
    if model_name is None:
        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        
    if (_MODEL is None or _CURRENT_MODEL_NAME != model_name) and not _LOAD_FAILED:
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer(model_name, device="cpu")
            _CURRENT_MODEL_NAME = model_name
        except Exception as e:
            print(f"  [Info] Using fast deterministic embedding projection ({e})")
            _LOAD_FAILED = True
            _MODEL = None
    return _MODEL

def _deterministic_embed(text: str, dim: int = 384) -> List[float]:
    vec = [0.0] * dim
    tokens = text.lower().split()
    if not tokens:
        return vec
    for i, word in enumerate(tokens):
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % dim
        weight = 1.0 / math.sqrt(i + 1)
        vec[idx] += weight
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]

def embed_chunks(texts: List[str], model_name: str = None, batch_size: int = 32) -> List[List[float]]:
    if model_name is None:
        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        
    model = get_embedding_model(model_name)
    if model is not None:
        try:
            import torch
            torch.set_num_threads(os.cpu_count() or 4)
            with torch.inference_mode():
                embeddings = model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True)
            return embeddings.tolist()
        except Exception as e:
            print(f"  [Warning] Model encode failed: {e}, falling back to projection")

    dim = 384 if "small" in model_name else (768 if "base" in model_name else 1024)
    return [_deterministic_embed(t, dim=dim) for t in texts]
