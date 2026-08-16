import os
import hashlib
import zipfile
import re
import io
import requests
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from bs4 import BeautifulSoup
from ingestion.discovery import decode_3gpp_version

SPECS_DIR = Path("data/specs")
CHECKSUM_DIR = Path("data/checksums")

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def discover_latest_archive(series: str, spec_num: str, release: int) -> Tuple[str, str]:
    """
    Scrapes the 3GPP FTP HTML index to discover the exact latest zip archive URL and version code for the requested release.
    """
    letter_code = chr(ord('a') + release - 10)  # 'i' for Rel-18, 'h' for Rel-17
    base_url = f"https://www.3gpp.org/ftp/Specs/archive/{series}_series/{spec_num}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        r = requests.get(base_url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            zips = [a.get("href") for a in soup.find_all("a") if a.get("href", "").endswith(".zip")]
            pat = re.compile(rf"-{letter_code}([0-9a-zA-Z]+)\.zip", re.IGNORECASE)
            rel_matches = []
            for z in zips:
                m = pat.search(z)
                if m:
                    rel_matches.append((z, f"{letter_code}{m.group(1)}"))
            if rel_matches:
                zip_href, vcode = rel_matches[-1]
                full_url = zip_href if zip_href.startswith("http") else f"{base_url}{zip_href.lstrip('/')}"
                return full_url, vcode
    except Exception as e:
        print(f"  [Discovery Warning] Could not auto-discover archive: {e}")

    # Fallback to default version code
    default_vcode = f"{letter_code}40" if release == 18 else f"{letter_code}20"
    spec_digits = spec_num.replace(".", "")
    return f"{base_url}{spec_digits}-{default_vcode}.zip", default_vcode

def download_spec(spec: Dict[str, Any], dest_dir: Path = SPECS_DIR) -> Tuple[Path, str, str, str, int, str]:
    """
    Downloads and extracts a 3GPP specification archive (ZIP/DOCX/PDF).
    Auto-discovers the latest Release archive version dynamically.
    Returns (extracted_document_path, version_string, checksum_sha256, version_code, file_size_bytes, ftp_relative_path).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    CHECKSUM_DIR.mkdir(parents=True, exist_ok=True)
    
    spec_num = spec["spec_number"].replace("TS ", "").replace("TR ", "").replace(" ", "")
    spec_digits = spec_num.replace(".", "")
    series = spec.get("series", spec_digits[:2])
    release = int(spec.get("release", 18))
    
    # Auto-discover the exact latest archive URL and version letter code
    archive_url, version_code = discover_latest_archive(series, spec_num, release)
    version_str = decode_3gpp_version(version_code)
    zip_filename = f"{spec_digits}-{version_code}.zip"
    ftp_relative_path = f"Specs/archive/{series}_series/{spec_num}/{zip_filename}"

    checksum_file = CHECKSUM_DIR / f"{spec_digits}_rel{release}_{version_code}.sha256"
    for ext in [".docx", ".doc", ".pdf"]:
        candidate = dest_dir / f"{spec_digits}_rel{release}_{version_code}{ext}"
        if candidate.exists() and checksum_file.exists():
            return candidate, version_str, checksum_file.read_text().strip(), version_code, candidate.stat().st_size, ftp_relative_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }

    print(f"  Downloading 3GPP archive from: {archive_url}")
    resp = requests.get(archive_url, headers=headers, timeout=120)
    resp.raise_for_status()

    # Extract ZIP
    extracted_doc = None
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        for member_name in z.namelist():
            ext = Path(member_name).suffix.lower()
            if ext in [".docx", ".doc", ".pdf"]:
                out_path = dest_dir / f"{spec_digits}_rel{release}_{version_code}{ext}"
                with open(out_path, "wb") as f_out:
                    f_out.write(z.read(member_name))
                extracted_doc = out_path
                break

    if extracted_doc is None:
        out_path = dest_dir / f"{spec_digits}_rel{release}_{version_code}.zip"
        out_path.write_bytes(resp.content)
        extracted_doc = out_path

    sha = compute_sha256(extracted_doc)
    checksum_file.write_text(sha)

    return extracted_doc, version_str, sha, version_code, extracted_doc.stat().st_size, ftp_relative_path
