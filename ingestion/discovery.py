import re
import hashlib
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import httpx
try:
    from app.logging_config import get_logger
except ImportError:
    import logging
    get_logger = lambda name: logging.getLogger(name)

logger = get_logger(__name__)

# 3GPP FTP Base URL (HTTP Mirror)
FTP_BASE_URL = "https://www.3gpp.org/ftp/Specs/archive"

# Flagship Curated 5GS Specifications
FLAGSHIP_5GS_SPECS = [
    # Series 23: Architecture & Procedures
    {"spec_number": "TS 23.501", "series": "23", "title": "System Architecture for the 5G System (5GS)", "wg": "SA2"},
    {"spec_number": "TS 23.502", "series": "23", "title": "Procedures for the 5G System (5GS)", "wg": "SA2"},
    {"spec_number": "TS 23.503", "series": "23", "title": "Policy and Charging Control Framework for the 5GS", "wg": "SA2"},
    {"spec_number": "TS 23.548", "series": "23", "title": "5G System User Plane Protocols including Edge Computing", "wg": "SA2"},
    {"spec_number": "TS 23.558", "series": "23", "title": "Architecture for enabling Edge Applications", "wg": "SA2"},
    
    # Series 24: NAS Signaling
    {"spec_number": "TS 24.501", "series": "24", "title": "Non-Access-Stratum (NAS) protocol for 5GS", "wg": "CT1"},
    {"spec_number": "TS 24.502", "series": "24", "title": "Access to the 3GPP 5G Core Network via Non-3GPP Access Networks", "wg": "CT1"},
    {"spec_number": "TS 24.526", "series": "24", "title": "User Equipment (UE) Route Selection Policy (URSP)", "wg": "CT1"},
    
    # Series 38: NR Radio & RRC/NGAP
    {"spec_number": "TS 38.300", "series": "38", "title": "NR and NG-RAN Overall Description", "wg": "RAN2"},
    {"spec_number": "TS 38.331", "series": "38", "title": "NR Radio Resource Control (RRC) Protocol Specification", "wg": "RAN2"},
    {"spec_number": "TS 38.401", "series": "38", "title": "NG-RAN Architecture Description", "wg": "RAN3"},
    {"spec_number": "TS 38.413", "series": "38", "title": "NG Application Protocol (NGAP)", "wg": "RAN3"},
    {"spec_number": "TS 38.423", "series": "38", "title": "Xn Application Protocol (XnAP)", "wg": "RAN3"},

    # Series 33: Security & 5G-AKA
    {"spec_number": "TS 33.501", "series": "33", "title": "Security Architecture and Procedures for 5G System", "wg": "SA3"},
    {"spec_number": "TS 33.535", "series": "33", "title": "Authentication and Key Management for Applications (AKMA)", "wg": "SA3"},

    # Series 29: SBI Core Network APIs
    {"spec_number": "TS 29.500", "series": "29", "title": "5G System Technical Realization of Service Based Architecture", "wg": "CT4"},
    {"spec_number": "TS 29.501", "series": "29", "title": "5G System Principles and Guidelines for Services Definition", "wg": "CT4"},
    {"spec_number": "TS 29.502", "series": "29", "title": "5G System Session Management Services (Nsmf)", "wg": "CT4"},
    {"spec_number": "TS 29.503", "series": "29", "title": "5G System Unified Data Management Services (Nudm)", "wg": "CT4"},
    {"spec_number": "TS 29.510", "series": "29", "title": "5G System Network Function Repository Services (Nnrf)", "wg": "CT4"},
    {"spec_number": "TS 29.518", "series": "29", "title": "5G System Access and Mobility Management Services (Namf)", "wg": "CT4"},
    {"spec_number": "TS 29.571", "series": "29", "title": "5G System Common Data Types for Service Based Interfaces", "wg": "CT4"},
]

def decode_3gpp_version(version_code: str) -> str:
    """
    Decodes 3GPP 3-character version code into semver string (e.g. 'i40' -> '18.4.0', 'h20' -> '17.2.0').
    Base: 3GPP uses a=10, b=11, ..., g=16, h=17, i=18, j=19, k=20.
    """
    if not version_code or len(version_code) < 3:
        return version_code

    first_char = version_code[0].lower()
    if first_char.isalpha():
        major = ord(first_char) - ord('a') + 10
    elif first_char.isdigit():
        major = int(first_char)
    else:
        major = 0

    second_char = version_code[1]
    if second_char.isalpha():
        minor = ord(second_char.lower()) - ord('a') + 10
    elif second_char.isdigit():
        minor = int(second_char)
    else:
        minor = 0

    third_char = version_code[2]
    if third_char.isalpha():
        patch = ord(third_char.lower()) - ord('a') + 10
    elif third_char.isdigit():
        patch = int(third_char)
    else:
        patch = 0

    return f"{major}.{minor}.{patch}"

@dataclass
class DiscoveredSpecVersion:
    spec_number: str
    series: str
    release: int
    version_string: str
    version_code: str
    title: str
    download_url: str
    relative_path: str

class SpecDiscoveryEngine:
    def __init__(self, target_releases: List[int] = [17, 18]):
        self.target_releases = target_releases

    def get_curated_catalog(self) -> List[DiscoveredSpecVersion]:
        """Returns the curated catalog of flagship Core 5GS specifications for target releases."""
        catalog = []
        for spec in FLAGSHIP_5GS_SPECS:
            spec_digits = spec["spec_number"].replace("TS ", "").replace("TR ", "").replace(".", "")
            series = spec["series"]
            for rel in self.target_releases:
                # Map release to 3GPP letter code base (Rel-17 -> h, Rel-18 -> i)
                letter_code = chr(ord('a') + rel - 10)
                version_code = f"{letter_code}40" if rel == 18 else f"{letter_code}20"
                version_str = decode_3gpp_version(version_code)
                
                spec_dotted = spec["spec_number"].replace("TS ", "").replace("TR ", "")
                rel_path = f"{series}_series/{spec_dotted}/{spec_digits}-{version_code}.zip"
                url = f"{FTP_BASE_URL}/{rel_path}"
                
                catalog.append(DiscoveredSpecVersion(
                    spec_number=spec["spec_number"],
                    series=series,
                    release=rel,
                    version_string=version_str,
                    version_code=version_code,
                    title=spec["title"],
                    download_url=url,
                    relative_path=rel_path
                ))
        return catalog
