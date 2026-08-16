from ingestion.chunker import chunk_document
from ingestion.section_detector import Section

def test_chunker_basic():
    clause_text = """The Access and Mobility Management Function (AMF) includes the following functionalities:
- Termination of RAN CP interface (N2).
- Termination of NAS (N1), NAS ciphering and integrity protection.
- Registration management.
- Connection management.
- Reachability management.
- Mobility Management.
- Lawful intercept (for AMF events and interface to LI System).
- Provide transport for SM messages between UE and SMF.
- Transparent proxy for routing SM messages.
- Access Authentication and Access Authorization.
- Provide transport for SMS messages between UE and SMSF.
- Security Anchor Functionality (SEAF).
- Application Triggering with UDM and AUSF interfaces."""

    sections = [
        Section(
            section_number="4.2.2.2.1",
            section_title="AMF Functionality",
            parent_section="4.2.2",
            start_char=0,
            end_char=len(clause_text),
            text=clause_text,
            page_start=45,
            page_end=45
        )
    ]
    chunks = chunk_document(sections, {"spec_number": "TS 23.501", "release": 18})
    assert len(chunks) == 1
    assert chunks[0].section_number == "4.2.2.2.1"
    assert "AMF" in chunks[0].text
    assert chunks[0].token_count >= 50
