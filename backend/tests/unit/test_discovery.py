import pytest
from ingestion.discovery import decode_3gpp_version, SpecDiscoveryEngine, FLAGSHIP_5GS_SPECS

def test_decode_3gpp_version():
    # 3GPP letter code decoding: a=10, ..., g=16, h=17, i=18
    assert decode_3gpp_version("i40") == "18.4.0"
    assert decode_3gpp_version("h20") == "17.2.0"
    assert decode_3gpp_version("g80") == "16.8.0"
    assert decode_3gpp_version("f00") == "15.0.0"
    assert decode_3gpp_version("810") == "8.1.0"

def test_spec_discovery_catalog():
    engine = SpecDiscoveryEngine(target_releases=[17, 18])
    catalog = engine.get_curated_catalog()
    assert len(catalog) == len(FLAGSHIP_5GS_SPECS) * 2
    
    spec_numbers = {s.spec_number for s in catalog}
    assert "TS 23.501" in spec_numbers
    assert "TS 24.501" in spec_numbers
    assert "TS 38.331" in spec_numbers
    assert "TS 33.501" in spec_numbers
    assert "TS 29.518" in spec_numbers

    # Verify download URLs
    sample = catalog[0]
    assert sample.download_url.startswith("https://www.3gpp.org/ftp/Specs/archive")
    assert sample.release in [17, 18]
