import asyncpg
import ssl
from app.logging_config import get_logger
from fastapi import Request
from app.config import settings

logger = get_logger(__name__)

async def create_db_pool() -> asyncpg.Pool:
    if not settings.database_url or "localhost" in settings.database_url:
        ssl_ctx = None
    elif "neon.tech" in settings.database_url or "supabase.com" in settings.database_url or "sslmode=require" in settings.database_url:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
    else:
        ssl_ctx = None

    dsn = settings.database_url.split("?")[0] if "?" in settings.database_url else settings.database_url

    try:
        pool = await asyncpg.create_pool(
            dsn=dsn,
            ssl=ssl_ctx,
            min_size=1,
            max_size=10,
            command_timeout=60,
            statement_cache_size=0
        )
        logger.info("database_pool_initialized")
        return pool
    except Exception as e:
        logger.error("database_pool_init_failed", error=str(e))
        return None

def get_db_pool(request: Request) -> asyncpg.Pool:
    return getattr(request.app.state, "db_pool", None)
