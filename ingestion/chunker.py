from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from ingestion.tagger import generate_chunk_tags

@dataclass
class Chunk:
    chunk_index: int
    section_number: Optional[str]
    section_title: Optional[str]
    parent_section: Optional[str]
    page_start: int
    page_end: int
    text: str
    token_count: int
    metadata: Dict[str, Any]
    tags: Optional[List[str]] = None

_ENC = None

def get_encoder():
    global _ENC
    if _ENC is None:
        try:
            import tiktoken
            _ENC = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _ENC = "fallback"
    return _ENC

def count_tokens(text: str) -> int:
    enc = get_encoder()
    if enc == "fallback" or enc is None:
        return max(1, int(len(text.split()) * 1.3))
    try:
        return len(enc.encode(text))
    except Exception:
        return max(1, int(len(text.split()) * 1.3))

def chunk_document(sections: list, doc_metadata: Dict[str, Any]) -> List[Chunk]:
    chunks: List[Chunk] = []
    chunk_idx = 0

    for sec in sections:
        sec_text = sec.text
        tok_count = count_tokens(sec_text)

        if tok_count <= 800 and tok_count >= 50:
            chunks.append(
                Chunk(
                    chunk_index=chunk_idx,
                    section_number=sec.section_number,
                    section_title=sec.section_title,
                    parent_section=sec.parent_section,
                    page_start=sec.page_start,
                    page_end=sec.page_end,
                    text=sec_text,
                    token_count=tok_count,
                    metadata=doc_metadata,
                    tags=generate_chunk_tags(doc_metadata.get("spec_number", ""), sec.section_title or "", sec_text)
                )
            )
            chunk_idx += 1
        elif tok_count > 800:
            paragraphs = sec_text.split("\n\n")
            curr_para_block = []
            curr_tok_count = 0

            for para in paragraphs:
                p_toks = count_tokens(para)
                if curr_tok_count + p_toks <= 600:
                    curr_para_block.append(para)
                    curr_tok_count += p_toks
                else:
                    if curr_para_block:
                        block_text = "\n\n".join(curr_para_block)
                        chunks.append(
                            Chunk(
                                chunk_index=chunk_idx,
                                section_number=sec.section_number,
                                section_title=sec.section_title,
                                parent_section=sec.parent_section,
                                page_start=sec.page_start,
                                page_end=sec.page_end,
                                text=block_text,
                                token_count=curr_tok_count,
                                metadata=doc_metadata,
                                tags=generate_chunk_tags(doc_metadata.get("spec_number", ""), sec.section_title or "", block_text)
                            )
                        )
                        chunk_idx += 1
                    curr_para_block = [para]
                    curr_tok_count = p_toks

            if curr_para_block:
                block_text = "\n\n".join(curr_para_block)
                chunks.append(
                    Chunk(
                        chunk_index=chunk_idx,
                        section_number=sec.section_number,
                        section_title=sec.section_title,
                        parent_section=sec.parent_section,
                        page_start=sec.page_start,
                        page_end=sec.page_end,
                        text=block_text,
                        token_count=curr_tok_count,
                        metadata=doc_metadata,
                        tags=generate_chunk_tags(doc_metadata.get("spec_number", ""), sec.section_title or "", block_text)
                    )
                )
                chunk_idx += 1

    return chunks
