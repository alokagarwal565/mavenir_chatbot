import json
from typing import List, Dict, Any, Optional
import asyncpg
from app.logging_config import get_logger
from app.providers.base import ScoredChunk

logger = get_logger(__name__)

# ============================================================================
# RETRIEVAL QUERIES
# ============================================================================

async def vector_search(
    pool: asyncpg.Pool,
    query_vector: List[float],
    release_filter: Optional[int] = None,
    spec_filter: Optional[str] = None,
    top_k: int = 40
) -> List[ScoredChunk]:
    """Executes dense HNSW vector search using cosine distance in PostgreSQL."""
    vector_str = f"[{','.join(map(str, query_vector))}]"
    
    query = """
        SELECT 
            c.id,
            c.document_id,
            COALESCE(c.spec_number, 'Unknown') AS spec_number,
            COALESCE(c.release_number, 18) AS release,
            COALESCE(c.version_string, '18.0.0') AS version,
            c.section_number,
            c.section_title,
            NULL AS parent_section,
            c.page_start,
            c.page_end,
            c.text,
            COALESCE(c.token_count, 0) AS token_count,
            c.tags,
            (ce.embedding <=> $1::halfvec) AS vector_distance
        FROM document_chunks c
        JOIN chunk_embeddings ce ON c.id = ce.chunk_id
        WHERE ($2::text IS NULL OR c.spec_number = $2)
          AND ($3::int IS NULL OR c.release_number = $3)
        ORDER BY ce.embedding <=> $1::halfvec
        LIMIT $4;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, vector_str, spec_filter, release_filter, top_k)
        results = []
        for r in rows:
            results.append(ScoredChunk(
                chunk_id=str(r["id"]),
                document_id=str(r["document_id"]),
                spec_number=r["spec_number"],
                release=r["release"],
                version=r["version"],
                section_number=r["section_number"],
                section_title=r["section_title"],
                parent_section=r["parent_section"] if "parent_section" in r else None,
                page_start=r["page_start"],
                page_end=r["page_end"],
                text=r["text"],
                token_count=r["token_count"],
                vector_distance=float(r["vector_distance"]) if r["vector_distance"] is not None else None,
                tags=list(r["tags"]) if r["tags"] else []
            ))
        return results

async def lexical_search(
    pool: asyncpg.Pool,
    query_text: str,
    release_filter: Optional[int] = None,
    spec_filter: Optional[str] = None,
    top_k: int = 40
) -> List[ScoredChunk]:
    """Executes BM25-style full-text search with ts_rank_cd over English FTS tsvector."""
    query = """
        SELECT 
            c.id,
            c.document_id,
            COALESCE(c.spec_number, 'Unknown') AS spec_number,
            COALESCE(c.release_number, 18) AS release,
            COALESCE(c.version_string, '18.0.0') AS version,
            c.section_number,
            c.section_title,
            NULL AS parent_section,
            c.page_start,
            c.page_end,
            c.text,
            COALESCE(c.token_count, 0) AS token_count,
            c.tags,
            ts_rank_cd(c.fts_vector, plainto_tsquery('english', $1)) AS lexical_score
        FROM document_chunks c
        WHERE c.fts_vector @@ plainto_tsquery('english', $1)
          AND ($2::text IS NULL OR c.spec_number = $2)
          AND ($3::int IS NULL OR c.release_number = $3)
        ORDER BY lexical_score DESC
        LIMIT $4;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, query_text, spec_filter, release_filter, top_k)
        results = []
        for r in rows:
            results.append(ScoredChunk(
                chunk_id=str(r["id"]),
                document_id=str(r["document_id"]),
                spec_number=r["spec_number"],
                release=r["release"],
                version=r["version"],
                section_number=r["section_number"],
                section_title=r["section_title"],
                parent_section=r["parent_section"] if "parent_section" in r else None,
                page_start=r["page_start"],
                page_end=r["page_end"],
                text=r["text"],
                token_count=r["token_count"],
                tags=list(r["tags"]) if r["tags"] else []
            ))
        return results

async def query_figures_by_section(
    pool: asyncpg.Pool,
    spec_number: str,
    section_number: str
) -> List[Dict[str, Any]]:
    """Fetches extracted call flow diagrams / Mermaid AST for a specific section."""
    query = """
        SELECT 
            f.id,
            f.figure_number,
            f.figure_title,
            f.figure_type,
            f.mermaid_syntax,
            f.extracted_text,
            f.page_number
        FROM doc_figures f
        JOIN canonical_documents cd ON f.document_id = cd.id
        WHERE cd.spec_number = $1
          AND ($2::text IS NULL OR f.figure_title ILIKE '%' || $2 || '%')
        LIMIT 5;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, spec_number, section_number)
        return [dict(r) for r in rows]

# ============================================================================
# LOGGING QUERIES
# ============================================================================

async def insert_query_log(pool: Optional[asyncpg.Pool], log_data: Dict[str, Any]) -> None:
    """Inserts a structured query execution record into query_logs."""
    if pool is None:
        return
    query = """
        INSERT INTO query_logs (
            request_id, query_hash, detected_spec, detected_release,
            retrieval_count, reranked_count, confidence, abstained,
            citation_count, citation_valid, llm_provider, llm_model,
            retrieval_ms, reranker_ms, llm_ms, total_ms,
            llm_timeout_count, model_fallback_used, key_fallback_used,
            input_tokens, output_tokens, cost_usd, cost_warn_flag,
            user_query, streaming_used, history_turns_sent, history_tokens_sent,
            first_token_ms, stream_cancelled
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
            $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24,
            $25, $26, $27, $28, $29
        );
    """
    async with pool.acquire() as conn:
        await conn.execute(
            query,
            log_data.get("request_id"),
            log_data.get("query_hash"),
            log_data.get("detected_spec"),
            log_data.get("detected_release"),
            log_data.get("retrieval_count", 0),
            log_data.get("reranked_count", 0),
            log_data.get("confidence", "LOW"),
            log_data.get("abstained", False),
            log_data.get("citation_count", 0),
            log_data.get("citation_valid", False),
            log_data.get("llm_provider", "gemini"),
            log_data.get("llm_model", "gemini-3.5-flash-lite"),
            log_data.get("retrieval_ms", 0),
            log_data.get("reranker_ms", 0),
            log_data.get("llm_ms", 0),
            log_data.get("total_ms", 0),
            log_data.get("llm_timeout_count", 0),
            log_data.get("model_fallback_used", False),
            log_data.get("key_fallback_used", False),
            log_data.get("input_tokens", 0),
            log_data.get("output_tokens", 0),
            log_data.get("cost_usd", 0.0),
            log_data.get("cost_warn_flag", False),
            log_data.get("user_query"),
            log_data.get("streaming_used", False),
            log_data.get("history_turns_sent", 0),
            log_data.get("history_tokens_sent", 0),
            log_data.get("first_token_ms"),
            log_data.get("stream_cancelled", False)
        )

async def get_documents_list(pool: Optional[asyncpg.Pool]) -> List[Dict[str, Any]]:
    """Returns the list of ingested specifications and documents."""
    if pool is None:
        return []
    query = """
        SELECT 
            cd.id::text,
            cd.spec_number,
            cd.title,
            cd.release_number AS release,
            cd.version_string AS version,
            cd.total_pages AS page_count,
            cd.total_chunks AS chunk_count,
            cd.ingested_at
        FROM canonical_documents cd
        ORDER BY cd.spec_number, cd.release_number DESC;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query)
        return [dict(r) for r in rows]

log_query_event = insert_query_log
