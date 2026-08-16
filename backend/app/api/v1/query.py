from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import QueryRequest, QueryResponse, ErrorResponse, StreamQueryRequest
from app.services.query_router import QueryRouter, ROUTE_RAG
import json
import asyncio
from app.logging_config import ctx_request_id

router = APIRouter()

@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse}
    },
    tags=["Query"]
)
async def query_standards(req: QueryRequest, request: Request):
    req_id = ctx_request_id.get()
    query_service = getattr(request.app.state, "query_service", None)
    pool = getattr(request.app.state, "db_pool", None)

    if query_service is None:
        raise HTTPException(
            status_code=503,
            detail={"request_id": req_id, "error_code": "SERVICE_INITIALIZING", "message": "Query service is still initializing"}
        )

    try:
        response = await query_service.execute_query(pool, req, req_id)
        return response
    except Exception as e:
        err_msg = str(e)
        status = 503 if "quota" in err_msg.lower() or "timeout" in err_msg.lower() or "503" in err_msg else 500
        raise HTTPException(
            status_code=status,
            detail={"request_id": req_id, "error_code": "QUERY_EXECUTION_FAILED", "message": err_msg}
        )

@router.post(
    "/query/stream",
    tags=["Query"]
)
async def query_stream(req: StreamQueryRequest, request: Request):
    req_id = ctx_request_id.get()
    query_service = getattr(request.app.state, "query_service", None)
    pool = getattr(request.app.state, "db_pool", None)

    if query_service is None:
        raise HTTPException(
            status_code=503,
            detail={"request_id": req_id, "error_code": "SERVICE_INITIALIZING", "message": "Query service is still initializing"}
        )

    async def event_generator():
        try:
            # --- Scope router: classify before touching retrieval ---
            decision = QueryRouter.classify(req.question, req.conversation_history)

            if decision.route != ROUTE_RAG:
                yield f"event: {decision.route}\ndata: {json.dumps({'message': decision.fast_response, 'category': decision.category})}\n\n"
                yield f"event: done\ndata: {{}}\n\n"
                return

            # --- Full RAG pipeline ---
            async for event in query_service.run_streaming(
                pool=pool,
                query=req.question,
                conversation_history=req.conversation_history,
                spec_filter=req.spec_filter,
                release_filter=req.release_filter,
                request_id=req_id
            ):
                yield f"event: {event.type}\ndata: {json.dumps(event.data)}\n\n"
        except asyncio.CancelledError:
            pass  # client disconnected — normal
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Stream error: {e}")
            error_data = json.dumps({"message": "Internal error mid-stream"})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
