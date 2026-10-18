import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

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
    raw_analyses = rep.get("analyses") or {}
    formatted_analyses = {}
    summary_text = rep.get("summary_text", "")
    for scope_key, data in raw_analyses.items():
        if isinstance(data, dict):
            formatted_analyses[scope_key] = schemas.ScopeAnalysisDetail(
                text=parser.sanitize_ai_output(data.get("text", ""), summary_text),
                trace=data.get("trace", ""),
                updated_at=_to_iso(data.get("updated_at"))
            )
    return schemas.ReportDetail(
        id=rep["id"],
        file_hash=rep["file_hash"],
        filename=rep["filename"],
        custom_name=rep["custom_name"],
        description=rep.get("description", ""),
        timestamp_str=rep.get("timestamp_str", ""),
        device_info=rep.get("device_info", ""),
        summary_text=summary_text,
        initial_analysis=parser.sanitize_ai_output(rep.get("initial_analysis", ""), summary_text),
        reasoning_trace=rep.get("reasoning_trace", ""),
        custom_night_start=_to_iso(rep.get("custom_night_start")),
        custom_night_end=_to_iso(rep.get("custom_night_end")),
        analysis_updated_at=_to_iso(rep.get("analysis_updated_at")),
        created_at=_to_iso(rep.get("created_at")),
        analyses=formatted_analyses
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
    timezone: Optional[str] = Form(None)
):
    effective_tz = timezone or db.get_setting("device_timezone", "Europe/Warsaw")
    try:
        content = await file.read()
        processed = telemetry_service.process_bugreport_upload(
            filename=file.filename or "unknown_bugreport.zip",
            file_bytes=content,
            timezone=effective_tz,
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


@app.post("/api/v1/reports/upload-stream")
async def upload_report_stream(
    file: UploadFile = File(...),
    auto_diagnose: bool = Form(False),
    timezone: Optional[str] = Form(None)
):
    effective_tz = timezone or db.get_setting("device_timezone", "Europe/Warsaw")
    filename = file.filename or "unknown_bugreport.zip"
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def progress_callback(phase: str, progress: int, message: str):
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "progress", "phase": phase, "progress": progress, "message": message}
            )

        def run_processing():
            try:
                progress_callback("unpacking", 10, "Preparing and unpacking bugreport...")
                processed = telemetry_service.process_bugreport_upload(
                    filename=filename,
                    file_bytes=content,
                    timezone=effective_tz,
                    auto_diagnose=auto_diagnose,
                    progress_callback=progress_callback
                )
                progress_callback("saving", 95, "Saving report to database...")
                existing = db.get_report_by_hash(processed["file_hash"])
                if existing:
                    rep_detail = _format_report_detail(existing)
                else:
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
                        raise ValueError("Failed to retrieve persisted report.")
                    rep_detail = _format_report_detail(created)

                detail_dict = rep_detail.model_dump() if hasattr(rep_detail, "model_dump") else rep_detail.dict()
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "done",
                        "phase": "completed",
                        "progress": 100,
                        "message": "Import complete!",
                        "report": detail_dict
                    }
                )
            except Exception as e:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "error", "phase": "error", "message": str(e)}
                )

        worker_task = asyncio.to_thread(run_processing)
        fut = asyncio.create_task(worker_task)

        try:
            while True:
                item = await queue.get()
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("type") in ("done", "error"):
                    break
            await fut
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


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

    if req.reset_night_window or (req.custom_night_start == "" and req.custom_night_end == ""):
        db.update_report_night_window(report_id, None, None)
    elif req.custom_night_start is not None and req.custom_night_end is not None:
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
        night_bounds=payload.get("night_bounds"),
        session_bounds=payload.get("session_bounds")
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
        raise HTTPException(status_code=502, detail=llm_manager.parse_llm_error(e))

    now_iso = datetime.now().isoformat()
    db.update_report_analysis(report_id, analysis, trace, now_iso, scope=req.scope)

    updated_rep = db.get_report_by_id(report_id)
    raw_analyses = updated_rep.get("analyses") or {} if updated_rep else {}
    formatted_analyses = {
        k: schemas.ScopeAnalysisDetail(
            text=v.get("text", ""),
            trace=v.get("trace", ""),
            updated_at=_to_iso(v.get("updated_at"))
        )
        for k, v in raw_analyses.items() if isinstance(v, dict)
    }

    return schemas.DiagnosisResponse(
        report_id=report_id,
        scope=req.scope,
        diagnosis=analysis,
        reasoning_trace=trace,
        updated_at=now_iso,
        analyses=formatted_analyses
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
        raise HTTPException(status_code=502, detail=llm_manager.parse_llm_error(e))

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
    if report_id > 0:
        rep = db.get_report_by_id(report_id)
        if not rep:
            raise HTTPException(status_code=404, detail="Report not found.")
    elif report_id != -999999 and report_id < 0:
        prof = db.get_device_profile(-report_id)
        if not prof:
            raise HTTPException(status_code=404, detail="Device profile not found.")

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

    rep_id = th.get("report_id")

    # 1. Save user prompt
    user_msg_id = db.save_chat_message(
        report_id=rep_id,
        role="user",
        content=req.content,
        thread_id=thread_id,
        filter_context=req.filter_context or ""
    )

    # 2. Auto-title if it's the first message
    existing_msgs = db.get_chat_messages(report_id=rep_id, thread_id=thread_id)
    if len(existing_msgs) <= 1 and any(tag in th.get("title", "") for tag in ["New", "Main", "Untitled", "Initial", "General"]):
        auto_title = req.content[:30].strip() + ("..." if len(req.content) > 30 else "")
        db.rename_thread(thread_id, auto_title)

    # 3. Build system prompt & history
    action_type = "chat"
    if rep_id == -999999:
        action_type = "master_experiment_chat"
        current_synth = db.get_master_synthesis()
        synth_ctx = current_synth["text"] if current_synth else "No master synthesis generated yet."
        all_rep = db.get_all_reports()
        chronicle_lines = []
        active_inv_profile = db.get_latest_device_profile()
        profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
        if profile_summary:
            chronicle_lines.append(profile_summary + "\n")
        active_routers = db.get_active_wifi_routers()
        router_summary = parser.format_router_context_for_llm(active_routers)
        if router_summary:
            chronicle_lines.append(router_summary + "\n")
        n_s = int(db.get_setting("night_start_hour", "23"))
        n_e = int(db.get_setting("night_end_hour", "7"))
        for idx, r in enumerate(all_rep):
            chronicle_lines.append(f"SESSION {idx+1}: {r['custom_name']} ({r.get('timestamp_str', '')}) - {r.get('description', '')}")
            chronicle_lines.append(telemetry_service.build_compact_summary(r, filter_mode="night", n_start=n_s, n_end=n_e))
        sys_prompt = (
            "You are a Principal Android Battery & Performance Architect.\n"
            "You are consulting with the user regarding their overarching multi-day battery experiment synthesis and long-term optimization blueprint.\n\n"
            "=== EXECUTIVE MASTER SYNTHESIS ===\n"
            f"{synth_ctx}\n\n"
            "=== COMPLETE MULTI-DAY TEST RUN CHRONICLE ===\n"
            + "\n".join(chronicle_lines)
        )
    elif rep_id is not None and rep_id < 0:
        action_type = "profile_chat"
        prof = db.get_device_profile(-rep_id)
        p_data = prof.get("parsed_data", {}) if prof else {}
        prof_telemetry_summary = parser.get_inventory_summary_for_llm(p_data)
        active_routers = db.get_active_wifi_routers()
        router_summary = parser.format_router_context_for_llm(active_routers)
        if router_summary:
            prof_telemetry_summary = f"{router_summary}\n\n{prof_telemetry_summary}"
        prof_chat_tmpl = llm_manager.get_prompt_template("profile_chat")
        try:
            sys_prompt = prof_chat_tmpl.format(
                device_model=p_data.get("device_model", "Unknown Device"),
                os_build=p_data.get("os_build", "Unknown Build"),
                android_version=p_data.get("android_version", "Unknown"),
                doze_deep=p_data.get("doze_deep_state", "UNKNOWN"),
                doze_light=p_data.get("doze_light_state", "UNKNOWN"),
                audit_report=prof.get("ai_analysis", "") if prof else "",
                profile_telemetry=prof_telemetry_summary
            )
        except Exception:
            sys_prompt = f"Device Profile Context:\n{prof_telemetry_summary}"
    else:
        rep = db.get_report_by_id(rep_id) if rep_id else None
        if rep:
            scope_filter = (req.filter_context or "all").lower().strip()
            valid_scope = scope_filter if scope_filter in ["night", "screen_off", "custom", "all"] else "all"
            n_s = int(db.get_setting("night_start_hour", "23"))
            n_e = int(db.get_setting("night_end_hour", "7"))
            summary_compact = telemetry_service.build_compact_summary(
                rep,
                filter_mode=valid_scope,
                n_start=n_s,
                n_end=n_e
            )
            active_inv = db.get_latest_device_profile()
            inv_sum = parser.get_inventory_summary_for_llm(active_inv.get("parsed_data", {})) if active_inv else ""
            active_routers = db.get_active_wifi_routers()
            r_sum = parser.format_router_context_for_llm(active_routers)
            full_tel = summary_compact
            if inv_sum:
                full_tel = f"{inv_sum}\n\n{full_tel}"
            if r_sum:
                full_tel = f"{r_sum}\n\n{full_tel}"

            rep_analyses = rep.get("analyses") or {}
            active_diag = rep_analyses.get(valid_scope) or rep_analyses.get("all")
            if active_diag and isinstance(active_diag, dict) and active_diag.get("text"):
                diag_block = f"\n\n=== PRIOR AI DIAGNOSTIC FOR ACTIVE SCOPE ({valid_scope.upper()}) ===\n{active_diag['text']}"
                full_tel = f"{full_tel}{diag_block}"

            chat_tmpl = llm_manager.get_prompt_template("chat_assistant")
            try:
                sys_prompt = chat_tmpl.format(
                    filter_context=valid_scope,
                    report_name=rep.get("custom_name", rep.get("filename", "")),
                    device_info=rep.get("device_info", "Android Device"),
                    timestamp_str=rep.get("timestamp_str", ""),
                    description=rep.get("description", ""),
                    telemetry_data=full_tel
                )
            except Exception:
                sys_prompt = f"You are Battery Oracle.\nActive Report: {rep.get('custom_name')}\nFilter Context: {valid_scope}\n{full_tel}"
        else:
            sys_prompt = "You are Battery Oracle, an expert Android battery telemetry and drain regression AI consultant."

    llm_messages = [{"role": "system", "content": sys_prompt}]
    for m in existing_msgs:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    # 4. Invoke LLM
    try:
        reply = llm_manager.call_llm_tracked(
            messages=llm_messages,
            report_id=rep_id,
            thread_id=thread_id,
            action_type=action_type
        )
    except Exception as e:
        if user_msg_id:
            db.delete_chat_message(user_msg_id)
        raise HTTPException(status_code=502, detail=llm_manager.parse_llm_error(e))

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


# --- System Settings, Providers, Models & Prompts ---

@app.get("/api/v1/settings", response_model=schemas.SettingsResponse)
def get_settings():
    cfg = llm_manager.get_active_config()
    prov = db.get_setting("llm_provider") or db.get_setting("active_llm_provider") or cfg["provider"]
    mod = db.get_setting("llm_model") or db.get_setting("active_llm_model") or cfg["model"]
    api_key = db.get_setting("llm_api_key") or cfg["api_key"] or ""
    api_base = db.get_setting("llm_api_base") or cfg["api_base"] or ""

    providers_list = []
    for k, v in llm_manager.PROVIDER_PRESETS.items():
        providers_list.append(
            schemas.ProviderPresetInfo(
                name=k,
                default_model=v.get("default_model", ""),
                default_base=v.get("default_base"),
                requires_key=bool(v.get("requires_key", True))
            )
        )

    return schemas.SettingsResponse(
        device_timezone=db.get_setting("device_timezone", "Europe/Warsaw"),
        night_start_hour=int(db.get_setting("night_start_hour", "23")),
        night_end_hour=int(db.get_setting("night_end_hour", "7")),
        chat_enter_mode=db.get_setting("chat_enter_mode", "newline"),
        active_llm_provider=prov,
        active_llm_model=mod,
        llm_api_key=api_key,
        llm_api_base=api_base,
        gemini_key_set=bool(os.getenv("GEMINI_API_KEY") or db.get_setting("gemini_api_key") or (prov == "Google Gemini" and api_key)),
        openrouter_key_set=bool(os.getenv("OPENROUTER_API_KEY") or db.get_setting("openrouter_api_key") or (prov == "OpenRouter" and api_key)),
        providers=providers_list
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
        db.set_setting("llm_provider", req.active_llm_provider)
        db.set_setting("active_llm_provider", req.active_llm_provider)
    if req.active_llm_model is not None:
        prov = req.active_llm_provider or db.get_setting("llm_provider", "Google Gemini")
        norm_mod = llm_manager.save_custom_model(prov, req.active_llm_model) or req.active_llm_model
        db.set_setting("llm_model", norm_mod)
        db.set_setting("active_llm_model", norm_mod)
    if req.llm_api_key is not None:
        db.set_setting("llm_api_key", req.llm_api_key)
    if req.llm_api_base is not None:
        db.set_setting("llm_api_base", req.llm_api_base)
    if req.gemini_api_key is not None:
        db.set_setting("gemini_api_key", req.gemini_api_key)
        if (req.active_llm_provider or db.get_setting("llm_provider", "Google Gemini")) == "Google Gemini":
            db.set_setting("llm_api_key", req.gemini_api_key)
    if req.openrouter_api_key is not None:
        db.set_setting("openrouter_api_key", req.openrouter_api_key)
        if (req.active_llm_provider or db.get_setting("llm_provider")) == "OpenRouter":
            db.set_setting("llm_api_key", req.openrouter_api_key)

    return get_settings()


@app.get("/api/v1/models", response_model=schemas.ModelsResponse)
def get_models(provider: str = "Google Gemini"):
    models = llm_manager.get_all_models_for_provider(provider)
    custom_models = llm_manager.get_custom_models(provider)
    preset = llm_manager.PROVIDER_PRESETS.get(provider, {})
    raw_default = preset.get("default_model", models[0] if models else "")

    # Include both full IDs and short IDs in `models` list for backward compatibility with existing tests
    combined_list = list(models)
    for m in models:
        short = m.replace("gemini/", "").replace("openrouter/", "")
        if short not in combined_list:
            combined_list.append(short)

    details = [
        schemas.ModelItemDetail(
            id=m,
            pricing=llm_manager.get_model_pricing(m),
            is_custom=(m in custom_models)
        )
        for m in models
    ]

    return schemas.ModelsResponse(
        provider=provider,
        models=combined_list,
        model_details=details,
        custom_models=custom_models,
        default_model=raw_default
    )


@app.post("/api/v1/models/fetch-live", response_model=schemas.FetchLiveModelsResponse)
def fetch_live_models_endpoint(req: schemas.FetchLiveModelsRequest):
    prov_arg = "Ollama" if req.provider == "Ollama / Local" else req.provider
    discovered, msg = llm_manager.fetch_available_models(
        provider=prov_arg,
        api_key=req.api_key,
        api_base=req.api_base
    )
    custom_models = llm_manager.get_custom_models(req.provider)
    details = [
        schemas.ModelItemDetail(
            id=m,
            pricing=llm_manager.get_model_pricing(m),
            is_custom=(m in custom_models)
        )
        for m in discovered
    ]
    return schemas.FetchLiveModelsResponse(
        provider=req.provider,
        models=discovered,
        model_details=details,
        message=msg
    )


@app.post("/api/v1/models/custom", response_model=schemas.ModelsResponse)
def add_custom_model_endpoint(req: schemas.CustomModelRequest):
    llm_manager.save_custom_model(req.provider, req.model_name)
    return get_models(req.provider)


@app.delete("/api/v1/models/custom", response_model=schemas.ModelsResponse)
def delete_custom_model_endpoint(provider: str, model_name: str):
    llm_manager.delete_custom_model(provider, model_name)
    return get_models(provider)


@app.post("/api/v1/settings/test-connection")
def test_connection_endpoint(req: schemas.ConnectionTestRequest):
    ok, msg = llm_manager.test_connection(
        model=req.model,
        api_key=req.api_key,
        api_base=req.api_base,
        provider=req.provider
    )
    return {"success": ok, "message": msg}


@app.get("/api/v1/prompts")
def get_all_prompts():
    res = {}
    for k in llm_manager.DEFAULT_PROMPTS.keys():
        res[k] = llm_manager.get_prompt_template(k)
    return {"prompts": res, "defaults": llm_manager.DEFAULT_PROMPTS}


@app.put("/api/v1/prompts")
def update_prompts_endpoint(req: schemas.PromptsUpdateRequest):
    data = req.model_dump(exclude_none=True)
    for k, val in data.items():
        if k in llm_manager.DEFAULT_PROMPTS:
            llm_manager.set_prompt_template(k, val)
    return get_all_prompts()


@app.post("/api/v1/prompts/reset")
def reset_prompts_endpoint():
    llm_manager.reset_prompt_templates()
    return get_all_prompts()


# --- Device Profiles ---

def _format_device_profile_detail(p: dict) -> schemas.DeviceProfileDetail:
    active_id = db.get_active_device_profile_id()
    return schemas.DeviceProfileDetail(
        id=p["id"],
        profile_name=p["profile_name"],
        device_model=p.get("device_model") or p.get("parsed_data", {}).get("device_model", "Unknown Device"),
        os_build=p.get("os_build") or p.get("parsed_data", {}).get("os_build", "Unknown OS"),
        is_active_context=(p["id"] == active_id),
        raw_content=p["raw_content"],
        parsed_data=p.get("parsed_data", {}),
        analysis_text=p.get("ai_analysis") or p.get("analysis_text") or "",
        reasoning_trace=p.get("ai_analysis_trace") or p.get("reasoning_trace") or "",
        analysis_updated_at=_to_iso(p.get("ai_analysis_updated_at") or p.get("updated_at")),
        created_at=_to_iso(p.get("created_at")),
        updated_at=_to_iso(p.get("updated_at"))
    )


@app.get("/api/v1/device-profiles", response_model=List[schemas.DeviceProfileSummary])
def list_device_profiles():
    profiles = db.get_all_device_profiles()
    active_id = db.get_active_device_profile_id()
    return [
        schemas.DeviceProfileSummary(
            id=p["id"],
            profile_name=p["profile_name"],
            device_model=p.get("device_model") or p.get("parsed_data", {}).get("device_model", "Unknown Device"),
            os_build=p.get("os_build") or p.get("parsed_data", {}).get("os_build", "Unknown OS"),
            is_active_context=(p["id"] == active_id),
            created_at=_to_iso(p.get("created_at")),
            updated_at=_to_iso(p.get("updated_at"))
        )
        for p in profiles
    ]


@app.post("/api/v1/device-profiles/upload", response_model=schemas.DeviceProfileDetail)
async def upload_device_profile(
    file: UploadFile = File(...),
    profile_name: Optional[str] = Form(None),
    profile_id: Optional[int] = Form(None)
):
    content = await file.read()
    raw_text = content.decode("utf-8", errors="replace")

    # Upfront validation of device profile content
    is_valid, err_msg = parser.validate_device_inventory(raw_text)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)

    parsed_data = parser.parse_device_inventory(raw_text)

    name = profile_name or (file.filename or "Device Profile").replace(".txt", "")
    pid = db.save_device_profile(
        profile_name=name,
        raw_content=raw_text,
        parsed_data=parsed_data,
        profile_id=profile_id
    )
    created = db.get_device_profile(pid)
    return _format_device_profile_detail(created)


@app.put("/api/v1/device-profiles/{profile_id}/set-active", response_model=schemas.DeviceProfileDetail)
def set_active_device_profile_endpoint(profile_id: int):
    p = db.get_device_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Device profile not found.")
    db.set_active_device_profile(profile_id)
    return _format_device_profile_detail(p)


@app.get("/api/v1/device-profiles/compare")
def compare_device_profiles(profile_a: int, profile_b: int):
    pa = db.get_device_profile(profile_a)
    pb = db.get_device_profile(profile_b)
    if not pa or not pb:
        raise HTTPException(status_code=404, detail="One or both device profiles not found.")

    diff = parser.compute_profile_diff(pa, pb)
    cmp_cache_key = f"profile_cmp_ai_{min(profile_a, profile_b)}_{max(profile_a, profile_b)}_{profile_a}"
    cached_analysis = db.get_setting(cmp_cache_key, "")
    cached_ts = db.get_setting(f"{cmp_cache_key}_ts", "")

    return {
        "profile_a": _format_device_profile_detail(pa),
        "profile_b": _format_device_profile_detail(pb),
        "diff": diff,
        "ai_analysis": cached_analysis,
        "updated_at": cached_ts
    }


@app.post("/api/v1/device-profiles/compare/audit")
def audit_device_profile_comparison(req: schemas.ProfileCompareRequest):
    pa = db.get_device_profile(req.profile_a_id)
    pb = db.get_device_profile(req.profile_b_id)
    if not pa or not pb:
        raise HTTPException(status_code=404, detail="One or both device profiles not found.")

    diff = parser.compute_profile_diff(pa, pb)
    diff_summary_str = parser.format_profile_diff_for_llm(pa, pb, diff)
    cmp_prompt_tmpl = llm_manager.get_prompt_template("profile_comparison")
    formatted_cmp_prompt = cmp_prompt_tmpl.format(
        baseline_name=pa["profile_name"],
        baseline_model=diff["model_a"],
        baseline_build=diff["build_a"],
        target_name=pb["profile_name"],
        target_model=diff["model_b"],
        target_build=diff["build_b"],
        diff_summary=diff_summary_str
    )

    try:
        cmp_res = llm_manager.call_llm_tracked(
            messages=[{"role": "system", "content": formatted_cmp_prompt}],
            action_type="profile_comparison"
        )
        cmp_res = parser.sanitize_ai_output(cmp_res)
    except Exception as e:
        raise HTTPException(status_code=502, detail=llm_manager.parse_llm_error(e))

    cmp_cache_key = f"profile_cmp_ai_{min(req.profile_a_id, req.profile_b_id)}_{max(req.profile_a_id, req.profile_b_id)}_{req.profile_a_id}"
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.set_setting(cmp_cache_key, cmp_res)
    db.set_setting(f"{cmp_cache_key}_ts", now_ts)

    return {
        "ai_analysis": cmp_res,
        "updated_at": now_ts,
        "diff": diff
    }


@app.get("/api/v1/device-profiles/{profile_id}", response_model=schemas.DeviceProfileDetail)
def get_device_profile(profile_id: int):
    p = db.get_device_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Device profile not found.")
    return _format_device_profile_detail(p)


@app.put("/api/v1/device-profiles/{profile_id}", response_model=schemas.DeviceProfileDetail)
def rename_device_profile(profile_id: int, req: schemas.DeviceProfileUpdate):
    p = db.get_device_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Device profile not found.")
    db.update_device_profile_name(profile_id, req.profile_name)
    updated = db.get_device_profile(profile_id)
    return _format_device_profile_detail(updated)


@app.post("/api/v1/device-profiles/{profile_id}/audit", response_model=schemas.DeviceProfileDetail)
def audit_device_profile(profile_id: int):
    profile = db.get_device_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Device profile not found.")

    p_data = profile.get("parsed_data", {})
    profile_telemetry_str = parser.get_inventory_summary_for_llm(p_data)
    active_routers = db.get_active_wifi_routers()
    router_summary = parser.format_router_context_for_llm(active_routers)
    if router_summary:
        profile_telemetry_str = f"{router_summary}\n\n{profile_telemetry_str}"

    audit_prompt_tmpl = llm_manager.get_prompt_template("profile_audit")
    formatted_audit_prompt = audit_prompt_tmpl.format(
        device_model=p_data.get("device_model", "Unknown"),
        os_build=p_data.get("os_build", "Unknown"),
        android_version=p_data.get("android_version", "Unknown"),
        profile_telemetry=profile_telemetry_str
    )

    try:
        new_analysis = llm_manager.call_llm_tracked(
            messages=[{"role": "system", "content": formatted_audit_prompt}],
            report_id=-profile_id,
            action_type="profile_audit"
        )
        new_analysis = parser.sanitize_ai_output(new_analysis)
    except Exception as e:
        raise HTTPException(status_code=502, detail=llm_manager.parse_llm_error(e))

    db.update_device_profile_analysis(profile_id, new_analysis, "")
    updated = db.get_device_profile(profile_id)
    return _format_device_profile_detail(updated)


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


@app.post("/api/v1/wifi-routers/discover")
def discover_wifi_router_specs_endpoint(req: schemas.RouterDiscoverRequest):
    specs, err = llm_manager.discover_router_specs(req.brand.strip(), req.model.strip())
    return {"specs": specs, "error": err}


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

    if req.router_name is not None or req.brand is not None or req.model is not None or req.specs_json is not None or req.location_tag is not None or req.notes is not None:
        db.save_wifi_router(
            router_name=req.router_name if req.router_name is not None else r["router_name"],
            brand=req.brand if req.brand is not None else r["brand"],
            model=req.model if req.model is not None else r["model"],
            specs_json=req.specs_json if req.specs_json is not None else r.get("specs", {}),
            location_tag=req.location_tag if req.location_tag is not None else r.get("location_tag", "Home"),
            is_active=req.is_active if req.is_active is not None else r.get("is_active", 1),
            notes=req.notes if req.notes is not None else r.get("notes", ""),
            router_id=router_id
        )
    elif req.is_active is not None:
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


# --- Master Experiment Synthesis ---

@app.get("/api/v1/master-synthesis", response_model=schemas.MasterSynthesisResponse)
def get_master_synthesis_endpoint():
    all_reports = db.get_all_reports()
    n_start = int(db.get_setting("night_start_hour", "23"))
    n_end = int(db.get_setting("night_end_hour", "7"))

    scorecard = []
    dates = []
    for r in all_reports:
        if r.get("timestamp_str"):
            dates.append(str(r["timestamp_str"]))
        df_h = r.get("history_data")
        kpi_full = parser.compute_window_kpis(df_h)

        if df_h is not None and not df_h.empty and "Time" in df_h.columns:
            db_c_s = r.get("custom_night_start")
            db_c_e = r.get("custom_night_end")
            if db_c_s and db_c_e:
                s_dt, e_dt = db_c_s, db_c_e
            else:
                s_dt, e_dt = parser.get_latest_night_window(df_h["Time"].min(), df_h["Time"].max(), n_start, n_end)
            df_night = parser.slice_timeline_range(df_h, s_dt, e_dt)
            kpi_night = parser.compute_window_kpis(df_night)
        else:
            kpi_night = parser.compute_window_kpis(None)

        scorecard.append(
            schemas.ScorecardItem(
                report_id=r["id"],
                session_name=r["custom_name"],
                recorded_interval=f"{kpi_full['start_time']} -> {kpi_full['end_time']}",
                full_drop_rate=f"{kpi_full['rate_per_hr']:.2f}% / hr",
                night_standby_rate=f"{kpi_night['rate_per_hr']:.2f}% / hr",
                total_loss=f"{kpi_full['drop_pct']}% ({kpi_full['duration_hrs']:.1f} hrs)",
                night_drop=f"{kpi_night['drop_pct']}% ({kpi_night['duration_hrs']:.1f} hrs)",
                notes=r.get("description") or "Baseline"
            )
        )

    saved = db.get_master_synthesis()
    date_range = f"{min(dates)} -> {max(dates)}" if len(dates) > 1 else (dates[0] if dates else "")

    return schemas.MasterSynthesisResponse(
        scorecard=scorecard,
        synthesis_text=saved["text"] if saved else "",
        reasoning_trace=saved.get("trace", "") if saved else "",
        updated_at=saved.get("updated_at") if saved else None,
        report_count=len(all_reports),
        date_range=date_range
    )


@app.post("/api/v1/master-synthesis/generate", response_model=schemas.MasterSynthesisResponse)
def generate_master_synthesis_endpoint():
    all_reports = db.get_all_reports()
    if not all_reports:
        raise HTTPException(status_code=400, detail="No bugreports available to synthesize.")

    n_s = int(db.get_setting("night_start_hour", "23"))
    n_e = int(db.get_setting("night_end_hour", "7"))

    chronicle = []
    active_inv_profile = db.get_latest_device_profile()
    profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
    if profile_summary:
        chronicle.append(profile_summary + "\n")
    active_routers = db.get_active_wifi_routers()
    router_summary = parser.format_router_context_for_llm(active_routers)
    if router_summary:
        chronicle.append(router_summary + "\n")

    for idx, r in enumerate(all_reports):
        chronicle.append("\n==========================================")
        chronicle.append(f"SESSION {idx+1}: {r['custom_name']}")
        chronicle.append(f"File: {r['filename']} | Timestamp: {r.get('timestamp_str', '')}")
        chronicle.append(f"Device: {r.get('device_info', 'Android Device')}")
        chronicle.append(f"User State / Notes: {r.get('description', 'None')}")
        chronicle.append(telemetry_service.build_compact_summary(r, filter_mode="night", n_start=n_s, n_end=n_e))
        chronicle.append("==========================================\n")

    synth_prompt = llm_manager.get_prompt_template("master_synthesis").format(
        experiment_chronicle="\n".join(chronicle)
    )

    try:
        synthesis_text = llm_manager.call_llm_tracked(
            messages=[{"role": "system", "content": synth_prompt}],
            report_id=-999999,
            action_type="master_experiment_synthesis"
        )
        synthesis_text = parser.sanitize_ai_output(synthesis_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=llm_manager.parse_llm_error(e))

    db.save_master_synthesis(synthesis_text)
    return get_master_synthesis_endpoint()


# --- Token & Cost Accounting ---

@app.get("/api/v1/accounting", response_model=schemas.AccountingDashboardResponse)
def get_accounting_dashboard():
    return schemas.AccountingDashboardResponse(
        totals=db.get_token_totals(),
        by_report=db.get_token_summary_by_report(),
        by_thread=db.get_token_summary_by_thread(),
        over_time=db.get_token_summary_over_time()
    )


# --- Static Files & SPA Catch-All Route ---

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))






