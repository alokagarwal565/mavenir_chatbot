export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'ABSTAIN';

export interface QueryRequest {
  question: string;
  spec_filter?: string | null;
  release_filter?: number | null;
  debug?: boolean;
}

export interface ClaimSource {
  chunk_id: string;
  spec_number: string;
  release: number;
  version: string;
  section_number: string | null;
  section_title: string | null;
  page_start: number | null;
  excerpt: string;
  tags?: string[];
}

export interface Claim {
  text: string;
  source_ids: string[];
}

export interface FigureMatch {
  figure_number: string;
  figure_title: string;
  figure_type: string;
  mermaid_syntax: string | null;
  page_number: number;
}

export interface ScoredChunkDebug {
  chunk_id: string;
  spec_number: string;
  section_number: string | null;
  text_preview: string;
  rrf_score: number;
  reranker_score: number | null;
  vector_distance: number | null;
  tags?: string[];
}

export interface DebugInfo {
  evidence_score: number;
  retrieval_count: number;
  reranked_count: number;
  top_chunks: ScoredChunkDebug[];
  retrieval_ms: number;
  reranker_ms: number;
  llm_ms: number;
  tags_extracted?: string[];
  tag_confidence?: number;
}

export interface QueryResponse {
  request_id: string;
  question: string;
  answer: string;
  claims: Claim[];
  sources: ClaimSource[];
  figures?: FigureMatch[];
  confidence: ConfidenceLevel;
  abstained: boolean;
  abstain_reason: string | null;
  total_ms: number;
  debug?: DebugInfo | null;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  question?: string;
  specFilter?: string | null;
  releaseFilter?: number | null;
  response?: QueryResponse;
  error?: string;
  isLoading?: boolean;
}

export interface DocumentItem {
  id: string;
  spec_number: string;
  title: string;
  release: number;
  version: string;
  page_count: number;
  chunk_count: number;
  ingested_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  service: string;
  db: string;
}
