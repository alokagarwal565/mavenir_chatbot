import re
from app.logging_config import get_logger
from typing import List, Dict, Any, Set, Tuple
from app.models.schemas import Claim, ClaimSource
from app.providers.base import ScoredChunk

logger = get_logger(__name__)

class CitationValidationResult:
    def __init__(self, valid_claims: List[Claim], valid_sources: List[ClaimSource], all_invalid: bool, uncovered_count: int = 0):
        self.valid_claims = valid_claims
        self.valid_sources = valid_sources
        self.all_invalid = all_invalid
        self.uncovered_count = uncovered_count

class CitationValidator:
    @staticmethod
    def check_answer_claim_coverage(answer: str, claims: List[Claim]) -> int:
        """FM-7: Detects factual sentences in answer not covered by any claim."""
        sentences = re.split(r'(?<=[.!?])\s+', answer.strip())
        factual = [s for s in sentences if len(s.split()) >= 10 and not s.lower().startswith(("based on", "according to", "in summary"))]
        uncovered = 0
        for sent in factual:
            if not any(sent[:30].lower() in c.text.lower() for c in claims):
                uncovered += 1
        return uncovered

    @staticmethod
    def validate(
        claims: List[Claim],
        retrieved_chunks: List[ScoredChunk],
        answer_text: str = ""
    ) -> CitationValidationResult:
        retrieved_map: Dict[str, ScoredChunk] = {c.chunk_id: c for c in retrieved_chunks}
        retrieved_ids: Set[str] = set(retrieved_map.keys())

        valid_claims: List[Claim] = []
        cited_sources: Dict[str, ClaimSource] = {}

        for claim in claims:
            valid_source_ids = []
            for sid in claim.source_ids:
                # Check 1 & 2: Chunk ID exists in retrieved set
                if sid in retrieved_ids:
                    chunk = retrieved_map[sid]
                    valid_source_ids.append(sid)
                    
                    if sid not in cited_sources:
                        cited_sources[sid] = ClaimSource(
                            chunk_id=chunk.chunk_id,
                            spec_number=chunk.spec_number,
                            release=chunk.release,
                            version=chunk.version,
                            section_number=chunk.section_number,
                            section_title=chunk.section_title,
                            page_start=chunk.page_start,
                            excerpt=chunk.text[:220] + ("..." if len(chunk.text) > 220 else "")
                        )
                else:
                    logger.warning("invalid_citation_detected", invalid_source_id=sid)

            if valid_source_ids:
                valid_claims.append(Claim(text=claim.text, source_ids=valid_source_ids))

        all_invalid = (len(valid_claims) == 0 and len(claims) > 0)
        uncovered_count = CitationValidator.check_answer_claim_coverage(answer_text, valid_claims)

        return CitationValidationResult(
            valid_claims=valid_claims,
            valid_sources=list(cited_sources.values()),
            all_invalid=all_invalid,
            uncovered_count=uncovered_count
        )
