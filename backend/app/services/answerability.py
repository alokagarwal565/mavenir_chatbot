from dataclasses import dataclass
from typing import List
from app.providers.base import ScoredChunk
from app.config import settings

@dataclass
class EvidenceAssessment:
    evidence_score: float
    is_sufficient: bool
    reason: str

class AnswerabilityChecker:
    def __init__(self, abstain_threshold: float = settings.abstain_threshold):
        self.abstain_threshold = abstain_threshold

    def evaluate(self, chunks: List[ScoredChunk]) -> EvidenceAssessment:
        if not chunks:
            return EvidenceAssessment(
                evidence_score=0.0,
                is_sufficient=False,
                reason="No relevant 3GPP specification chunks retrieved."
            )

        # Calculate score based on top candidate quality
        top_chunk = chunks[0]
        if top_chunk.reranker_score is not None:
            top_score = (top_chunk.reranker_score + 1.0) / 2.0  # normalize -1..1 to 0..1
        else:
            top_score = min(top_chunk.rrf_score * 50.0, 1.0)

        # High supporting chunks
        high_support = sum(1 for c in chunks if (c.reranker_score or 0) > settings.reranker_floor or c.rrf_score > settings.rrf_floor)
        coverage_bonus = min(high_support / 4.0, 1.0)

        evidence_score = (0.7 * top_score) + (0.3 * coverage_bonus)

        is_sufficient = evidence_score >= self.abstain_threshold

        return EvidenceAssessment(
            evidence_score=round(evidence_score, 3),
            is_sufficient=is_sufficient,
            reason="Sufficient authoritative evidence found." if is_sufficient else "Insufficient evidence in indexed 3GPP specifications."
        )
