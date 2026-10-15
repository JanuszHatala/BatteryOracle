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

def test_parse_device_inventory_modern_dump():
    dump_text = """=== DEVICE_HEADER ===
model=Pixel 10 Pro
manufacturer=Google
android_version=17
sdk=37
build_id=CP3A.260905.009
=== SETTINGS_GLOBAL ===
mobile_data_always_on=0
cell_on=1
wifi_scan_always_enabled=0
ble_scan_always_enabled=0
=== SETTINGS_SECURE ===
location_mode=3
doze_pulse_on_tap=1
=== SETTINGS_SYSTEM ===
peak_refresh_rate=120.0
screen_off_timeout=15000
=== DEVICEIDLE ===
  Whitelist system apps:
    com.android.providers.calendar
  Whitelist user apps:
    com.google.android.retaildemo
=== APPOPS_RUN_IN_BG ===
com.google.android.GoogleCamera
=== APPOPS_RUN_ANY_IN_BG ===
com.google.android.retaildemo
=== APPOPS_WAKE_LOCK ===
com.google.android.iwlan
"""
    parsed = parser.parse_device_inventory(dump_text)
    assert parsed["device_model"] == "Pixel 10 Pro"
    assert parsed["os_build"] == "CP3A.260905.009"
    assert parsed["android_version"] == "17"
    assert "global" in parsed["settings"]
    assert parsed["settings"]["global"]["mobile_data_always_on"] == "0"
    assert "retaildemo" in parsed["doze_whitelist"]["user_apps"][0]
    assert "retaildemo" in parsed["appops_summary"]["unrestricted"][0]
    assert "network_radio" in parsed["highlights"]
    assert parsed["kpis"]["whitelisted_user_apps"] == 1
    assert parsed["kpis"]["total_settings_keys"] == 8

def test_extract_battery_history_screen_tracking(tmp_path):
    sample_content = """Battery History:
  10-12 06:58:46.345 095 e4891a10 status=charging
  10-12 07:30:00.264 095 c4191a10 +screen
  10-12 07:30:30.968 094 c4091a10 -screen
  10-12 07:35:00.000 093 c4091a10
Per-PID Stats:
"""
    log_file = tmp_path / "batterystats_sample.txt"
    log_file.write_text(sample_content)

    df = parser.extract_battery_history(str(log_file), base_year="2026")
    assert not df.empty
    assert "Screen" in df.columns
    assert "Level" in df.columns
    screens = list(df["Screen"])
    assert "on" in screens
    assert "off" in screens
