import pytest
from ingestion.tagger import generate_chunk_tags
from backend.app.services.tag_extractor import QueryTagExtractor

def test_7layer_tag_generation():
    text = (
        "The UE SHALL initiate the initial registration procedure by sending a Registration Request "
        "message over the N1 reference point to the AMF using NAS 5GMM protocol. "
        "Timer T3510 is started."
    )
    tags = generate_chunk_tags(
        spec_number="TS 23.502",
        section_title="Initial Registration Procedure",
        text=text,
        release=18
    )

    # Layer 1: Domain
    assert "domain:procedures" in tags
    assert "domain:core_5gc" in tags

    # Layer 2: Procedure & Timers
    assert "proc:registration" in tags
    assert "topic:timers" in tags

    # Layer 3: Network Function
    assert "nf:amf" in tags
    assert "nf:ue" in tags

    # Layer 4: Interface
    assert "iface:n1" in tags

    # Layer 5: Protocol
    assert "proto:nas_5gmm" in tags

    # Layer 6: Release
    assert "rel:18" in tags

    # Layer 7: Normative
    assert "normative:mandatory" in tags

def test_7layer_query_tag_extraction():
    query = "What are the AMF procedures during initial registration in Release 18 over N1?"
    result = QueryTagExtractor.extract(query)

    tags = result["tags"]
    assert "nf:amf" in tags
    assert "proc:registration" in tags
    assert "iface:n1" in tags
    assert "rel:18" in tags
    assert result["is_confident"] is True
    assert result["confidence"] >= 0.7
