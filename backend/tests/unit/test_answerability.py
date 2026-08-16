from app.services.answerability import AnswerabilityChecker
from app.providers.base import ScoredChunk

def test_answerability_empty_chunks():
    checker = AnswerabilityChecker(abstain_threshold=0.25)
    assessment = checker.evaluate([])
    assert assessment.is_sufficient is False
    assert assessment.evidence_score == 0.0

def test_answerability_with_strong_evidence():
    checker = AnswerabilityChecker(abstain_threshold=0.25)
    chunks = [
        ScoredChunk("c1", "d1", "TS 23.501", 18, "18.6.0", "4.2.2", "AMF", "4.2", 1, 1, "AMF text", 30, rrf_score=0.03, reranker_score=0.85),
        ScoredChunk("c2", "d1", "TS 23.501", 18, "18.6.0", "6.2.1", "SMF", "6.2", 2, 2, "SMF text", 30, rrf_score=0.02, reranker_score=0.72)
    ]
    assessment = checker.evaluate(chunks)
    assert assessment.is_sufficient is True
    assert assessment.evidence_score >= 0.25
