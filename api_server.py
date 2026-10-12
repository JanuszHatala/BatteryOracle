import os
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

import db
import parser
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

