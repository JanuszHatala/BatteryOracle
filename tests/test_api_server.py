import io
import os
import zipfile
import pytest
from fastapi.testclient import TestClient

import db
import api_server


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_battery_oracle.db")
    monkeypatch.setenv("BATTERY_ORACLE_DB_PATH", test_db)
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield test_db


@pytest.fixture
def client():
    return TestClient(api_server.app)


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"


def test_reports_lifecycle(client):
    # 1. Empty list
    res = client.get("/api/v1/reports")
    assert res.status_code == 200
    assert res.json() == []

    # 2. Upload valid bugreport
    content = """========================================================
== dumpstate: 2026-09-04 06:47:00
========================================================
Build: TQ3A.230901.001
Build fingerprint: 'Google/pixel6/cheetah:13/TQ3A.230901.001/10750761:user/release-keys'
Battery History:
    0 (10) 100 status=discharging
    +1m (10) 099
    Capacity: 5000
Estimated power use (mAh):
  Screen: 50.0
All partial wake locks:
  Wake lock 1000:*alarm*: 10s (5 times) realtime
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bugreport-test.txt", content)

    upload_res = client.post(
        "/api/v1/reports/upload",
        files={"file": ("202609040647_bugreport.zip", buf.getvalue(), "application/zip")},
        data={"auto_diagnose": "false"}
    )
    assert upload_res.status_code == 200
    rep = upload_res.json()
    rep_id = rep["id"]
    assert rep["filename"] == "202609040647_bugreport.zip"

    # 3. Get single report
    get_res = client.get(f"/api/v1/reports/{rep_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == rep_id

    # 4. Update metadata and custom night bounds
    update_res = client.put(
        f"/api/v1/reports/{rep_id}",
        json={
            "custom_name": "Updated Night Session",
            "description": "Tested airplane mode",
            "custom_night_start": "2026-09-04T00:00:00",
            "custom_night_end": "2026-09-04T06:00:00"
        }
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["custom_name"] == "Updated Night Session"
    assert updated["custom_night_start"] == "2026-09-04T00:00:00"

    # 5. Export Markdown
    export_res = client.get(f"/api/v1/reports/{rep_id}/export-md")
    assert export_res.status_code == 200
    assert "Battery Oracle Diagnostic Report" in export_res.text

    # 6. Delete report
    del_res = client.delete(f"/api/v1/reports/{rep_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 7. Verify 404 after delete
    get_404 = client.get(f"/api/v1/reports/{rep_id}")
    assert get_404.status_code == 404


def test_upload_invalid_file(client):
    res = client.post(
        "/api/v1/reports/upload",
        files={"file": ("empty.zip", b"not-a-valid-zip", "application/zip")}
    )
    assert res.status_code == 400
    assert "Invalid bugreport archive" in res.json()["detail"]
