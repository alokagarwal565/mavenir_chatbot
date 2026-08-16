import os
from pathlib import Path
from dotenv import load_dotenv

# Force HuggingFace cache to D: drive before any model modules load
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = str(ROOT_DIR)

# Force PyTorch and OpenMP to use 1 thread to prevent starving the Uvicorn event loop on Render (0.1 CPU limit)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

try:
    import torch
    torch.set_num_threads(1)
except ImportError:
    pass

import psutil
from app.logging_config import get_logger
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import configure_logging, ctx_request_id
from app.api.v1.health import router as health_router
from app.api.v1.query import router as query_router
from app.api.v1.documents import router as doc_router
from app.api.v1.evaluation import router as eval_router
from app.db.connection import create_db_pool
from app.providers.bge_provider import BGEEmbeddingProvider, BGEReranker
from app.providers.gemini_provider import GeminiProvider
from app.services.query_service import QueryService

configure_logging(settings.log_level)
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    vm = psutil.virtual_memory()
    total_ram_gb = round(vm.total / (1024**3), 2)
    avail_ram_gb = round(vm.available / (1024**3), 2)

    logger.info(
        "service_startup",
        total_ram_gb=total_ram_gb,
        available_ram_gb=avail_ram_gb,
        reranker_enabled=settings.reranker_enabled,
        embedding_model=settings.embedding_model,
        llm_model=settings.llm_model,
        port=settings.port
    )

    # 1. Initialize asyncpg database pool
    app.state.db_pool = await create_db_pool()

    # 2. Initialize embedding provider
    embedder = BGEEmbeddingProvider(settings.embedding_model)
    app.state.embedding_provider = embedder

    # 3. Initialize reranker if enabled
    reranker = BGEReranker(settings.reranker_model) if settings.reranker_enabled else None
    app.state.reranker = reranker

    # 4. Initialize LLM Provider
    llm = GeminiProvider()
    app.state.llm_provider = llm

    # 5. Initialize orchestrating QueryService
    app.state.query_service = QueryService(
        embedding_provider=embedder,
        reranker=reranker,
        llm_provider=llm
    )

    yield

    # Clean up on shutdown
    if app.state.db_pool is not None:
        await app.state.db_pool.close()
        logger.info("database_pool_closed")

def create_app() -> FastAPI:
    app = FastAPI(
        title="3GPP Standards Intelligence Assistant API",
        description="Evidence-first RAG API for 3GPP 5GS Release 18 specifications with deterministic citation validation and automated abstention",
        version="1.0.0",
        lifespan=lifespan
    )

    origins = [settings.frontend_url]
    if settings.frontend_url != "*":
        origins.extend(["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        import uuid
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = ctx_request_id.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            ctx_request_id.reset(token)

    app.include_router(health_router)
    app.include_router(query_router, prefix="/api/v1")
    app.include_router(doc_router, prefix="/api/v1")
    app.include_router(eval_router, prefix="/api/v1")

    return app

app = create_app()
