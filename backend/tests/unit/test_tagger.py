from ingestion.tagger import generate_chunk_tags
from app.services.tag_extractor import QueryTagExtractor

def test_chunk_tag_generation():
    text = "The AMF shall execute general registration procedures and select target SMF based on S-NSSAI."
    tags = generate_chunk_tags("TS 23.501", "AMF Registration Management", text)
    
    assert "domain:architecture" in tags
    assert "domain:core_5gc" in tags
    assert "nf:amf" in tags
    assert "nf:smf" in tags
    assert "proc:registration" in tags
    assert "topic:slicing" in tags
    assert "type:normative_rule" in tags

def test_query_tag_extraction():
    q = "What are the 5G AKA authentication procedures in TS 33.501?"
    result = QueryTagExtractor.extract(q)
    
    assert "domain:security" in result["tags"]
    assert "proc:aka_auth" in result["tags"]
    assert result["is_confident"] is True

def test_unrelated_query_tag_extraction_fail_open():
    q = "How do you make pizza in Rome?"
    result = QueryTagExtractor.extract(q)
    
    assert len(result["tags"]) == 0
    assert result["is_confident"] is False
