import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
import yaml
import asyncpg
import ssl
from pathlib import Path
from ingestion.downloader import download_spec
from ingestion.parser import parse_document
from ingestion.section_detector import detect_sections
from ingestion.chunker import chunk_document
from ingestion.embedder import embed_chunks
from ingestion.validator import validate_ingestion_data
from ingestion.db_writer import write_document_and_chunks

DB_SIZE_LIMIT_MB = 400  # stop at 400 MB to leave a 100 MB buffer for Supabase's 500MB limit

async def create_pool_with_retry(database_url: str) -> asyncpg.Pool:
    if not database_url or "localhost" in database_url:
        return None
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    dsn = database_url.split("?")[0] if "?" in database_url else database_url
    return await asyncpg.create_pool(
        dsn=dsn, 
        ssl=ssl_ctx,
        statement_cache_size=0,
        min_size=1,
        max_size=5,
        command_timeout=60
    )

async def get_db_size_mb(pool: asyncpg.Pool) -> float:
    """Returns current DB size in MB with retry."""
    for attempt in range(3):
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow("SELECT pg_database_size(current_database()) AS size")
                return row["size"] / (1024 * 1024)
        except Exception as e:
            if attempt == 2:
                print(f"  [DB Size Warning] Could not fetch size: {e}")
                return 0.0
            await asyncio.sleep(1)

async def run_pipeline(config_path: str = "ingestion/specs_config.yaml", database_url: str = None):
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    specs = config.get("specifications", [])
    print(f"Loaded {len(specs)} specification manifests from {config_path}")

    pool = None
    if database_url:
        try:
            pool = await create_pool_with_retry(database_url)
            print("Connected to Supabase database successfully.")
        except Exception as e:
            print(f"Database connection failed: {e}")

    for spec in specs:
        # Check DB size before processing each spec
        if pool is not None:
            size_mb = await get_db_size_mb(pool)
            print(f"  [DB] Current size: {size_mb:.1f} MB / {DB_SIZE_LIMIT_MB} MB limit")
            if size_mb >= DB_SIZE_LIMIT_MB:
                print(f"\n⚠️  DB size limit reached ({size_mb:.1f} MB). Stopping pipeline safely.")
                break

        print(f"\n--- Processing {spec['spec_number']}: {spec['title']} (Release {spec['release']}) ---")
        try:
            doc_path, version, checksum, version_code, file_size, ftp_path = download_spec(spec)
            print(f"  Document ready: {doc_path} (Version: {version}, SHA256: {checksum[:8]}...)")

            pages = parse_document(doc_path)
            print(f"  Parsed {len(pages)} pages/sections.")

            full_markdown = "\n\n".join(f"# Page {p.page_number}\n" + p.text for p in pages)
            sections = detect_sections(full_markdown)
            print(f"  Detected {len(sections)} sections/clauses.")

            doc_meta = {
                "spec_number": spec["spec_number"],
                "title": spec["title"],
                "release": spec["release"],
                "version": version,
                "source_url": spec.get("archive_url", ""),
                "checksum_sha256": checksum,
                "page_count": len(pages),
                "version_letter_code": version_code,
                "ftp_relative_path": ftp_path,
                "file_size_bytes": file_size,
                "ast_json": [
                    {
                        "section_number": s.section_number,
                        "section_title": s.section_title,
                        "parent_section": s.parent_section,
                        "page_start": s.page_start,
                        "page_end": s.page_end,
                    }
                    for s in sections
                ]
            }

            chunks = chunk_document(sections, doc_meta)
            print(f"  Created {len(chunks)} structure-aware chunks (300-800 tokens).")

            report = validate_ingestion_data(spec["spec_number"], chunks)
            print(f"  Validation: valid_sections_rate={report.valid_sections_rate:.1%}, is_valid={report.is_valid}")
            if report.issues:
                for iss in report.issues:
                    print(f"    [Warning] {iss}")

            if pool is not None and chunks:
                print("  Generating BGE-M3 embeddings...")
                texts = [c.text for c in chunks]
                embeddings = embed_chunks(texts)
                print("  Writing to database and generating FTS tsvectors...")
                
                # Write with retry in case of transient pool glitch
                doc_id = None
                for write_attempt in range(2):
                    try:
                        doc_id = await write_document_and_chunks(pool, doc_meta, chunks, embeddings)
                        break
                    except Exception as we:
                        if write_attempt == 0:
                            print(f"  [DB Retry] Reconnecting after write error: {we}")
                            await asyncio.sleep(2)
                            pool = await create_pool_with_retry(database_url)
                        else:
                            raise we

                print(f"  Successfully ingested document ID: {doc_id}")

                # Report size after write
                size_mb = await get_db_size_mb(pool)
                print(f"  [DB] Size after ingest: {size_mb:.1f} MB")

        except Exception as e:
            print(f"  Error processing {spec['spec_number']}: {e}")

    if pool is not None:
        try:
            await pool.close()
        except Exception:
            pass
        print("\nPipeline execution complete.")

if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL")
    asyncio.run(run_pipeline(database_url=db_url))
