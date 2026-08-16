from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ScoredChunk:
    chunk_id: str
    document_id: str
    spec_number: str
    release: int
    version: str
    section_number: Optional[str]
    section_title: Optional[str]
    parent_section: Optional[str]
    page_start: Optional[int]
    page_end: Optional[int]
    text: str
    token_count: int
    rrf_score: float = 0.0
    reranker_score: Optional[float] = None
    vector_distance: Optional[float] = None
    tags: Optional[List[str]] = None

class EmbeddingProvider(Protocol):
    def embed_query(self, text: str) -> List[float]:
        ...

class Reranker(Protocol):
    def rerank(self, query: str, candidates: List[ScoredChunk]) -> List[ScoredChunk]:
        ...

class LLMProvider(Protocol):
    async def generate(self, prompt: str, system: str) -> Any:
        ...
