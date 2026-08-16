from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW", "ABSTAIN"]

class ConversationTurn(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(..., max_length=10000)

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="Natural language question about 3GPP 5GS specifications")
    conversation_history: List[ConversationTurn] = Field(default_factory=list, max_length=20, description="Previous conversation turns")
    spec_filter: Optional[str] = Field(None, description="Optional specification filter, e.g., 'TS 23.501'")
    release_filter: Optional[int] = Field(18, description="Release filter (default 18)")
    debug: bool = Field(False, description="Whether to include retrieval scores and debugging metadata")

class StreamQueryRequest(QueryRequest):
    pass

class ClaimSource(BaseModel):
    chunk_id: str
    spec_number: str
    release: int
    version: str
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    page_start: Optional[int] = None
    excerpt: str

class Claim(BaseModel):
    text: str
    source_ids: List[str]

class ScoredChunkDebug(BaseModel):
    chunk_id: str
    spec_number: str
    section_number: Optional[str] = None
    text_preview: str
    rrf_score: float
    reranker_score: Optional[float] = None
    vector_distance: Optional[float] = None

class DebugInfo(BaseModel):
    evidence_score: float
    retrieval_count: int
    reranked_count: int
    top_chunks: List[ScoredChunkDebug]
    retrieval_ms: int
    reranker_ms: int
    llm_ms: int

class LLMResponse(BaseModel):
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_fallback_used: bool = False
    key_fallback_used: bool = False

class QueryResponse(BaseModel):
    request_id: str
    question: str
    answer: str
    claims: List[Claim]
    sources: List[ClaimSource]
    confidence: ConfidenceLevel
    abstained: bool
    abstain_reason: Optional[str] = None
    total_ms: int
    debug: Optional[DebugInfo] = None

class DocumentItem(BaseModel):
    id: str
    spec_number: str
    title: str
    release: int
    version: str
    page_count: Optional[int] = None
    chunk_count: int = 0
    ingested_at: str

class ErrorResponse(BaseModel):
    request_id: str
    error_code: str
    message: str
    details: Optional[Any] = None

class StreamEvent(BaseModel):
    type: Literal["status", "token", "citations", "metadata", "abstain", "error", "done"]
    data: Dict[str, Any]

