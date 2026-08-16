-- ============================================================================
-- 3GPP STANDARDS INTELLIGENCE KNOWLEDGE PIPELINE SCHEMA
-- Enterprise Edition: Catalog, Canonical AST, Decoupled Vectors & Observability
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. SPECIFICATION MASTER CATALOG & VERSIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS specifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_number         VARCHAR(20) NOT NULL UNIQUE, -- e.g., 'TS 23.501'
    series_number       VARCHAR(5) NOT NULL,         -- e.g., '23'
    spec_type           VARCHAR(5) NOT NULL,         -- 'TS' or 'TR'
    title               TEXT NOT NULL,
    description         TEXT,
    primary_wg          VARCHAR(20),                 -- 'SA2', 'CT1', 'RAN2', 'SA3', 'SA5'
    status              VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'withdrawn', 'historical'
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spec_versions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    specification_id    UUID NOT NULL REFERENCES specifications(id) ON DELETE CASCADE,
    spec_number         VARCHAR(20) NOT NULL,
    release_number      INTEGER NOT NULL,            -- e.g., 18
    version_string      VARCHAR(20) NOT NULL,        -- e.g., '18.4.0'
    version_letter_code VARCHAR(10) NOT NULL,        -- e.g., 'i40'
    ftp_relative_path   TEXT NOT NULL,               -- e.g., 'Rel-18/23_series/23501-i40.zip'
    raw_file_sha256     VARCHAR(64) NOT NULL,
    file_size_bytes     BIGINT NOT NULL,
    publication_date    DATE,
    is_latest_in_release BOOLEAN NOT NULL DEFAULT FALSE,
    is_latest_global    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT spec_versions_unique_idx UNIQUE (spec_number, release_number, version_string)
);

CREATE TABLE IF NOT EXISTS canonical_documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_version_id     UUID NOT NULL REFERENCES spec_versions(id) ON DELETE CASCADE,
    spec_number         VARCHAR(20) NOT NULL,
    release_number      INTEGER NOT NULL,
    version_string      VARCHAR(20) NOT NULL,
    title               TEXT NOT NULL,
    total_pages         INTEGER NOT NULL,
    total_sections      INTEGER NOT NULL DEFAULT 0,
    total_chunks        INTEGER NOT NULL DEFAULT 0,
    total_tables        INTEGER NOT NULL DEFAULT 0,
    total_figures       INTEGER NOT NULL DEFAULT 0,
    ast_storage_path    TEXT,                        -- S3 URI for serialized document AST
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (spec_version_id)
);

-- ============================================================================
-- 2. CANONICAL DOCUMENT AST NODES (SECTIONS, TABLES, FIGURES, REFERENCES)
-- ============================================================================

CREATE TABLE IF NOT EXISTS doc_sections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES canonical_documents(id) ON DELETE CASCADE,
    parent_section_id   UUID REFERENCES doc_sections(id) ON DELETE SET NULL,
    section_number      TEXT NOT NULL,               -- e.g., '4.2.2.2.2'
    section_title       TEXT NOT NULL,
    clause_level        INTEGER NOT NULL,            -- 1 for 4, 2 for 4.2, 5 for 4.2.2.2.2
    breadcrumb_path     TEXT NOT NULL,               -- '4 > 4.2 > 4.2.2 > 4.2.2.2 > 4.2.2.2.2'
    page_start          INTEGER NOT NULL,
    page_end            INTEGER NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doc_tables (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES canonical_documents(id) ON DELETE CASCADE,
    section_id          UUID REFERENCES doc_sections(id) ON DELETE CASCADE,
    table_number        TEXT,                        -- e.g., 'Table 5.2.2-1'
    table_title         TEXT,
    headers             JSONB NOT NULL,              -- Array of column header strings
    rows                JSONB NOT NULL,              -- 2D array of cell values
    markdown_grid       TEXT NOT NULL,
    page_number         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS doc_figures (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES canonical_documents(id) ON DELETE CASCADE,
    section_id          UUID REFERENCES doc_sections(id) ON DELETE CASCADE,
    figure_number       TEXT,                        -- e.g., 'Figure 4.2.2.2.2-1'
    figure_title        TEXT,                        -- e.g., 'Initial Registration Procedure'
    figure_type         VARCHAR(30) NOT NULL DEFAULT 'CALL_FLOW', -- 'CALL_FLOW', 'BLOCK_DIAGRAM', 'STATE_CHART'
    raw_image_path      TEXT,
    mermaid_syntax      TEXT,                        -- Executable Mermaid sequenceDiagram representation
    extracted_text      TEXT NOT NULL,               -- Textual message sequence for search
    page_number         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS doc_references (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc_id       UUID NOT NULL REFERENCES canonical_documents(id) ON DELETE CASCADE,
    source_section_id   UUID REFERENCES doc_sections(id) ON DELETE CASCADE,
    target_spec_number  VARCHAR(20) NOT NULL,        -- 'TS 24.501'
    target_clause       TEXT,                        -- 'Clause 5.5.1.2'
    reference_context   TEXT NOT NULL                -- Excerpt showing how it is referenced
);

-- ============================================================================
-- 3. DOCUMENT CHUNKS & MULTI-MODEL EMBEDDINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES canonical_documents(id) ON DELETE CASCADE,
    section_id          UUID REFERENCES doc_sections(id) ON DELETE SET NULL,
    chunk_index         INTEGER NOT NULL,
    spec_number         VARCHAR(20) NOT NULL,
    release_number      INTEGER NOT NULL,
    version_string      VARCHAR(20) NOT NULL,
    section_number      TEXT,
    section_title       TEXT,
    breadcrumb_path     TEXT,
    page_start          INTEGER NOT NULL,
    page_end            INTEGER NOT NULL,
    text                TEXT NOT NULL,               -- Full text stored in PostgreSQL
    token_count         INTEGER NOT NULL,
    fts_vector          TSVECTOR,                    -- Full-Text Search tsvector
    tags                TEXT[] DEFAULT '{}',         -- 7-layer taxonomy tags
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS chunk_embeddings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id            UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    model_name          VARCHAR(50) NOT NULL,        -- 'BAAI/bge-small-en-v1.5' or 'BAAI/bge-m3'
    embedding_dim       INTEGER NOT NULL,            -- 384 (Demo) or 1024 (Prod)
    embedding           halfvec(384) NOT NULL,       -- 16-bit float halfvec (384-dim for Demo tier)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chunk_id, model_name)
);

-- ============================================================================
-- 4. INGESTION STATE MACHINE & STAGE LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_number         VARCHAR(20) NOT NULL,
    release_number      INTEGER NOT NULL,
    version_string      VARCHAR(20) NOT NULL,
    current_stage       VARCHAR(30) NOT NULL DEFAULT 'DISCOVERED',
    -- Stages: 'DISCOVERED', 'DOWNLOADED', 'VERIFIED', 'PARSED', 'CHUNKED', 'EMBEDDED', 'COMPLETED', 'FAILED'
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    attempt_count       INTEGER NOT NULL DEFAULT 0,
    max_attempts        INTEGER NOT NULL DEFAULT 3,
    error_message       TEXT,
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (spec_number, release_number, version_string)
);

CREATE TABLE IF NOT EXISTS ingestion_stage_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id              UUID NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
    stage_name          VARCHAR(30) NOT NULL,
    status              VARCHAR(20) NOT NULL,        -- 'SUCCESS', 'FAILED', 'RETRY'
    duration_ms         INTEGER NOT NULL,
    metrics             JSONB DEFAULT '{}',          -- {pages: 540, chunks: 720, bytes: 4200000}
    error_detail        TEXT,
    logged_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS query_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id          TEXT NOT NULL UNIQUE,
    query_hash          TEXT NOT NULL,
    detected_spec       TEXT,
    detected_release    INTEGER,
    retrieval_count     INTEGER,
    reranked_count      INTEGER,
    confidence          TEXT,
    abstained           BOOLEAN NOT NULL DEFAULT FALSE,
    citation_count      INTEGER,
    citation_valid      BOOLEAN,
    llm_provider        TEXT,
    llm_model           TEXT,
    retrieval_ms        INTEGER,
    reranker_ms         INTEGER,
    llm_ms              INTEGER,
    total_ms            INTEGER,
    llm_timeout_count   INTEGER DEFAULT 0,
    model_fallback_used BOOLEAN DEFAULT FALSE,
    key_fallback_used   BOOLEAN DEFAULT FALSE,
    input_tokens        INTEGER DEFAULT 0,
    output_tokens       INTEGER DEFAULT 0,
    cost_usd            NUMERIC(10, 6) DEFAULT 0.0,
    cost_warn_flag      BOOLEAN DEFAULT FALSE,
    user_query          TEXT,
    streaming_used      BOOLEAN DEFAULT FALSE,
    history_turns_sent  INTEGER DEFAULT 0,
    history_tokens_sent INTEGER DEFAULT 0,
    first_token_ms      INTEGER,
    stream_cancelled    BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evaluation_questions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id         TEXT NOT NULL UNIQUE,
    spec_number         TEXT NOT NULL,
    release             INTEGER NOT NULL,
    section             TEXT NOT NULL,
    category            TEXT NOT NULL,
    question            TEXT NOT NULL,
    ground_truth_answer TEXT NOT NULL,
    ground_truth_clause TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_run_id   TEXT NOT NULL,
    question_id         TEXT NOT NULL,
    generated_answer    TEXT,
    confidence          TEXT,
    abstained           BOOLEAN,
    citation_valid      BOOLEAN,
    context_recall      FLOAT,
    context_precision   FLOAT,
    faithfulness        FLOAT,
    answer_relevance    FLOAT,
    latency_ms          INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 6. HIGH-PERFORMANCE INDEXES
-- ============================================================================

-- HNSW Vector Indexes (Cosine Distance)

CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw 
ON chunk_embeddings USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-Text Search GIN Indexes
CREATE INDEX IF NOT EXISTS idx_document_chunks_fts 
ON document_chunks USING gin (fts_vector);

-- Multi-Layer Taxonomy Tag GIN Indexes
CREATE INDEX IF NOT EXISTS idx_document_chunks_tags 
ON document_chunks USING gin (tags);

-- Release & Spec Fast Filtering B-Tree Indexes
CREATE INDEX IF NOT EXISTS idx_spec_versions_lookup 
ON spec_versions (spec_number, release_number, is_latest_global);

CREATE INDEX IF NOT EXISTS idx_document_chunks_lookup 
ON document_chunks (spec_number, release_number, section_number);

CREATE INDEX IF NOT EXISTS idx_doc_sections_lookup 
ON doc_sections (document_id, section_number);

CREATE INDEX IF NOT EXISTS idx_doc_figures_lookup 
ON doc_figures (document_id, figure_number);

CREATE INDEX IF NOT EXISTS idx_query_logs_created_at 
ON query_logs (created_at DESC);
