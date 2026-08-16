import time
import hashlib
import json
import re
import tiktoken
from app.logging_config import get_logger
from typing import Optional, List
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.models.schemas import QueryRequest, QueryResponse, DebugInfo, ScoredChunkDebug, Claim, StreamEvent, ConversationTurn
from app.providers.base import ScoredChunk
from app.providers.gemini_provider import GeminiProvider
from app.prompts.answer_prompt import build_grounded_prompt, SYSTEM_PROMPT
from app.services.retriever import RetrieverService
from app.services.answerability import AnswerabilityChecker
from app.services.citation_validator import CitationValidator
from app.services.confidence import ConfidenceClassifier
from app.db.queries import log_query_event

logger = get_logger(__name__)
def count_tokens_quick(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return max(1, int(len(text.split()) * 1.3))

SPEC_REGEX = re.compile(r'\b(TS\s*\d{2}\.\d{3}|\d{2}\.\d{3})\b', re.IGNORECASE)

class QueryService:
    def __init__(self, embedding_provider, reranker=None, llm_provider=None):
        self.retriever = RetrieverService(embedding_provider)
        self.reranker = reranker
        self.llm = llm_provider or GeminiProvider()
        self.answerability = AnswerabilityChecker()

    def _normalize_spec_query(self, query: str) -> Optional[str]:
        m = SPEC_REGEX.search(query)
        if m:
            s = m.group(1).upper()
            if not s.startswith("TS"):
                s = f"TS {s}"
            return s
        return None

    def _trim_context_budget(self, chunks: List[ScoredChunk], max_tokens: int = 6000) -> List[ScoredChunk]:
        """FM-5: Enforces strict token context budget."""
        budget = max_tokens
        selected = []
        for c in chunks:
            tok_count = c.token_count or count_tokens_quick(c.text)
            if tok_count <= budget:
                selected.append(c)
                budget -= tok_count
            if budget <= 0:
                break
        return selected or chunks[:1]

    async def execute_query(self, pool, req: QueryRequest, request_id: str) -> QueryResponse:
        t_start = time.time()
        query_hash = hashlib.sha256(req.question.encode()).hexdigest()[:16]

        detected_spec = req.spec_filter or self._normalize_spec_query(req.question)

        # 1. Retrieval
        t_ret_start = time.time()
        candidates, fallback_used = await self.retriever.retrieve(
            pool=pool,
            query=req.question,
            release_filter=req.release_filter,
            spec_filter=detected_spec
        )
        retrieval_ms = int((time.time() - t_ret_start) * 1000)

        # 2. Reranking
        t_rerank_start = time.time()
        if self.reranker and settings.reranker_enabled:
            reranked = await run_in_threadpool(self.reranker.rerank, req.question, candidates, 8)
            has_reranker_scores = any(c.reranker_score is not None for c in reranked)
            if has_reranker_scores:
                reranked = [c for c in reranked if (c.reranker_score or 0.0) >= settings.reranker_floor]
            else:
                reranked = [c for c in reranked if (c.rrf_score or 0.0) >= settings.rrf_floor]
        else:
            reranked = [c for c in candidates[:8] if (c.rrf_score or 0.0) >= settings.rrf_floor]
        reranker_ms = int((time.time() - t_rerank_start) * 1000)

        # 3. Answerability Check
        assessment = self.answerability.evaluate(reranked)

        if not assessment.is_sufficient:
            total_ms = int((time.time() - t_start) * 1000)
            await log_query_event(pool, {
                "request_id": request_id,
                "query_hash": query_hash,
                "detected_spec": detected_spec,
                "detected_release": req.release_filter,
                "retrieval_count": len(candidates),
                "reranked_count": len(reranked),
                "confidence": "ABSTAIN",
                "abstained": True,
                "citation_count": 0,
                "citation_valid": True,
                "llm_provider": "gemini",
                "llm_model": settings.llm_model,
                "retrieval_ms": retrieval_ms,
                "reranker_ms": reranker_ms,
                "llm_ms": 0,
                "total_ms": total_ms,
                "fallback_used": fallback_used
            })

            return QueryResponse(
                request_id=request_id,
                question=req.question,
                answer=assessment.reason,
                claims=[],
                sources=[],
                confidence="ABSTAIN",
                abstained=True,
                abstain_reason=assessment.reason,
                total_ms=total_ms,
                debug=DebugInfo(
                    evidence_score=assessment.evidence_score,
                    retrieval_count=len(candidates),
                    reranked_count=len(reranked),
                    top_chunks=[
                        ScoredChunkDebug(
                            chunk_id=c.chunk_id,
                            spec_number=c.spec_number,
                            section_number=c.section_number,
                            text_preview=c.text[:180],
                            rrf_score=c.rrf_score,
                            reranker_score=c.reranker_score,
                            vector_distance=c.vector_distance
                        ) for c in reranked[:5]
                    ],
                    retrieval_ms=retrieval_ms,
                    reranker_ms=reranker_ms,
                    llm_ms=0
                ) if req.debug else None
            )

        # 4. Context budget trimming
        context_chunks = self._trim_context_budget(reranked, max_tokens=settings.context_token_limit)
        context_tokens = sum(c.token_count for c in context_chunks)

        # 5. LLM Grounded Generation
        prompt = build_grounded_prompt(req.question, context_chunks)
        t_llm_start = time.time()
        
        llm_resp = await self.llm.generate(prompt, SYSTEM_PROMPT)
        llm_ms = int((time.time() - t_llm_start) * 1000)

        # 6. Parse JSON output
        try:
            parsed_json = json.loads(llm_resp.text)
            answer_text = parsed_json.get("answer", "")
            raw_claims = [Claim(text=cl.get("text", ""), source_ids=cl.get("source_ids", [])) for cl in parsed_json.get("claims", [])]
            llm_abstain = parsed_json.get("abstain", False)
        except Exception:
            answer_text = llm_resp.text
            raw_claims = []
            llm_abstain = False

        # 7. Citation Validation (8 checks)
        val_result = CitationValidator.validate(raw_claims, context_chunks, answer_text)

        # 8. Confidence Classification
        top_s = (reranked[0].reranker_score + 1.0)/2.0 if reranked[0].reranker_score is not None else reranked[0].rrf_score * 50.0
        confidence = ConfidenceClassifier.classify(
            top_score=min(top_s, 1.0),
            evidence_score=assessment.evidence_score,
            supporting_chunks_count=len(context_chunks),
            claims=val_result.valid_claims,
            uncovered_sentences=val_result.uncovered_count
        )

        abstained = llm_abstain or val_result.all_invalid or confidence == "ABSTAIN"
        abstain_reason = None
        if abstained:
            confidence = "ABSTAIN"
            abstain_reason = "Citation validation failed or model self-reported insufficient evidence."

        total_ms = int((time.time() - t_start) * 1000)

        # 9. Log query event
        await log_query_event(pool, {
            "request_id": request_id,
            "query_hash": query_hash,
            "detected_spec": detected_spec,
            "detected_release": req.release_filter,
            "retrieval_count": len(candidates),
            "reranked_count": len(reranked),
            "confidence": confidence,
            "abstained": abstained,
            "citation_count": len(val_result.valid_sources),
            "citation_valid": not val_result.all_invalid,
            "llm_provider": llm_resp.provider,
            "llm_model": llm_resp.model,
            "retrieval_ms": retrieval_ms,
            "reranker_ms": reranker_ms,
            "llm_ms": llm_ms,
            "total_ms": total_ms,
            "model_fallback_used": llm_resp.model_fallback_used,
            "key_fallback_used": llm_resp.key_fallback_used,
            "input_tokens": llm_resp.input_tokens,
            "output_tokens": llm_resp.output_tokens,
            "estimated_cost_usd": llm_resp.estimated_cost_usd,
            "context_token_count": context_tokens,
            "uncovered_claim_count": val_result.uncovered_count,
            "fallback_used": fallback_used
        })

        return QueryResponse(
            request_id=request_id,
            question=req.question,
            answer=answer_text,
            claims=val_result.valid_claims,
            sources=val_result.valid_sources,
            confidence=confidence,
            abstained=abstained,
            abstain_reason=abstain_reason,
            total_ms=total_ms,
            debug=DebugInfo(
                evidence_score=assessment.evidence_score,
                retrieval_count=len(candidates),
                reranked_count=len(reranked),
                top_chunks=[
                    ScoredChunkDebug(
                        chunk_id=c.chunk_id,
                        spec_number=c.spec_number,
                        section_number=c.section_number,
                        text_preview=c.text[:180],
                        rrf_score=c.rrf_score,
                        reranker_score=c.reranker_score,
                        vector_distance=c.vector_distance
                    ) for c in reranked[:5]
                ],
                retrieval_ms=retrieval_ms,
                reranker_ms=reranker_ms,
                llm_ms=llm_ms
            ) if req.debug else None
        )

    from typing import AsyncGenerator
    async def run_streaming(
        self,
        pool,
        query: str,
        conversation_history: List[ConversationTurn],
        spec_filter: Optional[str] = None,
        release_filter: Optional[int] = 18,
        request_id: str = None
    ) -> 'AsyncGenerator[StreamEvent, None]':
        t_start = time.time()
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]

        from app.services.context_manager import trim_history, build_effective_query
        
        trimmed_history = trim_history(conversation_history)
        effective_query = build_effective_query(query, trimmed_history)
        
        detected_spec = spec_filter or self._normalize_spec_query(query)

        # 1. Retrieval
        yield StreamEvent(type="status", data={"stage": "retrieving", "message": "Searching 3GPP knowledge base..."})
        t_ret_start = time.time()
        candidates, fallback_used = await self.retriever.retrieve(
            pool=pool,
            query=effective_query,
            release_filter=release_filter,
            spec_filter=detected_spec
        )
        retrieval_ms = int((time.time() - t_ret_start) * 1000)

        # 2. Reranking
        yield StreamEvent(type="status", data={"stage": "reranking", "message": "Ranking evidence..."})
        t_rerank_start = time.time()
        if self.reranker and settings.reranker_enabled:
            reranked = await run_in_threadpool(self.reranker.rerank, effective_query, candidates, 8)
            has_reranker_scores = any(c.reranker_score is not None for c in reranked)
            if has_reranker_scores:
                reranked = [c for c in reranked if (c.reranker_score or 0.0) >= settings.reranker_floor]
            else:
                reranked = [c for c in reranked if (c.rrf_score or 0.0) >= settings.rrf_floor]
        else:
            reranked = [c for c in candidates[:8] if (c.rrf_score or 0.0) >= settings.rrf_floor]
        reranker_ms = int((time.time() - t_rerank_start) * 1000)

        # 3. Answerability Check
        assessment = self.answerability.evaluate(reranked)

        if not assessment.is_sufficient:
            yield StreamEvent(type="status", data={"stage": "abstaining", "message": "Insufficient evidence in indexed specifications."})
            yield StreamEvent(type="abstain", data={"reason": assessment.reason, "confidence": "ABSTAIN"})
            yield StreamEvent(type="done", data={})
            
            total_ms = int((time.time() - t_start) * 1000)
            await log_query_event(pool, {
                "request_id": request_id or "",
                "query_hash": query_hash,
                "detected_spec": detected_spec,
                "detected_release": release_filter,
                "retrieval_count": len(candidates),
                "reranked_count": len(reranked),
                "confidence": "ABSTAIN",
                "abstained": True,
                "citation_count": 0,
                "citation_valid": True,
                "llm_provider": "gemini",
                "llm_model": settings.llm_model,
                "retrieval_ms": retrieval_ms,
                "reranker_ms": reranker_ms,
                "llm_ms": 0,
                "total_ms": total_ms,
                "fallback_used": fallback_used,
                "streaming_used": True,
                "history_turns_sent": len(trimmed_history),
                "history_tokens_sent": 0 
            })
            return

        # 4. Context budget trimming
        context_chunks = self._trim_context_budget(reranked, max_tokens=settings.context_token_limit)
        context_tokens = sum(c.token_count for c in context_chunks)

        # 5. LLM Grounded Generation
        prompt = build_grounded_prompt(query, context_chunks, trimmed_history)
        yield StreamEvent(type="status", data={"stage": "generating", "message": "Generating answer..."})
        
        t_llm_start = time.time()
        first_token_ms = None
        full_text = ""
        
        try:
            async for token in self.llm.generate_streaming(prompt, SYSTEM_PROMPT):
                if first_token_ms is None:
                    first_token_ms = int((time.time() - t_llm_start) * 1000)
                full_text += token
                yield StreamEvent(type="token", data={"text": token})
        except Exception as e:
            logger.error(f"Streaming error from LLM: {e}")
            yield StreamEvent(type="error", data={"message": "LLM timeout or generation error. Please retry."})
            yield StreamEvent(type="done", data={})
            return
            
        llm_ms = int((time.time() - t_llm_start) * 1000)

        # 6. Parse JSON output
        try:
            parsed_json = json.loads(full_text)
            answer_text = parsed_json.get("answer", "")
            raw_claims = [Claim(text=cl.get("text", ""), source_ids=cl.get("source_ids", [])) for cl in parsed_json.get("claims", [])]
            llm_abstain = parsed_json.get("abstain", False)
        except Exception:
            # If the streaming text is not valid JSON, we fallback
            answer_text = full_text
            raw_claims = []
            llm_abstain = False

        # 7. Citation Validation
        val_result = CitationValidator.validate(raw_claims, context_chunks, answer_text)

        # 8. Confidence Classification
        top_s = (reranked[0].reranker_score + 1.0)/2.0 if reranked[0].reranker_score is not None else reranked[0].rrf_score * 50.0
        confidence = ConfidenceClassifier.classify(
            top_score=min(top_s, 1.0),
            evidence_score=assessment.evidence_score,
            supporting_chunks_count=len(context_chunks),
            claims=val_result.valid_claims,
            uncovered_sentences=val_result.uncovered_count
        )

        abstained = llm_abstain or val_result.all_invalid or confidence == "ABSTAIN"
        if abstained:
            confidence = "ABSTAIN"

        total_ms = int((time.time() - t_start) * 1000)

        yield StreamEvent(
            type="citations", 
            data={
                "claims": [c.model_dump() for c in val_result.valid_claims],
                "sources": [s.model_dump() for s in val_result.valid_sources],
                "confidence": confidence,
                "abstained": abstained
            }
        )

        yield StreamEvent(
            type="metadata", 
            data={
                "request_id": request_id or "",
                "retrieval_ms": retrieval_ms,
                "reranker_ms": reranker_ms,
                "llm_ms": llm_ms,
                "total_ms": total_ms,
                "first_token_ms": first_token_ms or 0
            }
        )

        yield StreamEvent(type="done", data={})

        await log_query_event(pool, {
            "request_id": request_id or "",
            "query_hash": query_hash,
            "detected_spec": detected_spec,
            "detected_release": release_filter,
            "retrieval_count": len(candidates),
            "reranked_count": len(reranked),
            "confidence": confidence,
            "abstained": abstained,
            "citation_count": len(val_result.valid_sources),
            "citation_valid": not val_result.all_invalid,
            "llm_provider": "gemini",
            "llm_model": settings.llm_model,
            "retrieval_ms": retrieval_ms,
            "reranker_ms": reranker_ms,
            "llm_ms": llm_ms,
            "total_ms": total_ms,
            "context_token_count": context_tokens,
            "uncovered_claim_count": val_result.uncovered_count,
            "fallback_used": fallback_used,
            "streaming_used": True,
            "history_turns_sent": len(trimmed_history),
            "history_tokens_sent": 0,
            "first_token_ms": first_token_ms or 0
        })
