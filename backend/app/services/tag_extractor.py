import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Set

root_dir = str(Path(__file__).resolve().parents[3])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from ingestion.tagger import NF_VOCAB, PROC_VOCAB, IFACE_VOCAB, PROTO_VOCAB

class QueryTagExtractor:
    @staticmethod
    def extract(query: str, target_release: int = None) -> Dict[str, Any]:
        """
        Extracts recognized 7-layer 3GPP domain, NF, procedure, interface, protocol, and release tags
        from user queries with a deterministic fail-open confidence score.
        """
        tags: Set[str] = set()
        q_lower = query.lower()

        # Layer 1: Domain clues
        if "security" in q_lower or "authentication" in q_lower or "crypto" in q_lower or "aka" in q_lower:
            tags.add("domain:security")
        if "radio" in q_lower or "rrc" in q_lower or "cell" in q_lower or "bearer" in q_lower:
            tags.add("domain:radio_nr")
        if "architecture" in q_lower or "system" in q_lower:
            tags.add("domain:architecture")
        if "sbi" in q_lower or "service based" in q_lower or "rest" in q_lower or "openapi" in q_lower:
            tags.add("domain:sbi_apis")

        # Layer 2: Procedure clues
        for proc_tag, pat in PROC_VOCAB.items():
            if pat.search(query):
                tags.add(proc_tag)

        # Layer 3: Network Function clues
        for nf_name, pat in NF_VOCAB.items():
            if pat.search(query):
                tags.add(f"nf:{nf_name}")

        # Layer 4: Interface clues
        for iface_tag, pat in IFACE_VOCAB.items():
            if pat.search(query):
                tags.add(iface_tag)

        # Layer 5: Protocol clues
        for proto_tag, pat in PROTO_VOCAB.items():
            if pat.search(query):
                tags.add(proto_tag)

        # Layer 6: Release clues (explicit or user filtered)
        if target_release:
            tags.add(f"rel:{target_release}")
        else:
            rel_match = re.search(r'\b(?:Rel(?:ease)?[- ]?)(1[5-9]|20)\b', query, re.IGNORECASE)
            if rel_match:
                tags.add(f"rel:{rel_match.group(1)}")

        # Layer 7: Normative requirement clues
        if re.search(r'\b(shall|must|mandatory|required)\b', query, re.IGNORECASE):
            tags.add("normative:mandatory")

        tag_list = sorted(list(tags))
        confidence = min(len(tag_list) * 0.35, 1.0) if tag_list else 0.0

        return {
            "tags": tag_list,
            "confidence": round(confidence, 2),
            "is_confident": confidence >= 0.35
        }
