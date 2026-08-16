from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ValidationReport:
    document_id: str
    spec_number: str
    total_chunks: int
    null_embeddings_count: int
    valid_sections_rate: float
    is_valid: bool
    issues: List[str]

def validate_ingestion_data(spec_number: str, chunks: list) -> ValidationReport:
    issues = []
    total = len(chunks)
    if total == 0:
        return ValidationReport(
            document_id="",
            spec_number=spec_number,
            total_chunks=0,
            null_embeddings_count=0,
            valid_sections_rate=0.0,
            is_valid=False,
            issues=["No chunks generated"]
        )

    with_section = sum(1 for c in chunks if c.section_number is not None)
    rate = with_section / total

    if rate < 0.5:
        issues.append(f"Section parsing rate ({rate:.1%}) is below threshold (50%)")

    # Character validity checks
    for c in chunks:
        non_ascii = sum(1 for ch in c.text if ord(ch) > 127)
        if len(c.text) > 0 and (non_ascii / len(c.text)) > 0.30:
            issues.append(f"Chunk {c.chunk_index} has high non-ASCII character ratio (>30%)")

    return ValidationReport(
        document_id="",
        spec_number=spec_number,
        total_chunks=total,
        null_embeddings_count=0,
        valid_sections_rate=rate,
        is_valid=len(issues) == 0,
        issues=issues
    )
