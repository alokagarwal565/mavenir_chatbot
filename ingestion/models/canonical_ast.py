from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class SectionNode:
    section_number: str
    section_title: str
    clause_level: int
    breadcrumb_path: str
    page_start: int
    page_end: int
    paragraphs: List[str] = field(default_factory=list)
    parent_section: Optional[str] = None
    subsections: List[SectionNode] = field(default_factory=list)
    normative_type: str = "INFORMATIVE"  # "MANDATORY", "OPTIONAL", "CONDITIONAL", "RECOMMENDATION", "INFORMATIVE"

@dataclass
class TableNode:
    table_number: str
    table_title: str
    section_number: str
    headers: List[str]
    rows: List[List[str]]
    markdown_grid: str
    page_number: int

@dataclass
class FigureNode:
    figure_number: str
    figure_title: str
    section_number: str
    figure_type: str  # "CALL_FLOW", "BLOCK_DIAGRAM", "STATE_CHART"
    raw_image_path: Optional[str] = None
    mermaid_syntax: Optional[str] = None
    extracted_text: str = ""
    page_number: int = 1

@dataclass
class ReferenceNode:
    source_section: str
    target_spec: str
    target_clause: Optional[str]
    context: str

@dataclass
class DocumentAST:
    spec_number: str
    release_number: int
    version_string: str
    title: str
    total_pages: int
    sections: List[SectionNode] = field(default_factory=list)
    tables: List[TableNode] = field(default_factory=list)
    figures: List[FigureNode] = field(default_factory=list)
    references: List[ReferenceNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_number": self.spec_number,
            "release_number": self.release_number,
            "version_string": self.version_string,
            "title": self.title,
            "total_pages": self.total_pages,
            "total_sections": len(self.sections),
            "total_tables": len(self.tables),
            "total_figures": len(self.figures),
            "total_references": len(self.references),
            "metadata": self.metadata,
            "created_at": self.created_at
        }
