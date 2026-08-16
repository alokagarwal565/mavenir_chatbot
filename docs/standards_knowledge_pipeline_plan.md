# Production-Grade 3GPP Standards Knowledge Pipeline
## Master Architectural Blueprint & Implementation Plan

> **Document Version:** 2.3.0 (All-in-PostgreSQL Curated Core 5GS Architecture · $0/mo Neon Free Tier)  
> **Target Scope:** Complete 3GPP Standards Body (All Series 01–55, Releases 15–20, TS & TR Documents)  
> **Status:** Architectural Proposal & Implementation Blueprint  
> **Author:** Principal AI/ML Systems Architect, 3GPP Telecom Domain Specialist, Database Reliability Engineer  

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Analysis](#2-current-architecture-analysis)
3. [Current Implementation Strengths](#3-current-implementation-strengths)
4. [Current Implementation Weaknesses](#4-current-implementation-weaknesses)
5. [Target Architecture](#5-target-architecture)
6. [Data Model Changes](#6-data-model-changes)
7. [3GPP Corpus Strategy](#7-3gpp-corpus-strategy)
8. [Source Discovery Strategy](#8-source-discovery-strategy)
9. [Version & Release Management](#9-version--release-management)
10. [Immutable Raw Document Storage](#10-immutable-raw-document-storage)
11. [High-Fidelity Parsing Architecture](#11-high-fidelity-parsing-architecture)
12. [Canonical Document Representation (AST)](#12-canonical-document-representation-ast)
13. [Section-Aware & Structure-Preserving Chunking](#13-section-aware--structure-preserving-chunking)
14. [Layered Tagging Architecture](#14-layered-tagging-architecture)
15. [Taxonomy Design](#15-taxonomy-design)
16. [Hybrid Retrieval Architecture](#16-hybrid-retrieval-architecture)
17. [Reranking Strategy](#17-reranking-strategy)
18. [Citation & Provenance Architecture](#18-citation--provenance-architecture)
19. [Cross-Reference & Knowledge Graph Strategy](#19-cross-reference--knowledge-graph-strategy)
20. [Embedding Architecture](#20-embedding-architecture)
21. [Asynchronous Ingestion Job Architecture](#21-asynchronous-ingestion-job-architecture)
22. [Continuous Corpus Update Strategy](#22-continuous-corpus-update-strategy)
23. [Evaluation Framework](#23-evaluation-framework)
24. [Observability & Telemetry](#24-observability--telemetry)
25. [Security & Untrusted Document Defense](#25-security--untrusted-document-defense)
26. [Scalability & Capacity Planning](#26-scalability--capacity-planning)
27. [Cost Considerations](#27-cost-considerations)
28. [Migration Strategy](#28-migration-strategy)
29. [Phased Implementation Roadmap](#29-phased-implementation-roadmap)
30. [Testing Strategy](#30-testing-strategy)
31. [Deployment Architecture](#31-deployment-architecture)
32. [Risks & Mitigations](#32-risks--mitigations)
33. [Open Decisions & Technical Trade-offs](#33-open-decisions--technical-trade-offs)
34. [File-Level Implementation Plan](#34-file-level-implementation-plan)
35. [Database Migration Plan](#35-database-migration-plan)
36. [Backward Compatibility Assurance](#36-backward-compatibility-assurance)
37. [Definition of Done](#37-definition-of-done)

---

## 1. Executive Summary

The existing Mavenir 3GPP RAG platform functions as an evaluation prototype indexed over a static set of 5 Release 18 specifications (`TS 23.501`, `TS 23.502`, `TS 24.501`, `TS 38.331`, `TS 33.501`). While it establishes solid foundational patterns (hybrid pgvector + FTS search, deterministic citation validation, and an evidence score gate), its ingestion and storage model cannot scale to the **complete, versioned, continuously changing 3GPP standards ecosystem**.

The complete 3GPP corpus spans:
- **55 Specification Series** covering radio, core, security, codecs, management, and protocols.
- **Multiple active and historical releases** (Rel-15 through Rel-18 in production; Rel-19/Rel-20 in drafting).
- **Over 4,500 distinct specifications** and **over 85,000 document versions/revisions**, totaling over **3.2 million pages** of normative text, tables, message structures, and call flows.

This document presents a comprehensive, production-grade architectural blueprint to evolve the system into an **enterprise-scale, version-aware, continuously maintained 3GPP Standards Knowledge Platform**.

---

## 2. Current Architecture Analysis

The existing codebase consists of:
- `backend/`: FastAPI application containing synchronous/async database queries, BGE embedding and reranking providers, Gemini LLM cascade provider, and deterministic grounding services.
- `ingestion/`: Monolithic, sequential ingestion script that downloads 5 hard-coded specs, runs basic PyMuPDF extraction for PDFs **and** python‑docx parsing for Word documents, chunks on token limits, embeds with BGE-M3, and writes directly to `documents` and `chunks` tables.
- `frontend/`: React + Vite + TypeScript interface for query input, custom dropdown spec filtering, citation card rendering, and diagnostic inspection.

### Current Retrieval & Generation Data Flow
```
User Query ──► QueryTagExtractor ──► pgvector HNSW (top-40) + FTS (top-20) 
           ──► Tag-Boosted RRF Fusion (top-60) ──► BGE Cross-Encoder Reranker (top-8) 
           ──► Evidence Gate (threshold 0.25) ──► Gemini Cascade ──► Citation Validator ──► Response
```

---

## 3. Current Implementation Strengths

1. **Deterministic Citation & Grounding Gate:** The 8-point validator in `backend/app/services/citation_validator.py` ensures generated claims strictly match retrieved chunks and verifies UUID authenticity.
2. **Hybrid Search with Reciprocal Rank Fusion (RRF):** Combining dense vector similarity (`pgvector` HNSW) with lexical search (`tsvector` GIN) via RRF ($k=60$) provides robust initial retrieval for telecom terms.
3. **Resilient Multi-Stage LLM Cascade:** The 4-stage fallback cascade in `backend/app/providers/gemini_provider.py` (Primary Model $\to$ Exponential Retry $\to$ Fallback Model $\to$ Backup Key) prevents rate-limit and transient provider outages.
4. **Prompt Injection XML Sanitization:** Escapes delimiters in user input before prompt framing (`</question><chunks>`).
5. **Zero-Cost Ingestion Tagger:** Rule-based 4-layer classifier in `ingestion/tagger.py` extracts Domain, NF, Procedure, and Clause Type tags without per-chunk LLM API costs.

---

## 4. Current Implementation Weaknesses

1. **Static 5-Spec Manifest:** Ingestion is restricted to a hard-coded YAML list. Cannot discover, index, or maintain the other 4,500+ specifications.
2. **Fragile Versioning:** The `documents` table uses `UNIQUE(spec_number, release, checksum)`. Updating a revision (e.g. v18.6.0 $\to$ v18.7.0) either fails or overwrites the previous version.
3. **Monolithic Ingestion Script:** The pipeline in `ingestion/pipeline.py` is a single synchronous loop. If embedding fails on chunk 4,000, the entire document must be re-downloaded and re-parsed.
4. **Parsing Text Flattening:** Basic PDF (PyMuPDF) and DOCX (python‑docx) extraction drop Markdown tables (ASN.1 IE tables, timer value matrices) and flatten nested clause hierarchies.
5. **Tightly Coupled Vectors:** Chunks table has a fixed `embedding VECTOR(1024)` column. Migrating to another embedding model requires schema destruction.
6. **No Relational Cross-Referencing:** Chunks are isolated without normative reference mapping.

---

## 5. Target Architecture

```
                             Official 3GPP FTP Archive (ftp.3gpp.org)
                                               │
                                               ▼
                              [Specification Discovery Engine]
                                               │
                                               ▼
                              [Master Catalog & Release Manager]
                                 (PostgreSQL Catalog Schema)
                                               │
                                               ▼
                              [Asynchronous Stage Worker Queue]
                                               │
                ┌──────────────────────────────┼──────────────────────────────┐
                ▼                              ▼                              ▼
        [STAGE 1: DOWNLOAD]           [STAGE 2: VALIDATE]            [STAGE 3: PARSE]
        Immutable CAS Storage         Checksum & File Format         Docling / AST Parser
        data/storage/raw/             Verification (SHA-256)         Preserves Tables & Trees
                │                              │                              │
                └──────────────────────────────┼──────────────────────────────┘
                                               │
                ┌──────────────────────────────┼──────────────────────────────┐
                ▼                              ▼                              ▼
        [STAGE 4: STRUCTURE]           [STAGE 5: TAGGING]            [STAGE 6: CHUNK]
        Sections, Tables, Figures,     7-Layer Taxonomy              Structure-Aware Windowing
        ASN.1, Cross-References       Deterministic + Hybrid        (300-800 tok + Metadata)
                │                              │                              │
                └──────────────────────────────┼──────────────────────────────┘
                                               │
                ┌──────────────────────────────┴──────────────────────────────┐
                ▼                                                             ▼
        [STAGE 7: EMBED]                                              [STAGE 8: INDEX]
        Decoupled Model Vectors                                       pgvector HNSW + FTS GIN
        (BGE-M3 / Domain Models)                                      + Relation Graph Edges
                                               │
                                               ▼
                                  [Query & Retrieval Service]
                                               │
                     ┌─────────────────────────┼─────────────────────────┐
                     ▼                         ▼                         ▼
             [Release Filter]           [Lexical FTS]             [Vector HNSW]
             Strict Rel-17/18 / Latest  Acronyms, Timers, IEs     Dense 1024-dim Cosine
             (PostgreSQL WHERE)         (PostgreSQL FTS GIN)      (PostgreSQL HNSW Index)
                     │                         │                         │
                     └─────────────────────────┼─────────────────────────┘
                                               │
                                               ▼
                                  [Tag-Aware RRF Fusion Engine]
                                  (Fuses dense + lexical ranks with 7-layer tag boost)
                                               │ (Top-60 Candidate Chunks + Text from Postgres)
                                               ▼
                                  [BGE Cross-Encoder Reranker]
                                  (Joint query + chunk attention · top-8 selection)
                                               │ (Top-8 Grounded Chunks)
                                               ▼
                                  [Context Trimmer & Provenance]
                                               │
                                               ▼
                                  [Citation-Grounded LLM RAG]
                                               │
                                               ▼
                                  [Engineering Intelligence API]
```

---

## 6. Data Model Changes

The target schema partitions data into 4 distinct domains:
1. **Catalog Domain:** `spec_series`, `specifications`, `spec_releases`, `spec_versions`.
2. **Structure Domain:** `canonical_documents`, `doc_sections`, `doc_tables`, `doc_figures`, `doc_references`.
3. **Chunk & Vector Domain:** `document_chunks`, `chunk_embeddings` (multi-model vectors).
4. **Taxonomy & Ingestion Domain:** `taxonomy_tags`, `ingestion_jobs`, `ingestion_stage_logs`.

### Full PostgreSQL DDL Schema

```sql
-- Enable Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- 1. CATALOG DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS spec_series (
    series_number   VARCHAR(10) PRIMARY KEY, -- e.g., '23', '24', '38'
    title           TEXT NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS specifications (
    spec_number     VARCHAR(20) PRIMARY KEY, -- e.g., 'TS 23.501'
    series_number   VARCHAR(10) NOT NULL REFERENCES spec_series(series_number),
    spec_type       VARCHAR(5) NOT NULL CHECK (spec_type IN ('TS', 'TR')),
    title           TEXT NOT NULL,
    primary_wg      VARCHAR(20),             -- e.g., 'SA2', 'CT1', 'RAN2'
    status          VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'withdrawn', 'draft')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spec_releases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_number     VARCHAR(20) NOT NULL REFERENCES specifications(spec_number) ON DELETE CASCADE,
    release_number  INTEGER NOT NULL,        -- e.g., 15, 16, 17, 18, 19
    is_frozen       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (spec_number, release_number)
);

CREATE TABLE IF NOT EXISTS spec_versions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_release_id     UUID NOT NULL REFERENCES spec_releases(id) ON DELETE CASCADE,
    version_string      VARCHAR(20) NOT NULL, -- e.g., '18.6.0'
    version_letter_code VARCHAR(10) NOT NULL, -- e.g., 'i60'
    publication_date    DATE,
    source_url          TEXT NOT NULL,
    checksum_sha256     VARCHAR(64) NOT NULL,
    storage_path_raw    TEXT NOT NULL,
    is_latest_in_rel    BOOLEAN NOT NULL DEFAULT FALSE,
    is_latest_global    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (spec_release_id, version_string),
    UNIQUE (checksum_sha256)
);

-- ============================================================================
-- 2. STRUCTURE & MULTI-MODAL CONTENT DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS canonical_documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_version_id     UUID NOT NULL REFERENCES spec_versions(id) ON DELETE CASCADE,
    page_count          INTEGER NOT NULL,
    word_count          INTEGER NOT NULL,
    storage_path_ast    TEXT NOT NULL,        -- Path to parsed JSON AST representation
    parsed_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    parser_version      VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS doc_sections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES canonical_documents(id) ON DELETE CASCADE,
    section_number      TEXT NOT NULL,        -- e.g., '4.2.2.2.1'
    section_title       TEXT NOT NULL,
    parent_section      TEXT,                 -- e.g., '4.2.2.2'
    depth_level         INTEGER NOT NULL,     -- e.g., 5
    page_start          INTEGER NOT NULL,
    page_end            INTEGER NOT NULL,
    raw_markdown        TEXT NOT NULL,
    has_normative_rules BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doc_tables (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES canonical_documents(id) ON DELETE CASCADE,
    section_id          UUID REFERENCES doc_sections(id) ON DELETE CASCADE,
    table_number        TEXT,                 -- e.g., 'Table 5.2.2.2-1'
    table_title         TEXT,
    header_json         JSONB NOT NULL,
    rows_json           JSONB NOT NULL,
    markdown_repr       TEXT NOT NULL,
    page_number         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS doc_figures (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES canonical_documents(id) ON DELETE CASCADE,
    section_id          UUID REFERENCES doc_sections(id) ON DELETE CASCADE,
    figure_number       TEXT,                 -- e.g., 'Figure 4.2.2.2.2-1'
    figure_title        TEXT,                 -- e.g., 'Initial Registration Procedure'
    figure_type         VARCHAR(30) NOT NULL, -- 'CALL_FLOW', 'BLOCK_DIAGRAM', 'STATE_CHART'
    raw_image_path      TEXT,
    mermaid_syntax      TEXT,                 -- Executable Mermaid sequenceDiagram representation
    extracted_text      TEXT NOT NULL,        -- Textual message sequence for FTS/Vector search
    page_number         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS doc_references (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc_id       UUID NOT NULL REFERENCES canonical_documents(id) ON DELETE CASCADE,
    source_section_id   UUID REFERENCES doc_sections(id) ON DELETE CASCADE,
    target_spec_number  VARCHAR(20) NOT NULL, -- e.g., '3GPP TS 24.501'
    target_clause       TEXT,                 -- e.g., 'Clause 5.4.1'
    reference_text      TEXT NOT NULL,
    is_normative        BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================================
-- 3. CHUNKS & MULTI-MODEL EMBEDDINGS DOMAIN
-- ============================================================================

-- All-in-PostgreSQL Schema (Text, Embeddings, FTS, and Tags in PostgreSQL)
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
    page_start          INTEGER NOT NULL,
    page_end            INTEGER NOT NULL,
    text                TEXT NOT NULL,        -- Complete Markdown chunk text stored in PostgreSQL
    token_count         INTEGER NOT NULL,
    fts_vector          TSVECTOR,             -- Full-Text Search vector
    tags                TEXT[] DEFAULT '{}',  -- 7-layer taxonomy tags
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS chunk_embeddings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id            UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    model_name          VARCHAR(100) NOT NULL, -- e.g., 'BAAI/bge-m3'
    model_version       VARCHAR(50) NOT NULL,  -- e.g., 'v1.0'
    dimension           INTEGER NOT NULL,      -- e.g., 1024
    embedding           VECTOR(1024) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chunk_id, model_name, model_version)
);

-- ============================================================================
-- 4. TAXONOMY & INGESTION STAGE MACHINES
-- ============================================================================

CREATE TABLE IF NOT EXISTS taxonomy_tags (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_name            VARCHAR(100) UNIQUE NOT NULL, -- e.g., 'nf:amf', 'proc:registration'
    layer_level         INTEGER NOT NULL,             -- 0 through 6
    parent_tag_id       UUID REFERENCES taxonomy_tags(id),
    display_label       TEXT NOT NULL,
    description         TEXT,
    synonyms            TEXT[] DEFAULT '{}',
    regex_pattern       TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_version_id     UUID REFERENCES spec_versions(id) ON DELETE SET NULL,
    job_type            VARCHAR(50) NOT NULL, -- 'FULL_INGEST', 'RE_EMBED', 'RE_PARSE'
    status              VARCHAR(30) NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING')),
    stage_current       VARCHAR(30) NOT NULL DEFAULT 'DISCOVER',
    retry_count         INTEGER NOT NULL DEFAULT 0,
    max_retries         INTEGER NOT NULL DEFAULT 3,
    error_message       TEXT,
    stage_latencies_ms  JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ingestion_stage_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id              UUID NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
    stage_name          VARCHAR(30) NOT NULL,
    status              VARCHAR(20) NOT NULL,
    duration_ms         INTEGER NOT NULL,
    items_processed     INTEGER DEFAULT 0,
    details             JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 7. 3GPP Corpus Strategy & Comprehensive Series Hierarchy

The platform is designed to represent and maintain the **complete 3GPP standards body across all 55 specification series and all historical/active releases (Releases 1999 to 20)**:

### 7.1 Complete 3GPP 55-Series Master Breakdown

| Series Range | Technical Area & Responsibility | Key Working Groups | Representative Specifications | Historical & Active Scope |
|---|---|---|---|---|
| **Series 01–13** | GSM Phase 1 & Phase 2 (Legacy 2G Specifications) | SMG / CT | TS 04.08, TS 08.08, TS 03.60 | Historical Reference (Rel-99, Phase 2+) |
| **Series 21–23** | System Architecture, Requirements & Technical Realization | SA1, SA2 | TS 22.261 (5G Requirements), **TS 23.501** (5GS Arch), **TS 23.502** (5GS Procedures), TS 23.503 (Policy/QoS), TS 23.401 (LTE EPC Arch) | Complete Core Architecture (Rel-15 to Rel-20) |
| **Series 24** | Core Network Non-Access Stratum (NAS) & Signaling Protocols | CT1 | **TS 24.501** (5GMM/5GSM NAS), TS 24.502 (Non-3GPP Access), TS 24.526 (URSP), TS 24.301 (LTE NAS) | Complete Core Signaling (Rel-15 to Rel-20) |
| **Series 25** | UTRA (UMTS 3G Radio Access Network & Protocols) | RAN1–RAN4 | TS 25.331 (UMTS RRC), TS 25.413 (RANAP), TS 25.211 | Historical 3G Architecture (Rel-99 to Rel-10) |
| **Series 26** | Codecs, Speech, Audio, Video & Multimedia Telephony Services | SA4 | TS 26.114 (IMS Multimedia), TS 26.501 (5G Media Streaming), TS 26.071 (AMR Codec) | Media & Voice Processing (Rel-99 to Rel-19) |
| **Series 27** | Terminal Adaptation, AT Command Set & Data Services | CT1 | TS 27.007 (AT Command Set for UE), TS 27.005 | Device & Modem Interfacing (Rel-99 to Rel-19) |
| **Series 28** | Management, Orchestration, Slicing & Charging Architecture | SA5 | TS 28.530 (5G Slicing Concepts), TS 28.531 (Provisioning), TS 28.532 (Generic Management), TS 28.541 (NR NRM) | OAM & Network Management (Rel-15 to Rel-20) |
| **Series 29** | Core Network Service-Based Interfaces (SBI) & Interworking | CT3, CT4 | **TS 29.500** (SBI Realization), **TS 29.518** (Namf), **TS 29.502** (Nsmf), **TS 29.503** (Nudm), **TS 29.510** (Nnrf), **TS 29.571** (Common Types), TS 29.274 (GTPv2-C) | Service Based Protocols & APIs (Rel-15 to Rel-20) |
| **Series 31** | Universal Subscriber Identity Module (USIM) & UICC Protocols | CT6 | TS 31.102 (USIM Application), TS 31.121 (UICC Testing), TS 31.124 | Identity & Smart Card Security (Rel-99 to Rel-19) |
| **Series 32** | Telecommunication Management, Charging Management & OAM | SA5 | TS 32.240 (Charging Arch), TS 32.291 (5G Charging SBI), TS 32.298 (CDR) | Revenue & Charging Systems (Rel-99 to Rel-19) |
| **Series 33** | 3GPP Security Architecture, Cryptography & Privacy Protocols | SA3 | **TS 33.501** (5GS Security & 5G-AKA), TS 33.535 (AKMA), TS 33.541 (gNB Sec), TS 33.401 (LTE Security) | Complete Security Suite (Rel-99 to Rel-20) |
| **Series 34** | User Equipment (UE) Conformance & Testing Specifications | RAN5 | TS 34.121, TS 34.229 (IMS Client Conformance) | Testing & Certification (Rel-99 to Rel-18) |
| **Series 35** | Cryptographic Algorithm Specifications & Security Building Blocks | SA3 | TS 35.206 (MILENAGE Algorithm Set), TS 35.221 (TUAK Algorithm Set) | Cryptographic Primitives (Rel-99 to Rel-18) |
| **Series 36** | E-UTRA (LTE / LTE-Advanced Radio Access Network & Protocols) | RAN1–RAN4 | TS 36.300 (LTE Overall), TS 36.331 (LTE RRC), TS 36.413 (S1AP), TS 36.423 (X2AP) | LTE & LTE-A Systems (Rel-8 to Rel-17) |
| **Series 37** | Multiple Radio Access Technology (Multi-RAT) & Dual Connectivity | RAN2, RAN3 | TS 37.340 (Multi-RAT Dual Connectivity MR-DC), TS 37.324 (SDAP), TS 37.571 | Inter-RAT & Dual Connectivity (Rel-14 to Rel-19) |
| **Series 38** | 5G NR (New Radio Access Network, Physical Layer & Protocols) | RAN1–RAN4 | **TS 38.300** (NR Overall), **TS 38.331** (NR RRC), **TS 38.401** (NG-RAN Arch), **TS 38.413** (NGAP), **TS 38.423** (XnAP), **TS 38.473** (F1AP) | Complete 5G NR Radio Stack (Rel-15 to Rel-20) |

---

### 7.2 Two-Horizon Phased Implementation Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                      HORIZON 1: PHASE 1 CURATED CORE 5GS (IMMEDIATE PRODUCTION)                 │
│  - Scope: 44 Flagship Specifications across Releases 17 & 18 (Series 23, 24, 29, 33, 38)       │
│  - Total Chunks: ~30,200 chunks | Total Database Size: ~270 MB                                  │
│  - Infrastructure: 100% Free on Neon PostgreSQL (0.5 GB Cap) + Render Backend ($0/month)        │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                      HORIZON 2: COMPLETE 55-SERIES HISTORICAL CORPUS (ENTERPRISE EXPANSION)     │
│  - Scope: All 4,500+ Specifications across Releases 1999 to 20 (All 55 Series)                  │
│  - Total Chunks: ~1,200,000 chunks | Total Database Size: ~11.5 GB                              │
│  - Infrastructure: Scaled PostgreSQL on Neon standard tier (~$1.90/mo storage)                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Source Discovery Strategy

The automated discovery engine (`ingestion/discovery.py`) queries the official 3GPP archive (`https://www.3gpp.org/ftp/Specs/archive/`):
1. Traverses series directories.
2. Parses filenames (e.g. `23501-i60.zip`).
3. Decodes release and version numbers:
   $$\text{Release} = \text{ord}(\text{letter}) - \text{ord}('a') + 10$$
4. Compares SHA-256 against catalog.
5. Emits `ingestion_jobs` for new or modified files.

---

## 9. Version & Release Management

1. **Version Immutability:** Historical versions are never overwritten.
2. **Latest Resolution:** Flags `is_latest_in_rel` (e.g. latest Rel-17) and `is_latest_global` (latest overall release).
3. **Query-Time Intent Resolution:**
   - "In Rel-17..." $\to$ filters `release_number = 17`.
   - "What does TS 23.501 specify?" $\to$ filters `is_latest_global = TRUE`.
   - "Compare Rel-17 and Rel-18..." $\to$ spawns parallel retrieval for both releases.

---

## 10. Immutable Raw Document Storage

Content-Addressable Storage (CAS) directory hierarchy:
```
data/storage/
├── raw/
│   ├── zips/{series}/{spec}-{version}_{sha256}.zip
│   └── pdfs/{series}/{spec}-{version}_{sha256}.pdf
├── parsed_ast/
│   └── {series}/{spec}-{version}_{sha256}.ast.json
└── checksums/
    └── master_catalog.sha256
```

---

## 11. High-Fidelity Multi-Modal Parsing Architecture

The ingestion pipeline employs a **100% free, CPU-friendly multi-modal parsing stack** tailored to 3GPP standards:

```
                            Input 3GPP Specification (.pdf)
                                           │
                                           ▼
                           [Digital Text Stream Check]
                                           │
                 ┌─────────────────────────┴─────────────────────────┐
                 ▼                                                   ▼
    [Native Digital Vector PDF]                         [Scanned Legacy Archive PDF]
         (98% of Corpus)                                     (2% Historical Archives)
                 │                                                   │
                 ▼                                                   ▼
    [PyMuPDF4LLM + Docling Parser]                      [OCRmyPDF + RapidOCR Pre-Processor]
    - Digital Unicode stream extraction                 - Lightweight CPU ONNX OCR
    - Coordinate-based table grid parsing               - Sandwich searchable text layer
    - 300+ pages/sec on standard CPU                    - Output fed to PyMuPDF4LLM
                 │                                                   │
                 └─────────────────────────┬─────────────────────────┘
                                           │
                 ┌─────────────────────────┴─────────────────────────┐
                 ▼                                                   ▼
    [Normative Text & Tables]                           [Figure & Diagram Extraction]
    - Nested clause hierarchies                         - Vector Bounding Box text cropper
    - Parameter/Timer Markdown tables                   - Gemini 3.6 Flash Vision (GEMINI_MODEL_HEAVY) (Free Tier)
    - RFC-2119 keyword tagging                           converts call flows to Mermaid AST
                 │                                                   │
                 └─────────────────────────┬─────────────────────────┘
                                           │
                                           ▼
                           [Canonical Document AST Output]
```

### Parsing Pipeline Sub-Components:

1. **Digital Document Engine (PDF via PyMuPDF4LLM + DOCX via python‑docx):**
   - Extracts character streams with exact byte-level Unicode fidelity (zero OCR hallucination on acronyms like `S-NSSAI`, `T3512`, `0x7F`).
   - Reconstructs complex 3GPP multi-column tables, information element (IE) matrices, and ASN.1 structures into clean Markdown.

2. **Scanned Archive Engine (OCRmyPDF + RapidOCR) – still for legacy scanned PDFs**
   - **Cost:** **$0.00** (Runs on standard CPU via ONNX runtime).
   - Detects image‑only pages in legacy PDFs (e.g., Rel‑99 / GSM Phase 1/2) and sandwiches an invisible, searchable digital text layer into the PDF, allowing downstream parsers to treat it identically to modern digital specifications.

3. **Call Flow & Diagram Transcription Engine (Dual-Strategy):**
   - **Strategy 1 (Vector Text Cropper):** In modern vector PDFs, call flow message labels (`Registration Request`, `N2 Message`) are vector text objects. `PyMuPDF` extracts text within figure bounding boxes sorted temporally $(y)$ and spatially $(x)$ with zero added latency.
   - **Strategy 2 (Gemini 3.6 Flash Vision (GEMINI_MODEL_HEAVY) - Free Tier):** Complex architectural bitmaps and multi-party message sequence charts are transcribed into structured **Mermaid sequenceDiagrams** via the free-tier Gemini API (15 RPM / 1,500 RPD), embedding executable call flows directly into chunk context:
     ```mermaid
     sequenceDiagram
       autonumber
       actor UE
       participant gNB
       participant AMF
       participant UDM
       UE->>gNB: Registration Request (SUCI)
       gNB->>AMF: N2 Message (Registration Request)
       AMF->>UDM: Nudm_UECM_Registration
     ```

---

## 12. Canonical Document Representation (AST)

The parsed document is serialized as a Canonical JSON Abstract Syntax Tree:
```json
{
  "spec_number": "TS 23.501",
  "release": 18,
  "version": "18.6.0",
  "checksum_sha256": "e4d9f1a...",
  "sections": [
    {
      "section_number": "4.2.2.2.1",
      "section_title": "AMF Functionality",
      "parent_section": "4.2.2.2",
      "depth": 5,
      "page_start": 45,
      "page_end": 46,
      "content": "The Access and Mobility Management Function...",
      "has_normative_rules": true,
      "tables": [],
      "references": [
        {"target_spec": "TS 24.501", "clause": "5.4.1", "is_normative": true}
      ]
    }
  ]
}
```

---

## 13. Section-Aware & Structure-Preserving Chunking

1. **Clause Boundary Respect:** Sections under 800 tokens remain as a single chunk.
2. **Adaptive Paragraph Sliding Window:** For long clauses, split at paragraph boundaries with 100-token sliding overlap.
3. **Context Breadcrumbs:** Every chunk is prefixed with its full hierarchical path:
   ```
   [Context: TS 23.501 Rel-18 > Clause 4.2.2.2.1 AMF Functionality]
   ```
4. **Table Row Preservation:** Tables are chunked by row blocks while retaining header columns.

---

## 14. Layered Tagging Architecture

7 semantic layers:
- **Layer 0:** Technology Generation (`5G_SYSTEM`, `5G_ADVANCED`, `6G_EXPLORATORY`, `LTE_EPC`)
- **Layer 1:** 3GPP Domain (`CORE_5GC`, `RADIO_NR`, `SECURITY`, `PROTOCOL_NAS`, `SYSTEM_ARCH`)
- **Layer 2:** Network Function / Protocol (`AMF`, `SMF`, `UPF`, `UDM`, `AUSF`, `NSSF`, `PCF`, `RRC`, `NGAP`)
- **Layer 3:** Procedure / Lifecycle (`INITIAL_REGISTRATION`, `PDU_SESSION_ESTABLISHMENT`, `HANDOVER`, `5G_AKA`)
- **Layer 4:** Information / Clause Type (`NORMATIVE_RULE`, `CALL_FLOW_STEPS`, `PARAMETER_TABLE`, `IE_DEFINITION`)
- **Layer 5:** Standard Concept (`NETWORK_SLICING`, `QOS_FLOW`, `MOBILITY_MANAGEMENT`, `INTEGRITY_PROTECTION`)
- **Layer 6:** Named Technical Entity (`SUPI`, `SUCI`, `5G-GUTI`, `S-NSSAI`, `5QI`, `T3512_TIMER`, `N1_INTERFACE`)

---

## 15. Taxonomy Design

- Stored in `taxonomy_tags` table with hierarchical parent-child pointers.
- Rule-based regex and keyword density matching during ingestion.
- Extensible via configuration without code refactoring.

---

## 16. Hybrid Retrieval Architecture

Multi-signal candidate retrieval:
1. **Dense Vector Search:** Top-40 candidates via `pgvector` HNSW index on `chunk_embeddings`.
2. **Lexical Search:** Top-20 candidates via PostgreSQL FTS (`fts_vector @@ plainto_tsquery(...)`).
3. **Tag-Aware RRF Fusion:**
   $$\text{RRF\_Score}(d) = \sum \frac{1}{60 + \text{rank}_i(d)} + (0.015 \times |d.\text{tags} \cap q.\text{tags}|)$$
4. **Fail-Open Default:** If query tag confidence < 0.50, bypass tag filtering completely.

---

## 17. Reranking Strategy & Dual-Tier Architecture

The platform applies a cross-encoder joint-attention reranking layer to precisely order candidate chunks retrieved via RRF fusion:

### 17.1 Dual-Tier Reranker Specification Matrix

| Metric | **Demo / Evaluation Tier** (Current Baseline) | **Production Tier** (Target Deployment) |
|---|---|---|
| **Model** | `BAAI/bge-reranker-base` | `BAAI/bge-reranker-v2-m3` |
| **Model Footprint** | ~440 MB | ~2.27 GB |
| **Parameter Count** | 110 Million | 560 Million |
| **Cross-Encoder Latency (Top-8, CPU)** | **~80–150 ms** | ~1.5–3.0 s |
| **Hardware Target** | Consumer CPU / Memory-efficient instances | Dedicated GPU (NVIDIA CUDA / TensorRT) |
| **Target Task** | Fast English 3GPP standards clause ranking | Multi-lingual, long-context complex telecom questions |
| **Graceful Fallback** | Automatic fallback to RRF tag-boosted ranking if disabled | RRF tag-boosted fallback |

- **Input:** Joint token pairs `[query, chunk_text]` scored via cross-encoder softmax.
- **Output:** Top-8 highest-scoring chunks filtered by `RERANKER_FLOOR` (0.15) and passed to context assembler.
- **Graceful Fallback:** If cross-encoder is disabled or uninitialized, tag-boosted RRF score with `RRF_FLOOR` (0.005) ranks candidates directly.

---

## 18. Citation & Provenance Architecture

- Every claim generated by the LLM is mapped to `ClaimSource` objects containing:
  - `spec_number`, `release`, `version`, `section_number`, `section_title`, `page_start`, `page_end`, and `excerpt`.
- 8-point deterministic validator rejects fabricated UUIDs, mismatched text excerpts, and unsupported assertions.

---

## 19. Cross-Reference & Knowledge Graph Strategy

- Normative references between specifications are extracted into `doc_references` table:
  ```
  TS 23.501 Clause 5.15 ──► [references] ──► TS 24.501 Clause 6.4 (S-NSSAI NAS signaling)
  ```
- Retrieval engine can expand candidates across 1-hop normative references for multi-hop questions.

---

## 20. Embedding Architecture & Dual-Tier Strategy

The platform implements a decoupled, configuration-driven **Dual-Tier Embedding Architecture** to support rapid local evaluation/demo cycles alongside high-accuracy production deployments:

### 20.1 Dual-Tier Embedding Specification Matrix

| Metric | **Demo / Evaluation Tier** (Current Baseline) | **Production Tier** (Target Deployment) |
|---|---|---|
| **Model** | `BAAI/bge-small-en-v1.5` | `BAAI/bge-m3` |
| **Model Footprint** | ~130 MB | ~2.27 GB |
| **Parameter Count** | 33 Million | 560 Million |
| **Vector Dimension** | **384 dimensions** (`halfvec(384)`) | **1024 dimensions** (`halfvec(1024)`) |
| **Hardware Target** | Consumer CPU (Multi-core x86/ARM) | Dedicated GPU (NVIDIA T4 / A10G / CUDA) |
| **Throughput (CPU)** | **~200–300 chunks / minute** | ~3–4 chunks / minute |
| **Phase 1 Ingestion Time (16 Specs)** | **~25 to 35 minutes total** | ~54 hours (CPU) / ~15 mins (GPU) |
| **Optimal Ingestion Batch Size** | **32 chunks / batch** | 16–32 chunks / batch |
| **Use Case** | Local development, CI/CD, rapid demo & grading | Multi-lingual, dense+sparse hybrid, enterprise production |

### 20.2 Decoupled Vector Storage Design
- Vector representations are strictly decoupled into the `chunk_embeddings` relational table with a compound key `(chunk_id, model_name)`.
- Column definition uses PostgreSQL `pgvector` half-precision float: `embedding halfvec(384)` with HNSW cosine distance index (`halfvec_cosine_ops`).
- Environment variable `EMBEDDING_MODEL` in `.env` dictates both runtime query vectorization and batch ingestion without hardcoded model references.
- Switching between Demo (`BAAI/bge-small-en-v1.5`) and Production (`BAAI/bge-m3`) requires zero application code changes—only an `.env` toggle and corresponding database vector dimension initialization.

---

## 21. Asynchronous Ingestion Job Architecture

State machine with independent retryable stages:
```
DISCOVER ──► DOWNLOAD ──► VALIDATE ──► PARSE ──► STRUCTURE ──► TAG ──► CHUNK ──► EMBED ──► INDEX
```
- Each stage logs execution duration, status, and item counts to `ingestion_stage_logs`.
- Failed jobs resume from the exact failed stage without repeating upstream work.

---

## 22. Continuous Corpus Update Strategy

1. Nightly cron job checks 3GPP FTP archive for new `.zip` uploads.
2. Identifies new version codes or modified checksums.
3. Automatically triggers asynchronous ingestion jobs.
4. Activates new versions atomically upon successful benchmark validation.

---

## 23. Evaluation Framework

150-Question Benchmark Dataset:
- 50 Factual Single-Spec Questions
- 30 Cross-Document Multi-Hop Questions
- 30 Cross-Release Comparative Questions ("Rel-17 vs Rel-18")
- 40 Adversarial & Unanswerable Questions

### Target Metrics:
- Recall@5 $\ge 0.90$
- MRR $\ge 0.85$
- nDCG@5 $\ge 0.88$
- Abstention Precision $= 100\%$

---

## 24. Observability & Telemetry

`query_logs` table records:
- Latencies: `retrieval_ms`, `reranker_ms`, `llm_ms`, `total_ms`.
- Reliability metrics: `llm_timeout_count`, `model_fallback_used`, `key_fallback_used`.
- Cost tracking: `input_tokens`, `output_tokens`, `estimated_cost_usd`.
- Grounding: `uncovered_claim_count`, `abstained`, `citation_valid`.

---

## 25. Security & Untrusted Document Defense

1. **XML Delimiter Sanitization:** Escapes `<question>` and `<chunks>` tags in user inputs.
2. **Untrusted Document Boundary:** Chunks treated as untrusted text; instructions inside chunks are ignored.
3. **Database Security:** Parameterized queries; SSL-enforced connections (`sslmode=require`).

---

## 26. Scalability & Capacity Planning (Multi-Horizon Enterprise Architecture)

### 26.1 Comparative Capacity Matrix: Phase 1 Curated 5GS vs. Complete Historical Corpus

| Metric | **Phase 1: Curated Core 5GS Suite**<br>*(Immediate Zero-Cost Baseline)* | **Complete Historical 3GPP Corpus**<br>*(All 55 Series · Releases 1999–20)* |
|---|---|---|
| **Target Specifications** | **44 Flagship 5GS Specifications**<br>(Series 23, 24, 29, 33, 38 · Rel-17 & 18) | **4,500+ Specifications**<br>(GSM Phase 1/2, UMTS, LTE, 5G, 6G Study Items) |
| **Document Versions / Revisions** | **88 Active Document Versions** | **85,000+ Historical & Draft Revisions** |
| **Total Specification Pages** | **~14,800 Pages** | **~3,200,000 Pages** |
| **Total Canonical Chunks (300–800 tok)**| **~30,200 Chunks** | **~1,200,000 Chunks** |
| **Raw PDF / CAS Storage** | **~850 MB** (Compressed) | **~250 GB** (Compressed) |
| **`document_chunks` (Text + Breadcrumbs)** | **~60 MB** | **~3.5 GB** |
| **`chunk_embeddings` (BGE-M3 1024-dim)**| **~140 MB** (Vector + HNSW Index) | **~5.2 GB** (Vector + HNSW Index) |
| **Full-Text Search GIN Index (`tsvector`)**| **~35 MB** | **~1.8 GB** |
| **Relational Metadata (AST, Tables, Figs)**| **~35 MB** | **~1.0 GB** |
| **Total PostgreSQL Database Size** | **~270 MB** ✅<br>*(54% of Neon 0.5 GB Free Tier)* | **~11.5 GB**<br>*(Neon Standard Tier: ~$1.90/month)* |
| **Monthly Database Infrastructure Cost**| **$0.00 / month (Neon Free Tier)** | **~$1.90 / month** |

---

### 26.2 Horizon 1: Immediate Zero-Cost Execution (Neon 0.5 GB Free Tier)
- Stores all **30,200 chunks**, full Markdown text, 1024-dim BGE-M3 vectors, and 7-layer tags directly inside Neon PostgreSQL.
- Consumes **~270 MB**, leaving **~230 MB free buffer** for runtime query logs, evaluation runs, and transaction WAL.
- **Zero external blob store complexity:** 100% of queries, vector scans, and text retrieval execute in a single PostgreSQL query.

---

### 26.3 Horizon 2: Full Historical Corpus Scaling Path (All 55 Series)
- As the system scales to index all 55 Series (GSM 01–13, UMTS 25, LTE 36, IMS 26, OAM 28/32, 5G 38, etc.):
  1. Database smoothly scales to **~11.5 GB** on Neon PostgreSQL.
  2. Index partitioning (`PARTITION BY LIST (release_number)`) segregates historical releases (Rel-99 to Rel-14) from active releases (Rel-15 to Rel-20), maintaining sub-15ms HNSW vector scan latencies across 1.2M vectors.
  3. Continuous background ingestion jobs crawl `ftp.3gpp.org` without disrupting active retrieval services.

---

## 27. Cost Considerations

- **Ingestion Embeddings (One-Time):** Local GPU/CPU BGE-M3 batch embedding $\to$ **$0.00 API cost**.
- **LLM Grounding (Runtime):** Gemini 3.5 Flash Lite (GEMINI_MODEL_FAST) at $0.000075 / 1K input tokens $\to$ **~$0.00045 per user query**.
- **Storage Cost:** 12 GB Postgres on Neon + 250 GB S3 CAS $\to$ **< $15.00 / month**.

---

## 28. Migration Strategy

1. **Phase 1 Schema Migration:** Execute `CREATE TABLE` DDL for new catalog and embedding tables.
2. **Phase 2 Dual-Writing:** Backfill existing 5 specifications into catalog schema.
3. **Phase 3 Cutover:** Point query services to version-filtered tables.
4. **Phase 4 Deprecation:** Drop legacy unversioned tables.

---

## 29. Phased Implementation Roadmap

- **Phase 0:** Architecture Blueprint & Baseline Audit
- **Phase 1:** Catalog Schema, Discovery Engine & CAS Storage
- **Phase 2:** High-Fidelity AST Parsing & Table Extraction
- **Phase 3:** Multi-Layer Taxonomy & Rule-Based Tagger
- **Phase 4:** Structure-Aware Chunking & Multi-Model Embeddings
- **Phase 5:** Version-Aware Hybrid Retrieval & Comparative RAG
- **Phase 6:** Asynchronous Ingestion Stage Machine & Background Queue
- **Phase 7:** Comprehensive Evaluation Framework & Automated Benchmark
- **Phase 8:** Automated Continuous Updates & Observability Dashboard
- **Phase 9:** Production Scale Hardening & Verification

---

## 30. Testing Strategy

1. **Unit Tests:** Parser AST validation, chunk token limits, tagger rules, citation validation.
2. **Integration Tests:** Discovery FTP crawler, stage machine resume-on-failure, database transactions.
3. **Adversarial Tests:** Delimiter escaping, hallucinated UUID rejection, out-of-scope abstention.
4. **Regression Tests:** 150-question automated benchmark executed on every release cutover.

---

## 31. Deployment Architecture (100% Free Production Stack)

The entire platform operates on **100% free-tier cloud infrastructure** with zero external storage complexity:

| Component | Free Tier Service | Runtime Configuration | Monthly Cost |
|---|---|---|---|
| **Backend API** | **Render Web Service (Free Tier)** | Python 3.12 + FastAPI running via `render.yaml` with `uvicorn app.main:app` | **$0.00** |
| **Database & Vector Store** | **Neon PostgreSQL (Free Tier)** | Serverless PostgreSQL with pgvector, HNSW index, FTS GIN index (0.5 GB storage, 2 CU compute autoscaling) | **$0.00** |
| **Frontend UI** | **Vercel (Free Tier)** | React 18 + Vite + TypeScript SPA with custom dark-mode telecom dashboard | **$0.00** |
| **LLM Grounding & Synthesis** | **Gemini 3.5 Flash Lite + 3-Key Pool** | Free Tier with 15 RPM / 1,500 RPD per key (45 RPM / 4,500 RPD aggregate) | **$0.00** |
| **Total System Cost** | | | **$0.00 / month** |

---

## 32. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| 3GPP FTP rate limiting / throttling | Discovery failure | Exponential backoff, local HTTP mirror caching, user-agent rotation |
| Corrupted or non-standard PDF formatting | Parsing crash | Fallback to OCR / raw text parser, error logging in `ingestion_stage_logs` |
| Vector memory exhaustion | OOM crash | Hugging Face 16 GB RAM tier; HNSW index pruning; batch size limits |
| Outdated release answered as current | Incorrect answer | Strict default to `is_latest_global = TRUE` with explicit release badge in UI |

---

## 33. Open Decisions & Technical Trade-offs

1. **Decision 1: Curated Core 5GS Scope on All-in-PostgreSQL (LOCKED):**
   - *Decision:* **Store all chunks, text, vectors, FTS, and tags strictly inside Neon PostgreSQL for the curated Core 5GS Suite (Releases 17 & 18 across Series 23, 24, 29, 33, 38 · ~30,200 chunks).**
   - *Rationale:* Eliminates architectural complexity. Total database size is **~270 MB**, staying well inside the 500 MB Neon cap (54% utilization) with zero external blob stores.
2. **Decision 2: Multi-Modal Parser & Diagram Engine Stack (100% Free / Open-Source - LOCKED):**
   - *Decision:* Use **PyMuPDF4LLM + Docling** (digital specifications), **OCRmyPDF + RapidOCR** (scanned legacy), and **Gemini 3.6 Flash** (diagram $	o$ Mermaid sequenceDiagrams).
3. **Decision 3: Zero-Cost Production Hosting Strategy (LOCKED):**
   - *Decision:* **Deploy backend on Render Free Web Service (`render.yaml`), database on Neon Free Tier, and frontend on Vercel.**
   - *Rationale:* 100% free, production-ready, and completely vendor-independent with zero subscription fees.

---

## 34. File-Level Implementation Plan

| File Path | Responsibility | Action | Why | Dependencies |
|---|---|---|---|---|
| `backend/app/db/schema.sql` | PostgreSQL DDL | **MODIFY** | Add catalog, AST, multi-model embeddings, and job state tables | None |
| `backend/app/db/queries.py` | SQL Execution Layer | **MODIFY** | Add version-filtered and comparative multi-release search queries | `schema.sql` |
| `ingestion/discovery.py` | 3GPP Catalog Discovery | **NEW** | Crawl 3GPP FTP archive, detect new versions, populate catalog | None |
| `ingestion/models/canonical_ast.py` | Document AST Models | **NEW** | Dataclasses for Section, Table, Figure, and Reference nodes | None |
| `ingestion/parsers/docling_parser.py` | High-Fidelity Parser | **NEW** | Extract structured sections, tables, and callouts from PDF **and DOCX** | `canonical_ast.py` |
| `ingestion/tagger.py` | Multi-Layer Tagger | **MODIFY** | Expand from 4 to 7 taxonomy layers | None |
| `ingestion/chunker.py` | Structure-Aware Chunker | **MODIFY** | Clause breadcrumbs and table row chunking | `canonical_ast.py` |
| `ingestion/job_worker.py` | Stage Machine Worker | **NEW** | Async stage worker with checkpointing and retries | `queries.py` |
| `backend/app/services/retriever.py` | Retrieval Orchestrator | **MODIFY** | Add version-aware routing and multi-release comparative search | `queries.py` |
| `backend/app/services/query_service.py` | Full RAG Service | **MODIFY** | Version-specific context formatting and comparative prompting | `retriever.py` |
| `evaluation/runner.py` | Benchmark Runner | **MODIFY** | Include cross-release and version comparison test cases | `query_service.py` |
| `frontend/src/components/VersionSelector.tsx`| Release Selector UI | **NEW** | Multi-release and latest/historical selection UI | `src/types/api.ts` |

---

## 35. Database Migration Plan

```sql
-- Migration Step 1: Create catalog and decoupled embedding tables
-- (Executed without dropping existing documents or chunks tables)
-- Migration Step 2: Backfill existing 5 specs into specifications & spec_versions
INSERT INTO specifications (spec_number, series_number, spec_type, title, status)
SELECT DISTINCT spec_number, substring(spec_number from 4 for 2), 'TS', title, 'active'
FROM documents ON CONFLICT DO NOTHING;

-- Migration Step 3: Populate document_chunks and chunk_embeddings from legacy chunks
INSERT INTO document_chunks (id, document_id, chunk_index, spec_number, release_number, version_string, section_number, section_title, page_start, page_end, text, token_count, fts_vector, tags)
SELECT c.id, c.document_id, c.chunk_index, d.spec_number, d.release, d.version, c.section_number, c.section_title, c.page_start, c.page_end, c.text, c.token_count, c.fts_vector, c.tags
FROM chunks c JOIN documents d ON c.document_id = d.id ON CONFLICT DO NOTHING;

INSERT INTO chunk_embeddings (chunk_id, model_name, model_version, dimension, embedding)
SELECT id, 'BAAI/bge-m3', 'v1.0', 1024, embedding FROM chunks WHERE embedding IS NOT NULL
ON CONFLICT DO NOTHING;
```

---

## 36. Backward Compatibility Assurance

- Existing `/api/v1/query` endpoint maintains exact request/response JSON schema.
- Unversioned queries automatically resolve to the latest release (`is_latest_global = TRUE`).
- Frontend continues functioning without requiring mandatory user release selections.

---

## 37. Definition of Done

- [ ] Complete 3GPP archive discoverable and tracked in `spec_versions`.
- [ ] Releases 15 through 20 addressable with distinct release filters.
- [ ] Tables, message structures, and normative clauses extracted into canonical AST.
- [ ] Chunks carry full clause hierarchy breadcrumbs and 7-layer tags.
- [ ] Ingestion jobs run asynchronously with retryable stage checkpoints.
- [ ] Zero downtime during quarterly 3GPP specification updates.
- [ ] All 150 benchmark test cases automated and passing regression gates.
