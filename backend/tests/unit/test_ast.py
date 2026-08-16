import pytest
from ingestion.models.canonical_ast import SectionNode, TableNode, FigureNode, ReferenceNode, DocumentAST

def test_canonical_ast_creation():
    sec = SectionNode(
        section_number="4.2.2.2",
        section_title="General Registration Procedure",
        clause_level=4,
        breadcrumb_path="4 > 4.2 > 4.2.2 > 4.2.2.2",
        page_start=45,
        page_end=48,
        paragraphs=["The UE initiates the registration procedure by sending a Registration Request to the gNB."],
        normative_type="MANDATORY"
    )

    tbl = TableNode(
        table_number="Table 4.2.2.2-1",
        table_title="Registration Type Values",
        section_number="4.2.2.2",
        headers=["Type", "Description"],
        rows=[["001", "Initial Registration"], ["010", "Mobility Registration Updating"]],
        markdown_grid="| Type | Description |\n|---|---|\n| 001 | Initial Registration |",
        page_number=46
    )

    fig = FigureNode(
        figure_number="Figure 4.2.2.2.2-1",
        figure_title="Initial Registration Call Flow",
        section_number="4.2.2.2",
        figure_type="CALL_FLOW",
        mermaid_syntax="sequenceDiagram\nUE->>gNB: Registration Request\ngNB->>AMF: N2 Message",
        extracted_text="UE sends Registration Request to gNB. gNB forwards to AMF.",
        page_number=47
    )

    doc = DocumentAST(
        spec_number="TS 23.502",
        release_number=18,
        version_string="18.4.0",
        title="Procedures for the 5G System (5GS)",
        total_pages=540,
        sections=[sec],
        tables=[tbl],
        figures=[fig]
    )

    d = doc.to_dict()
    assert d["spec_number"] == "TS 23.502"
    assert d["total_sections"] == 1
    assert d["total_tables"] == 1
    assert d["total_figures"] == 1
    assert doc.figures[0].figure_type == "CALL_FLOW"
