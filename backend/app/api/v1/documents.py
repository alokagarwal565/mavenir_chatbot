from fastapi import APIRouter, Request, HTTPException
from typing import List
from app.models.schemas import DocumentItem, ErrorResponse
from app.db.queries import get_documents_list
from app.logging_config import ctx_request_id

router = APIRouter()

@router.get("/documents", response_model=List[DocumentItem], tags=["Documents"])
async def list_documents(request: Request):
    pool = getattr(request.app.state, "db_pool", None)
    docs = await get_documents_list(pool)
    return [
        DocumentItem(
            id=d["id"],
            spec_number=d["spec_number"],
            title=d["title"],
            release=d["release"],
            version=d["version"],
            page_count=d.get("page_count"),
            chunk_count=d.get("chunk_count", 0),
            ingested_at=str(d.get("ingested_at", ""))
        ) for d in docs
    ]
