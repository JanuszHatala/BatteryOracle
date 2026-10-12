import os
import pytest
from fastapi.testclient import TestClient

import db
import api_server

TEST_DB = "test_e2e_oracle.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    monkeypatch.setattr(db, "DB_PATH", TEST_DB)
    db.init_db()
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture
def client():
    with TestClient(api_server.app) as c:
        yield c


def test_e2e_health_check(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "version": "2.0.0"}


def test_e2e_spa_fallback_and_static_assets(client):
    # Root route should return SPA index.html
    res = client.get("/")
    assert res.status_code == 200
    assert "<!doctype html>" in res.text.lower() or "<html" in res.text.lower()

    # Arbitrary non-api route should fall back to index.html (SPA client routing)
    res_fallback = client.get("/report/42/details")
    assert res_fallback.status_code == 200
    assert "<!doctype html>" in res_fallback.text.lower() or "<html" in res_fallback.text.lower()


def test_e2e_full_lifecycle(client):
    # 1. Create a report directly
    report_id = db.save_report(
        file_hash="e2e_hash_123",
        filename="bugreport_e2e.txt",
        custom_name="E2E Bugreport",
        description="E2E test description",
        timestamp_str="2026-10-12 12:00:00",
        device_info="Google Pixel 8 Pro",
        summary_text="E2E test summary text",
        chart_df=None,
        history_df=None,
        initial_analysis="E2E initial analysis diagnosis markdown"
    )

    # 2. Query report list and detail
    res = client.get("/api/v1/reports")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["id"] == report_id
    assert items[0]["custom_name"] == "E2E Bugreport"

    res_detail = client.get(f"/api/v1/reports/{report_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["device_info"] == "Google Pixel 8 Pro"

    # 3. Create thread, send user message, toggle collapse, fork
    res_th = client.post(f"/api/v1/reports/{report_id}/threads", json={"title": "E2E Thread"})
    assert res_th.status_code == 200
    thread_id = res_th.json()["id"]

    res_msg = client.post(
        f"/api/v1/threads/{thread_id}/messages",
        json={"content": "What caused the drain?", "filter_context": "night"}
    )
    assert res_msg.status_code == 200
    msg_id = res_msg.json()["id"]

    # Toggle collapse
    res_col = client.put(f"/api/v1/messages/{msg_id}/collapse")
    assert res_col.status_code == 200
    assert res_col.json()["is_collapsed"] is True

    # Fork thread
    res_fork = client.post(
        f"/api/v1/threads/{thread_id}/fork",
        json={"from_message_id": msg_id, "new_title": "Forked Branch"}
    )
    assert res_fork.status_code == 200
    fork_id = res_fork.json()["id"]
    assert fork_id != thread_id

    # 4. Settings and models
    res_set = client.get("/api/v1/settings")
    assert res_set.status_code == 200

    res_models = client.get("/api/v1/models?provider=Google Gemini")
    assert res_models.status_code == 200
    assert len(res_models.json()["models"]) > 0

    # 5. Clean up
    del_res = client.delete(f"/api/v1/reports/{report_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True
