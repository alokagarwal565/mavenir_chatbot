import pytest
from app.config import settings

@pytest.fixture(scope="session")
async def db_pool():
    try:
        import asyncpg
    except ImportError:
        yield None
        return

    if not settings.database_url or "localhost" in settings.database_url:
        yield None
        return
    
    ssl_mode = "require" if "sslmode=require" in settings.database_url or "neon.tech" in settings.database_url else None
    dsn = settings.database_url.split("?")[0] if ssl_mode and "?" in settings.database_url else settings.database_url

    try:
        pool = await asyncpg.create_pool(dsn=dsn, ssl=ssl_mode, min_size=1, max_size=3)
        yield pool
        await pool.close()
    except Exception:
        yield None
