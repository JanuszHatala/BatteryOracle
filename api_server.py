import os
import json
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

import db
import parser
import llm_manager
import telemetry_service
import schemas


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Non-destructive database initialization
    db.init_db()
    yield


app = FastAPI(
    title="BatteryOracle API",
    version="2.0.0",
    description="High-performance Android bugreport telemetry diagnostics and AI consultation backend",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- System Health ---

@app.get("/api/v1/health")
def get_health():
    return {"status": "ok", "version": "2.0.0"}


# --- Helper Serializers ---

def _to_iso(val: Optional[Any]) -> Optional[str]:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _parse_json(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return json.loads(val)
        except Exception:
            return {}
    return {}


def _format_wifi_router(r: dict) -> schemas.WifiRouterResponse:
    return schemas.WifiRouterResponse(
        id=r["id"],
        router_name=r["router_name"],
        brand=r["brand"],
        model=r["model"],
        specs_json=_parse_json(r.get("specs_json", {})),
        location_tag=r.get("location_tag", "Home"),
        is_active=r.get("is_active", 1),
        notes=r.get("notes", ""),
        created_at=_to_iso(r.get("created_at"))
    )


def _format_report_detail(rep: dict) -> schemas.ReportDetail:
    return schemas.ReportDetail(
        id=rep["id"],
        file_hash=rep["file_hash"],
        filename=rep["filename"],
        custom_name=rep["custom_name"],
        description=rep.get("description", ""),
        timestamp_str=rep.get("timestamp_str", ""),
        device_info=rep.get("device_info", ""),
        summary_text=rep.get("summary_text", ""),
        initial_analysis=rep.get("initial_analysis", ""),
        reasoning_trace=rep.get("reasoning_trace", ""),
        custom_night_start=_to_iso(rep.get("custom_night_start")),
        custom_night_end=_to_iso(rep.get("custom_night_end")),
        analysis_updated_at=_to_iso(rep.get("analysis_updated_at")),
        created_at=_to_iso(rep.get("created_at"))
    )


# --- Reports Management ---

@app.get("/api/v1/reports", response_model=List[schemas.ReportSummary])

def list_reports():
    summaries = db.get_all_reports_summary()
    results = []
    for s in summaries:
        results.append(schemas.ReportSummary(
            id=s["id"],
            filename=s["filename"],
            custom_name=s["custom_name"],
            description=s.get("description", ""),
            timestamp_str=s.get("timestamp_str", ""),
            device_info=s.get("device_info", ""),
            rate_per_hr=s.get("rate_per_hr"),
            status=s.get("status"),
            created_at=s.get("created_at")
        ))
    return results


@app.post("/api/v1/reports/upload", response_model=schemas.ReportDetail)
async def upload_report(
    file: UploadFile = File(...),
    auto_diagnose: bool = Form(False),
    timezone: str = Form("UTC")
):
    try:
        content = await file.read()
        processed = telemetry_service.process_bugreport_upload(
            filename=file.filename or "unknown_bugreport.zip",
            file_bytes=content,
            timezone=timezone,
            auto_diagnose=auto_diagnose
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {e}")

    existing = db.get_report_by_hash(processed["file_hash"])
    if existing:
        return _format_report_detail(existing)

    report_id = db.save_report(
        file_hash=processed["file_hash"],
        filename=processed["filename"],
        custom_name=processed["custom_name"],
        description=processed["description"],
        timestamp_str=processed["timestamp_str"],
        device_info=processed["device_info"],
        summary_text=processed["summary_text"],
        chart_df=processed["chart_df"],
        history_df=processed["history_df"],
        initial_analysis=processed["initial_analysis"],
        reasoning_trace=processed["reasoning_trace"]
    )

    created = db.get_report_by_id(report_id)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to retrieve persisted report.")
    return _format_report_detail(created)


@app.get("/api/v1/reports/{report_id}", response_model=schemas.ReportDetail)
def get_report(report_id: int):
    rep = db.get_report_by_id(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found.")
    return _format_report_detail(rep)


@app.put("/api/v1/reports/{report_id}", response_model=schemas.ReportDetail)
def update_report(report_id: int, req: schemas.ReportUpdateRequest):
    rep = db.get_report_by_id(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found.")

    if req.custom_name is not None or req.description is not None:
        new_name = req.custom_name if req.custom_name is not None else rep["custom_name"]
        new_desc = req.description if req.description is not None else rep.get("description", "")
        db.update_report_metadata(report_id, new_name, new_desc)

    if req.custom_night_start is not None and req.custom_night_end is not None:
        try:
            s_dt = datetime.fromisoformat(req.custom_night_start)
            e_dt = datetime.fromisoformat(req.custom_night_end)
            db.update_report_night_window(report_id, s_dt, e_dt)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")

    updated = db.get_report_by_id(report_id)
    return _format_report_detail(updated)


@app.delete("/api/v1/reports/{report_id}")
def delete_report(report_id: int):
    rep = db.get_report_by_id(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found.")
    db.delete_report(report_id)
    return {"deleted": True, "id": report_id}


@app.get("/api/v1/reports/{report_id}/export-md")
def export_report_markdown(report_id: int, scope: str = "night"):
    rep = db.get_report_by_id(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found.")

    payload = telemetry_service.build_telemetry_payload(rep, scope=scope)
    md = telemetry_service.build_single_report_markdown(
        report=rep,
        filter_mode=scope,
        kpis=payload["kpis"],
        diagnosis_text=rep.get("initial_analysis", ""),
        gen_timestamp=rep.get("analysis_updated_at")
    )

    clean_filename = f"{rep['custom_name']}_{scope}_diagnostic.md".replace(" ", "_")
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'}
    )


# --- Telemetry Slicing & Metrics ---

@app.get("/api/v1/reports/{report_id}/telemetry", response_model=schemas.TelemetryResponse)
def get_report_telemetry(
    report_id: int,
    scope: str = "night",
    start: Optional[str] = None,
    end: Optional[str] = None
):
    rep = db.get_report_by_id(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found.")

    payload = telemetry_service.build_telemetry_payload(
        report=rep,
        scope=scope,
        custom_start=start,
        custom_end=end
    )
    return schemas.TelemetryResponse(
        scope=payload["scope"],
        kpis=schemas.KpiMetrics(**payload["kpis"]),
        timeline=[schemas.TimelinePoint(**p) for p in payload["timeline"]],
        components=[schemas.PowerComponent(**c) for c in payload["components"]],
        night_bounds=payload.get("night_bounds")
    )


# --- AI Diagnosis Generation ---

@app.post("/api/v1/reports/{report_id}/diagnose", response_model=schemas.DiagnosisResponse)
def diagnose_report(report_id: int, req: schemas.DiagnosisRequest):
    rep = db.get_report_by_id(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found.")

    try:
        analysis, trace = telemetry_service.run_single_diagnosis(
            report=rep,
            scope=req.scope,
            custom_start=req.custom_start,
            custom_end=req.custom_end
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI diagnosis generation failed: {e}")

    now_iso = datetime.now().isoformat()
    db.update_report_analysis(report_id, analysis, trace, now_iso)

    return schemas.DiagnosisResponse(
        report_id=report_id,
        scope=req.scope,
        diagnosis=analysis,
        reasoning_trace=trace,
        updated_at=now_iso
    )


# --- Comparative Multi-Report Analysis ---

@app.post("/api/v1/comparative/analyze", response_model=schemas.ComparativeResponse)
def analyze_comparative(req: schemas.ComparativeRequest):
    if not req.report_ids:
        raise HTTPException(status_code=400, detail="No report IDs provided.")

    comp_key = "_".join(str(i) for i in sorted(req.report_ids))
    cached = db.get_combined_analysis(comp_key, scope_key=req.scope)
    if cached and cached.get("analysis_text"):
        return schemas.ComparativeResponse(
            report_ids=req.report_ids,
            scope=req.scope,
            analysis=cached["analysis_text"],
            reasoning_trace=cached.get("reasoning_trace", ""),
            cached=True
        )

    all_reps = [db.get_report_by_id(rid) for rid in req.report_ids]
    valid_reps = [r for r in all_reps if r]
    if len(valid_reps) < len(req.report_ids):
        raise HTTPException(status_code=404, detail="One or more specified reports were not found.")

    try:
        combined_text, trace = telemetry_service.run_comparative_analysis(
            reports=valid_reps,
            scope=req.scope
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparative analysis failed: {e}")

    db.save_combined_analysis(comp_key, combined_text, reasoning_trace=trace, scope_key=req.scope)

    return schemas.ComparativeResponse(
        report_ids=req.report_ids,
        scope=req.scope,
        analysis=combined_text,
        reasoning_trace=trace,
        cached=False
    )


@app.get("/api/v1/comparative/export-md")
def export_comparative_markdown(report_ids: str, scope: str = "night"):
    try:
        rids = [int(x.strip()) for x in report_ids.split(",") if x.strip()]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report_ids format. Expected comma-separated integers.")

    if not rids:
        raise HTTPException(status_code=400, detail="No report IDs supplied.")

    reports = [db.get_report_by_id(rid) for rid in rids]
    valid_reps = [r for r in reports if r]
    if not valid_reps:
        raise HTTPException(status_code=404, detail="None of the specified reports were found.")

    comp_key = "_".join(str(i) for i in sorted(rids))
    cached = db.get_combined_analysis(comp_key, scope_key=scope)
    analysis_text = cached.get("analysis_text", "") if cached else ""

    md = telemetry_service.build_comparative_markdown(
        reports=valid_reps,
        filter_mode=scope,
        analysis_text=analysis_text
    )

    clean_filename = f"comparative_{scope}_{comp_key}.md"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'}
    )


# --- Chat Consultation Threads & Messages ---

def _format_thread_response(th: dict) -> schemas.ThreadResponse:
    count = db.get_message_count_for_thread(th["id"])
    return schemas.ThreadResponse(
        id=th["id"],
        report_id=th.get("report_id"),
        title=th["title"],
        message_count=count,
        created_at=_to_iso(th.get("created_at")),
        updated_at=_to_iso(th.get("updated_at"))
    )


def _format_message_response(m: dict) -> schemas.MessageResponse:
    return schemas.MessageResponse(
        id=m["id"],
        report_id=m.get("report_id"),
        thread_id=m.get("thread_id"),
        role=m["role"],
        content=m["content"],
        filter_context=m.get("filter_context", ""),
        is_collapsed=bool(m.get("is_collapsed", 0)),
        created_at=_to_iso(m.get("created_at"))
    )


@app.get("/api/v1/reports/{report_id}/threads", response_model=List[schemas.ThreadResponse])
def get_report_threads(report_id: int):
    threads = db.get_threads_for_report(report_id)
    return [_format_thread_response(th) for th in threads]


@app.post("/api/v1/reports/{report_id}/threads", response_model=schemas.ThreadResponse)
def create_report_thread(report_id: int, req: schemas.ThreadCreateRequest):
    rep = db.get_report_by_id(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found.")

    th_id = db.create_thread(report_id=report_id, title=req.title)
    th = db.get_thread_by_id(th_id)
    return _format_thread_response(th)


@app.put("/api/v1/threads/{thread_id}", response_model=schemas.ThreadResponse)
def rename_thread(thread_id: int, req: schemas.ThreadRenameRequest):
    th = db.get_thread_by_id(thread_id)
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found.")

    db.rename_thread(thread_id, req.title)
    updated = db.get_thread_by_id(thread_id)
    return _format_thread_response(updated)


@app.delete("/api/v1/threads/{thread_id}")
def delete_thread(thread_id: int):
    th = db.get_thread_by_id(thread_id)
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found.")

    db.delete_thread(thread_id)
    return {"deleted": True, "id": thread_id}


@app.post("/api/v1/threads/{thread_id}/clear")
def clear_thread(thread_id: int):
    th = db.get_thread_by_id(thread_id)
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found.")

    db.clear_thread_messages(thread_id)
    return {"cleared": True, "id": thread_id}


@app.get("/api/v1/threads/{thread_id}/messages", response_model=List[schemas.MessageResponse])
def get_thread_messages(thread_id: int):
    th = db.get_thread_by_id(thread_id)
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found.")

    msgs = db.get_chat_messages(report_id=th.get("report_id"), thread_id=thread_id)
    return [_format_message_response(m) for m in msgs]


@app.post("/api/v1/threads/{thread_id}/messages", response_model=schemas.MessageResponse)
def post_thread_message(thread_id: int, req: schemas.MessageCreateRequest):
    th = db.get_thread_by_id(thread_id)
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found.")

    # 1. Save user prompt
    db.save_chat_message(
        report_id=th.get("report_id"),
        role="user",
        content=req.content,
        thread_id=thread_id,
        filter_context=req.filter_context or ""
    )

    # 2. Auto-title if it's the first message
    existing_msgs = db.get_chat_messages(report_id=th.get("report_id"), thread_id=thread_id)
    if len(existing_msgs) <= 1 and any(tag in th.get("title", "") for tag in ["New", "Main", "Untitled"]):
        auto_title = req.content[:30].strip() + ("..." if len(req.content) > 30 else "")
        db.rename_thread(thread_id, auto_title)

    # 3. Build system prompt & history
    rep = db.get_report_by_id(th["report_id"]) if th.get("report_id") else None
    sys_prompt = "You are Battery Oracle, an expert Android battery telemetry and drain regression AI consultant."
    if rep:
        summary_compact = telemetry_service.build_compact_summary(rep)
        sys_prompt += f"\n\nActive Report Context:\nDevice: {rep.get('device_info', 'Android')}\n{summary_compact}"

    active_inv = db.get_latest_device_profile()
    if active_inv:
        inv_sum = parser.get_inventory_summary_for_llm(active_inv.get("parsed_data", {}))
        if inv_sum:
            sys_prompt += f"\n\nInstalled Apps & System Profile:\n{inv_sum}"

    active_routers = db.get_active_wifi_routers()
    r_sum = parser.format_router_context_for_llm(active_routers)
    if r_sum:
        sys_prompt += f"\n\nWi-Fi AP Context:\n{r_sum}"

    llm_messages = [{"role": "system", "content": sys_prompt}]
    for m in existing_msgs:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    # 4. Invoke LLM
    try:
        reply = llm_manager.call_llm_tracked(
            messages=llm_messages,
            report_id=th.get("report_id"),
            thread_id=thread_id,
            action_type="chat"
        )
    except Exception as e:
        reply = f"Oracle AI response temporarily unavailable: {e}"

    # 5. Persist assistant reply
    asst_id = db.save_chat_message(
        report_id=th.get("report_id"),
        role="assistant",
        content=reply,
        thread_id=thread_id,
        filter_context=req.filter_context or ""
    )

    # Return newly generated assistant message
    asst_msgs = db.get_chat_messages(report_id=th.get("report_id"), thread_id=thread_id)
    target_msg = next((m for m in asst_msgs if m["id"] == asst_id), None)
    if not target_msg:
        target_msg = {
            "id": asst_id,
            "report_id": th.get("report_id"),
            "thread_id": thread_id,
            "role": "assistant",
            "content": reply,
            "filter_context": req.filter_context or "",
            "is_collapsed": 0,
            "created_at": datetime.now().isoformat()
        }
    return _format_message_response(target_msg)


@app.put("/api/v1/messages/{message_id}/collapse", response_model=schemas.MessageResponse)
def toggle_message_collapse(message_id: int):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_messages WHERE id = ?", (message_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Message not found.")

    msg = dict(row)
    new_state = not bool(msg.get("is_collapsed", 0))
    db.toggle_message_collapsed(message_id, new_state)
    msg["is_collapsed"] = 1 if new_state else 0
    return _format_message_response(msg)


@app.delete("/api/v1/messages/{message_id}")
def delete_message(message_id: int):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM chat_messages WHERE id = ?", (message_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Message not found.")

    db.delete_chat_message(message_id)
    return {"deleted": True, "id": message_id}


@app.post("/api/v1/threads/{thread_id}/fork", response_model=schemas.ThreadResponse)
def fork_thread_endpoint(thread_id: int, req: schemas.ThreadForkRequest):
    th = db.get_thread_by_id(thread_id)
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found.")

    new_th_id = db.fork_thread(
        source_thread_id=thread_id,
        from_message_id=req.from_message_id,
        new_title=req.new_title or "Forked Investigation"
    )
    new_th = db.get_thread_by_id(new_th_id)
    return _format_thread_response(new_th)


@app.get("/api/v1/threads/{thread_id}/export-md")
def export_thread_markdown(thread_id: int):
    th = db.get_thread_by_id(thread_id)
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found.")

    msgs = db.get_chat_messages(report_id=th.get("report_id"), thread_id=thread_id)

    md = [f"# 💬 Battery Oracle Investigation Transcript: {th.get('title', 'Investigation')}\n"]
    if th.get("created_at"):
        md.append(f"- **Thread Created:** `{th['created_at']}`")
    md.append(f"- **Exported:** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`")
    md.append(f"- **Messages Count:** `{len(msgs)}`\n\n---\n")

    for m in msgs:
        role_label = "🧑 User" if m["role"] == "user" else "🔮 Oracle AI"
        ts = f" *({m.get('created_at', '')})*" if m.get("created_at") else ""
        ctx = f" `[{m['filter_context']}]`" if m.get("filter_context") else ""
        md.append(f"### {role_label}{ctx}{ts}\n")
        md.append(f"{m['content']}\n\n---\n")

    clean_filename = f"chat_thread_{thread_id}.md"
    return PlainTextResponse(
        content="\n".join(md),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'}
    )


# --- System Settings & LLM Configuration ---

@app.get("/api/v1/settings", response_model=schemas.SettingsResponse)
def get_settings():
    return schemas.SettingsResponse(
        device_timezone=db.get_setting("device_timezone", "UTC"),
        night_start_hour=int(db.get_setting("night_start_hour", "23")),
        night_end_hour=int(db.get_setting("night_end_hour", "7")),
        chat_enter_mode=db.get_setting("chat_enter_mode", "newline"),
        active_llm_provider=db.get_setting("active_llm_provider", "Google Gemini"),
        active_llm_model=db.get_setting("active_llm_model", "gemini-3.8-flash"),
        gemini_key_set=bool(os.getenv("GEMINI_API_KEY") or db.get_setting("gemini_api_key")),
        openrouter_key_set=bool(os.getenv("OPENROUTER_API_KEY") or db.get_setting("openrouter_api_key"))
    )


@app.post("/api/v1/settings", response_model=schemas.SettingsResponse)
def update_settings(req: schemas.SettingsUpdateRequest):
    if req.device_timezone is not None:
        db.set_setting("device_timezone", req.device_timezone)
    if req.night_start_hour is not None:
        db.set_setting("night_start_hour", str(req.night_start_hour))
    if req.night_end_hour is not None:
        db.set_setting("night_end_hour", str(req.night_end_hour))
    if req.chat_enter_mode is not None:
        db.set_setting("chat_enter_mode", req.chat_enter_mode)
    if req.active_llm_provider is not None:
        db.set_setting("active_llm_provider", req.active_llm_provider)
    if req.active_llm_model is not None:
        db.set_setting("active_llm_model", req.active_llm_model)
    if req.gemini_api_key is not None:
        db.set_setting("gemini_api_key", req.gemini_api_key)
    if req.openrouter_api_key is not None:
        db.set_setting("openrouter_api_key", req.openrouter_api_key)

    return get_settings()


@app.get("/api/v1/models", response_model=schemas.ModelsResponse)
def get_models(provider: str = "Google Gemini"):
    models = llm_manager.get_all_models_for_provider(provider)
    preset = llm_manager.PROVIDER_PRESETS.get(provider, {})
    clean_models = [m.replace("gemini/", "").replace("openrouter/", "") for m in models]
    raw_default = preset.get("default_model", models[0] if models else "")
    clean_default = raw_default.replace("gemini/", "").replace("openrouter/", "")
    return schemas.ModelsResponse(
        provider=provider,
        models=clean_models,
        default_model=clean_default
    )



@app.post("/api/v1/settings/test-connection")
def test_connection_endpoint(req: schemas.ConnectionTestRequest):
    ok, msg = llm_manager.test_connection(
        model=req.model,
        api_key=req.api_key,
        provider=req.provider
    )
    return {"success": ok, "message": msg}


# --- Device Profiles ---

@app.get("/api/v1/device-profiles", response_model=List[schemas.DeviceProfileSummary])
def list_device_profiles():
    profiles = db.get_all_device_profiles()
    return [
        schemas.DeviceProfileSummary(
            id=p["id"],
            profile_name=p["profile_name"],
            created_at=_to_iso(p.get("created_at"))
        )
        for p in profiles
    ]


@app.post("/api/v1/device-profiles/upload", response_model=schemas.DeviceProfileDetail)
async def upload_device_profile(
    file: UploadFile = File(...),
    profile_name: Optional[str] = Form(None)
):
    content = await file.read()
    raw_text = content.decode("utf-8", errors="replace")
    parsed_data = parser.parse_device_inventory(raw_text)

    name = profile_name or (file.filename or "Device Profile").replace(".txt", "")
    pid = db.save_device_profile(profile_name=name, raw_content=raw_text, parsed_data=parsed_data)
    created = db.get_device_profile(pid)

    return schemas.DeviceProfileDetail(
        id=created["id"],
        profile_name=created["profile_name"],
        raw_content=created["raw_content"],
        parsed_data=created.get("parsed_data", {}),
        analysis_text=created.get("analysis_text", ""),
        reasoning_trace=created.get("reasoning_trace", ""),
        created_at=_to_iso(created.get("created_at"))
    )


@app.get("/api/v1/device-profiles/{profile_id}", response_model=schemas.DeviceProfileDetail)
def get_device_profile(profile_id: int):
    p = db.get_device_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Device profile not found.")
    return schemas.DeviceProfileDetail(
        id=p["id"],
        profile_name=p["profile_name"],
        raw_content=p["raw_content"],
        parsed_data=p.get("parsed_data", {}),
        analysis_text=p.get("analysis_text", ""),
        reasoning_trace=p.get("reasoning_trace", ""),
        created_at=_to_iso(p.get("created_at"))
    )


@app.delete("/api/v1/device-profiles/{profile_id}")
def delete_device_profile(profile_id: int):
    p = db.get_device_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Device profile not found.")
    db.delete_device_profile(profile_id)
    return {"deleted": True, "id": profile_id}


# --- Wi-Fi Routers ---

@app.get("/api/v1/wifi-routers", response_model=List[schemas.WifiRouterResponse])
def list_wifi_routers():
    routers = db.get_all_wifi_routers()
    return [_format_wifi_router(r) for r in routers]


@app.post("/api/v1/wifi-routers", response_model=schemas.WifiRouterResponse)
def create_wifi_router(req: schemas.WifiRouterCreate):
    rid = db.save_wifi_router(
        router_name=req.router_name,
        brand=req.brand,
        model=req.model,
        specs_json=req.specs_json,
        location_tag=req.location_tag,
        is_active=req.is_active,
        notes=req.notes or ""
    )
    r = db.get_wifi_router(rid)
    return _format_wifi_router(r)


@app.put("/api/v1/wifi-routers/{router_id}", response_model=schemas.WifiRouterResponse)
def update_wifi_router_status(router_id: int, req: schemas.WifiRouterUpdate):
    r = db.get_wifi_router(router_id)
    if not r:
        raise HTTPException(status_code=404, detail="Router not found.")

    db.update_wifi_router_active(router_id, req.is_active)
    updated = db.get_wifi_router(router_id)
    return _format_wifi_router(updated)


@app.delete("/api/v1/wifi-routers/{router_id}")
def delete_wifi_router(router_id: int):
    r = db.get_wifi_router(router_id)
    if not r:
        raise HTTPException(status_code=404, detail="Router not found.")

    db.delete_wifi_router(router_id)
    return {"deleted": True, "id": router_id}




