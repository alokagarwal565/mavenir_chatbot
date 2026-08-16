from app.services.tag_extractor import QueryTagExtractor
import re
from app.logging_config import get_logger
from typing import List, Optional, Tuple
from app.providers.base import ScoredChunk, EmbeddingProvider
from app.db.queries import vector_search, lexical_search
from starlette.concurrency import run_in_threadpool

logger = get_logger(__name__)

STOPWORDS = {"what", "is", "the", "are", "for", "in", "of", "and", "to", "a", "an", "does", "specify", "about", "per", "how"}

class RetrieverService:
    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedder = embedding_provider

    async def retrieve(
        self,
        pool,
        query: str,
        release_filter: Optional[int] = 18,
        spec_filter: Optional[str] = None
    ) -> Tuple[List[ScoredChunk], bool]:
        fallback_used = False

        # 1. Dense vector search
        query_vec = await run_in_threadpool(self.embedder.embed_query, query)
        
        if query_vec:
            vector_candidates = await vector_search(
                pool=pool,
                query_vector=query_vec,
                release_filter=release_filter,
                spec_filter=spec_filter,
                top_k=40
            )
        else:
            vector_candidates = []

        # 2. Lexical search
        lexical_candidates = await lexical_search(
            pool=pool,
            query_text=query,
            release_filter=release_filter,
            spec_filter=spec_filter,
            top_k=20
        )

        # 3. FM-1: Keyword fallback if both dense and lexical return 0
        if not vector_candidates and not lexical_candidates:
            terms = [t for t in re.findall(r'\w+', query.lower()) if t not in STOPWORDS and len(t) > 2]
            if terms:
                fallback_used = True
                fallback_query = " OR ".join(terms[:5])
                logger.info("keyword_fallback_triggered", query=fallback_query)
                lexical_candidates = await lexical_search(
                    pool=pool,
                    query_text=fallback_query,
                    release_filter=release_filter,
                    spec_filter=spec_filter,
                    top_k=20
                )

        # Extract query tags for soft boosting
        tag_info = QueryTagExtractor.extract(query)
        q_tags = set(tag_info.get("tags", []))

        # 4. Reciprocal Rank Fusion (RRF, k=60) with soft tag overlap boost
        chunk_map = {}
        rrf_scores = {}
        k = 60

        for rank, c in enumerate(vector_candidates):
            cid = c.chunk_id
            chunk_map[cid] = c
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        for rank, c in enumerate(lexical_candidates):
            cid = c.chunk_id
            if cid not in chunk_map:
                chunk_map[cid] = c
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        fused = []
        for cid, score in rrf_scores.items():
            chunk = chunk_map[cid]
            # Soft tag overlap boost (no hard pruning)
            if q_tags and chunk.tags:
                overlap = len(set(chunk.tags).intersection(q_tags))
                score += (0.015 * overlap)
            chunk.rrf_score = score
            fused.append(chunk)

        # Sort descending by RRF score
        fused_sorted = sorted(fused, key=lambda x: x.rrf_score, reverse=True)
        return fused_sorted[:60], fallback_used
