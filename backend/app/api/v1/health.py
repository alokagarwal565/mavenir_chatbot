from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/health", tags=["Health"])
@router.head("/health", tags=["Health"])
async def health_check(request: Request):
    db_status = "unknown"
    pool = getattr(request.app.state, "db_pool", None)
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_status = "connected"
        except Exception:
            db_status = "disconnected"

    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "3gpp-standards-intelligence-api",
        "db": db_status
    }
