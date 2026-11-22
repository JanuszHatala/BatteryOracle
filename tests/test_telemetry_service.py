import io
import zipfile
import pytest
import pandas as pd
from datetime import datetime, timedelta

import telemetry_service
import schemas


def create_synthetic_bugreport_zip(filename="bugreport-test-2026-09-04-06-47-00.zip"):
    content = """========================================================
== dumpstate: 2026-09-04 06:47:00
========================================================
Build: TQ3A.230901.001
Build fingerprint: 'Google/pixel6/cheetah:13/TQ3A.230901.001/10750761:user/release-keys'

------ DUMP OF SERVICE batterystats ------
Battery History:
    0 (10) 100 status=discharging
    +1m (10) 099
    Capacity: 5000

Estimated power use (mAh):
  Capacity: 5000, Computed drain: 120, actual drain: 100-150
  Screen: 50.0
  Uid 1000: 25.0
  Uid 10001: 15.0

All partial wake locks:
  Wake lock 1000:*alarm*: 10s (5 times) realtime
------ 1.000s was the duration of 'DUMP OF SERVICE batterystats' ------
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bugreport-test.txt", content)
    return buf.getvalue()


def test_process_bugreport_upload_success():
    zip_bytes = create_synthetic_bugreport_zip()
    res = telemetry_service.process_bugreport_upload(
        filename="202609040647_bugreport.zip",
        file_bytes=zip_bytes,
        timezone="UTC",
        auto_diagnose=False
    )
    assert res["filename"] == "202609040647_bugreport.zip"
    assert "file_hash" in res
    assert "summary_text" in res
    assert isinstance(res["chart_df"], pd.DataFrame)
    assert isinstance(res["history_df"], pd.DataFrame)


def test_process_bugreport_upload_invalid_zip():
    bad_bytes = b"not a valid zip file"
    with pytest.raises(ValueError, match="Invalid bugreport archive"):
        telemetry_service.process_bugreport_upload(
            filename="invalid.zip",
            file_bytes=bad_bytes,
            timezone="UTC",
            auto_diagnose=False
        )


def test_get_effective_telemetry_bounds_and_clamping():
    now = datetime(2026, 9, 4, 0, 0, 0)
    times = [now + timedelta(hours=i) for i in range(10)]
    df_history = pd.DataFrame({
        "Time": times,
        "Level": [100 - i * 2 for i in range(10)],
        "Screen": ["off"] * 10
    })
    report = {
        "id": 1,
        "history_data": df_history,
        "custom_night_start": None,
        "custom_night_end": None
    }

    # Full scope
    s_dt, e_dt, sl_df = telemetry_service.get_effective_telemetry_bounds(report, scope="full")
    assert s_dt == times[0]
    assert e_dt == times[-1]
    assert len(sl_df) == 10

    # Inverted custom scope (end before start) should clamp or fallback safely
    inv_start = (now + timedelta(hours=5)).isoformat()
    inv_end = (now + timedelta(hours=2)).isoformat()
    s_dt, e_dt, sl_df = telemetry_service.get_effective_telemetry_bounds(
        report, scope="custom", custom_start_str=inv_start, custom_end_str=inv_end
    )
    assert s_dt < e_dt
    assert not sl_df.empty


def test_build_telemetry_payload_and_kpis():
    now = datetime(2026, 9, 4, 0, 0, 0)
    times = [now + timedelta(hours=i) for i in range(5)]
    df_history = pd.DataFrame({
        "Time": times,
        "Level": [100, 98, 96, 94, 92],
        "Screen": ["off"] * 5
    })
    df_chart = pd.DataFrame({
        "Component": ["Screen", "Android System"],
        "mAh": [50.0, 25.0]
    })
    report = {
        "id": 1,
        "history_data": df_history,
        "chart_data": df_chart,
        "summary_text": "Estimated power use..."
    }
    payload = telemetry_service.build_telemetry_payload(report, scope="full")
    assert "kpis" in payload
    assert payload["kpis"]["drop_pct"] == 8
    assert payload["kpis"]["start_level"] == 100
    assert payload["kpis"]["end_level"] == 92
    assert "timeline" in payload
    assert "components" in payload
    assert len(payload["timeline"]) == 5


def test_build_markdown_outputs():
    report = {
        "id": 1,
        "custom_name": "Test Session",
        "timestamp_str": "2026-09-04 06:47",
        "filename": "test.zip",
        "device_info": "Google Pixel 6",
        "description": "Night standby test",
        "summary_text": "Estimated Power Use:\nScreen: 50 mAh",
        "chart_data": pd.DataFrame({"Component": ["Screen"], "mAh": [50.0]})
    }
    kpis = {
        "start_time": "2026-09-04 00:00",
        "end_time": "2026-09-04 06:00",
        "start_level": 100,
        "end_level": 94,
        "drop_pct": 6,
        "duration_hrs": 6.0,
        "rate_per_hr": 1.0,
        "status": "Optimal"
    }
    md = telemetry_service.build_single_report_markdown(
        report=report,
        filter_mode="night",
        kpis=kpis,
        diagnosis_text="No regressions detected."
    )
    assert "# 🔋 Battery Oracle Diagnostic Report: Test Session" in md
    assert "| **Discharge Velocity** | **1.00% / hour** |" in md

    cmp_md = telemetry_service.build_comparative_markdown(
        reports=[report],
        filter_mode="night",
        analysis_text="Comparative analysis synthesis text."
    )
    assert "# 🔀 Battery Oracle: Multi-Report Comparative Analysis" in cmp_md
