from app.services.citation_validator import CitationValidator
from app.models.schemas import Claim
from app.providers.base import ScoredChunk

def test_citation_validator_filters_fake_uuid():
    retrieved = [
        ScoredChunk("valid-uuid-1", "d1", "TS 23.501", 18, "18.6.0", "4.2.2", "AMF", "4.2", 1, 1, "AMF terminates N1.", 20)
    ]
    
    claims = [
        Claim(text="AMF terminates N1 interface.", source_ids=["valid-uuid-1"]),
        Claim(text="Quantum core routing is used.", source_ids=["fake-hallucinated-uuid-999"])
    ]

    result = CitationValidator.validate(claims, retrieved, "AMF terminates N1 interface.")
    assert len(result.valid_claims) == 1
    assert result.valid_claims[0].source_ids == ["valid-uuid-1"]
    assert len(result.valid_sources) == 1
    assert result.all_invalid is False
