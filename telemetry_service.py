import os
import re
import io
import zipfile
import tempfile
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

import pandas as pd

import parser
import db
import llm_manager


def process_bugreport_upload(
    filename: str,
    file_bytes: bytes,
    timezone: str = "UTC",
    auto_diagnose: bool = False
) -> Dict[str, Any]:
    """Parse bugreport archive or text file into structured telemetry data."""
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    file_hash = parser.calculate_sha256(file_bytes)

    with tempfile.TemporaryDirectory() as tmpdirname:
        file_path = os.path.join(tmpdirname, filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        target_txt = file_path
        file_timestamp = parser.parse_filename_timestamp(filename)

        if filename.endswith(".zip"):
            try:
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    extracted = False
                    for name in zip_ref.namelist():
                        if (name.startswith("bugreport-") or "bugreport" in name) and name.endswith(".txt"):
                            zip_ref.extract(name, tmpdirname)
                            target_txt = os.path.join(tmpdirname, name)
                            file_timestamp = parser.parse_filename_timestamp(name)
                            extracted = True
                            break
                    if not extracted:
                        # Fall back to any .txt in the zip
                        for name in zip_ref.namelist():
                            if name.endswith(".txt"):
                                zip_ref.extract(name, tmpdirname)
                                target_txt = os.path.join(tmpdirname, name)
                                extracted = True
                                break
                    if not extracted:
                        raise ValueError("Invalid bugreport archive: no bugreport text found.")
            except zipfile.BadZipFile as e:
                raise ValueError("Invalid bugreport archive: corrupted zip file.") from e

        # Extract UIDs
        uid_map = parser.extract_uid_mapping(target_txt)

        # Extract Batterystats
        power_lines, wake_lines, device_info_str = parser.extract_batterystats(target_txt)

        power_lines = parser.replace_uids_safely(power_lines, uid_map)
        wake_lines = parser.replace_uids_safely(wake_lines, uid_map)

        summary_text = "Estimated Power Use:\n" + "".join(power_lines)
        summary_text += "\n\nPartial Wakelocks:\n" + "".join(wake_lines)
        chart_df = parser.extract_chart_data(power_lines, uid_map)

        year_match = re.search(r"(\d{4})", file_timestamp or "")
        base_year = year_match.group(1) if year_match else "2026"
        history_df = parser.extract_battery_history(target_txt, base_year=base_year)

        initial_analysis = ""
        reasoning_trace = ""

        if auto_diagnose:
            active_llm_cfg = llm_manager.get_active_config()
            diag_prompt_tmpl = llm_manager.get_prompt_template("single_diagnosis")

            active_inv_profile = db.get_latest_device_profile()
            profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
            combined_telemetry = summary_text[:30000]
            if profile_summary:
                combined_telemetry = f"{profile_summary}\n\n{combined_telemetry}"

            formatted_diag_prompt = diag_prompt_tmpl.format(
                report_name=filename,
                timestamp_str=file_timestamp,
                device_info=device_info_str,
                timezone_info=timezone,
                telemetry_data=combined_telemetry
            )

            try:
                raw_analysis = llm_manager.call_llm_tracked(
                    messages=[{"role": "system", "content": formatted_diag_prompt}],
                    action_type="initial_diagnosis"
                )
                initial_analysis = parser.sanitize_ai_output(raw_analysis, summary_text)
                reasoning_trace = f"Analyzed {len(power_lines)} power records and {len(wake_lines)} wakelocks for {device_info_str}."
            except Exception as e:
                initial_analysis = f"AI diagnosis import deferred: {e}"
                reasoning_trace = f"Initial diagnosis failed: {e}"
        else:
            initial_analysis = "Initial analysis pending. Select scope and generate diagnosis."
            reasoning_trace = "Uploaded without immediate LLM generation."

        custom_name = filename.replace(".zip", "").replace(".txt", "")

        return {
            "file_hash": file_hash,
            "filename": filename,
            "custom_name": custom_name,
            "description": "",
            "timestamp_str": file_timestamp,
            "device_info": device_info_str,
            "summary_text": summary_text,
            "chart_df": chart_df,
            "history_df": history_df,
            "initial_analysis": initial_analysis,
            "reasoning_trace": reasoning_trace
        }


def get_effective_telemetry_bounds(
    report: Dict[str, Any],
    scope: str = "night",
    custom_start_str: Optional[str] = None,
    custom_end_str: Optional[str] = None,
    night_start: Optional[int] = None,
    night_end: Optional[int] = None
) -> Tuple[datetime, datetime, pd.DataFrame]:
    """Calculate effective start/end timestamps and return sliced timeline."""
    if night_start is None:
        try:
            night_start = int(db.get_setting("night_start_hour", "23"))
        except Exception:
            night_start = 23
    if night_end is None:
        try:
            night_end = int(db.get_setting("night_end_hour", "7"))
        except Exception:
            night_end = 7

    df_h = report.get("history_data")
    if df_h is None or df_h.empty or "Time" not in df_h.columns:
        now = datetime.now()
        return now, now, pd.DataFrame()

    r_min = df_h["Time"].min()
    r_max = df_h["Time"].max()
    if hasattr(r_min, "to_pydatetime"):
        r_min = r_min.to_pydatetime()
    if hasattr(r_max, "to_pydatetime"):
        r_max = r_max.to_pydatetime()

    if scope == "screen_off":
        off_df = df_h[df_h["Screen"] == "off"] if "Screen" in df_h.columns else df_h
        return r_min, r_max, off_df

    if scope == "night":
        auto_s, auto_e = parser.get_latest_night_window(r_min, r_max, night_start, night_end)
        if hasattr(auto_s, "to_pydatetime"):
            auto_s = auto_s.to_pydatetime()
        if hasattr(auto_e, "to_pydatetime"):
            auto_e = auto_e.to_pydatetime()

        db_c_s = report.get("custom_night_start")
        db_c_e = report.get("custom_night_end")

        def_s = auto_s
        def_e = auto_e
        if db_c_s and db_c_e:
            try:
                def_s = datetime.fromisoformat(db_c_s)
                def_e = datetime.fromisoformat(db_c_e)
            except Exception:
                pass

        s_dt = max(r_min, min(r_max, def_s))
        e_dt = max(r_min, min(r_max, def_e))
        if s_dt >= e_dt:
            s_dt, e_dt = auto_s, auto_e

        sl_df = parser.slice_timeline_range(df_h, s_dt, e_dt)
        return s_dt, e_dt, sl_df

    if scope == "custom":
        try:
            s_dt = datetime.fromisoformat(custom_start_str) if custom_start_str else r_min
            e_dt = datetime.fromisoformat(custom_end_str) if custom_end_str else r_max
        except Exception:
            s_dt, e_dt = r_min, r_max

        # Clamp within session bounds
        s_dt = max(r_min, min(r_max, s_dt))
        e_dt = max(r_min, min(r_max, e_dt))

        if s_dt >= e_dt:
            # Safe fallback if inverted
            s_dt = r_min
            e_dt = r_max

        sl_df = parser.slice_timeline_range(df_h, s_dt, e_dt)
        return s_dt, e_dt, sl_df

    # Full scope
    return r_min, r_max, df_h


def build_telemetry_payload(
    report: Dict[str, Any],
    scope: str = "night",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None
) -> Dict[str, Any]:
    """Compute KPIs, slice timeline, and format power consumer breakdown."""
    s_dt, e_dt, sliced_df = get_effective_telemetry_bounds(
        report=report,
        scope=scope,
        custom_start_str=custom_start,
        custom_end_str=custom_end
    )

    kpis = parser.compute_window_kpis(sliced_df)

    # Format timeline points
    timeline = []
    if sliced_df is not None and not sliced_df.empty:
        for _, row in sliced_df.iterrows():
            t = row["Time"]
            t_str = t.isoformat() if hasattr(t, "isoformat") else str(t)
            timeline.append({
                "timestamp": t_str,
                "battery_level": int(row.get("Level", 0)),
                "screen_state": str(row.get("Screen", "off"))
            })

    # Format components
    components = []
    df_c = report.get("chart_data")
    if df_c is not None and not df_c.empty:
        clean_df = parser.clean_chart_dataframe(df_c, report.get("summary_text", ""))
        total_mah = clean_df["mAh"].sum() if "mAh" in clean_df.columns else 0.0
        for _, row in clean_df.head(20).iterrows():
            comp_mah = float(row.get("mAh", 0.0))
            pct = round((comp_mah / total_mah * 100), 1) if total_mah > 0 else 0.0
            components.append({
                "component": str(row.get("Component", "Unknown")),
                "mah": comp_mah,
                "percentage": pct
            })

    return {
        "scope": scope,
        "kpis": kpis,
        "timeline": timeline,
        "components": components,
        "night_bounds": {
            "start": s_dt.isoformat() if s_dt else None,
            "end": e_dt.isoformat() if e_dt else None
        }
    }


def build_single_report_markdown(
    report: Dict[str, Any],
    filter_mode: str,
    kpis: Dict[str, Any],
    diagnosis_text: str,
    gen_timestamp: Optional[str] = None
) -> str:
    """Generate publication-quality Markdown document for a single report."""
    md = []
    md.append(f"# 🔋 Battery Oracle Diagnostic Report: {report.get('custom_name', 'Untitled')}\n")
    md.append(f"- **Captured:** `{report.get('timestamp_str', 'Unknown')}`")
    md.append(f"- **Source File:** `{report.get('filename', 'Unknown')}`")
    md.append(f"- **Device Profile:** `{report.get('device_info', 'Android Device')}`")
    if report.get("description"):
        md.append(f"- **User Notes:** *{report['description']}*")
    md.append(f"- **Analysis Scope:** `{filter_mode.upper()}`")
    if gen_timestamp:
        md.append(f"- **AI Diagnosis Generated:** `{str(gen_timestamp)[:19]}`")
    md.append(f"- **Exported:** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`\n")

    md.append("## 📊 Telemetry & Discharge Metrics")
    md.append("| Metric | Value |")
    md.append("| :--- | :--- |")
    md.append(f"| **Active Window** | {kpis.get('start_time', 'N/A')} -> {kpis.get('end_time', 'N/A')} |")
    md.append(f"| **Battery Level Delta** | {kpis.get('start_level', 0)}% -> {kpis.get('end_level', 0)}% |")
    md.append(f"| **Total Drop** | {kpis.get('drop_pct', 0)}% over {kpis.get('duration_hrs', 0):.1f} hrs |")
    md.append(f"| **Discharge Velocity** | **{kpis.get('rate_per_hr', 0):.2f}% / hour** |")
    md.append(f"| **Standby Health Status** | {kpis.get('status', 'Unknown')} |\n")

    df_c = report.get("chart_data")
    if df_c is not None and not df_c.empty:
        clean_df = parser.clean_chart_dataframe(df_c, report.get("summary_text", ""))
        md.append("## ⚡ Top Power Consumers (mAh)")
        md.append("| App / Component | Energy Consumption (mAh) |")
        md.append("| :--- | :--- |")
        for _, row in clean_df.head(15).iterrows():
            md.append(f"| {row['Component']} | {row['mAh']} mAh |")
        md.append("")

    md.append("## 🔮 AI Diagnostic Evaluation & Action Plan\n")
    md.append(diagnosis_text or "No diagnosis generated.")
    md.append(f"\n---\n*Exported from Battery Oracle on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    return "\n".join(md)


def build_comparative_markdown(
    reports: List[Dict[str, Any]],
    filter_mode: str,
    analysis_text: str,
    gen_timestamp: Optional[str] = None
) -> str:
    """Generate Markdown document for comparative multi-report evaluation."""
    md = []
    md.append("# 🔀 Battery Oracle: Multi-Report Comparative Analysis\n")
    if gen_timestamp:
        md.append(f"- **Generated:** `{str(gen_timestamp)[:19]}`")
    md.append(f"- **Comparison Scope:** `{filter_mode.upper()}`")
    md.append(f"- **Sessions Analyzed:** `{len(reports)}`\n")

    md.append("## 📋 Compared Sessions")
    md.append("| # | Custom Name | Timestamp | Device | Notes |")
    md.append("| :--- | :--- | :--- | :--- | :--- |")
    for idx, r in enumerate(reports):
        md.append(f"| {idx + 1} | {r.get('custom_name', 'Report')} | {r.get('timestamp_str', 'N/A')} | {r.get('device_info', 'Android')} | {r.get('description', '')} |")
    md.append("")

    md.append("## 🔮 Comparative AI Synthesis\n")
    md.append(analysis_text or "No comparative synthesis generated.")
    md.append(f"\n---\n*Exported from Battery Oracle on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    return "\n".join(md)


def build_compact_summary(
    rep: Dict[str, Any],
    filter_mode: str = "night",
    n_start: int = 23,
    n_end: int = 7,
    custom_start_dt = None,
    custom_end_dt = None
) -> str:
    """Build compact text summary of report telemetry for LLM context."""
    s_dt, e_dt, sl_df = get_effective_telemetry_bounds(
        report=rep,
        scope=filter_mode,
        custom_start_str=custom_start_dt.isoformat() if hasattr(custom_start_dt, "isoformat") else custom_start_dt,
        custom_end_str=custom_end_dt.isoformat() if hasattr(custom_end_dt, "isoformat") else custom_end_dt,
        night_start=n_start,
        night_end=n_end
    )
    kpis = parser.compute_window_kpis(sl_df)

    lines = [
        f"• Active Time Window: {kpis['start_time']} to {kpis['end_time']}",
        f"• Battery Level: {kpis['start_level']}% -> {kpis['end_level']}% (Drop: {kpis['drop_pct']}%)",
        f"• Duration: {kpis['duration_hrs']:.1f} hours | Discharge Rate: {kpis['rate_per_hr']:.2f}%/hr ({kpis['status']})"
    ]

    df_c = rep.get("chart_data")
    if df_c is not None and not df_c.empty:
        clean_df = parser.clean_chart_dataframe(df_c, rep.get("summary_text", ""))
        top_comps = clean_df.head(8)
        c_lines = [f"{r['Component']}: {r['mAh']:.1f} mAh" for _, r in top_comps.iterrows()]
        lines.append("• Top Drainers: " + ", ".join(c_lines))

    summary_text = rep.get("summary_text", "")
    if summary_text:
        uid_map = parser.extract_uid_mapping_from_text(summary_text)
        text_lines = parser.replace_uids_safely([l for l in summary_text.splitlines() if l.strip()], uid_map)
        lines.append("• Key Telemetry & Wakelock Excerpt:")
        lines.extend([f"    {l}" for l in text_lines[:35]])

    return "\n".join(lines)


def run_single_diagnosis(
    report: Dict[str, Any],
    scope: str = "night",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None
) -> Tuple[str, str]:
    """Execute LLM diagnosis for report under specific scope."""
    diag_prompt_tmpl = llm_manager.get_prompt_template("single_diagnosis")

    s_dt, e_dt, sl_df = get_effective_telemetry_bounds(
        report=report,
        scope=scope,
        custom_start_str=custom_start,
        custom_end_str=custom_end
    )
    kpis = parser.compute_window_kpis(sl_df)
    filtered_telemetry = parser.get_filtered_telemetry_for_llm(report.get("summary_text", ""), scope, kpis)

    active_inv_profile = db.get_latest_device_profile()
    profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
    if profile_summary:
        filtered_telemetry = f"{profile_summary}\n\n{filtered_telemetry}"

    active_routers = db.get_active_wifi_routers()
    router_summary = parser.format_router_context_for_llm(active_routers)
    if router_summary:
        filtered_telemetry = f"{router_summary}\n\n{filtered_telemetry}"

    timezone = db.get_setting("device_timezone", "UTC")
    formatted_diag_prompt = diag_prompt_tmpl.format(
        report_name=report.get("filename", "Bugreport"),
        timestamp_str=report.get("timestamp_str", "Unknown"),
        device_info=report.get("device_info", "Android Device"),
        timezone_info=timezone,
        telemetry_data=filtered_telemetry
    )

    raw_analysis = llm_manager.call_llm_tracked(
        messages=[{"role": "system", "content": formatted_diag_prompt}],
        report_id=report["id"],
        action_type=f"diagnosis_{scope}"
    )
    analysis = parser.sanitize_ai_output(raw_analysis, report.get("summary_text", ""))
    trace = f"Analyzed {scope} telemetry for {report.get('custom_name', 'Report')} ({kpis['start_time']} - {kpis['end_time']})."
    return analysis, trace


def run_comparative_analysis(
    reports: List[Dict[str, Any]],
    scope: str = "night"
) -> Tuple[str, str]:
    """Execute LLM comparative evaluation across multiple reports."""
    reports_summary_text = ""
    n_s = int(db.get_setting("night_start_hour", "23"))
    n_e = int(db.get_setting("night_end_hour", "7"))

    for idx, rep in enumerate(reports):
        reports_summary_text += f"\n--- REPORT {idx + 1}: {rep.get('custom_name', 'Report')} (Captured: {rep.get('timestamp_str', 'Unknown')}) ---\n"
        reports_summary_text += f"Device: {rep.get('device_info', 'Unknown')}\n"
        reports_summary_text += f"Notes: {rep.get('description', 'None')}\n"
        reports_summary_text += build_compact_summary(rep, filter_mode=scope, n_start=n_s, n_end=n_e) + "\n"

    active_inv_profile = db.get_latest_device_profile()
    profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
    if profile_summary:
        reports_summary_text = f"{profile_summary}\n\n{reports_summary_text}"

    active_routers = db.get_active_wifi_routers()
    router_summary = parser.format_router_context_for_llm(active_routers)
    if router_summary:
        reports_summary_text = f"{router_summary}\n\n{reports_summary_text}"

    comp_prompt_tmpl = llm_manager.get_prompt_template("comparison")
    timezone = db.get_setting("device_timezone", "UTC")
    formatted_comp_prompt = comp_prompt_tmpl.format(
        report_count=len(reports),
        timezone_info=timezone,
        reports_summary=reports_summary_text
    )

    combined_text = llm_manager.call_llm_tracked(
        messages=[{"role": "system", "content": formatted_comp_prompt}],
        action_type=f"comparative_evaluation_{scope}"
    )
    trace = f"Compared {len(reports)} sessions under scope {scope}."
    return combined_text, trace

