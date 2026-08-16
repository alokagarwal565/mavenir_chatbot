import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Section:
    section_number: Optional[str]
    section_title: Optional[str]
    parent_section: Optional[str]
    start_char: int
    end_char: int
    text: str
    page_start: int
    page_end: int

SECTION_HEADING_PAT = re.compile(r'^(#{1,6})\s+(\d+(?:\.\d+)*)\s+(.+)$', re.MULTILINE)

def get_parent_section(sec_num: str) -> str:
    if not sec_num or "." not in sec_num:
        return sec_num
    parts = sec_num.rsplit(".", 1)
    return parts[0]

def detect_sections(markdown_text: str, page_num: int = 1) -> List[Section]:
    """
    Detects clause/subclause hierarchies in markdown output.
    """
    matches = list(SECTION_HEADING_PAT.finditer(markdown_text))
    if not matches:
        return [
            Section(
                section_number=None,
                section_title="General",
                parent_section=None,
                start_char=0,
                end_char=len(markdown_text),
                text=markdown_text,
                page_start=page_num,
                page_end=page_num
            )
        ]

    sections: List[Section] = []
    for i, match in enumerate(matches):
        sec_num = match.group(2).strip()
        sec_title = match.group(3).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        sec_text = markdown_text[start:end].strip()

        sections.append(
            Section(
                section_number=sec_num,
                section_title=sec_title,
                parent_section=get_parent_section(sec_num),
                start_char=start,
                end_char=end,
                text=sec_text,
                page_start=page_num,
                page_end=page_num
            )
        )

    return sections
