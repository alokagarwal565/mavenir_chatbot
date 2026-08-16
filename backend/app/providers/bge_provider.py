import os
import math
import hashlib
from typing import List, Optional
from app.logging_config import get_logger
from app.providers.base import ScoredChunk

logger = get_logger(__name__)

class BGEEmbeddingProvider:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self._model = None
        self._load_attempted = False

    def _get_model(self):
        if not self._load_attempted:
            self._load_attempted = True
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device="cpu")
                logger.info("loaded_embedding_model", model=self.model_name)
            except Exception as e:
                logger.info("using_fast_deterministic_embedding", reason=str(e))
                self._model = None
        return self._model

    def embed_query(self, text: str) -> List[float]:
        if os.environ.get("RENDER"):
            logger.info("skipping_embeddings_on_render_free_tier_to_prevent_oom")
            return []

        model = self._get_model()
        if model is not None:
            try:
                emb = model.encode(text, normalize_embeddings=True)
                return emb.tolist()
            except Exception as e:
                logger.warning("embedding_encode_failed_using_fallback", error=str(e))

        # Dynamic normalized projection fallback
        dim = 384 if "small" in self.model_name else (768 if "base" in self.model_name else 1024)
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

class BGEReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._cross_encoder = None
        self._load_attempted = False

    def _get_model(self):
        if not self._load_attempted:
            self._load_attempted = True
            try:
                from sentence_transformers import CrossEncoder
                self._cross_encoder = CrossEncoder(self.model_name, device="cpu")
                logger.info("loaded_reranker_model", model=self.model_name)
            except Exception as e:
                logger.info("using_rrf_scoring_without_heavy_reranker", reason=str(e))
                self._cross_encoder = None
        return self._cross_encoder

    def rerank(self, query: str, candidates: List[ScoredChunk], top_k: int = 8) -> List[ScoredChunk]:
        if not candidates:
            return []
        
        if os.environ.get("RENDER"):
            logger.info("skipping_reranker_on_render_free_tier_to_prevent_oom")
            return candidates[:top_k]
        
        model = self._get_model()
        if model is not None:
            try:
                pairs = [[query, c.text] for c in candidates]
                scores = model.predict(pairs)
                for chunk, score in zip(candidates, scores):
                    chunk.reranker_score = float(score)

                scored = sorted(candidates, key=lambda x: x.reranker_score if x.reranker_score is not None else -1.0, reverse=True)
                return scored[:top_k]
            except Exception as e:
                logger.warning("reranker_predict_failed_using_rrf", error=str(e))

        return candidates[:top_k]
