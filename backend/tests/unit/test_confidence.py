from app.services.confidence import ConfidenceClassifier
from app.models.schemas import Claim

def test_confidence_classification_levels():
    claims = [Claim(text="Valid claim", source_ids=["uuid-1"])]
    
    # High score
    high = ConfidenceClassifier.classify(top_score=0.9, evidence_score=0.85, supporting_chunks_count=4, claims=claims)
    assert high == "HIGH"

    # Low score
    low = ConfidenceClassifier.classify(top_score=0.2, evidence_score=0.28, supporting_chunks_count=1, claims=claims)
    assert low == "LOW"

    # Abstain when evidence score < 0.25
    abstain = ConfidenceClassifier.classify(top_score=0.1, evidence_score=0.10, supporting_chunks_count=0, claims=[])
    assert abstain == "ABSTAIN"
