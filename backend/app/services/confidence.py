from typing import List
from app.models.schemas import ConfidenceLevel, Claim
from app.providers.base import ScoredChunk

class ConfidenceClassifier:
    @staticmethod
    def classify(
        top_score: float,
        evidence_score: float,
        supporting_chunks_count: int,
        claims: List[Claim],
        uncovered_sentences: int = 0
    ) -> ConfidenceLevel:
        if not claims or evidence_score < 0.25:
            return "ABSTAIN"

        score = (0.4 * top_score) + (0.3 * evidence_score) + (0.3 * min(supporting_chunks_count / 3.0, 1.0))

        # Soft downgrade if > 50% sentences uncovered
        if uncovered_sentences > 2:
            score -= 0.15

        if score >= 0.70:
            return "HIGH"
        elif score >= 0.45:
            return "MEDIUM"
        elif score >= 0.25:
            return "LOW"
        return "ABSTAIN"
