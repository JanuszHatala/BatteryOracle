import pytest
from datetime import datetime
import parser

def test_calculate_sha256():
    data = b"hello world"
    # sha256 of b"hello world"
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert parser.calculate_sha256(data) == expected

def test_parse_filename_timestamp():
    fn1 = "bugreport-coral-QQ3A.200805.001-2020-08-06-12-30-45.zip"
    assert parser.parse_filename_timestamp(fn1) == "2020 08 06 12 30 45"
    
    fn2 = "202609040647_bugreport.zip"
    assert parser.parse_filename_timestamp(fn2) == "2026-09-04 06:47"

def test_extract_device_info():
    headers = [
        "Build fingerprint: 'Google/pixel6/cheetah:13/TQ3A.230901.001/10750761:user/release-keys'",
        "Build: TQ3A.230901.001"
    ]
    batterystats = [
        "Battery History:",
        "Capacity: 5000"
    ]
    info = parser.extract_device_info(headers, batterystats)
    assert "Google Pixel6" in info
    assert "Build: TQ3A.230901.001" in info
    assert "Capacity: 5000 mAh" in info

def test_standard_components_dictionary():
    assert "0" in parser.STANDARD_COMPONENTS
    assert "1000" in parser.STANDARD_COMPONENTS
    assert "wifi" in parser.STANDARD_COMPONENTS
