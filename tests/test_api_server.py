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


def test_telemetry_and_diagnose_endpoints(client, monkeypatch):
    # Upload sample bugreport
    content = """========================================================
== dumpstate: 2026-09-04 06:47:00
========================================================
Build: TQ3A.230901.001
Battery History:
    0 (10) 100 status=discharging
    +1m (10) 099
    Capacity: 5000
Estimated power use (mAh):
  Screen: 50.0
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bugreport-test.txt", content)

    up = client.post(
        "/api/v1/reports/upload",
        files={"file": ("202609040647_bugreport.zip", buf.getvalue(), "application/zip")},
        data={"auto_diagnose": "false"}
    )
    rep_id = up.json()["id"]

    # 1. Test telemetry endpoint with scopes
    tel_full = client.get(f"/api/v1/reports/{rep_id}/telemetry?scope=full")
    assert tel_full.status_code == 200
    data_full = tel_full.json()
    assert data_full["scope"] == "full"
    assert "kpis" in data_full
    assert "timeline" in data_full

    tel_night = client.get(f"/api/v1/reports/{rep_id}/telemetry?scope=night")
    assert tel_night.status_code == 200

    tel_custom = client.get(f"/api/v1/reports/{rep_id}/telemetry?scope=custom&start=2026-09-04T05:00:00&end=2026-09-04T01:00:00")
    assert tel_custom.status_code == 200

    # 2. Test diagnose endpoint with mock LLM
    import llm_manager
    monkeypatch.setattr(llm_manager, "call_llm_tracked", lambda *args, **kwargs: "Mocked AI Diagnosis: Standby optimal.")

    diag_res = client.post(
        f"/api/v1/reports/{rep_id}/diagnose",
        json={"scope": "night"}
    )
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    assert "Mocked AI Diagnosis" in diag_data["diagnosis"]

    # Verify report in DB was updated with new diagnosis and scoped analyses
    get_rep = client.get(f"/api/v1/reports/{rep_id}").json()
    assert "Mocked AI Diagnosis" in get_rep["initial_analysis"]
    assert "night" in get_rep["analyses"]
    assert "Mocked AI Diagnosis" in get_rep["analyses"]["night"]["text"]


def test_comparative_endpoints(client, monkeypatch):
    import llm_manager
    monkeypatch.setattr(llm_manager, "call_llm_tracked", lambda *args, **kwargs: "Comparative Regression Diagnosis: Session 2 dropped 2% faster.")

    # Upload two reports
    def make_zip(name):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("bugreport.txt", f"Build: TQ3A-{name}\nBattery History:\n 0 (10) 100\nCapacity: 5000\n")
        return client.post(
            "/api/v1/reports/upload",
            files={"file": (name, buf.getvalue(), "application/zip")},
            data={"auto_diagnose": "false"}
        ).json()["id"]

    id1 = make_zip("rep1.zip")
    id2 = make_zip("rep2.zip")

    # 1. Analyze
    cmp_res = client.post(
        "/api/v1/comparative/analyze",
        json={"report_ids": [id1, id2], "scope": "night"}
    )
    assert cmp_res.status_code == 200
    cmp_data = cmp_res.json()
    assert "Comparative Regression Diagnosis" in cmp_data["analysis"]

    # 2. Export comparative Markdown
    exp_res = client.get(f"/api/v1/comparative/export-md?report_ids={id1},{id2}&scope=night")
    assert exp_res.status_code == 200
    assert "Multi-Report Comparative Analysis" in exp_res.text


def test_chat_thread_and_messages(client, monkeypatch):
    import llm_manager
    monkeypatch.setattr(llm_manager, "call_llm_tracked", lambda *args, **kwargs: "Oracle Answer: High discharge caused by wifi scan wakelock.")

    # 1. Create report
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bugreport.txt", "Build: TQ3A-Chat\nBattery History:\n 0 (10) 100\nCapacity: 5000\n")
    rep_id = client.post(
        "/api/v1/reports/upload",
        files={"file": ("chat_rep.zip", buf.getvalue(), "application/zip")},
        data={"auto_diagnose": "false"}
    ).json()["id"]

    # 2. Create thread
    th_res = client.post(
        f"/api/v1/reports/{rep_id}/threads",
        json={"title": "New Investigation"}
    )
    assert th_res.status_code == 200
    th_id = th_res.json()["id"]
    assert th_res.json()["title"] == "New Investigation"

    # List threads for report
    list_th = client.get(f"/api/v1/reports/{rep_id}/threads")
    assert list_th.status_code == 200
    assert len(list_th.json()) >= 1

    # 3. Rename thread
    ren_res = client.put(f"/api/v1/threads/{th_id}", json={"title": "Custom Investigation"})
    assert ren_res.status_code == 200
    assert ren_res.json()["title"] == "Custom Investigation"

    # 4. Send user message and get assistant response
    msg_res = client.post(
        f"/api/v1/threads/{th_id}/messages",
        json={"content": "Why did my battery drain overnight?", "filter_context": "Scope: Night Standby"}
    )
    assert msg_res.status_code == 200
    assert msg_res.json()["role"] == "assistant"
    assert "Oracle Answer" in msg_res.json()["content"]

    # 5. List messages in thread
    msgs_list = client.get(f"/api/v1/threads/{th_id}/messages")
    assert msgs_list.status_code == 200
    msgs = msgs_list.json()
    assert len(msgs) == 2  # user + assistant
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    user_msg_id = msgs[0]["id"]
    asst_msg_id = msgs[1]["id"]

    # 6. Toggle collapse
    col_res = client.put(f"/api/v1/messages/{asst_msg_id}/collapse")
    assert col_res.status_code == 200
    assert col_res.json()["is_collapsed"] is True

    # 7. Fork thread from user message
    fork_res = client.post(
        f"/api/v1/threads/{th_id}/fork",
        json={"from_message_id": user_msg_id, "new_title": "Forked Branch"}
    )
    assert fork_res.status_code == 200
    fork_th_id = fork_res.json()["id"]
    assert fork_res.json()["title"] == "Forked Branch"

    # Verify forked thread has the message up to fork point
    fork_msgs = client.get(f"/api/v1/threads/{fork_th_id}/messages").json()
    assert len(fork_msgs) == 1

    # 8. Export markdown transcript
    exp_md = client.get(f"/api/v1/threads/{th_id}/export-md")
    assert exp_md.status_code == 200
    assert "Why did my battery drain overnight?" in exp_md.text

    # 9. Delete single message
    del_msg = client.delete(f"/api/v1/messages/{asst_msg_id}")
    assert del_msg.status_code == 200
    assert del_msg.json()["deleted"] is True

    # 10. Clear thread
    clr_res = client.post(f"/api/v1/threads/{th_id}/clear")
    assert clr_res.status_code == 200
    assert client.get(f"/api/v1/threads/{th_id}/messages").json() == []

    # 11. Delete thread
    del_th = client.delete(f"/api/v1/threads/{th_id}")
    assert del_th.status_code == 200
    assert del_th.json()["deleted"] is True


def test_settings_and_models(client, monkeypatch):
    # 1. Get settings
    res = client.get("/api/v1/settings")
    assert res.status_code == 200
    data = res.json()
    assert "device_timezone" in data
    assert "active_llm_model" in data

    # 2. Update settings
    up_res = client.post(
        "/api/v1/settings",
        json={
            "device_timezone": "Europe/Warsaw",
            "night_start_hour": 22,
            "night_end_hour": 6,
            "chat_enter_mode": "send",
            "active_llm_provider": "Google Gemini",
            "active_llm_model": "gemini-3.8-flash"
        }
    )
    assert up_res.status_code == 200
    up_data = up_res.json()
    assert up_data["device_timezone"] == "Europe/Warsaw"
    assert up_data["night_start_hour"] == 22
    assert up_data["chat_enter_mode"] == "send"

    # 3. Get models
    m_res = client.get("/api/v1/models?provider=Google Gemini")
    assert m_res.status_code == 200
    m_data = m_res.json()
    assert "gemini-3.8-flash" in m_data["models"]

    # 4. Test connection
    import llm_manager
    monkeypatch.setattr(llm_manager, "test_connection", lambda model, **kwargs: (True, "Connection successful!"))
    tc_res = client.post("/api/v1/settings/test-connection", json={"model": "gemini-3.8-flash"})
    assert tc_res.status_code == 200
    assert tc_res.json()["success"] is True


def test_device_profiles(client):
    # Upload profile
    content = "Package [com.google.android.gms] (1000): version=123\n"
    up_res = client.post(
        "/api/v1/device-profiles/upload",
        files={"file": ("profile.txt", content.encode("utf-8"), "text/plain")},
        data={"profile_name": "Pixel 6 Android 14 Baseline"}
    )
    assert up_res.status_code == 200
    prof = up_res.json()
    prof_id = prof["id"]
    assert prof["profile_name"] == "Pixel 6 Android 14 Baseline"

    # List profiles
    list_res = client.get("/api/v1/device-profiles")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Get single profile
    get_res = client.get(f"/api/v1/device-profiles/{prof_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == prof_id

    # Delete profile
    del_res = client.delete(f"/api/v1/device-profiles/{prof_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True


def test_wifi_routers(client):
    # 1. Create router
    c_res = client.post(
        "/api/v1/wifi-routers",
        json={
            "router_name": "Home Fritz!Box 7590",
            "brand": "AVM",
            "model": "FRITZ!Box 7590 AX",
            "specs_json": {"wifi_standard": "Wi-Fi 6", "frequency": "2.4GHz / 5GHz"},
            "location_tag": "Living Room",
            "is_active": 1,
            "notes": "Main mesh router"
        }
    )
    assert c_res.status_code == 200
    r = c_res.json()
    r_id = r["id"]
    assert r["router_name"] == "Home Fritz!Box 7590"

    # 2. List routers
    l_res = client.get("/api/v1/wifi-routers")
    assert l_res.status_code == 200
    assert any(x["id"] == r_id for x in l_res.json())

    # 3. Update router active status
    u_res = client.put(f"/api/v1/wifi-routers/{r_id}", json={"is_active": 0})
    assert u_res.status_code == 200
    assert u_res.json()["is_active"] == 0

    # 4. Delete router
    d_res = client.delete(f"/api/v1/wifi-routers/{r_id}")
    assert d_res.status_code == 200
    assert d_res.json()["deleted"] is True


def test_prompts_and_custom_models(client):
    # 1. Get prompts
    p_res = client.get("/api/v1/prompts")
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert "prompts" in p_data
    assert "single_diagnosis" in p_data["prompts"]

    # 2. Update prompt
    up_p = client.put(
        "/api/v1/prompts",
        json={"single_diagnosis": "Custom Diagnosis System Prompt"}
    )
    assert up_p.status_code == 200
    assert up_p.json()["prompts"]["single_diagnosis"] == "Custom Diagnosis System Prompt"

    # 3. Reset prompts
    rst_p = client.post("/api/v1/prompts/reset")
    assert rst_p.status_code == 200
    assert rst_p.json()["prompts"]["single_diagnosis"] != "Custom Diagnosis System Prompt"

    # 4. Add & delete custom model
    add_m = client.post(
        "/api/v1/models/custom",
        json={"provider": "Google Gemini", "model_name": "gemini/gemini-custom-test"}
    )
    assert add_m.status_code == 200
    assert "gemini/gemini-custom-test" in add_m.json()["custom_models"]

    del_m = client.delete("/api/v1/models/custom?provider=Google Gemini&model_name=gemini/gemini-custom-test")
    assert del_m.status_code == 200
    assert "gemini/gemini-custom-test" not in del_m.json()["custom_models"]


def test_master_synthesis_and_accounting(client, monkeypatch):
    import llm_manager
    monkeypatch.setattr(llm_manager, "call_llm_tracked", lambda *args, **kwargs: "Master Synthesis Action Plan")

    # 1. Get master synthesis
    ms_res = client.get("/api/v1/master-synthesis")
    assert ms_res.status_code == 200
    assert "scorecard" in ms_res.json()

    # 2. Master consultation chat thread (report_id = -999999)
    th_res = client.post("/api/v1/reports/-999999/threads", json={"title": "Master Consultation"})
    assert th_res.status_code == 200
    th_id = th_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/threads/{th_id}/messages",
        json={"content": "Summarize all my reports"}
    )
    assert msg_res.status_code == 200
    assert "Master Synthesis Action Plan" in msg_res.json()["content"]

    # 3. Accounting endpoint
    acc_res = client.get("/api/v1/accounting")
    assert acc_res.status_code == 200
    acc_data = acc_res.json()
    assert "totals" in acc_data
    assert "by_report" in acc_data
    assert "by_thread" in acc_data
    assert "over_time" in acc_data

