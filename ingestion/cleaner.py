import re

def clean_text(text: str) -> str:
    """
    Cleans 3GPP document text:
    - Strips recurring header lines (e.g. '3GPP TS 23.501 V18.6.0')
    - Strips page number footers
    - Removes ETSI/3GPP copyright boilerplate
    - Normalizes multiple blank lines and unicode spaces
    """
    lines = text.splitlines()
    cleaned_lines = []

    header_pat = re.compile(r'^\s*3GPP\s+TS\s+\d{2}\.\d{3}.*?version', re.IGNORECASE)
    footer_pat = re.compile(r'^\s*(ETSI\s+)?3GPP\s*$', re.IGNORECASE)
    page_num_pat = re.compile(r'^\s*\d+\s*$', re.IGNORECASE)
    copyright_pat = re.compile(r'copyright\s+.*?(3gpp|etsi)', re.IGNORECASE)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        if header_pat.match(stripped):
            continue
        if footer_pat.match(stripped):
            continue
        if page_num_pat.match(stripped):
            continue
        if copyright_pat.search(stripped):
            continue
        
        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)
    # Collapse 3+ consecutive newlines to 2
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()
