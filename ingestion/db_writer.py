import asyncpg
import json
import os
import boto3
from typing import Dict, Any, List
from ingestion.tagger import generate_chunk_tags

def upload_ast_to_s3(spec_number: str, release: int, version: str, ast_data: dict) -> str:
    """Uploads the AST JSON to Supabase S3 and returns the S3 URI."""
    bucket = os.getenv("S3_BUCKET_NAME", "knowledge_pipeline")
    endpoint = os.getenv("S3_ENDPOINT")
    if not endpoint:
        return None
        
    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=os.getenv("S3_REGION", "ap-south-1"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY")
    )
    
    file_key = f"ast/{release}/{spec_number}_{version}_ast.json"
    
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=file_key,
            Body=json.dumps(ast_data),
            ContentType="application/json"
        )
        return f"s3://{bucket}/{file_key}"
    except Exception as e:
        print(f"S3 Upload failed for {spec_number}: {e}")
        return None

async def write_document_and_chunks(
    pool: asyncpg.Pool,
    doc_meta: Dict[str, Any],
    chunks: List[Any],
    embeddings: List[List[float]]
) -> str:
    spec_number = doc_meta["spec_number"]
    series = doc_meta.get("series", spec_number.replace("TS ", "").split(".")[0])
    release = int(doc_meta["release"])
    version_str = doc_meta["version"]
    title = doc_meta["title"]
    source_url = doc_meta.get("source_url", "")
    checksum = doc_meta.get("checksum_sha256", "auto")
    page_count = int(doc_meta.get("page_count", 0))

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Upsert into master `specifications`
            spec_row = await conn.fetchrow(
                """
                INSERT INTO specifications (spec_number, series_number, spec_type, title, primary_wg)
                VALUES ($1, $2, 'TS', $3, 'SA2')
                ON CONFLICT (spec_number) DO UPDATE SET title = EXCLUDED.title
                RETURNING id;
                """,
                spec_number,
                series,
                title
            )
            specification_id = spec_row["id"]

            # 2. Upsert into `spec_versions`
            spec_version_row = await conn.fetchrow(
                """
                INSERT INTO spec_versions (
                    specification_id, spec_number, release_number, version_string,
                    version_letter_code, ftp_relative_path, file_size_bytes,
                    is_latest_in_release, is_latest_global, raw_file_sha256
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, TRUE, $8)
                ON CONFLICT (spec_number, release_number, version_string) DO UPDATE 
                SET updated_at = NOW()
                RETURNING id;
                """,
                specification_id,
                spec_number,
                release,
                version_str,
                doc_meta.get("version_letter_code", ""),
                doc_meta.get("ftp_relative_path", ""),
                doc_meta.get("file_size_bytes", 0),
                checksum
            )
            spec_version_id = spec_version_row["id"]

            # 3. Upload AST to S3 (if provided)
            ast_path = None
            if "ast_json" in doc_meta:
                ast_path = upload_ast_to_s3(spec_number, release, version_str, doc_meta["ast_json"])

            # 4. Upsert into `canonical_documents`
            canon_doc_row = await conn.fetchrow(
                """
                INSERT INTO canonical_documents (
                    spec_version_id, spec_number, release_number, version_string,
                    title, total_pages, ast_storage_path
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (spec_version_id) DO UPDATE
                SET ingested_at = NOW(),
                    ast_storage_path = EXCLUDED.ast_storage_path
                RETURNING id;
                """,
                spec_version_id,
                spec_number,
                release,
                version_str,
                title,
                page_count,
                ast_path
            )
            canonical_doc_id = canon_doc_row["id"]

            # 5. Insert structure-preserving `document_chunks` & `chunk_embeddings`
            for chunk, emb in zip(chunks, embeddings):
                # Generate 7-layer tags
                tags = generate_chunk_tags(
                    spec_number=spec_number,
                    section_title=chunk.section_title or "",
                    text=chunk.text,
                    release=release
                )

                # Insert into enterprise `document_chunks`
                chunk_row = await conn.fetchrow(
                    """
                    INSERT INTO document_chunks (
                        document_id, chunk_index, spec_number, release_number, version_string,
                        section_number, section_title, page_start, page_end,
                        text, token_count, tags
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (document_id, chunk_index) DO UPDATE
                    SET text = EXCLUDED.text,
                        tags = EXCLUDED.tags
                    RETURNING id;
                    """,
                    canonical_doc_id,
                    chunk.chunk_index,
                    spec_number,
                    release,
                    version_str,
                    chunk.section_number,
                    chunk.section_title,
                    chunk.page_start,
                    chunk.page_end,
                    chunk.text,
                    chunk.token_count,
                    tags
                )
                chunk_id = chunk_row["id"]

                model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
                embedding_dim = len(emb)

                # Insert vector into `chunk_embeddings`
                await conn.execute(
                    """
                    INSERT INTO chunk_embeddings (chunk_id, model_name, embedding_dim, embedding)
                    VALUES ($1, $2, $3, $4::halfvec)
                    ON CONFLICT (chunk_id, model_name) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        embedding_dim = EXCLUDED.embedding_dim;
                    """,
                    chunk_id,
                    model_name,
                    embedding_dim,
                    str(emb)
                )

            # 6. Update FTS tsvector on both tables
            await conn.execute(
                """
                UPDATE document_chunks
                SET fts_vector = to_tsvector('english', text)
                WHERE document_id = $1;
                """,
                canonical_doc_id
            )

            return str(canonical_doc_id)
