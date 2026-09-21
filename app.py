import os
import re
import zipfile
import tempfile
import time
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

import importlib
import db
import parser
import llm_manager
import web_search

importlib.reload(db)
importlib.reload(parser)
importlib.reload(llm_manager)
importlib.reload(web_search)


# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Battery Oracle",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide top-right 'Deploy' button and Streamlit decoration
st.markdown("""
<style>
.stAppDeployButton,
div[data-testid="stDeployButton"],
[data-testid="stToolbarActions"],
[data-testid="stHeader"] button[title="Deploy this app"] {
    display: none !important;
}

/* Prevent browser password managers & autofill extensions from displaying hover badges/overlays on selectboxes */
[data-baseweb="select"] input {
    autocomplete: off !important;
}
div[data-testid="stSelectbox"] input {
    background-image: none !important;
}

/* Compact sidebar uploader padding */
div[data-testid="stFileUploader"] section {
    padding: 0.5rem 0.5rem !important;
}
div[data-testid="stFileUploader"] section > input + div {
    padding: 0.3rem !important;
}

/* Allow metric values to wrap gracefully and scale font cleanly without truncation */
div[data-testid="stMetricValue"] > div {
    font-size: 1.15rem !important;
    white-space: normal !important;
    word-break: break-word !important;
    line-height: 1.35 !important;
}

div[data-testid="stMetricLabel"] > div {
    white-space: normal !important;
    word-break: break-word !important;
    font-size: 0.82rem !important;
}

/* Sleek compact disclosure toggle on top-left of chat messages */
div[data-testid="column"]:has(div[class*="st-key-tog_"]) {
    min-width: 26px !important;
    max-width: 28px !important;
    flex: 0 0 26px !important;
    width: 26px !important;
}
div[class*="st-key-tog_"] button {
    padding: 0px !important;
    min-height: 20px !important;
    height: 20px !important;
    width: 20px !important;
    min-width: 20px !important;
    font-size: 11px !important;
    line-height: 1 !important;
    border: none !important;
    background: transparent !important;
    color: #94a3b8 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
div[class*="st-key-tog_"] button:hover {
    color: #38bdf8 !important;
    background: rgba(56, 189, 248, 0.12) !important;
    border-radius: 4px !important;
}

/* Sleek compact delete button on top-right of chat messages */
div[data-testid="column"]:has(div[class*="st-key-delmsg_"]) {
    min-width: 26px !important;
    max-width: 28px !important;
    flex: 0 0 26px !important;
    width: 26px !important;
}
div[class*="st-key-delmsg_"] button {
    padding: 0px !important;
    min-height: 20px !important;
    height: 20px !important;
    width: 20px !important;
    min-width: 20px !important;
    font-size: 11px !important;
    line-height: 1 !important;
    border: none !important;
    background: transparent !important;
    color: #94a3b8 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    opacity: 0.6 !important;
    transition: opacity 0.15s ease, color 0.15s ease !important;
}
div[class*="st-key-delmsg_"] button:hover {
    opacity: 1 !important;
    color: #ef4444 !important;
    background: rgba(239, 68, 68, 0.12) !important;
    border-radius: 4px !important;
}

/* Distinct, subtle styling for AI-powered sections using Streamlit native containers */
div[class*="st-key-ai_zone_"] {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.04) 50%, rgba(56, 189, 248, 0.03) 100%) !important;
    border: 1px solid rgba(139, 92, 246, 0.28) !important;
    border-left: 4px solid #8b5cf6 !important;
    border-radius: 10px !important;
    padding: 16px 20px !important;
    margin: 10px 0 18px 0 !important;
    box-shadow: 0 2px 12px rgba(139, 92, 246, 0.05) !important;
}

/* Explicit diagnostic alert card for AI API and quota failures */
div[class*="st-key-ai_err_zone_"] {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.06) 0%, rgba(245, 158, 11, 0.04) 100%) !important;
    border: 1px solid rgba(239, 68, 68, 0.35) !important;
    border-left: 4px solid #ef4444 !important;
    border-radius: 10px !important;
    padding: 16px 20px !important;
    margin: 10px 0 18px 0 !important;
    width: 100% !important;
    box-shadow: 0 2px 12px rgba(239, 68, 68, 0.06) !important;
}

.ai-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(139, 92, 246, 0.14);
    border: 1px solid rgba(139, 92, 246, 0.35);
    color: #8b5cf6;
    font-size: 0.76rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    letter-spacing: 0.02em;
    vertical-align: middle;
    margin-left: 8px;
}

/* Subtle, recognizable tint for AI chat messages */
div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.06) 0%, rgba(168, 85, 247, 0.04) 100%) !important;
    border: 1px solid rgba(139, 92, 246, 0.2) !important;
    border-left: 3px solid #a855f7 !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
}

/* ========================================================================== */
/* UI/UX BUTTON DESIGN SYSTEM - Crisp affordance, bold typography & contrast  */
/* ========================================================================== */

/* Standard (Secondary) Buttons & Download Buttons */
div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {
    font-weight: 600 !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 8px !important;
    color: #1e293b !important;
    background-color: #f8fafc !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
    letter-spacing: 0.01em !important;
}

div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover {
    border-color: #6366f1 !important;
    color: #4338ca !important;
    background-color: #ffffff !important;
    box-shadow: 0 3px 10px rgba(99, 102, 241, 0.12) !important;
    transform: translateY(-1px) !important;
}

div[data-testid="stButton"] > button:active,
div[data-testid="stDownloadButton"] > button:active {
    transform: translateY(0px) !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}

/* Primary Action Buttons */
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stDownloadButton"] > button[kind="primary"] {
    font-weight: 700 !important;
    border: 1.5px solid #4f46e5 !important;
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 2px 6px rgba(79, 70, 229, 0.28) !important;
}

div[data-testid="stButton"] > button[kind="primary"]:hover,
div[data-testid="stDownloadButton"] > button[kind="primary"]:hover {
    border-color: #4338ca !important;
    background: linear-gradient(135deg, #4338ca 0%, #4f46e5 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35) !important;
    transform: translateY(-1px) !important;
}

/* Action Command Bar Container */
.action-command-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 4px 0 14px 0;
    flex-wrap: wrap;
}

.action-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.83rem;
    color: #64748b;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    padding: 5px 12px;
    border-radius: 20px;
    font-weight: 500;
}

/* AI Consultation Chat Panel */
.chat-header-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 2px;
}

.chat-header-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1e293b;
}

.scope-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.8rem;
    color: #475569;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    padding: 3px 10px;
    border-radius: 12px;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# Initialize database
db.init_db()

# Retrieve saved timezone setting (default: Europe/Warsaw)
timezone = db.get_setting("device_timezone", "Europe/Warsaw")

# --- Helper Functions & Export Generators ---

def parse_llm_error(error: Exception):
    """Inspect LLM exception and return structured diagnostic details with actionable recovery suggestions."""
    err_str = str(error)
    err_lower = err_str.lower()
    
    # Defaults
    category = "API Error"
    title = "AI Service Request Failed"
    icon = "⚠️"
    suggestions = []
    retry_delay_sec = None
    
    # 1. Check for Rate Limit / Quota Exhaustion (429)
    if "ratelimit" in err_lower or "429" in err_lower or "resource_exhausted" in err_lower or "quota" in err_lower:
        category = "Rate Limit & Quota Exhausted (429)"
        title = "AI Model Quota / Rate Limit Exceeded"
        icon = "⏳"
        
        # Try to extract retry delay from Gemini / LiteLLM error string (e.g. "retry in 29.103s" or "retryDelay': '29s'")
        m_delay = re.search(r"retry\s+(?:in\s+)?([0-9]+(?:\.[0-9]+)?)\s*s", err_str, re.IGNORECASE)
        if not m_delay:
            m_delay = re.search(r"retryDelay['\"]?\s*:\s*['\"]?([0-9]+)s?", err_str, re.IGNORECASE)
        if m_delay:
            try:
                retry_delay_sec = int(float(m_delay.group(1)))
            except Exception:
                retry_delay_sec = None

        if retry_delay_sec:
            suggestions.append(f"⏱️ **Wait {retry_delay_sec} seconds** for the provider's rate-limiting window to roll over, then retry.")
        else:
            suggestions.append("⏱️ **Wait 30–60 seconds** for your API provider's rate-limit window to reset, then retry.")
            
        suggestions.append("🔄 **Switch Model**: Open **⚙️ AI & LLM Settings** in the left sidebar and select a model with higher free allowances (e.g., `gemini-2.5-flash` instead of `gemini-3.7-flash`).")
        suggestions.append("🔑 **Add / Switch Provider Key**: Switch to an **OpenRouter**, **OpenAI**, or **Groq** key in Settings to bypass provider-specific quotas.")

    # 2. Check for Authentication / Bad Key (401 / 403)
    elif "auth" in err_lower or "401" in err_lower or "unauthorized" in err_lower or "api_key" in err_lower or "forbidden" in err_lower:
        category = "Authentication / Invalid API Key (401/403)"
        title = "AI Provider Authentication Failed"
        icon = "🔑"
        suggestions.append("🔑 **Check API Key**: Open **⚙️ AI & LLM Settings** in the left sidebar and verify your API key is correctly pasted without leading/trailing whitespace.")
        suggestions.append("🌐 **Verify Provider Account**: Confirm your API key is active and not revoked in your provider's developer dashboard.")

    # 3. Check for Context Window Exceeded / Prompt Too Long
    elif "context_length_exceeded" in err_lower or "maximum context length" in err_lower or "context window" in err_lower or "too large" in err_lower:
        category = "Context Length Exceeded"
        title = "Telemetry Exceeds Model Context Window"
        icon = "📜"
        suggestions.append("✂️ **Narrow Filter Scope**: Try selecting a specific **Night Standby** or **Screen-Off** interval rather than a multi-day full window.")
        suggestions.append("🧠 **Switch to High-Context Model**: Switch to `gemini-2.5-flash` or `gemini-2.5-pro` (up to 1M–2M token context window) in **⚙️ AI & LLM Settings**.")

    # 4. Check for Service Unavailable / High Demand / Capacity (503)
    elif "serviceunavailable" in err_lower or "503" in err_lower or "high demand" in err_lower or "unavailable" in err_lower:
        category = "Model High Demand / Service Unavailable (503)"
        title = "Model Temporarily Overloaded (503 High Demand)"
        icon = "🔥"
        suggestions.append("⏱️ **Wait a Moment & Retry**: Spikes in demand on preview/experimental models are temporary. Wait 10–30 seconds and click the button again.")
        suggestions.append("🔄 **Switch Model**: In **⚙️ AI & LLM Settings**, switch to a stable production model (e.g. `gemini-2.5-flash` or `gemini-2.5-pro`) which has dedicated capacity.")
        suggestions.append("🔑 **Try Another Provider**: If Google Gemini is congested, switch provider to **OpenRouter** or **OpenAI** in settings.")

    # 5. Check for Connection / Timeout / Network
    elif "timeout" in err_lower or "connection" in err_lower or "connecterror" in err_lower:
        category = "Network / Connection Timeout"
        title = "Cannot Connect to AI Provider"
        icon = "🌐"
        suggestions.append("📡 **Check Internet Connection**: Verify your machine has outbound internet connectivity to API endpoints.")
        suggestions.append("🖥️ **Local LLM (Ollama)**: If using Ollama, ensure the Ollama service is running (`ollama serve`) on `http://localhost:11434`.")
        suggestions.append("🔄 **Retry**: The provider may be experiencing temporary network latency. Try clicking the button again.")
        
    else:
        suggestions.append("🔄 **Retry**: Check your network connection and click the operation again.")
        suggestions.append("⚙️ **Check Provider Status**: Open **⚙️ AI & LLM Settings** in the sidebar to verify your provider and model configuration.")

    return {
        "category": category,
        "title": title,
        "icon": icon,
        "raw_error": err_str,
        "suggestions": suggestions,
        "retry_delay_sec": retry_delay_sec
    }

def render_ai_error(error: Exception, action_description: str = "generating AI analysis", key_suffix: str = "err"):
    """Render an explicit, rich alert window with clear diagnostics and practical recovery suggestions."""
    diag = parse_llm_error(error)
    with st.container(border=True, key=f"ai_err_zone_{key_suffix}"):
        st.markdown(f"### {diag['icon']} {diag['title']}")
        st.markdown(f"**Failed while {action_description}.** Category: `{diag['category']}`")
        
        st.markdown("#### 💡 Recommended Next Steps:")
        for s in diag["suggestions"]:
            st.markdown(f"- {s}")
            
        with st.expander("🔍 View Raw Error Details & Technical Trace", expanded=False):
            st.code(diag["raw_error"], language="text")

def render_ai_block(content_markdown: str, key_suffix: str = "default"):
    """Renders AI markdown content inside a styled, border-contained block without breaking markdown syntax."""
    # Clean leading newline and raw HTML breaks if any to ensure clean table & heading rendering
    clean_md = parser.clean_markdown_breaks(content_markdown.strip()) if content_markdown else ""
    with st.container(border=True, key=f"ai_zone_{key_suffix}"):
        st.markdown(clean_md)

def highlight_search_query(text: str, query: str):
    """Safely highlights case-insensitive search matches in text/markdown without breaking HTML tags or code blocks."""
    if not query or not query.strip() or not text:
        return text, 0
    q = query.strip()
    p = re.compile(f"({re.escape(q)})", re.IGNORECASE)
    parts = re.split(r"(```[\s\S]*?```|<[^>]+>)", text)
    count = 0
    res = []
    mark_open = '<mark style="background-color: #f59e0b; color: #000000; padding: 1px 4px; border-radius: 3px; font-weight: 700;">'
    for part in parts:
        if part.startswith("```") or (part.startswith("<") and part.endswith(">")):
            res.append(part)
        else:
            c = len(p.findall(part))
            count += c
            if c:
                part = p.sub(lambda m: f"{mark_open}{m.group(1)}</mark>", part)
            res.append(part)
    return "".join(res), count

def build_compact_summary(rep, filter_mode="full", n_start=23, n_end=7, custom_start_dt=None, custom_end_dt=None):
    """Build a high-signal condensed summary for comparative analysis, respecting the active scope."""
    lines = []
    df_h = rep.get("history_data")
    summary_text = rep.get("summary_text", "")
    
    if df_h is not None and not df_h.empty and "Time" in df_h.columns and "Level" in df_h.columns:
        if filter_mode == "night":
            if custom_start_dt and custom_end_dt:
                s_dt, e_dt = custom_start_dt, custom_end_dt
            elif rep.get("custom_night_start") and rep.get("custom_night_end"):
                s_dt, e_dt = rep["custom_night_start"], rep["custom_night_end"]
            else:
                min_t = df_h["Time"].min()
                max_t = df_h["Time"].max()
                s_dt, e_dt = parser.get_latest_night_window(min_t, max_t, n_start, n_end)
            df_target = parser.slice_timeline_range(df_h, s_dt, e_dt)
            scope_desc = f"🌙 Night Window ({s_dt.strftime('%H:%M')} - {e_dt.strftime('%H:%M')})"
        else:
            df_target = df_h
            scope_desc = "🌐 Full Recording Window"
            
        kpis = parser.compute_window_kpis(df_target)
        lines.append(f"• Scope: {scope_desc} | Window: {kpis['start_time']} -> {kpis['end_time']}")
        lines.append(f"• Discharge: {kpis['start_level']}% -> {kpis['end_level']}% (Drop: {kpis['drop_pct']}%, Duration: {kpis['duration_hrs']:.1f} hrs, Avg Rate: {kpis['rate_per_hr']:.2f}%/hr)")
        lines.append(f"• Health Assessment: {kpis['status']}")
    
    if filter_mode in ["night", "screen_off"]:
        standby_df = parser.extract_screen_off_chart_data(summary_text)
        if standby_df is not None and not standby_df.empty:
            clean_s = parser.clean_chart_dataframe(standby_df, summary_text)
            lines.append("• Top Standby / Screen-Off Consumers (mAh):")
            for _, row in clean_s.head(10).iterrows():
                lines.append(f"    - {row['Component']}: {row['mAh']} mAh")
        else:
            df_c = rep.get("chart_data")
            if df_c is not None and not df_c.empty:
                lines.append("• Top Power Consumers (mAh):")
                for _, row in df_c.head(10).iterrows():
                    lines.append(f"    - {row['Component']}: {row['mAh']} mAh")
    else:
        df_c = rep.get("chart_data")
        if df_c is not None and not df_c.empty:
            lines.append("• Top Power Consumers (mAh):")
            for _, row in df_c.head(10).iterrows():
                lines.append(f"    - {row['Component']}: {row['mAh']} mAh")
            
    if summary_text:
        uid_map = parser.extract_uid_mapping_from_text(summary_text)
        text_lines = parser.replace_uids_safely([l for l in summary_text.splitlines() if l.strip()], uid_map)
        lines.append("• Key Telemetry & Wakelock Excerpt:")
        lines.extend([f"    {l}" for l in text_lines[:35]])
        
    return "\n".join(lines)

def get_effective_bounds(rep, m_mode, n_start=None, n_end=None):
    """Calculate the effective start/end timestamps and sliced timeline for a report."""
    if n_start is None:
        try:
            n_start = int(db.get_setting("night_start_hour", "23"))
        except Exception:
            n_start = 23
    if n_end is None:
        try:
            n_end = int(db.get_setting("night_end_hour", "7"))
        except Exception:
            n_end = 7
    df_h = rep.get("history_data")
    if df_h is None or df_h.empty or "Time" not in df_h.columns:
        return None, None, pd.DataFrame()
    r_min, r_max = df_h["Time"].min(), df_h["Time"].max()
    if m_mode == "night":
        auto_s, auto_e = parser.get_latest_night_window(r_min, r_max, n_start, n_end)
        if hasattr(auto_s, "to_pydatetime"):
            auto_s = auto_s.to_pydatetime()
        if hasattr(auto_e, "to_pydatetime"):
            auto_e = auto_e.to_pydatetime()

        db_c_s = rep.get("custom_night_start")
        db_c_e = rep.get("custom_night_end")
        def_s = db_c_s if (db_c_s and db_c_e) else auto_s
        def_e = db_c_e if (db_c_s and db_c_e) else auto_e

        ov_key = f"m_night_{rep['id']}"
        if ov_key not in st.session_state:
            st.session_state[ov_key] = (def_s, def_e)

        s_dt, e_dt = st.session_state[ov_key]
        if hasattr(s_dt, "to_pydatetime"):
            s_dt = s_dt.to_pydatetime()
        if hasattr(e_dt, "to_pydatetime"):
            e_dt = e_dt.to_pydatetime()

        s_dt = max(r_min.to_pydatetime(), min(r_max.to_pydatetime(), s_dt))
        e_dt = max(r_min.to_pydatetime(), min(r_max.to_pydatetime(), e_dt))
        if s_dt >= e_dt:
            s_dt, e_dt = def_s, def_e
        sl_df = parser.slice_timeline_range(df_h, s_dt, e_dt)
        return s_dt, e_dt, sl_df
    else:
        return r_min.to_pydatetime(), r_max.to_pydatetime(), df_h

def build_single_report_markdown(report, filter_mode, kpis, diagnosis_text):
    """Generate clean, publication-quality Markdown document for a single report."""
    md = []
    md.append(f"# 🔋 Battery Oracle Diagnostic Report: {report['custom_name']}\n")
    md.append(f"- **Captured:** `{report['timestamp_str']}`")
    md.append(f"- **Source File:** `{report['filename']}`")
    md.append(f"- **Device Profile:** `{report.get('device_info', 'Android Device')}`")
    if report.get('description'):
        md.append(f"- **User Notes:** *{report['description']}*")
    md.append(f"- **Analysis Scope:** `{filter_mode.upper()}`\n")
    
    md.append("## 📊 Telemetry & Discharge Metrics")
    md.append(f"| Metric | Value |")
    md.append(f"| :--- | :--- |")
    md.append(f"| **Active Window** | {kpis['start_time']} → {kpis['end_time']} |")
    md.append(f"| **Battery Level Delta** | {kpis['start_level']}% → {kpis['end_level']}% |")
    md.append(f"| **Total Drop** | {kpis['drop_pct']}% over {kpis['duration_hrs']:.1f} hrs |")
    md.append(f"| **Discharge Velocity** | **{kpis['rate_per_hr']:.2f}% / hour** |")
    md.append(f"| **Standby Health Status** | {kpis['status']} |\n")
    
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
    md.append("\n---\n*Generated by Battery Oracle on " + datetime.now().strftime("%Y-%m-%d %H:%M") + "*")
    return "\n".join(md)

def build_comparative_markdown(reports, filter_mode, analysis_text):
    """Generate clean Markdown document for comparative multi-report evaluation."""
    md = []
    md.append("# 🔀 Battery Oracle: Multi-Report Comparative Analysis\n")
    md.append(f"- **Generated:** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`")
    md.append(f"- **Compared Reports:** {len(reports)} sessions")
    md.append(f"- **Comparative Scope:** `{filter_mode.upper()}`\n")
    
    md.append("## 📋 Session Breakdown Matrix")
    md.append("| Session Name | Capture Time | Device | Notes |")
    md.append("| :--- | :--- | :--- | :--- |")
    for r in reports:
        md.append(f"| {r['custom_name']} | {r['timestamp_str']} | {r.get('device_info', 'Android')} | {r.get('description', '')} |")
    md.append("\n## 🔮 Comparative AI Synthesis & Optimization Impact\n")
    md.append(analysis_text or "No comparative synthesis available.")
    md.append("\n---\n*Generated by Battery Oracle*")
    return "\n".join(md)


def add_night_shading(fig, df_time, night_start=23, night_end=7):
    """Add subtle dark shading over nighttime hours on timeline chart."""
    if df_time is None or df_time.empty or "Time" not in df_time.columns:
        return fig
    min_time = df_time["Time"].min()
    max_time = df_time["Time"].max()
    
    current_date = min_time.floor('D')
    end_date = max_time.ceil('D')
    
    while current_date <= end_date:
        n_start = current_date + pd.Timedelta(hours=night_start)
        n_end = current_date + pd.Timedelta(days=1 if night_start > night_end else 0, hours=night_end)
        
        if n_end >= min_time and n_start <= max_time:
            x0 = max(n_start, min_time)
            x1 = min(n_end, max_time)
            fig.add_vrect(
                x0=x0, x1=x1,
                fillcolor="rgba(30, 41, 59, 0.20)",
                layer="below",
                line_width=0,
                annotation_text="🌙 Night",
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color="gray"
            )
        current_date += pd.Timedelta(days=1)
        
    return fig

@st.fragment
def render_chat_message_item(msg, rep_id=None, active_th_id=None, thread_dict=None, is_global=False, search_query=""):
    """Renders a single chat message inside an independent Streamlit fragment for instantaneous toggling and search highlighting."""
    msg_id = msg["id"]
    state_key = f"msg_col_{msg_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = bool(msg.get("is_collapsed", 0))
    is_col = st.session_state[state_key]

    raw_content = msg.get("content", "")
    highlighted_content = raw_content
    match_count = 0
    if search_query and search_query.strip():
        highlighted_content, match_count = highlight_search_query(raw_content, search_query)
        # If message contains searched string, automatically expand so the match is visible
        if match_count > 0:
            is_col = False

    with st.chat_message(msg["role"]):
        ts_str = msg.get("created_at", "")
        if ts_str and len(ts_str) >= 16:
            display_ts = ts_str[:16].replace("T", " ")
        else:
            display_ts = ts_str

        col_toggle, col_meta, col_del = st.columns([0.03, 0.94, 0.03], vertical_alignment="center")
        with col_toggle:
            toggle_icon = "▶" if is_col else "▼"
            tooltip = "Click to expand message" if is_col else "Click to collapse message"
            btn_key = f"tog_gmsg_{msg_id}" if is_global else f"tog_msg_{msg_id}"
            if st.button(toggle_icon, key=btn_key, type="tertiary", help=tooltip):
                new_state = not is_col
                st.session_state[state_key] = new_state
                db.toggle_message_collapsed(msg_id, new_state)
                st.rerun(scope="fragment")

        with col_meta:
            if is_col:
                first_line = raw_content.strip().split("\n")[0][:85]
                if search_query and search_query.strip():
                    first_line, _ = highlight_search_query(first_line, search_query)
                parts = []
                if display_ts:
                    parts.append(f"🕒 `{display_ts}`")
                parts.append(f"*(Collapsed: {first_line}...)*")
                st.caption(" &nbsp;•&nbsp; ".join(parts), unsafe_allow_html=True)
            else:
                header_parts = []
                if display_ts:
                    header_parts.append(f"🕒 `{display_ts}`")
                if msg.get("filter_context"):
                    header_parts.append(f"🎯 *Scope: {msg['filter_context']}*")
                if match_count > 0:
                    header_parts.append(f"🔍 **{match_count} match{'es' if match_count > 1 else ''}**")
                if msg["role"] == "assistant":
                    header_parts.append('<span class="ai-badge">✨ AI ASSISTANT</span>')
                if header_parts:
                    st.caption(" &nbsp;•&nbsp; ".join(header_parts), unsafe_allow_html=True)

        with col_del:
            del_key = f"del_gmsg_{msg_id}" if is_global else f"delmsg_{msg_id}"
            if st.button("🗑️", key=del_key, type="tertiary", help="Delete message from history"):
                db.delete_chat_message(msg_id)
                st.rerun(scope="fragment")

        if not is_col:
            st.markdown(highlighted_content, unsafe_allow_html=True)
            
            # Fork option for assistant messages in Single Report view
            if msg["role"] == "assistant" and not is_global and active_th_id and thread_dict:
                col_spacer, col_fork = st.columns([4, 1])
                with col_fork:
                    if st.button("🔀 Fork from here", key=f"fork_{msg_id}"):
                        forked_id = db.fork_thread(
                            source_thread_id=active_th_id,
                            from_message_id=msg_id,
                            new_title=f"Branch: {thread_dict.get(active_th_id, 'Thread')[:15]}..."
                        )
                        st.session_state.active_thread_id = forked_id
                        st.success("Forked into a new thread!")
                        st.rerun(scope="fragment")

@st.fragment
def render_ai_chat_panel(
    scope_key: str,
    panel_title: str,
    scope_badge: str,
    report_id: int | None,
    active_thread_state_key: str,
    sys_prompt_builder,
    action_type: str = "chat",
    filter_label: str = ""
):
    """
    Renders an isolated, full-screen AI chat consultation workspace within its dedicated tab.
    Decorated with @st.fragment so that sending messages, switching threads, or searching
    updates only this tab without dimming the application or resetting scroll position.
    """
    is_global = (report_id is None)
    threads = db.get_threads_for_report(report_id)
    if not threads:
        init_title = "Global Thread" if is_global else "Main Thread"
        init_id = db.create_thread(report_id, init_title)
        threads = db.get_threads_for_report(report_id)
    thread_dict = {t["id"]: t["title"] for t in threads}

    if active_thread_state_key not in st.session_state or st.session_state[active_thread_state_key] not in thread_dict:
        st.session_state[active_thread_state_key] = threads[0]["id"]
    active_th_id = st.session_state[active_thread_state_key]
    thread_messages = db.get_chat_messages(report_id, thread_id=active_th_id)
    total_msgs = len(thread_messages)

    # Visual Chat Header
    st.markdown(
        f"""
        <div class="chat-header-wrap">
            <div class="chat-header-title">💬 {panel_title}</div>
            <div>
                <span class="scope-pill">{scope_badge}</span>
                <span class="scope-pill">🧵 {len(threads)} thread{'s' if len(threads) != 1 else ''}</span>
                <span class="scope-pill">💬 {total_msgs} message{'s' if total_msgs != 1 else ''}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Primary Chat Management Toolbar: Thread select, New, Rename, Clear/Delete, Export
    c_sel, c_new, c_ren, c_del, c_exp = st.columns([3.6, 1.2, 1.2, 1.2, 1.2], vertical_alignment="center")

    with c_sel:
        def _fmt_thread(th_id):
            title = thread_dict.get(th_id, "Thread")
            cnt = db.get_message_count_for_thread(th_id)
            return f"🧵 {title} ({cnt} msg{'s' if cnt != 1 else ''})"

        selected_th = st.selectbox(
            "Thread",
            options=list(thread_dict.keys()),
            format_func=_fmt_thread,
            index=list(thread_dict.keys()).index(active_th_id),
            key=f"th_sel_{scope_key}",
            label_visibility="collapsed"
        )
        if selected_th != active_th_id:
            st.session_state[active_thread_state_key] = selected_th
            st.rerun(scope="fragment")

    with c_new:
        with st.popover("➕ New", use_container_width=True):
            new_title = st.text_input("Thread Title", placeholder="e.g. Wakelock Inquiry", key=f"new_th_t_{scope_key}")
            if st.button("Create Thread", key=f"btn_cr_th_{scope_key}", use_container_width=True):
                nid = db.create_thread(report_id, new_title.strip() if new_title else "New Thread")
                st.session_state[active_thread_state_key] = nid
                st.rerun(scope="fragment")

    with c_ren:
        with st.popover("✏️ Rename", use_container_width=True):
            curr_title = thread_dict.get(active_th_id, "")
            rename_val = st.text_input("New Title", value=curr_title, key=f"ren_th_t_{scope_key}")
            if st.button("Update Title", key=f"btn_rn_th_{scope_key}", use_container_width=True):
                if rename_val.strip():
                    db.rename_thread(active_th_id, rename_val.strip())
                    st.rerun(scope="fragment")

    with c_del:
        if len(threads) > 1:
            if st.button("🗑️ Delete", key=f"btn_del_th_{scope_key}", use_container_width=True, help="Delete this thread and all its messages"):
                db.delete_thread(active_th_id)
                st.session_state[active_thread_state_key] = None
                st.rerun(scope="fragment")
        else:
            if st.button("🧹 Clear", key=f"btn_clr_th_{scope_key}", use_container_width=True, help="Clear all messages in this thread"):
                db.clear_thread_messages(active_th_id)
                st.rerun(scope="fragment")

    with c_exp:
        # Markdown export of current thread
        if thread_messages:
            thread_md = f"# AI Chat Transcript - {thread_dict.get(active_th_id, 'Thread')}\n\n"
            thread_md += f"**Scope**: {scope_badge}  \n**Export Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
            for m in thread_messages:
                role_name = "👤 User" if m["role"] == "user" else "✨ Oracle AI"
                thread_md += f"### {role_name} ({m.get('timestamp_str', '')})\n{m.get('content', '')}\n\n"
            st.download_button(
                "📥 Export",
                data=thread_md,
                file_name=f"chat_export_{scope_key}_{active_th_id}.md",
                mime="text/markdown",
                key=f"dl_th_{scope_key}",
                use_container_width=True
            )
        else:
            st.button("📥 Export", key=f"dl_th_dis_{scope_key}", use_container_width=True, disabled=True)

    # Secondary Toolbar: Search + Expand/Collapse All
    s_col, b_exp, b_col = st.columns([3.6, 1.2, 1.2], vertical_alignment="center")
    with s_col:
        search_q = st.text_input(
            "Search messages",
            placeholder="🔎 Search conversation history...",
            key=f"search_q_{scope_key}_{active_th_id}",
            label_visibility="collapsed"
        )
    with b_exp:
        if st.button("⊞ Expand All", key=f"exp_all_{scope_key}", use_container_width=True, disabled=not bool(thread_messages)):
            db.set_thread_messages_collapsed(active_th_id, False)
            for m in thread_messages:
                st.session_state[f"msg_col_{m['id']}"] = False
            st.rerun(scope="fragment")
    with b_col:
        if st.button("⊟ Collapse All", key=f"col_all_{scope_key}", use_container_width=True, disabled=not bool(thread_messages)):
            db.set_thread_messages_collapsed(active_th_id, True)
            for m in thread_messages:
                st.session_state[f"msg_col_{m['id']}"] = True
            st.rerun(scope="fragment")

    if search_q and search_q.strip():
        sq = search_q.strip()
        total_m = 0
        matching_ids = set()
        for m in thread_messages:
            _, c = highlight_search_query(m.get("content", ""), sq)
            if c > 0:
                total_m += c
                matching_ids.add(m["id"])
        if total_m > 0:
            st.caption(f"🔎 Found **{total_m}** match{'es' if total_m != 1 else ''} in **{len(matching_ids)}** message{'s' if len(matching_ids) != 1 else ''}. *(Matching messages highlighted)*")
        else:
            st.caption(f"🔎 No matches found for **\"{sq}\"**.")

    st.divider()

    # Full Page Viewport: Render conversation messages naturally on the full page
    if not thread_messages:
        st.info("💡 No messages in this thread yet. Ask anything below to start the consultation!")
    else:
        for msg in thread_messages:
            render_chat_message_item(
                msg=msg,
                rep_id=report_id,
                active_th_id=active_th_id,
                thread_dict=thread_dict,
                is_global=is_global,
                search_query=search_q
            )

    # Dedicated Chat Input Box
    input_key = f"chat_input_{scope_key}"
    if prompt := st.chat_input("Ask a question, query telemetry, or consult about wakelocks...", key=input_key):
        # 1. Save user message
        db.save_chat_message(
            report_id=report_id,
            role="user",
            content=prompt,
            thread_id=active_th_id,
            filter_context=filter_label
        )

        # 2. Auto-title if it's the first message
        if len(thread_messages) == 0 and ("New" in thread_dict.get(active_th_id, "") or "Main" in thread_dict.get(active_th_id, "") or "Global" in thread_dict.get(active_th_id, "")):
            auto_title = prompt[:25].strip() + "..."
            db.rename_thread(active_th_id, auto_title)

        # 3. Stream/execute LLM response with live status on the full page
        with st.chat_message("user"):
            if filter_label:
                st.caption(f"🎯 *Scope: {filter_label}*")
            st.markdown(prompt)

        with st.chat_message("assistant"):
            msg_ph = st.empty()
            with st.status("🧠 Oracle AI is analyzing context and generating response...", expanded=True) as status_box:
                st.write("Synthesizing telemetry context & prompt...")
                sys_prompt = sys_prompt_builder()

                messages = [{"role": "system", "content": sys_prompt}]
                for m in thread_messages:
                    messages.append({"role": m["role"], "content": m["content"]})
                messages.append({"role": "user", "content": prompt})

                st.write("Invoking active LLM reasoning model...")
                try:
                    reply = llm_manager.call_llm_tracked(
                        messages=messages,
                        report_id=report_id if (report_id and report_id > 0) else None,
                        thread_id=active_th_id,
                        action_type=action_type
                    )
                    status_box.update(label="✨ Response generated successfully!", state="complete", expanded=False)
                    msg_ph.markdown(reply)
                    db.save_chat_message(
                        report_id=report_id,
                        role="assistant",
                        content=reply,
                        thread_id=active_th_id,
                        filter_context=filter_label
                    )
                except Exception as e:
                    status_box.update(label="❌ Failed to generate response", state="error", expanded=True)
                    with msg_ph.container():
                        render_ai_error(e, action_description="generating assistant reply", key_suffix=f"chat_{scope_key}_{active_th_id}")

        # Fragment-only rerun to refresh viewport with newly saved messages
        st.rerun(scope="fragment")

# --- Session State Initialization ---
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "single"
if "selected_report_id" not in st.session_state:
    st.session_state.selected_report_id = None
if "active_thread_id" not in st.session_state:
    st.session_state.active_thread_id = None
if "confirm_delete_id" not in st.session_state:
    st.session_state.confirm_delete_id = None
if "handled_upload_hashes" not in st.session_state:
    st.session_state.handled_upload_hashes = set()
if "inspect_package" not in st.session_state:
    st.session_state.inspect_package = None
if "inv_upload_counter" not in st.session_state:
    st.session_state.inv_upload_counter = 0
if "inv_upload_success_msg" not in st.session_state:
    st.session_state.inv_upload_success_msg = None
if "pending_ai_action" not in st.session_state:
    st.session_state.pending_ai_action = None

# Get active LLM configuration
active_llm_cfg = llm_manager.get_active_config()
night_start_cfg = int(db.get_setting("night_start_hour", "23"))
night_end_cfg = int(db.get_setting("night_end_hour", "7"))

# --- Execution Engine for Asynchronous / Modal AI Workflows ---
def execute_ai_action(action_type: str, payload: dict, progress_bar, status_box, curr_cfg: dict):
    """
    Executes an AI analysis workflow directly within the modal, providing real-time
    granular progress updates across extraction, prompt generation, LLM querying,
    and database persistence.
    """
    if not action_type or not payload:
        raise ValueError("Missing action_type or payload for AI execution.")

    if action_type == "single_diagnosis":
        progress_bar.progress(20, text="📊 Extracting and filtering telemetry...")
        status_box.info(f"Filtering batterystats for scope: {payload.get('filter_mode_choice', 'Targeted Scope')}...")
        rep = db.get_report_by_id(payload["rep_id"])
        if not rep:
            raise ValueError(f"Report ID {payload['rep_id']} not found in database.")
        
        filtered_telemetry = parser.get_filtered_telemetry_for_llm(
            rep.get("summary_text", ""), 
            payload["filter_mode"], 
            payload.get("kpis", {})
        )
        active_inv_profile = db.get_latest_device_profile()
        profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
        if profile_summary:
            filtered_telemetry = f"{profile_summary}\n\n{filtered_telemetry}"
        active_routers = db.get_active_wifi_routers()
        router_summary = parser.format_router_context_for_llm(active_routers)
        if router_summary:
            filtered_telemetry = f"{router_summary}\n\n{filtered_telemetry}"

        progress_bar.progress(40, text="📝 Assembling diagnostic prompt & context...")
        status_box.info("Injecting device profile, AppOps & power metrics...")
        diag_prompt_tmpl = llm_manager.get_prompt_template("single_diagnosis")
        formatted_diag_prompt = diag_prompt_tmpl.format(
            report_name=rep["custom_name"],
            timestamp_str=rep["timestamp_str"],
            device_info=rep.get("device_info", "Unknown"),
            timezone_info=payload.get("timezone", "UTC"),
            telemetry_data=filtered_telemetry
        )

        progress_bar.progress(60, text=f"🔮 Oracle is diagnosing battery telemetry ({curr_cfg['model']})...")
        status_box.info(f"Querying {curr_cfg['provider']} AI model for root causes & action plan...")
        new_diag = llm_manager.call_llm_tracked(
            messages=[{"role": "system", "content": formatted_diag_prompt}],
            report_id=payload["rep_id"],
            action_type=f"diagnosis_{payload['filter_mode']}"
        )
        new_diag = parser.sanitize_ai_output(new_diag, rep.get("summary_text", ""))

        progress_bar.progress(90, text="💾 Persisting diagnosis to local database...")
        status_box.info("Saving results to SQLite records...")
        if payload["filter_mode"] == "full":
            db.update_report_analysis(payload["rep_id"], new_diag, rep.get("reasoning_trace", ""))
            rep["initial_analysis"] = new_diag
        else:
            db.set_setting(payload["diag_cache_key"], new_diag)
        st.session_state.pop(f"err_diag_{payload['rep_id']}", None)

        progress_bar.progress(100, text="✅ Diagnosis complete!")
        status_box.success("Targeted diagnosis generated successfully! Loading report...")

    elif action_type == "comparative_synthesis":
        progress_bar.progress(20, text=f"📊 Aggregating telemetry across {len(payload.get('compared_report_ids', []))} sessions...")
        status_box.info(f"Extracting power metrics for scope: {payload.get('merged_filter_choice', 'Comparative Scope')}...")
        
        all_reps = {r["id"]: r for r in db.get_all_reports()}
        compared_reports = [all_reps[rid] for rid in payload.get("compared_report_ids", []) if rid in all_reps]
        
        reports_summary_text = ""
        n_s = payload.get("night_start_cfg", 23)
        n_e = payload.get("night_end_cfg", 7)
        for idx, rep in enumerate(compared_reports):
            r_s, r_e, _ = get_effective_bounds(rep, payload["merged_filter_mode"], n_s, n_e)
            reports_summary_text += f"\n--- REPORT {idx+1}: {rep['custom_name']} (Captured: {rep['timestamp_str']}) ---\n"
            reports_summary_text += f"Device: {rep.get('device_info', 'Unknown')}\n"
            reports_summary_text += f"Notes: {rep.get('description', 'None')}\n"
            reports_summary_text += f"{build_compact_summary(rep, filter_mode=payload['merged_filter_mode'], n_start=n_s, n_end=n_e, custom_start_dt=r_s, custom_end_dt=r_e)}\n"

        active_inv_profile = db.get_latest_device_profile()
        profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
        if profile_summary:
            reports_summary_text = f"{profile_summary}\n\n{reports_summary_text}"
        active_routers = db.get_active_wifi_routers()
        router_summary = parser.format_router_context_for_llm(active_routers)
        if router_summary:
            reports_summary_text = f"{router_summary}\n\n{reports_summary_text}"

        progress_bar.progress(40, text="📝 Building comparative synthesis prompt...")
        status_box.info("Structuring cross-report power differentials...")
        comp_prompt_tmpl = llm_manager.get_prompt_template("comparison")
        formatted_comp_prompt = comp_prompt_tmpl.format(
            report_count=len(compared_reports),
            timezone_info=payload.get("timezone", "UTC"),
            reports_summary=reports_summary_text
        )

        progress_bar.progress(60, text=f"🔮 Oracle is synthesizing comparative evaluation ({curr_cfg['model']})...")
        status_box.info("Querying LLM provider for regressions & behavioral deltas...")
        combined_text = llm_manager.call_llm_tracked(
            messages=[{"role": "system", "content": formatted_comp_prompt}],
            action_type=f"comparative_evaluation_{payload['merged_filter_mode']}"
        )

        progress_bar.progress(90, text="💾 Saving comparative analysis to SQLite...")
        status_box.info("Persisting cross-report synthesis...")
        db.save_combined_analysis(payload["comp_key"], combined_text, scope_key=payload["merged_filter_mode"])
        st.session_state.pop(f"err_comp_{payload['merged_filter_mode']}", None)

        progress_bar.progress(100, text="✅ Comparative synthesis complete!")
        status_box.success("Cross-session analysis generated successfully! Loading synthesis...")

    elif action_type == "profile_audit":
        progress_bar.progress(25, text="📊 Extracting device settings, Doze states & AppOps...")
        status_box.info("Inspecting system state and background policies...")
        profile = db.get_device_profile(payload["profile_id"])
        if not profile:
            raise ValueError(f"Profile ID {payload['profile_id']} not found in database.")
        p_data = profile.get("parsed_data", {})
        profile_telemetry_str = parser.get_inventory_summary_for_llm(p_data)
        active_routers = db.get_active_wifi_routers()
        router_summary = parser.format_router_context_for_llm(active_routers)
        if router_summary:
            profile_telemetry_str = f"{router_summary}\n\n{profile_telemetry_str}"

        progress_bar.progress(45, text="📝 Assembling audit prompt...")
        status_box.info("Structuring AppOps anomalies and Doze configuration...")
        audit_prompt_tmpl = llm_manager.get_prompt_template("profile_audit")
        formatted_audit_prompt = audit_prompt_tmpl.format(
            device_model=p_data.get("device_model", "Unknown"),
            os_build=p_data.get("os_build", "Unknown"),
            android_version=p_data.get("android_version", "Unknown"),
            profile_telemetry=profile_telemetry_str
        )

        progress_bar.progress(65, text=f"🔮 Auditing device configuration ({curr_cfg['model']})...")
        status_box.info("Querying LLM provider for misconfigurations & power optimizations...")
        new_analysis = llm_manager.call_llm_tracked(
            messages=[{"role": "system", "content": formatted_audit_prompt}],
            action_type="profile_audit"
        )
        new_analysis = parser.sanitize_ai_output(new_analysis)

        progress_bar.progress(90, text="💾 Persisting audit findings to database...")
        status_box.info("Saving configuration audit results...")
        db.update_device_profile_analysis(payload["profile_id"], new_analysis, "")
        st.session_state.pop(f"err_prof_audit_{payload['profile_id']}", None)

        progress_bar.progress(100, text="✅ Device audit complete!")
        status_box.success("Profile configuration audit generated successfully! Loading audit...")

    elif action_type == "profile_comparison":
        progress_bar.progress(25, text="📊 Analyzing configuration deltas...")
        status_box.info("Comparing package AppOps, Doze whitelists & system flags...")
        profile_a = db.get_device_profile(payload["p_a_id"])
        profile_b = db.get_device_profile(payload["p_b_id"])
        if not profile_a or not profile_b:
            raise ValueError("Comparison profiles could not be loaded from database.")
        diff = parser.compute_profile_diff(profile_a, profile_b)
        diff_summary_str = parser.format_profile_diff_for_llm(profile_a, profile_b, diff)

        progress_bar.progress(45, text="📝 Formatting delta audit prompt...")
        status_box.info("Preparing baseline vs target comparison payload...")
        cmp_prompt_tmpl = llm_manager.get_prompt_template("profile_comparison")
        formatted_cmp_prompt = cmp_prompt_tmpl.format(
            baseline_name=profile_a["profile_name"],
            baseline_model=diff["model_a"],
            baseline_build=diff["build_a"],
            target_name=profile_b["profile_name"],
            target_model=diff["model_b"],
            target_build=diff["build_b"],
            diff_summary=diff_summary_str
        )

        progress_bar.progress(65, text=f"🔮 Auditing configuration deltas ({curr_cfg['model']})...")
        status_box.info("Querying LLM provider for delta risks & regression sources...")
        cmp_analysis_res = llm_manager.call_llm_tracked(
            messages=[{"role": "system", "content": formatted_cmp_prompt}],
            action_type="profile_comparison"
        )
        cmp_analysis_res = parser.sanitize_ai_output(cmp_analysis_res)

        progress_bar.progress(90, text="💾 Persisting delta audit to database...")
        status_box.info("Saving comparison results...")
        db.set_setting(payload["cmp_cache_key"], cmp_analysis_res)
        st.session_state.pop(f"err_prof_cmp_{payload['p_a_id']}_{payload['p_b_id']}", None)

        progress_bar.progress(100, text="✅ Delta audit complete!")
        status_box.success("Profile delta audit generated successfully! Loading comparison...")

    elif action_type == "master_synthesis":
        progress_bar.progress(20, text="📊 Synthesizing chronicle across all bugreports...")
        status_box.info("Compiling telemetry timelines and test run notes...")
        all_reports = db.get_all_reports()
        chronicle = []
        active_inv_profile = db.get_latest_device_profile()
        profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
        if profile_summary:
            chronicle.append(profile_summary + "\n")
        active_routers = db.get_active_wifi_routers()
        router_summary = parser.format_router_context_for_llm(active_routers)
        if router_summary:
            chronicle.append(router_summary + "\n")

        n_s = payload.get("night_start_cfg", 23)
        n_e = payload.get("night_end_cfg", 7)
        for idx, r in enumerate(all_reports):
            chronicle.append(f"\n==========================================")
            chronicle.append(f"SESSION {idx+1}: {r['custom_name']}")
            chronicle.append(f"File: {r['filename']} | Timestamp: {r['timestamp_str']}")
            chronicle.append(f"Device: {r.get('device_info', 'Android Device')}")
            chronicle.append(f"User State / Notes: {r.get('description', 'None')}")
            chronicle.append(build_compact_summary(r, filter_mode='night', n_start=n_s, n_end=n_e))
            chronicle.append("==========================================\n")

        progress_bar.progress(45, text="📝 Assembling multi-day synthesis prompt...")
        status_box.info("Structuring chronological evolution & hypothesis validation...")
        synth_prompt = llm_manager.get_prompt_template("master_synthesis").format(
            experiment_chronicle="\n".join(chronicle)
        )

        progress_bar.progress(65, text=f"🔮 Synthesizing multi-day experiment ({curr_cfg['model']})...")
        status_box.info("Querying LLM provider for holistic insights & final recommendations...")
        synthesis_text = llm_manager.call_llm_tracked(
            messages=[{"role": "system", "content": synth_prompt}],
            action_type="master_experiment_synthesis"
        )
        synthesis_text = parser.sanitize_ai_output(synthesis_text)

        progress_bar.progress(90, text="💾 Persisting Grand Master Synthesis to database...")
        status_box.info("Saving executive retrospective...")
        db.save_master_synthesis(synthesis_text)
        st.session_state.pop("err_master_synth", None)

        progress_bar.progress(100, text="✅ Grand Master Synthesis complete!")
        status_box.success("Retrospective synthesis generated successfully! Loading blueprint...")

    else:
        raise ValueError(f"Unknown action_type: {action_type}")

# --- Confirmation Dialog for AI Execution ---
@st.dialog("🔮 Confirm AI Analysis Execution", width="medium")
def confirm_ai_analysis_dialog(
    action_key: str, 
    action_title: str, 
    target_desc: str, 
    details_dict: dict = None,
    action_type: str = None,
    action_payload: dict = None
):
    st.markdown(f"### {action_title}")
    st.write(target_desc)
    
    st.markdown("---")
    curr_cfg = llm_manager.get_active_config()
    model_pricing = llm_manager.get_model_pricing(curr_cfg["model"])
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown(f"**AI Provider:** `{curr_cfg['provider']}`")
        st.markdown(f"**Model:** `{curr_cfg['model']}`")
    with col_c2:
        st.markdown(f"**Standard Pricing:** `{model_pricing}`")
        st.markdown(f"**Token Cost:** *Tracked to SQLite*")
        
    if details_dict:
        with st.container(border=True):
            for k, v in details_dict.items():
                st.markdown(f"- **{k}:** {v}")
                
    st.caption("ℹ️ Running this analysis sends processed telemetry to the selected LLM provider. Tokens and estimated USD costs will be logged to your Accounting Dashboard.")
    
    st.markdown("")
    btn_area = st.empty()
    with btn_area.container():
        col_btn_cancel, col_btn_proceed = st.columns([1, 1])
        with col_btn_cancel:
            btn_cancel = st.button("❌ Cancel", key=f"btn_cancel_{action_key}", use_container_width=True)
        with col_btn_proceed:
            btn_proceed = st.button("🚀 Proceed with Analysis", key=f"btn_proceed_{action_key}", type="primary", use_container_width=True)

    if btn_cancel:
        st.rerun()

    if btn_proceed:
        # Erase confirmation buttons immediately so UI reflects execution state
        btn_area.empty()
        
        st.markdown("---")
        progress_bar = st.progress(5, text="🚀 Initializing analysis pipeline...")
        status_box = st.empty()
        status_box.info(f"Starting Oracle workflow: {action_title}...")
        
        if action_type and action_payload:
            try:
                execute_ai_action(action_type, action_payload, progress_bar, status_box, curr_cfg)
                time.sleep(0.6)
                st.rerun()
            except Exception as e:
                progress_bar.progress(100, text="❌ Execution encountered an error")
                status_box.error(f"Analysis failed: {str(e)}")
                st.session_state[f"err_{action_key}"] = (e, action_title)
                render_ai_error(e, action_description=action_title, key_suffix=f"dlg_err_{action_key}")
                if st.button("Close Dialog", key=f"btn_close_err_{action_key}", use_container_width=True):
                    st.rerun()
        else:
            # Fallback for untyped actions
            st.session_state.pending_ai_action = action_key
            st.rerun()

# --- Sidebar Configuration & Reports Manager ---
@st.dialog("⚙️ LLM & Prompt Configuration Studio", width="large")
def show_llm_config_dialog(active_cfg, n_start_val, n_end_val):
    st.caption("Manage AI providers, test credentials, and customize specialized diagnostic prompts with generous editing space.")
    settings_tab1, settings_tab2, settings_tab3 = st.tabs(["🤖 LLM Provider & Credentials", "✍️ Prompt Studio (Expert Prompts)", "🌙 Night Standby Settings"])
    
    with settings_tab1:
        st.markdown("#### Provider & Model Credentials")
        provider_list = list(llm_manager.PROVIDER_PRESETS.keys())
        current_provider = active_cfg["provider"]
        prov_idx = provider_list.index(current_provider) if current_provider in provider_list else 0
        
        c_prov, c_model = st.columns([1, 1])
        with c_prov:
            selected_prov = st.selectbox("Provider Preset", provider_list, index=prov_idx, key="cfg_provider_select")
            preset_info = llm_manager.PROVIDER_PRESETS[selected_prov]
        
        # Prepare dynamic model list from session cache or preset
        cache_key = f"models_{selected_prov}"
        if cache_key not in st.session_state:
            st.session_state[cache_key] = list(preset_info.get("models", []))
            
        available_models = st.session_state[cache_key]
        
        with c_model:
            if available_models:
                current_model = active_cfg["model"]
                mod_idx = available_models.index(current_model) if current_model in available_models else 0
                selected_model = st.selectbox(
                    "Model",
                    available_models,
                    index=mod_idx,
                    format_func=lambda m: f"{m}  —  [{llm_manager.get_model_pricing(m)}]",
                    key="cfg_model_select"
                )
            else:
                selected_model = st.text_input(
                    "Custom Model ID",
                    value=active_cfg["model"],
                    placeholder="e.g., openrouter/anthropic/claude-3.5-sonnet",
                    autocomplete="off"
                )
            
        c_key, c_base = st.columns([1, 1])
        with c_key:
            api_key_val = st.text_input(
                "API Key (Masked)",
                type="password",
                value=active_cfg["api_key"],
                placeholder="Enter API key or leave blank if using local",
                key="cfg_api_key_input",
                autocomplete="new-password"
            )
        with c_base:
            api_base_val = st.text_input(
                "API Base URL (Optional)",
                value=active_cfg["api_base"] or (preset_info.get("default_base") or ""),
                placeholder="e.g., http://localhost:11434 for Ollama",
                key="cfg_api_base_input",
                autocomplete="off"
            )
            
        # Model discovery button row
        col_fetch, col_info = st.columns([1, 2])
        with col_fetch:
            if st.button("🔄 Fetch Live Models", key="btn_fetch_live_models", use_container_width=True):
                with st.spinner(f"Querying {selected_prov} API..."):
                    discovered_models, fetch_msg = llm_manager.fetch_available_models(
                        selected_prov,
                        api_key=api_key_val,
                        api_base=api_base_val
                    )
                    st.session_state[cache_key] = discovered_models
                    if "✅" in fetch_msg:
                        st.toast(fetch_msg, icon="✅")
                    elif "⚠️" in fetch_msg:
                        st.warning(fetch_msg)
                    else:
                        st.info(fetch_msg)
                    st.rerun()
        with col_info:
            active_pricing = llm_manager.get_model_pricing(selected_model)
            st.caption(f"**Selected Model Standard Pricing:** `{active_pricing}`\n\n*Total available:* **{len(available_models)}** models for {selected_prov}.")
        
        st.divider()
        col_test, col_save = st.columns([1, 1])
        with col_test:
            if st.button("🧪 Test Connection", key="btn_test_conn", use_container_width=True):
                with st.spinner("Pinging model..."):
                    is_ok, msg = llm_manager.test_connection(selected_model, api_key_val, api_base_val)
                    if is_ok:
                        st.success(msg)
                    else:
                        st.error(msg)
        with col_save:
            if st.button("💾 Save & Apply Credentials", type="primary", key="btn_save_conn", use_container_width=True):
                db.set_setting("llm_provider", selected_prov)
                db.set_setting("llm_model", selected_model)
                db.set_setting("llm_api_key", api_key_val)
                db.set_setting("llm_api_base", api_base_val)
                st.success("Settings saved! Reloading...")
                time.sleep(0.5)
                st.rerun()
                
    with settings_tab2:
        st.markdown("#### ✍️ Expert Prompt Studio")
        st.caption("Customize instructions sent to the AI. Available placeholders: `{report_name}`, `{timestamp_str}`, `{device_info}`, `{timezone_info}`, `{telemetry_data}`, `{reports_summary}`, `{filter_context}`.")
        
        st.markdown("**1. Single Report Diagnosis System Prompt**")
        p_single = st.text_area(
            "Instructions for single bugreport evaluation:",
            value=llm_manager.get_prompt_template("single_diagnosis"),
            height=260,
            key="prompt_single_area"
        )
        
        st.markdown("**2. Comparative Evaluation System Prompt**")
        p_comp = st.text_area(
            "Instructions for multi-report comparative synthesis:",
            value=llm_manager.get_prompt_template("comparison"),
            height=260,
            key="prompt_comp_area"
        )
        
        st.markdown("**3. Chat Assistant System Prompt**")
        p_chat = st.text_area(
            "Instructions for interactive inquiry assistant:",
            value=llm_manager.get_prompt_template("chat_assistant"),
            height=200,
            key="prompt_chat_area"
        )
        
        st.markdown("**4. Master Experiment Synthesis System Prompt**")
        p_master = st.text_area(
            "Instructions for multi-day retrospective synthesis:",
            value=llm_manager.get_prompt_template("master_synthesis"),
            height=260,
            key="prompt_master_area"
        )
        
        st.divider()
        col_psave, col_preset = st.columns([1, 1])
        with col_psave:
            if st.button("💾 Save All Prompts", type="primary", key="btn_save_prompts", use_container_width=True):
                llm_manager.set_prompt_template("single_diagnosis", p_single)
                llm_manager.set_prompt_template("comparison", p_comp)
                llm_manager.set_prompt_template("chat_assistant", p_chat)
                llm_manager.set_prompt_template("master_synthesis", p_master)
                st.success("Custom prompts saved to database!")
        with col_preset:
            if st.button("🔄 Reset Prompts to Factory Defaults", key="btn_reset_prompts", use_container_width=True):
                llm_manager.reset_prompt_templates()
                st.success("Reset all prompts to factory defaults!")
                st.rerun()
                
    with settings_tab3:
        st.markdown("#### 🌙 Night Standby & Regional Settings")
        st.caption("Configure idle analysis hours and regional timezone preferences.")
        c_n1, c_n2 = st.columns(2)
        with c_n1:
            n_start = st.number_input("Night Start Hour (24h)", min_value=0, max_value=23, value=n_start_val)
        with c_n2:
            n_end = st.number_input("Night End Hour (24h)", min_value=0, max_value=23, value=n_end_val)
            
        tz_options = ["UTC", "Europe/London", "Europe/Warsaw", "Europe/Berlin", "America/New_York", "America/Los_Angeles", "Asia/Tokyo"]
        cur_tz = db.get_setting("device_timezone", "Europe/Warsaw")
        tz_idx = tz_options.index(cur_tz) if cur_tz in tz_options else 2
        selected_tz = st.selectbox("Preferred Timezone", tz_options, index=tz_idx, key="cfg_tz_select")
        
        if st.button("Save Settings", key="btn_save_night_hours", use_container_width=True):
            db.set_setting("night_start_hour", str(n_start))
            db.set_setting("night_end_hour", str(n_end))
            db.set_setting("device_timezone", selected_tz)
            st.success("Night window and timezone updated!")
            st.rerun()

with st.sidebar:
    st.markdown("## 🔋 Battery Oracle")
    st.caption("AI-Powered Android Battery Telemetry & Diagnostics")
    
    # 1. Unified Reports & Import Section (Top of sidebar, concise & compact)
    all_reports = db.get_all_reports_summary()
    st.markdown(f"### 📁 Reports & Import ({len(all_reports)})")
    
    if all_reports:
        report_options = {r["id"]: f"{r['custom_name']} ({r['timestamp_str']})" for r in all_reports}
        if st.session_state.selected_report_id not in report_options:
            st.session_state.selected_report_id = all_reports[0]["id"]
            
        selected_idx = list(report_options.keys()).index(st.session_state.selected_report_id)
        selected_id = st.selectbox(
            "Active Report:",
            options=list(report_options.keys()),
            format_func=lambda x: report_options[x],
            index=selected_idx,
            label_visibility="collapsed"
        )
        st.session_state.selected_report_id = selected_id
    else:
        st.info("No saved reports found yet.")
        
    uploaded_files = st.file_uploader(
        "Upload new bugreport (.zip/.txt)",
        type=['zip', 'txt'],
        accept_multiple_files=True,
        key="bugreport_uploader",
        help="Upload bugreports created via 'adb bugreport bugreport.zip'"
    )
    
    st.divider()
    
    # 2. Workspace View Switcher
    st.markdown("### 🧭 Workspace View")
    view_options = ["📄 Single Report View ✨", "🔀 Merged & Compare View ✨", "📱 Device Profile & Audit ✨", "🧪 Master Experiment Synthesis ✨", "📊 Token & Cost Accounting"]
    cur_view_idx = 0
    if st.session_state.active_tab == "merged":
        cur_view_idx = 1
    elif st.session_state.active_tab == "profile":
        cur_view_idx = 2
    elif st.session_state.active_tab == "master":
        cur_view_idx = 3
    elif st.session_state.active_tab == "accounting":
        cur_view_idx = 4
        
    mode = st.radio("Select View:", view_options, index=cur_view_idx, key="mode_radio", label_visibility="collapsed")
    if "Single" in mode:
        st.session_state.active_tab = "single"
    elif "Merged" in mode:
        st.session_state.active_tab = "merged"
    elif "Device Profile" in mode:
        st.session_state.active_tab = "profile"
    elif "Master" in mode:
        st.session_state.active_tab = "master"
    else:
        st.session_state.active_tab = "accounting"
        
    st.divider()
    
    # 3. Visualization Controls
    st.markdown("### 📊 Display & Charts")
    chart_type = st.radio("Drain Chart Type", ["Bar Chart", "Pie Chart"], horizontal=True)
    show_night_shading = st.checkbox("Show 🌙 Night Shading", value=True)
    
    st.divider()
    
    # 4. LLM Engine & Configuration (Bottom)
    st.markdown("### ⚙️ Engine & Settings")
    st.info(f"**Provider:** {active_llm_cfg['provider']}\n\n**Model:** `{active_llm_cfg['model']}`\n\n**Timezone:** `{timezone}`", icon="🤖")
    
    if st.button("⚙️ Configure LLM & Prompts", use_container_width=True):
        show_llm_config_dialog(active_llm_cfg, night_start_cfg, night_end_cfg)
        
    st.caption("💡 *Tip: Run `adb bugreport bugreport.zip` in your terminal to create bug reports.*")

# --- Centered Modal Progress Dialog for Bugreport Import ---
@st.dialog("📥 Processing Android Bugreport", width="medium")
def process_upload_modal(uploaded_file, file_bytes, file_hash):
    st.caption(f"Analyzing `{uploaded_file.name}` and extracting deep batterystats telemetry...")
    progress_bar = st.progress(0, text="📦 Unpacking archive...")
    status_box = st.empty()
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        file_path = os.path.join(tmpdirname, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        target_txt = file_path
        file_timestamp = parser.parse_filename_timestamp(uploaded_file.name)
        
        # Step 1: Unzip
        progress_bar.progress(20, text=f"📦 Unzipping {uploaded_file.name}...")
        status_box.info(f"Unpacking bugreport archive: `{uploaded_file.name}`")
        if uploaded_file.name.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                for name in zip_ref.namelist():
                    if name.startswith('bugreport-') and name.endswith('.txt'):
                        zip_ref.extract(name, tmpdirname)
                        target_txt = os.path.join(tmpdirname, name)
                        file_timestamp = parser.parse_filename_timestamp(name)
                        break
                        
        # Step 2: Deep UID Extraction
        progress_bar.progress(40, text="🔍 Scanning package mappings (UIDs)...")
        status_box.info("Resolving system and user app packages...")
        uid_map = parser.extract_uid_mapping(target_txt)
        
        # Step 3: Extract Batterystats
        progress_bar.progress(60, text="⚡ Extracting power metrics & wakelocks...")
        status_box.info("Parsing estimated power use and partial wakelocks...")
        power_lines, wake_lines, device_info_str = parser.extract_batterystats(target_txt)
        
        # Safely replace UIDs with real package names using word boundaries
        power_lines = parser.replace_uids_safely(power_lines, uid_map)
        wake_lines = parser.replace_uids_safely(wake_lines, uid_map)
        
        summary_text = "Estimated Power Use:\n" + "".join(power_lines)
        summary_text += "\n\nPartial Wakelocks:\n" + "".join(wake_lines)
        chart_df = parser.extract_chart_data(power_lines, uid_map)
        
        # Step 4: Extract Timeline
        progress_bar.progress(75, text="📈 Extracting battery discharge timeline...")
        status_box.info("Parsing battery discharge timeline curves...")
        year_match = re.search(r'(\d{4})', file_timestamp)
        base_year = year_match.group(1) if year_match else "2026"
        history_df = parser.extract_battery_history(target_txt, base_year=base_year)
        
        # Step 5: Initial AI Analysis
        progress_bar.progress(85, text="🔮 Oracle is diagnosing battery telemetry...")
        status_box.info(f"Calling AI diagnostic model ({active_llm_cfg['model']})...")
        
        diag_prompt_tmpl = llm_manager.get_prompt_template("single_diagnosis")
        
        # Inject active device profile inventory if available
        active_inv_profile = db.get_latest_device_profile()
        profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
        combined_telemetry = summary_text[:30000]
        if profile_summary:
            combined_telemetry = f"{profile_summary}\n\n{combined_telemetry}"

        formatted_diag_prompt = diag_prompt_tmpl.format(
            report_name=uploaded_file.name,
            timestamp_str=file_timestamp,
            device_info=device_info_str,
            timezone_info=timezone,
            telemetry_data=combined_telemetry
        )
        
        thinking_trace = ""
        try:
            initial_analysis = llm_manager.call_llm_tracked(
                messages=[{"role": "system", "content": formatted_diag_prompt}],
                action_type="initial_diagnosis"
            )
            initial_analysis = parser.sanitize_ai_output(initial_analysis, summary_text)
            thinking_trace = f"Analyzed {len(power_lines)} power records and {len(wake_lines)} wakelocks for {device_info_str}."
        except Exception as e:
            diag_err = parse_llm_error(e)
            initial_analysis = f"### {diag_err['icon']} {diag_err['title']}\n\n**Failed during initial diagnosis import.** Category: `{diag_err['category']}`\n\n#### 💡 Suggestions:\n" + "\n".join([f"- {s}" for s in diag_err["suggestions"]]) + f"\n\n```text\n{diag_err['raw_error']}\n```"
            thinking_trace = f"AI Analysis failed: {e}"
                
        # Step 6: Save to SQLite
        progress_bar.progress(95, text="💾 Persisting report to SQLite...")
        status_box.info("Saving processed report and metrics to local database...")
        custom_name = uploaded_file.name.replace(".zip", "").replace(".txt", "")
        
        new_id = db.save_report(
            file_hash=file_hash,
            filename=uploaded_file.name,
            custom_name=custom_name,
            description="",
            timestamp_str=file_timestamp,
            device_info=device_info_str,
            summary_text=summary_text,
            chart_df=chart_df,
            history_df=history_df,
            initial_analysis=initial_analysis,
            reasoning_trace=thinking_trace
        )
        
        progress_bar.progress(100, text="✅ Import finished successfully!")
        status_box.success("🎉 Import complete! Loading report workspace...")
        st.session_state.selected_report_id = new_id
        st.session_state.active_tab = "single"
        st.session_state.upload_to_process = None
        time.sleep(1.0)
        st.rerun()

# --- Processing Uploaded Files with Centered Modal & Deduplication ---
if not uploaded_files:
    st.session_state.handled_upload_hashes.clear()
else:
    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.getvalue()
        file_hash = parser.calculate_sha256(file_bytes)
        
        if file_hash in st.session_state.handled_upload_hashes:
            continue
            
        st.session_state.handled_upload_hashes.add(file_hash)
        
        # Deduplication check against DB
        existing_report = db.get_report_by_hash(file_hash)
        if existing_report:
            st.toast(f"ℹ️ '{uploaded_file.name}' was already imported as '{existing_report['custom_name']}'. Switched to it!", icon="📁")
            st.session_state.selected_report_id = existing_report["id"]
            st.session_state.active_tab = "single"
            st.rerun()
            continue
            
        # Trigger centered modal
        process_upload_modal(uploaded_file, file_bytes, file_hash)


# Reload fresh report list
all_reports = db.get_all_reports()

def render_wifi_routers_management_ui():
    """Render the WiFi router environment management interface with AI specs discovery."""
    st.markdown("### 📡 Registered WiFi Routers & Network Access Points")
    st.caption("Register the WiFi routers and access points your phone operates around (home, office, travel). Oracle uses AI to discover your exact hardware's power-saving capabilities (DTIM interval support, 802.11ax Target Wake Time, Band Steering) and firmware navigation paths, injecting them directly into all diagnostic reports and consultation chats.")

    routers = db.get_all_wifi_routers()
    active_count = sum(1 for r in routers if r.get("is_active", 1))

    c_m1, c_m2, _ = st.columns([2, 2, 4])
    c_m1.metric("Total Routers", len(routers))
    c_m2.metric("Active in AI Context", active_count)

    # Add new router expander
    with st.expander("➕ Register New WiFi Router Profile", expanded=(len(routers) == 0)):
        st.markdown("##### Add Router & Auto-Discover Technical Specifications")
        c_r1, c_r2, c_r3 = st.columns([2, 2, 2])
        with c_r1:
            new_r_name = st.text_input("Router / Profile Name *", placeholder="e.g. Home Asus Main Router", key="new_r_name_input")
        with c_r2:
            new_brand = st.text_input("Brand / Manufacturer *", placeholder="e.g. Asus, TP-Link, AVM, Netgear, UniFi", key="new_brand_input")
        with c_r3:
            new_model = st.text_input("Model Number *", placeholder="e.g. RT-AX88U Pro, Archer AX55, FRITZ!Box 7590 AX", key="new_model_input")

        c_r4, c_r5 = st.columns([2, 4])
        with c_r4:
            new_loc = st.text_input("Location Tag", value="Home", placeholder="e.g. Home, Office, Bedroom", key="new_loc_input")
        with c_r5:
            new_notes = st.text_input("Notes / Environment Details (Optional)", placeholder="e.g. Connected on 5GHz, dual-band Smart Connect enabled", key="new_notes_input")

        # Discovery action button
        c_disc1, c_disc2 = st.columns([2.5, 3.5], vertical_alignment="center")
        with c_disc1:
            btn_discover = st.button("🔍 Auto-Discover Specs with AI", key="btn_discover_router_specs", type="secondary", use_container_width=True)
        with c_disc2:
            st.caption("AI analyzes official hardware datasheets and admin UI navigation for this exact model.")

        if btn_discover:
            if not new_brand.strip() or not new_model.strip():
                st.error("Please provide both Brand and Model before running AI discovery.")
            else:
                with st.spinner(f"Querying AI knowledge base for {new_brand} {new_model} technical specs & firmware UI..."):
                    discovered_specs, disc_err = llm_manager.discover_router_specs(new_brand.strip(), new_model.strip())
                    if disc_err:
                        st.warning(f"Note: AI generated baseline specs ({disc_err})")
                    st.session_state["discovered_router_specs"] = discovered_specs

        # If specs exist in session state, display editable preview
        specs_to_save = st.session_state.get("discovered_router_specs")
        if specs_to_save:
            st.markdown("###### Discovered Hardware Specifications & Firmware Navigation")
            with st.container(border=True):
                col_sp1, col_sp2 = st.columns(2)
                with col_sp1:
                    edit_gen = st.text_input("Wi-Fi Generation", value=specs_to_save.get("wifi_generation", "Wi-Fi 6 (802.11ax)"), key="edit_disc_gen")
                    edit_dtim = st.text_input("DTIM Interval Support", value=specs_to_save.get("dtim_support", "Configurable"), key="edit_disc_dtim")
                    edit_fw = st.text_input("Firmware Family", value=specs_to_save.get("firmware_family", f"{new_brand} Firmware"), key="edit_disc_fw")
                with col_sp2:
                    edit_twt = st.text_input("Target Wake Time (TWT)", value=specs_to_save.get("twt_support", "Supported"), key="edit_disc_twt")
                    edit_band = st.text_input("Band Steering / Smart Connect", value=specs_to_save.get("band_steering", "Supported"), key="edit_disc_band")
                    edit_path = st.text_input("Firmware Path to Settings", value=specs_to_save.get("firmware_path", "Wireless > Professional"), key="edit_disc_path")
                
                edit_sum = st.text_area("Power Efficiency Summary", value=specs_to_save.get("summary", ""), height=70, key="edit_disc_sum")
                
                specs_to_save = {
                    "wifi_generation": edit_gen,
                    "firmware_family": edit_fw,
                    "dtim_support": edit_dtim,
                    "twt_support": edit_twt,
                    "band_steering": edit_band,
                    "firmware_path": edit_path,
                    "summary": edit_sum
                }

        c_save, _ = st.columns([2, 4])
        with c_save:
            if st.button("💾 Save Router Profile", key="btn_save_new_router", type="primary", use_container_width=True):
                if not new_r_name.strip() or not new_brand.strip() or not new_model.strip():
                    st.error("Please fill in Router Name, Brand, and Model.")
                else:
                    final_specs = specs_to_save if specs_to_save else {
                        "wifi_generation": "Wi-Fi 6 (802.11ax)",
                        "firmware_family": f"{new_brand.strip()} Firmware",
                        "dtim_support": "Configurable (Recommended: DTIM Interval = 3)",
                        "twt_support": "Supported if 802.11ax",
                        "band_steering": "Smart Connect / Band Steering",
                        "firmware_path": "Wireless > Advanced / Professional Settings",
                        "summary": f"{new_brand.strip()} {new_model.strip()} wireless network."
                    }
                    db.save_wifi_router(
                        router_name=new_r_name.strip(),
                        brand=new_brand.strip(),
                        model=new_model.strip(),
                        specs_json=final_specs,
                        location_tag=new_loc.strip() or "Home",
                        is_active=1,
                        notes=new_notes.strip()
                    )
                    st.session_state.pop("discovered_router_specs", None)
                    st.success(f"Router '{new_r_name.strip()}' saved successfully!")
                    st.rerun()

    st.divider()

    # Router list
    if not routers:
        st.info("No WiFi routers registered yet. Add your router above so Oracle can personalize battery diagnoses with your exact network hardware!")
        return

    st.markdown(f"#### 📋 Registered Routers ({len(routers)})")
    for r in routers:
        specs = r.get("specs", {})
        is_act = bool(r.get("is_active", 1))
        with st.container(border=True):
            head_col1, head_col2, head_col3 = st.columns([5, 2.5, 1.2], vertical_alignment="center")
            with head_col1:
                active_badge = "🟢 **Active in AI Context**" if is_act else "⚪ **Inactive (Ignored by AI)**"
                st.markdown(f"##### 📡 {r['router_name']} &nbsp;•&nbsp; {active_badge}")
                st.caption(f"**Hardware:** {r['brand']} {r['model']} &nbsp;|&nbsp; 📍 **Location:** `{r.get('location_tag', 'Home')}` &nbsp;|&nbsp; 🕒 **Updated:** `{r.get('updated_at', '')[:16]}`")
            with head_col2:
                new_act = st.checkbox("Active for AI Reports", value=is_act, key=f"chk_act_router_{r['id']}")
                if new_act != is_act:
                    db.update_wifi_router_active(r["id"], new_act)
                    st.rerun()
            with head_col3:
                with st.popover("🗑️ Delete", use_container_width=True):
                    st.warning(f"Delete router '{r['router_name']}'?")
                    if st.button("Confirm Delete", key=f"btn_del_router_{r['id']}", type="primary", use_container_width=True):
                        db.delete_wifi_router(r["id"])
                        st.rerun()

            # Spec Badges / KPIs
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("📶 Standard", specs.get("wifi_generation", "Wi-Fi 6"))
            k2.metric("⚙️ Firmware OS", specs.get("firmware_family", "Vendor Default"))
            dtim_val = specs.get("dtim_support", "Configurable")
            k3.metric("⏱️ DTIM Interval", dtim_val[:22] + "..." if len(dtim_val) > 22 else dtim_val)
            twt_val = specs.get("twt_support", "Supported")
            k4.metric("🎯 Target Wake Time", twt_val[:22] + "..." if len(twt_val) > 22 else twt_val)

            st.markdown(f"🧭 **Firmware Navigation Path for Power Tuning:** `{specs.get('firmware_path', 'Wireless > Advanced')}`")
            if specs.get("summary"):
                st.caption(f"💡 **AI Hardware Analysis:** {specs['summary']}")
            if r.get("notes"):
                st.info(f"📝 **Environment Notes:** {r['notes']}")

            with st.expander("✏️ Edit Details & Re-Run AI Discovery", expanded=False):
                e_c1, e_c2, e_c3 = st.columns([2, 2, 2])
                with e_c1:
                    e_name = st.text_input("Router Name:", value=r["router_name"], key=f"e_name_{r['id']}")
                with e_c2:
                    e_brand = st.text_input("Brand:", value=r["brand"], key=f"e_brand_{r['id']}")
                with e_c3:
                    e_model = st.text_input("Model:", value=r["model"], key=f"e_model_{r['id']}")

                e_c4, e_c5 = st.columns([2, 4])
                with e_c4:
                    e_loc = st.text_input("Location:", value=r.get("location_tag", "Home"), key=f"e_loc_{r['id']}")
                with e_c5:
                    e_notes = st.text_input("Notes:", value=r.get("notes", ""), key=f"e_notes_{r['id']}")

                e_c_btn1, e_c_btn2 = st.columns([2.5, 3.5])
                with e_c_btn1:
                    if st.button("🔍 Refresh Specs with AI", key=f"btn_refresh_specs_{r['id']}"):
                        with st.spinner(f"Discovering specs for {e_brand} {e_model}..."):
                            new_disc, _ = llm_manager.discover_router_specs(e_brand, e_model)
                            db.save_wifi_router(
                                router_id=r["id"],
                                router_name=e_name.strip(),
                                brand=e_brand.strip(),
                                model=e_model.strip(),
                                specs_json=new_disc,
                                location_tag=e_loc.strip(),
                                is_active=1 if is_act else 0,
                                notes=e_notes.strip()
                            )
                            st.success("Refreshed specs with AI!")
                            st.rerun()
                with e_c_btn2:
                    if st.button("Save Profile Edits", key=f"btn_save_edits_{r['id']}", type="primary"):
                        db.save_wifi_router(
                            router_id=r["id"],
                            router_name=e_name.strip(),
                            brand=e_brand.strip(),
                            model=e_model.strip(),
                            specs_json=specs,
                            location_tag=e_loc.strip(),
                            is_active=1 if is_act else 0,
                            notes=e_notes.strip()
                        )
                        st.success("Router profile updated!")
                        st.rerun()

# ==============================================================================
# VIEW 1: SINGLE REPORT VIEW
# ==============================================================================
if st.session_state.active_tab == "single":
    if not all_reports:
        st.title("🔋 Battery Oracle")
        st.info("👋 Welcome! Please upload an Android bugreport (`.zip` or `.txt`) using the sidebar to begin.")
    else:
        active_report = db.get_report_by_id(st.session_state.selected_report_id)
        if not active_report:
            active_report = all_reports[0]
            st.session_state.selected_report_id = active_report["id"]
            
        rep_id = active_report["id"]
        
        # --- Top Header & Metadata Badges ---
        col_title, col_actions = st.columns([5, 3])
        with col_title:
            st.markdown(f"## 📱 {active_report['custom_name']}")
        
        with col_actions:
            # Side-by-side action buttons aligned with title
            act_col1, act_col2 = st.columns([1, 1])
            with act_col1:
                with st.popover("✏️ Edit Notes", use_container_width=True):
                    new_name = st.text_input("Report Name", value=active_report["custom_name"], key=f"name_{rep_id}")
                    new_desc = st.text_area("Description / Notes", value=active_report.get("description", ""), placeholder="e.g., 5G disabled, bedtime standby...", key=f"desc_{rep_id}")
                    if st.button("Save Changes", key=f"save_meta_{rep_id}", use_container_width=True):
                        db.update_report_metadata(rep_id, new_name, new_desc)
                        st.success("Updated!")
                        st.rerun()
            with act_col2:
                if st.button("🗑️ Delete", type="secondary", key=f"del_btn_{rep_id}", use_container_width=True):
                    st.session_state.confirm_delete_id = rep_id
                    
            if st.session_state.confirm_delete_id == rep_id:
                st.warning("Are you sure you want to delete this report?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Yes, Delete", type="primary", key="confirm_del", use_container_width=True):
                        db.delete_report(rep_id)
                        st.session_state.confirm_delete_id = None
                        st.session_state.selected_report_id = None
                        st.success("Report deleted.")
                        st.rerun()
                with col_no:
                    if st.button("Cancel", key="cancel_del", use_container_width=True):
                        st.session_state.confirm_delete_id = None
                        st.rerun()
                        
        st.caption(f"📁 **Source:** `{active_report['filename']}` | 🕒 **Captured:** {active_report['timestamp_str']}")
        if active_report.get('device_info'):
            st.info(f"⚙️ **Device Profile:** {active_report['device_info']}", icon="ℹ️")
                        
        if active_report.get("description"):
            st.markdown(f"📝 **Notes:** *{active_report['description']}*")
            
        st.divider()
        
        # --- TIME WINDOW & FOCUS FILTER BAR ---
        st.markdown("### 🎯 Analysis Scope & Time Filter")
        scope_col1, scope_col2 = st.columns([2, 3])
        
        with scope_col1:
            filter_mode_choice = st.radio(
                "Filter Scope:",
                ["🌐 Full Session", "🌙 Night Standby (Preset)", "⏱️ Custom Window", "📴 Screen-Off Only"],
                horizontal=True,
                key=f"scope_radio_{rep_id}"
            )
            
        raw_hist_df = active_report.get("history_data")
        has_history = raw_hist_df is not None and not raw_hist_df.empty and "Time" in raw_hist_df.columns
        
        if has_history:
            min_t = raw_hist_df["Time"].min()
            max_t = raw_hist_df["Time"].max()
            min_dt = min_t.to_pydatetime()
            max_dt = max_t.to_pydatetime()
        else:
            min_dt = datetime(2026, 9, 1, 0, 0)
            max_dt = datetime(2026, 9, 1, 23, 59)

        # Expand max_dt to include bugreport capture timestamp if present
        cap_str = active_report.get("timestamp_str", "")
        if cap_str:
            cap_parts = re.split(r'[\s\-_:]+', cap_str.strip())
            if len(cap_parts) >= 5:
                sec_str = cap_parts[5] if len(cap_parts) >= 6 else '00'
                try:
                    cap_dt = pd.to_datetime(f"{cap_parts[0]}-{cap_parts[1]}-{cap_parts[2]} {cap_parts[3]}:{cap_parts[4]}:{sec_str}").to_pydatetime()
                    if cap_dt > max_dt:
                        max_dt = cap_dt
                except Exception:
                    pass
            
        start_dt, end_dt = min_dt, max_dt
        sliced_df = raw_hist_df
        filter_mode = "full"

        if "Night Standby" in filter_mode_choice:
            filter_mode = "night"
            if has_history:
                auto_s_dt, auto_e_dt = parser.get_latest_night_window(min_dt, max_dt, night_start_cfg, night_end_cfg)
                if hasattr(auto_s_dt, "to_pydatetime"):
                    auto_s_dt = auto_s_dt.to_pydatetime()
                if hasattr(auto_e_dt, "to_pydatetime"):
                    auto_e_dt = auto_e_dt.to_pydatetime()

                # Check database persistent override first, then session state
                db_c_s = active_report.get("custom_night_start")
                db_c_e = active_report.get("custom_night_end")
                init_s = db_c_s if (db_c_s and db_c_e) else auto_s_dt
                init_e = db_c_e if (db_c_s and db_c_e) else auto_e_dt
                
                night_key = f"night_bounds_{rep_id}"
                if night_key not in st.session_state:
                    st.session_state[night_key] = (init_s, init_e)
                    
                cur_s_dt, cur_e_dt = st.session_state[night_key]
                if hasattr(cur_s_dt, "to_pydatetime"):
                    cur_s_dt = cur_s_dt.to_pydatetime()
                if hasattr(cur_e_dt, "to_pydatetime"):
                    cur_e_dt = cur_e_dt.to_pydatetime()

                # Ensure within min_dt and max_dt bounds
                cur_s_dt = max(min_dt, min(max_dt, cur_s_dt))
                cur_e_dt = max(min_dt, min(max_dt, cur_e_dt))
                if cur_s_dt >= cur_e_dt:
                    cur_s_dt, cur_e_dt = auto_s_dt, auto_e_dt

                start_dt, end_dt = cur_s_dt, cur_e_dt
                if hasattr(start_dt, "to_pydatetime"):
                    start_dt = start_dt.to_pydatetime()
                if hasattr(end_dt, "to_pydatetime"):
                    end_dt = end_dt.to_pydatetime()
                if hasattr(min_dt, "to_pydatetime"):
                    min_dt = min_dt.to_pydatetime()
                if hasattr(max_dt, "to_pydatetime"):
                    max_dt = max_dt.to_pydatetime()

                sliced_df = parser.slice_timeline_range(raw_hist_df, start_dt, end_dt)
                
                is_custom_saved = (db_c_s is not None and db_c_e is not None) or (start_dt != auto_s_dt or end_dt != auto_e_dt)
                custom_badge = " *(Saved custom sleep interval active)*" if is_custom_saved else f" *(Default preset: {night_start_cfg:02d}:00 to {night_end_cfg:02d}:00)*"
                
                with scope_col2:
                    st.info(f"🌙 **Targeted Overnight Interval:** `{start_dt.strftime('%Y-%m-%d %H:%M')}` → `{end_dt.strftime('%Y-%m-%d %H:%M')}` (Duration: {(end_dt - start_dt).total_seconds()/3600:.1f} hrs)\n\n{custom_badge}")
                    with st.expander("⏱️ Adjust Night Sleep/Wake Window for this Report", expanded=False):
                        st.caption("Specify your bedtime (evening/night) and wake-up time (morning). Changes are permanently saved for this report:")
                        
                        col_t1, col_t2 = st.columns(2)
                        with col_t1:
                            in_bed = st.time_input("🌙 Bedtime (Start):", value=start_dt.time(), key=f"t_bed_{rep_id}")
                        with col_t2:
                            in_wake = st.time_input("☀️ Wake-up (End):", value=end_dt.time(), key=f"t_wake_{rep_id}")

                        # Calculate candidate start and end datetimes based on selected time
                        # Wake time is on the last morning of the bugreport (end_dt's date or max_dt's date)
                        wake_date = max_dt.date()
                        new_cand_end = datetime.combine(wake_date, in_wake)
                        # If bedtime hour is greater than wake-up hour (crosses midnight, e.g. 21:55 -> 07:22)
                        if in_bed > in_wake:
                            new_cand_start = datetime.combine(wake_date - pd.Timedelta(days=1), in_bed)
                        else:
                            new_cand_start = datetime.combine(wake_date, in_bed)

                        # Clamp to available dataset bounds
                        new_cand_start = max(min_dt, min(max_dt, new_cand_start))
                        new_cand_end = max(min_dt, min(max_dt, new_cand_end))

                        btn_c1, btn_c2 = st.columns([1, 1])
                        with btn_c1:
                            if st.button("💾 Apply & Save Window", key=f"save_night_{rep_id}", type="primary"):
                                if new_cand_start < new_cand_end:
                                    db.update_report_night_window(rep_id, new_cand_start, new_cand_end)
                                    active_report["custom_night_start"] = new_cand_start
                                    active_report["custom_night_end"] = new_cand_end
                                    st.session_state[night_key] = (new_cand_start, new_cand_end)
                                    st.session_state[f"m_night_{rep_id}"] = (new_cand_start, new_cand_end)
                                    st.rerun()
                                else:
                                    st.error("Bedtime must be earlier than Wake-up time.")
                        with btn_c2:
                            if st.button("↺ Reset to Detected Window", key=f"rst_night_{rep_id}"):
                                db.update_report_night_window(rep_id, None, None)
                                active_report["custom_night_start"] = None
                                active_report["custom_night_end"] = None
                                st.session_state[night_key] = (auto_s_dt, auto_e_dt)
                                st.session_state[f"m_night_{rep_id}"] = (auto_s_dt, auto_e_dt)
                                st.session_state.pop(f"t_bed_{rep_id}", None)
                                st.session_state.pop(f"t_wake_{rep_id}", None)
                                st.rerun()
        elif "Custom Window" in filter_mode_choice:
            filter_mode = "custom"
            with scope_col2:
                if has_history and min_dt < max_dt:
                    slider_val = st.slider(
                        "Drag custom window range (supports spanning across midnight):",
                        min_value=min_dt,
                        max_value=max_dt,
                        value=(min_dt, max_dt),
                        format="MM-DD HH:mm",
                        key=f"custom_slider_{rep_id}"
                    )
                    start_dt, end_dt = slider_val[0], slider_val[1]
                    sliced_df = parser.slice_timeline_range(raw_hist_df, start_dt, end_dt)
                else:
                    st.caption("Timeline history not sufficient for range slider.")
        elif "Screen-Off" in filter_mode_choice:
            filter_mode = "screen_off"
            with scope_col2:
                st.info("📴 **Screen-Off Standby Focus:** Evaluates energy consumed exclusively when the display was turned off/dozing.")
            sliced_df = raw_hist_df
        else:
            filter_mode = "full"
            with scope_col2:
                st.caption(f"Showing entire recorded bugreport session ({min_dt.strftime('%Y-%m-%d %H:%M')} to {max_dt.strftime('%Y-%m-%d %H:%M')}).")
            
        # Compute Sliced Timeline & KPIs
        kpis = parser.compute_window_kpis(sliced_df)
        
        # Display Targeted KPI Cards
        st.markdown(f"**Window Health: {kpis['status']}**")
        kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
        kpi_c1.metric("Window Interval", f"{kpis['start_time']} → {kpis['end_time']}")
        kpi_c2.metric("Battery Levels", f"{kpis['start_level']}% → {kpis['end_level']}%")
        kpi_c3.metric("Total Drop", f"{kpis['drop_pct']}% ({kpis['duration_hrs']:.1f} hrs)")
        kpi_c4.metric("Discharge Rate", f"{kpis['rate_per_hr']:.2f}% / hr")
        
        st.divider()

        # Two dedicated top-level tabs: Report vs Full-Screen Chat
        tab_single_report, tab_single_chat = st.tabs([
            "📊 Telemetry, Charts & Diagnosis Report",
            "💬 AI Investigation Chat ✨"
        ])

        with tab_single_report:
            # --- Visualizations Section ---
            chart_col1, chart_col2 = st.columns([1, 1])
            
            # 1. Timeline Chart
            with chart_col1:
                st.markdown("#### 📈 Battery Level Timeline")
                if sliced_df is not None and not sliced_df.empty and "Time" in sliced_df.columns and "Level" in sliced_df.columns:
                    title_suffix = f"({filter_mode_choice})" if filter_mode != "full" else ""
                    fig_hist = px.line(
                        sliced_df, x='Time', y='Level',
                        title=f"Discharge Curve {title_suffix}",
                        labels={"Level": "Battery Level (%)", "Time": "Device Time"}
                    )
                    fig_hist.update_yaxes(range=[0, 105])
                    fig_hist.update_traces(line=dict(width=2.5, color="#3b82f6"))
                    if show_night_shading:
                        if filter_mode == "night" and start_dt and end_dt:
                            fig_hist.add_vrect(
                                x0=start_dt, x1=end_dt,
                                fillcolor="rgba(30, 41, 59, 0.20)",
                                layer="below",
                                line_width=0,
                                annotation_text="🌙 Night",
                                annotation_position="top left",
                                annotation_font_size=10,
                                annotation_font_color="gray"
                            )
                        else:
                            fig_hist = add_night_shading(fig_hist, sliced_df, night_start=night_start_cfg, night_end=night_end_cfg)
                    st.plotly_chart(fig_hist, use_container_width=True, key=f"hist_single_{rep_id}_{filter_mode}")
                else:
                    st.info("No timeline data matches this filter.")
                    
            # 2. Drain Breakdown Chart & Web Search Tool
            with chart_col2:
                st.markdown("#### ⚡ Power Consumers & App Research")
                standby_df = parser.extract_screen_off_chart_data(active_report.get("summary_text", ""))
                
                if filter_mode in ["night", "screen_off"] and standby_df is not None and not standby_df.empty:
                    df_to_plot = parser.clean_chart_dataframe(standby_df, active_report.get("summary_text", ""))
                    fig_pie = px.pie(
                        df_to_plot, values='mAh', names='Component',
                        title=f"Standby Power Drain Breakdown (mAh - {filter_mode_choice})",
                        hole=0.4
                    )
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_single_{rep_id}_{filter_mode}")
                elif active_report.get("chart_data") is not None and not active_report["chart_data"].empty:
                    df_to_plot = parser.clean_chart_dataframe(active_report["chart_data"], active_report.get("summary_text", ""))
                    fig_pie = px.pie(
                        df_to_plot, values='mAh', names='Component',
                        title="Estimated Full-Session Power Drain Breakdown (mAh)",
                        hole=0.4
                    )
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_single_full_{rep_id}")
                else:
                    st.info("No breakdown data available for this view.")
                    
            st.divider()
            
            # --- AI Diagnosis Section ---
            st.markdown('### ✨ Oracle Diagnosis <span class="ai-badge">✨ AI GENERATED</span>', unsafe_allow_html=True)
            
            diag_cache_key = f"diag_{rep_id}_{filter_mode}"
            if filter_mode == "full":
                active_diagnosis = active_report.get("initial_analysis", "No baseline analysis available.")
                diag_subtitle = "🌐 Full Session Baseline Diagnosis"
            else:
                cached_filtered = db.get_setting(diag_cache_key)
                if cached_filtered:
                    active_diagnosis = cached_filtered
                    diag_subtitle = f"🎯 Targeted Scope Diagnosis: {filter_mode_choice}"
                else:
                    active_diagnosis = None
                    diag_subtitle = f"⏳ Targeted Scope: {filter_mode_choice} (Not yet generated)"
                    
            # Action Command Bar: Primary trigger + export button on left, status on right/inline
            diag_action_key = f"diag_{rep_id}_{filter_mode}"
            btn_label = "🔄 Re-Diagnose" if active_diagnosis else f"✨ Generate Targeted Diagnosis"
            
            c_diag_act1, c_diag_act2, c_diag_status = st.columns([1.5, 1.3, 3], vertical_alignment="center")
            with c_diag_act1:
                if st.button(btn_label, key=f"btn_diag_{rep_id}_{filter_mode}", type="primary" if not active_diagnosis else "secondary", use_container_width=True):
                    confirm_ai_analysis_dialog(
                        action_key=diag_action_key,
                        action_title=f"{'Re-Diagnose' if active_diagnosis else 'Generate Targeted Diagnosis'}: {filter_mode_choice}",
                        target_desc=f"Run an AI evaluation for **{active_report['custom_name']}** under the **{filter_mode_choice}** filter window.",
                        details_dict={
                            "Bugreport": active_report["custom_name"],
                            "Scope Window": f"{kpis['start_time']} → {kpis['end_time']}",
                            "Battery Drop / Rate": f"{kpis['drop_pct']}% ({kpis['rate_per_hr']:.2f}%/hr)",
                            "Device Info": active_report.get("device_info", "Unknown")
                        },
                        action_type="single_diagnosis",
                        action_payload={
                            "rep_id": rep_id,
                            "filter_mode": filter_mode,
                            "filter_mode_choice": filter_mode_choice,
                            "diag_cache_key": diag_cache_key,
                            "timezone": timezone,
                            "kpis": kpis
                        }
                    )
            with c_diag_act2:
                if active_diagnosis:
                    md_content = build_single_report_markdown(active_report, filter_mode, kpis, active_diagnosis)
                    st.download_button(
                        label="📥 Export Report (.md)",
                        data=md_content,
                        file_name=f"{active_report['custom_name']}_{filter_mode}_diagnosis.md",
                        mime="text/markdown",
                        key=f"dl_single_md_{rep_id}_{filter_mode}",
                        use_container_width=True
                    )
            with c_diag_status:
                st.caption(f"**Current Scope:** {diag_subtitle}")
                            
            # Render any captured diagnosis error at full width below the action bar
            if st.session_state.get(f"err_diag_{rep_id}"):
                err_obj, err_act = st.session_state[f"err_diag_{rep_id}"]
                render_ai_error(err_obj, action_description=err_act, key_suffix=f"diag_{rep_id}")

            if active_diagnosis:
                render_ai_block(active_diagnosis, key_suffix=f"single_{rep_id}_{filter_mode}")
            else:
                st.info(f"💡 You have selected **{filter_mode_choice}** (Window: {kpis['start_time']} → {kpis['end_time']}, Drop: {kpis['drop_pct']}%, Rate: {kpis['rate_per_hr']:.2f}%/hr).\n\nClick **'{btn_label}'** above to generate an AI diagnosis focused strictly on standby drain, wakelocks, and unoptimized background processes for this window.")
                with st.expander("📄 View Full Session Baseline Diagnosis for Reference", expanded=False):
                    render_ai_block(active_report.get("initial_analysis", "No baseline analysis available."), key_suffix=f"single_base_{rep_id}")
                    
            with st.expander("🔍 View Telemetry Snippet & Diagnostic Trace", expanded=False):
                if active_report.get("reasoning_trace"):
                    st.caption(f"**Diagnostic Trace:** {active_report['reasoning_trace']}")
                st.text_area("Batterystats Excerpt", active_report["summary_text"][:2500], height=200, disabled=True)

        with tab_single_chat:
            # --- FULL-SCREEN AI CHAT WORKSPACE (FRAGMENT ISOLATED) ---
            filter_label_single = f"{filter_mode_choice} ({kpis['start_time']} -> {kpis['end_time']})"
            def _build_single_sys_prompt():
                filtered_telemetry = parser.get_filtered_telemetry_for_llm(active_report["summary_text"], filter_mode, kpis)
                active_inv_profile = db.get_latest_device_profile()
                profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
                if profile_summary:
                    filtered_telemetry = f"{profile_summary}\n\n{filtered_telemetry}"
                active_routers = db.get_active_wifi_routers()
                router_summary = parser.format_router_context_for_llm(active_routers)
                if router_summary:
                    filtered_telemetry = f"{router_summary}\n\n{filtered_telemetry}"

                chat_tmpl = llm_manager.get_prompt_template("chat_assistant")
                return chat_tmpl.format(
                    filter_context=f"Active Scope: {filter_label_single} | Discharge Rate: {kpis['rate_per_hr']:.2f}%/hr | Status: {kpis['status']}",
                    report_name=active_report["custom_name"],
                    device_info=active_report.get("device_info", "Unknown"),
                    timestamp_str=active_report["timestamp_str"],
                    description=active_report.get("description", ""),
                    telemetry_data=filtered_telemetry
                )

            render_ai_chat_panel(
                scope_key=f"single_{rep_id}",
                panel_title=f"Session Telemetry Chat • {active_report['custom_name']}",
                scope_badge=f"🎯 Scope: {filter_mode_choice}",
                report_id=rep_id,
                active_thread_state_key="active_thread_id",
                sys_prompt_builder=_build_single_sys_prompt,
                action_type="chat",
                filter_label=filter_label_single
            )

# ==============================================================================
# VIEW 2: MERGED & COMPARE ALL REPORTS VIEW
# ==============================================================================
elif st.session_state.active_tab == "merged":
    st.markdown("## 🔀 Multi-Report Comparison & Merged Workspace")
    st.caption("Compare battery discharge curves, evaluate optimization changes, and isolate multi-day patterns.")
    
    if len(all_reports) < 2:
        st.warning("⚠️ You need at least 2 saved bugreports in the database to run a comparative analysis.")
        if all_reports:
            st.info(f"Currently saved: **{all_reports[0]['custom_name']}**. Upload a second bugreport using the sidebar to compare.")
    else:
        report_dict = {r["id"]: r for r in all_reports}
        selected_ids = st.multiselect(
            "Select reports to compare:",
            options=list(report_dict.keys()),
            default=list(report_dict.keys()),
            format_func=lambda x: f"{report_dict[x]['custom_name']} ({report_dict[x]['timestamp_str']})"
        )
        
        if len(selected_ids) >= 2:
            compared_reports = [report_dict[rid] for rid in selected_ids]
            
            # --- Scope Filter for Merged Comparison ---
            st.markdown("### 🎯 Comparative Analysis Scope & Filter")
            m_scope_col1, m_scope_col2 = st.columns([2, 3])
            with m_scope_col1:
                merged_filter_choice = st.radio(
                    "Comparative Scope:",
                    ["🌐 Full Session", "🌙 Night Standby (Preset)", "⏱️ Custom Window", "📴 Screen-Off Only"],
                    horizontal=True,
                    key="merged_scope_radio"
                )

            merged_filter_mode = "full"
            if "Night Standby" in merged_filter_choice:
                merged_filter_mode = "night"
                with m_scope_col2:
                    st.info(f"🌙 **Targeted Overnight Interval:** Analyzing sleep windows ({night_start_cfg:02d}:00 to {night_end_cfg:02d}:00) across all selected bugreports.")
                    with st.expander("⏱️ Adjust Per-Report Night Sleep/Wake Intervals", expanded=False):
                        st.caption("Fine-tune the exact bedtime and wake-up boundaries individually for each compared day. Changes are permanently saved:")
                        for r in compared_reports:
                            df_h_r = r.get("history_data")
                            if df_h_r is not None and not df_h_r.empty and "Time" in df_h_r.columns:
                                r_min_t = df_h_r["Time"].min()
                                r_max_t = df_h_r["Time"].max()
                                r_min_dt = r_min_t.to_pydatetime() if hasattr(r_min_t, "to_pydatetime") else r_min_t
                                r_max_dt = r_max_t.to_pydatetime() if hasattr(r_max_t, "to_pydatetime") else r_max_t

                                # Expand r_max_dt to include bugreport capture timestamp if present
                                r_cap_str = r.get("timestamp_str", "")
                                if r_cap_str:
                                    r_cap_parts = re.split(r'[\s\-_:]+', r_cap_str.strip())
                                    if len(r_cap_parts) >= 5:
                                        r_sec_str = r_cap_parts[5] if len(r_cap_parts) >= 6 else '00'
                                        try:
                                            r_cap_dt = pd.to_datetime(f"{r_cap_parts[0]}-{r_cap_parts[1]}-{r_cap_parts[2]} {r_cap_parts[3]}:{r_cap_parts[4]}:{r_sec_str}").to_pydatetime()
                                            if r_cap_dt > r_max_dt:
                                                r_max_dt = r_cap_dt
                                        except Exception:
                                            pass
                                
                                r_auto_s, r_auto_e = parser.get_latest_night_window(r_min_dt, r_max_dt, night_start_cfg, night_end_cfg)
                                if hasattr(r_auto_s, "to_pydatetime"):
                                    r_auto_s = r_auto_s.to_pydatetime()
                                if hasattr(r_auto_e, "to_pydatetime"):
                                    r_auto_e = r_auto_e.to_pydatetime()
                                    
                                db_c_s = r.get("custom_night_start")
                                db_c_e = r.get("custom_night_end")
                                def_s = db_c_s if (db_c_s and db_c_e) else r_auto_s
                                def_e = db_c_e if (db_c_s and db_c_e) else r_auto_e

                                r_ov_key = f"m_night_{r['id']}"
                                if r_ov_key not in st.session_state:
                                    st.session_state[r_ov_key] = (def_s, def_e)
                                    
                                cur_s, cur_e = st.session_state[r_ov_key]
                                if hasattr(cur_s, "to_pydatetime"):
                                    cur_s = cur_s.to_pydatetime()
                                if hasattr(cur_e, "to_pydatetime"):
                                    cur_e = cur_e.to_pydatetime()
                                    
                                # Guarantee bounds
                                cur_s = max(r_min_dt, min(r_max_dt, cur_s))
                                cur_e = max(r_min_dt, min(r_max_dt, cur_e))
                                
                                is_custom = (db_c_s is not None and db_c_e is not None) or (cur_s != r_auto_s or cur_e != r_auto_e)
                                badge_txt = " *(Custom saved)*" if is_custom else ""

                                st.markdown(f"**{r['custom_name']}** ({r['timestamp_str']}){badge_txt}")
                                mc1, mc2, mc3, mc4 = st.columns([2.5, 2.5, 1.5, 1.5])
                                with mc1:
                                    m_bed = st.time_input("🌙 Bedtime:", value=cur_s.time(), key=f"t_m_bed_{r['id']}")
                                with mc2:
                                    m_wake = st.time_input("☀️ Wake-up:", value=cur_e.time(), key=f"t_m_wake_{r['id']}")

                                m_wake_date = r_max_dt.date()
                                if m_bed > m_wake:
                                    m_cand_s = datetime.combine(m_wake_date - pd.Timedelta(days=1), m_bed)
                                else:
                                    m_cand_s = datetime.combine(m_wake_date, m_bed)
                                m_cand_e = datetime.combine(m_wake_date, m_wake)
                                m_cand_s = max(r_min_dt, min(r_max_dt, m_cand_s))
                                m_cand_e = max(r_min_dt, min(r_max_dt, m_cand_e))

                                with mc3:
                                    st.write("")
                                    if st.button("💾 Apply", key=f"btn_save_m_{r['id']}", type="primary", help="Save sleep interval"):
                                        if m_cand_s < m_cand_e:
                                            db.update_report_night_window(r['id'], m_cand_s, m_cand_e)
                                            r["custom_night_start"] = m_cand_s
                                            r["custom_night_end"] = m_cand_e
                                            st.session_state[r_ov_key] = (m_cand_s, m_cand_e)
                                            st.session_state[f"night_bounds_{r['id']}"] = (m_cand_s, m_cand_e)
                                            st.rerun()
                                        else:
                                            st.error("Invalid interval")
                                with mc4:
                                    st.write("")
                                    if st.button("↺ Reset", key=f"btn_rst_m_{r['id']}", help="Reset to auto-detected preset"):
                                        db.update_report_night_window(r['id'], None, None)
                                        r["custom_night_start"] = None
                                        r["custom_night_end"] = None
                                        st.session_state[r_ov_key] = (r_auto_s, r_auto_e)
                                        st.session_state[f"night_bounds_{r['id']}"] = (r_auto_s, r_auto_e)
                                        st.session_state.pop(f"t_m_bed_{r['id']}", None)
                                        st.session_state.pop(f"t_m_wake_{r['id']}", None)
                                        st.rerun()
            elif "Custom Window" in merged_filter_choice:
                merged_filter_mode = "custom"
                with m_scope_col2:
                    st.caption("Comparing customized window intervals across the loaded reports.")
            elif "Screen-Off" in merged_filter_choice:
                merged_filter_mode = "screen_off"
                with m_scope_col2:
                    st.info("📴 **Screen-Off Standby Focus:** Comparing idle battery loss consumed specifically while displays were turned off/dozing.")
            else:
                merged_filter_mode = "full"
                with m_scope_col2:
                    st.caption("Comparing full recorded bugreport durations.")
                    
            st.divider()

            # Two dedicated top-level tabs: Comparison Charts & Report vs Full-Screen Chat
            tab_comp_report, tab_comp_chat = st.tabs([
                "📊 Comparison Charts & Synthesis Report",
                "💬 Comparative AI Chat ✨"
            ])

            with tab_comp_report:
                # --- 1. Merged Timeline Chart ---
                st.markdown("### 📈 Merged Battery Level Timelines")
                fig_merged = go.Figure()
                colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]
                all_times = []
                
                for idx, rep in enumerate(compared_reports):
                    _, _, plot_df = get_effective_bounds(rep, merged_filter_mode)
                    if not plot_df.empty and "Time" in plot_df.columns and "Level" in plot_df.columns:
                        all_times.extend(plot_df["Time"].tolist())
                        fig_merged.add_trace(go.Scatter(
                            x=plot_df["Time"],
                            y=plot_df["Level"],
                            mode='lines',
                            name=f"{rep['custom_name']} ({'🌙 Night' if merged_filter_mode == 'night' else 'Full'})",
                            line=dict(width=2.5, color=colors[idx % len(colors)])
                        ))
                        
                fig_merged.update_layout(
                    title=f"Comparative Battery Discharge Curves ({merged_filter_choice})",
                    xaxis_title="Timeline",
                    yaxis_title="Battery Level (%)",
                    yaxis=dict(range=[0, 105]),
                    hovermode="x unified"
                )
                
                if show_night_shading and all_times:
                    if merged_filter_mode == "night":
                        # Collect night intervals across compared reports
                        night_intervals = []
                        for rep in compared_reports:
                            s_dt, e_dt, _ = get_effective_bounds(rep, "night")
                            if s_dt and e_dt and s_dt < e_dt:
                                night_intervals.append((s_dt, e_dt))
                        
                        # Merge overlapping or contiguous intervals
                        merged_intervals = []
                        for s, e in sorted(night_intervals, key=lambda x: x[0]):
                            if not merged_intervals:
                                merged_intervals.append([s, e])
                            else:
                                if s <= merged_intervals[-1][1]:
                                    merged_intervals[-1][1] = max(merged_intervals[-1][1], e)
                                else:
                                    merged_intervals.append([s, e])
                                    
                        for x0, x1 in merged_intervals:
                            fig_merged.add_vrect(
                                x0=x0, x1=x1,
                                fillcolor="rgba(30, 41, 59, 0.20)",
                                layer="below",
                                line_width=0,
                                annotation_text="🌙 Night",
                                annotation_position="top left",
                                annotation_font_size=10,
                                annotation_font_color="gray"
                            )
                    else:
                        df_all_times = pd.DataFrame({"Time": all_times})
                        fig_merged = add_night_shading(fig_merged, df_all_times, night_start=night_start_cfg, night_end=night_end_cfg)
                    
                st.plotly_chart(fig_merged, use_container_width=True, key=f"merged_timeline_{merged_filter_mode}")
                
                # --- Comparative Scorecard Table ---
                st.markdown("#### 📊 Comparative Session Metrics")
                kpi_rows = []
                for rep in compared_reports:
                    s_dt, e_dt, t_df = get_effective_bounds(rep, merged_filter_mode)
                    rep_kpi = parser.compute_window_kpis(t_df)
                    kpi_rows.append({
                        "Session": rep["custom_name"],
                        "Interval": f"{rep_kpi['start_time']} → {rep_kpi['end_time']}",
                        "Duration": f"{rep_kpi['duration_hrs']:.1f} hrs",
                        "Drop": f"{rep_kpi['drop_pct']}% ({rep_kpi['start_level']}% → {rep_kpi['end_level']}%)",
                        "Velocity": f"{rep_kpi['rate_per_hr']:.2f}% / hr",
                        "Assessment": rep_kpi["status"]
                    })
                st.dataframe(pd.DataFrame(kpi_rows), use_container_width=True)
                
                st.divider()
                
                # --- 2. Side-by-Side Drain Comparison ---
                st.markdown("### ⚡ Component Consumption Comparison (mAh)")
                comp_rows = []
                for rep in compared_reports:
                    summary_txt = rep.get("summary_text", "")
                    if merged_filter_mode in ["night", "screen_off"]:
                        df_c = parser.extract_screen_off_chart_data(summary_txt)
                    else:
                        df_c = rep.get("chart_data")
                        
                    if df_c is not None and not df_c.empty:
                        df_clean = parser.clean_chart_dataframe(df_c, summary_txt)
                        for _, row in df_clean.iterrows():
                            comp_rows.append({
                                "Report": rep["custom_name"],
                                "Component": row["Component"],
                                "mAh": row["mAh"]
                            })
                            
                if comp_rows:
                    df_comp = pd.DataFrame(comp_rows)
                    fig_comp = px.bar(
                        df_comp, x="Component", y="mAh", color="Report",
                        barmode="group",
                        title=f"Component Drain Across Reports (mAh - {merged_filter_choice})"
                    )
                    st.plotly_chart(fig_comp, use_container_width=True, key=f"merged_comp_chart_{merged_filter_mode}")
                    
                st.divider()
                
                # --- Comparative Synthesis Report Section ---
                comp_key = ",".join(map(str, sorted(selected_ids)))
                saved_combined = db.get_combined_analysis(comp_key, scope_key=merged_filter_mode)
                combined_text = saved_combined["analysis_text"] if saved_combined else ""
                gen_timestamp = saved_combined.get("updated_at", "") if saved_combined else ""
                
                # Action Command Bar: Primary trigger + export button adjacent on left
                comp_action_key = f"comp_{comp_key}_{merged_filter_mode}"
                btn_comp_label = "🔄 Refresh Analysis" if saved_combined else "✨ Generate Comparative Analysis"
                
                c_comp_act1, c_comp_act2, c_comp_status = st.columns([1.5, 1.3, 3], vertical_alignment="center")
                with c_comp_act1:
                    if st.button(btn_comp_label, key=f"btn_run_comp_{merged_filter_mode}", type="primary" if not saved_combined else "secondary", use_container_width=True):
                        confirm_ai_analysis_dialog(
                            action_key=comp_action_key,
                            action_title=f"{'Refresh' if saved_combined else 'Generate'} Comparative Analysis: {merged_filter_choice}",
                            target_desc=f"Run an overarching comparative AI analysis across all **{len(compared_reports)}** selected bugreports under the **{merged_filter_choice}** filter window.",
                            details_dict={
                                "Selected Sessions": f"{len(compared_reports)} bugreports",
                                "Active Scope": merged_filter_choice,
                                "Reports List": ", ".join([r['custom_name'] for r in compared_reports[:3]]) + (f" + {len(compared_reports)-3} more" if len(compared_reports) > 3 else "")
                            },
                            action_type="comparative_synthesis",
                            action_payload={
                                "comp_key": comp_key,
                                "merged_filter_mode": merged_filter_mode,
                                "merged_filter_choice": merged_filter_choice,
                                "compared_report_ids": [r["id"] for r in compared_reports],
                                "timezone": timezone,
                                "night_start_cfg": night_start_cfg,
                                "night_end_cfg": night_end_cfg
                            }
                        )
                with c_comp_act2:
                    if combined_text and not combined_text.startswith("⚠️"):
                        comp_md = build_comparative_markdown(compared_reports, merged_filter_choice, combined_text)
                        st.download_button(
                            label="📥 Export Analysis (.md)",
                            data=comp_md,
                            file_name=f"comparative_{merged_filter_mode}_analysis.md",
                            mime="text/markdown",
                            key=f"dl_comp_md_{merged_filter_mode}",
                            use_container_width=True
                        )
                with c_comp_status:
                    if gen_timestamp and combined_text:
                        clean_ts = gen_timestamp[:16].replace("T", " ")
                        st.caption(f"🕒 **Last Evaluated:** `{clean_ts}` &nbsp;•&nbsp; 🎯 **Scope:** `{merged_filter_choice}`")
                    else:
                        st.caption(f"🎯 **Active Scope:** `{merged_filter_choice}` &nbsp;•&nbsp; Telemetry across {len(compared_reports)} sessions.")
                                
                if st.session_state.get(f"err_comp_{merged_filter_mode}"):
                    c_err_obj, c_err_act = st.session_state[f"err_comp_{merged_filter_mode}"]
                    render_ai_error(c_err_obj, action_description=c_err_act, key_suffix=f"comp_{merged_filter_mode}")
                    
                if combined_text:
                    render_ai_block(combined_text, key_suffix=f"comp_{merged_filter_mode}")
                else:
                    st.info(f"💡 No comparative evaluation generated yet for **{merged_filter_choice}**.\n\nClick **'{btn_comp_label}'** above to compare power draw, wakelocks, and battery regressions across the {len(compared_reports)} selected sessions.")

            with tab_comp_chat:
                def _build_comp_sys_prompt():
                    context_prompt = f"You are an Android Battery Engineer. Answer the user's question comparing these {len(compared_reports)} reports:\n"
                    active_inv_profile = db.get_latest_device_profile()
                    profile_summary = parser.get_inventory_summary_for_llm(active_inv_profile.get("parsed_data", {})) if active_inv_profile else ""
                    if profile_summary:
                        context_prompt += f"\n{profile_summary}\n"
                    active_routers = db.get_active_wifi_routers()
                    router_summary = parser.format_router_context_for_llm(active_routers)
                    if router_summary:
                        context_prompt += f"\n{router_summary}\n"

                    for r in compared_reports:
                        r_s, r_e, _ = get_effective_bounds(r, merged_filter_mode)
                        context_prompt += f"\n--- {r['custom_name']} ({r['timestamp_str']}) ---\nNotes: {r.get('description','')}\n{build_compact_summary(r, filter_mode=merged_filter_mode, n_start=night_start_cfg, n_end=night_end_cfg, custom_start_dt=r_s, custom_end_dt=r_e)}\n"
                    return context_prompt

                render_ai_chat_panel(
                    scope_key="merged_global",
                    panel_title="Comparative Multi-Report Consultation",
                    scope_badge=f"🎯 Scope: {merged_filter_choice}",
                    report_id=None,
                    active_thread_state_key="global_thread_id",
                    sys_prompt_builder=_build_comp_sys_prompt,
                    action_type="global_chat",
                    filter_label=f"Comparative: {merged_filter_choice}"
                )
        else:
            st.info("Please select at least 2 reports above to see the comparison.")

# ==============================================================================
# VIEW: DEVICE PROFILE & AUDIT
# ==============================================================================
elif st.session_state.active_tab == "profile":
    st.markdown("## 📱 Device Profile & Configuration Audit")
    st.caption("Deep-dive inspection of device properties, Doze sleep policies, App Standby buckets, and background power restrictions.")

    # ADB Instructions Modal / Popover Script
    adb_script_code = """# Windows PowerShell or Linux / macOS Terminal:
adb shell "
echo '=== BUILD & OS PROPERTIES ==='
getprop ro.build.display.id
getprop ro.build.version.release

echo -e '\\n=== SETTINGS: GLOBAL ==='
settings list global

echo -e '\\n=== SETTINGS: SECURE ==='
settings list secure

echo -e '\\n=== SETTINGS: SYSTEM ==='
settings list system

echo -e '\\n=== DEVICE IDLE / DOZE STATE ==='
dumpsys deviceidle get deep
dumpsys deviceidle get light
dumpsys deviceidle whitelist

echo -e '\\n=== APP STANDBY BUCKETS (LAST ACTIVE) ==='
dumpsys usagestats app_standby

echo -e '\\n=== BATTERY SAVER / POWER RESTRICTIONS ==='
dumpsys power | grep -A 10 'mBatterySaver'
cmd appops query-op --user 0 RUN_IN_BACKGROUND allow
cmd appops query-op --user 0 RUN_ANY_IN_BACKGROUND allow

echo -e '\\n=== APPOPS WAKELOCK EXEMPTIONS ==='
cmd appops query-op --user 0 WAKE_LOCK allow

echo -e '\\n=== APPOPS RESTRICTED APPS ==='
cmd appops query-op --user 0 RUN_IN_BACKGROUND ignore
cmd appops query-op --user 0 RUN_ANY_IN_BACKGROUND ignore

echo -e '\\n=== APPOPS LOCATION PERMISSIONS ==='
cmd appops query-op --user 0 FINE_LOCATION allow
cmd appops query-op --user 0 COARSE_LOCATION allow
cmd appops query-op --user 0 MONITOR_LOCATION allow

echo -e '\\n=== DISABLED PACKAGES ==='
pm list packages -d

echo -e '\\n=== NETWORK POLICY & DATA SAVER ==='
dumpsys netpolicy | grep -E 'restrict_background|mRestrictBackground'

echo -e '\\n=== BACKGROUND JOBS SUMMARY ==='
dumpsys jobscheduler | grep -E 'JobHistory|Pending jobs'

echo -e '\\n=== LOCATION PROVIDERS & SCANNING ==='
settings get global wifi_scan_always_enabled
settings get secure location_mode
settings get secure location_providers_allowed
" > full_device_inventory.txt"""

    profiles = db.get_all_device_profiles()
    
    # Mode switch if at least 2 profiles exist
    view_mode = "Single Profile Audit"
    if profiles and len(profiles) >= 2:
        c_mode, _ = st.columns([3, 5])
        with c_mode:
            view_mode = st.radio(
                "Profile Analysis Mode:",
                ["Single Profile Audit", "🔀 Compare Profiles"],
                horizontal=True,
                key="device_profile_view_mode_radio"
            )

    if view_mode == "Single Profile Audit":
        # Top action bar: Selector + Action Buttons (Vertically centered and aligned with selectbox)
        c_sel, c_actions = st.columns([5, 3], vertical_alignment="bottom")
        with c_sel:
            if profiles:
                profile_dict = {p["id"]: f"{p['profile_name']} — {p['device_model']} ({p['updated_at'][:16]})" for p in profiles}
                
                # Ensure valid active_profile_id
                if st.session_state.get("active_profile_id") not in profile_dict:
                    st.session_state.active_profile_id = profiles[0]["id"]
                
                # Sync widget key if active_profile_id was changed programmatically before instantiation
                if "sel_active_profile_box" in st.session_state and st.session_state.sel_active_profile_box != st.session_state.active_profile_id:
                    st.session_state.sel_active_profile_box = st.session_state.active_profile_id

                def _on_profile_change():
                    st.session_state.active_profile_id = st.session_state.sel_active_profile_box

                st.selectbox(
                    "Select Device Profile Snapshot:",
                    options=list(profile_dict.keys()),
                    format_func=lambda x: profile_dict[x],
                    index=list(profile_dict.keys()).index(st.session_state.active_profile_id),
                    key="sel_active_profile_box",
                    on_change=_on_profile_change
                )
                
                # Fetch profile matching active_profile_id
                current_profile = db.get_device_profile(st.session_state.active_profile_id)
            else:
                current_profile = None
                st.info("No device profiles recorded yet. Upload a `full_device_inventory.txt` below to begin.")

        with c_actions:
            btn_c1, btn_c2, btn_c_rename, btn_c3 = st.columns([1.3, 1.2, 1.1, 1.0])
            with btn_c1:
                with st.popover("📋 ADB Commands", use_container_width=True):
                    st.markdown("#### 📱 Generate Inventory File via ADB")
                    st.write("Connect your phone via USB with **USB Debugging** enabled, then run this command in your terminal:")
                    st.code(adb_script_code, language="bash")
                    st.caption("This produces `full_device_inventory.txt` directly in your current folder.")
            with btn_c2:
                with st.popover("📤 Upload File", use_container_width=True):
                    st.markdown("#### 📤 Upload / Refresh Inventory")
                    u_count = st.session_state.inv_upload_counter
                    upload_mode = st.radio("Save mode:", ["Save as New Profile", "Overwrite Current Profile"] if current_profile else ["Save as New Profile"], key=f"inv_upload_mode_radio_{u_count}")
                    default_pname = "My Pixel Profile" if not current_profile else f"{current_profile['profile_name']} (Update)"
                    p_name_input = st.text_input("Profile Name:", value=default_pname, key=f"input_inv_pname_{u_count}")
                    uploaded_inv_file = st.file_uploader("Upload full_device_inventory.txt", type=["txt"], key=f"inv_file_uploader_{u_count}")
                    if uploaded_inv_file and st.button("Save Profile Snapshot", key=f"btn_save_inv_profile_{u_count}", use_container_width=True):
                        raw_inv_text = uploaded_inv_file.read().decode("utf-8", errors="replace")
                        parsed_inv = parser.parse_device_inventory(raw_inv_text)
                        target_pid = current_profile["id"] if "Overwrite" in upload_mode and current_profile else None
                        saved_pid = db.save_device_profile(
                            profile_name=p_name_input.strip() or "Device Inventory Snapshot",
                            raw_content=raw_inv_text,
                            parsed_data=parsed_inv,
                            profile_id=target_pid
                        )
                        st.session_state.active_profile_id = saved_pid
                        # Increment counter to reset file uploader & input fields
                        st.session_state.inv_upload_counter += 1
                        st.session_state.inv_upload_success_msg = f"✅ Device profile '{p_name_input.strip()}' successfully saved!"
                        st.rerun()
            with btn_c_rename:
                if current_profile:
                    with st.popover("✏️ Rename", use_container_width=True):
                        st.markdown(f"#### ✏️ Rename Profile")
                        new_pname = st.text_input("New Profile Name:", value=current_profile["profile_name"], key=f"rename_input_{current_profile['id']}")
                        if st.button("Save Name", key=f"btn_save_rename_{current_profile['id']}", use_container_width=True):
                            if new_pname.strip():
                                db.update_device_profile_name(current_profile["id"], new_pname.strip())
                                st.success("Profile renamed!")
                                st.rerun()
                            else:
                                st.error("Profile name cannot be empty.")
            with btn_c3:
                if current_profile:
                    with st.popover("🗑️ Delete", use_container_width=True):
                        st.warning(f"Delete '{current_profile['profile_name']}'?")
                        if st.button("Confirm Delete", type="primary", key=f"del_prof_{current_profile['id']}", use_container_width=True):
                            db.delete_device_profile(current_profile["id"])
                            st.session_state.active_profile_id = None
                            st.success("Profile deleted.")
                            st.rerun()

        st.divider()

        if st.session_state.get("inv_upload_success_msg"):
            st.success(st.session_state.inv_upload_success_msg)
            st.session_state.inv_upload_success_msg = None

        if current_profile:
            p_data = current_profile.get("parsed_data", {})
            k_settings = p_data.get("key_settings", {})
            
            # 1. Device Architecture & OS Health KPI Row
            st.markdown("### 🖥️ Device & System Environment")
            kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
            kpi1.metric("📱 Device Model", p_data.get("device_model", "Unknown"))
            kpi2.metric("🤖 Android Version", f"Android {p_data.get('android_version', 'Unknown')}")
            kpi3.metric("🏗️ OS Build ID", p_data.get("os_build", "Unknown"))
            kpi4.metric("💤 Deep Doze State", p_data.get("doze_deep_state", "UNKNOWN"))
            kpi5.metric("⚡ Light Doze State", p_data.get("doze_light_state", "UNKNOWN"))

            st.divider()

            # Three dedicated top-level tabs: Configuration Audit & System Environment, WiFi Router Environment, and Consultation Chat
            tab_prof_audit, tab_prof_routers, tab_prof_chat = st.tabs([
                "🛡️ Configuration Audit & System Environment",
                "📡 WiFi Router Environment ✨",
                "💬 Configuration & Doze Consultation Chat ✨"
            ])

            with tab_prof_audit:
                # --- AI Profile Audit Section ---
                st.markdown('### ✨ Oracle Configuration Audit <span class="ai-badge">✨ AI GENERATED</span>', unsafe_allow_html=True)
                p_analysis = current_profile.get("ai_analysis")
                p_trace = current_profile.get("ai_analysis_trace", "")
                
                prof_action_key = f"prof_audit_{current_profile['id']}"
                btn_ai_label = "🔄 Refresh AI Audit" if p_analysis else "✨ Run AI Configuration Audit"
                
                c_pact1, c_pact2 = st.columns([1.5, 4], vertical_alignment="center")
                with c_pact1:
                    if st.button(btn_ai_label, key=f"btn_audit_profile_{current_profile['id']}", type="primary" if not p_analysis else "secondary", use_container_width=True):
                        confirm_ai_analysis_dialog(
                            action_key=prof_action_key,
                            action_title=f"{'Refresh' if p_analysis else 'Run'} AI Configuration Audit",
                            target_desc=f"Run an in-depth AI configuration audit for **{current_profile['profile_name']}**.",
                            details_dict={
                                "Profile Name": current_profile["profile_name"],
                                "Device Model": p_data.get("device_model", "Unknown"),
                                "Android Version": f"Android {p_data.get('android_version', 'Unknown')}",
                                "Build ID": p_data.get("os_build", "Unknown")
                            },
                            action_type="profile_audit",
                            action_payload={
                                "profile_id": current_profile["id"]
                            }
                        )
                with c_pact2:
                    if p_analysis:
                        st.caption(f"🕒 **Last Evaluated:** `{current_profile.get('updated_at', '')[:16]}` &nbsp;•&nbsp; Grounded in full device inventory & AppOps.")
                    else:
                        st.caption("⏳ **Not Yet Generated** &nbsp;•&nbsp; Click above to audit Doze states, AppOps restrictions & risks.")

                if st.session_state.get(f"err_prof_audit_{current_profile['id']}"):
                    p_err_obj, p_err_act = st.session_state[f"err_prof_audit_{current_profile['id']}"]
                    render_ai_error(p_err_obj, action_description=p_err_act, key_suffix=f"prof_audit_{current_profile['id']}")

                if p_analysis:
                    render_ai_block(p_analysis, key_suffix=f"profile_{current_profile['id']}")
                    if p_trace:
                        with st.expander("🧠 AI Reasoning & System Audit Trace"):
                            st.markdown(p_trace)

                st.divider()

                # 2. Critical Standby Risks & WhiteList Violations
                st.markdown("### 🚨 Standby Drain Risks & Policy Audit")
                risks = p_data.get("standby_risks", [])
                if risks:
                    for r in risks:
                        sev = r.get("severity", "LOW")
                        icon = "🔴" if sev == "HIGH" else ("🟡" if sev == "MEDIUM" else "🔵")
                        with st.expander(f"{icon} [{sev}] {r['title']}", expanded=(sev == "HIGH")):
                            st.markdown(f"**Issue Description:** {r['detail']}")
                            st.markdown(f"**How to configure on device:** `{r['setting']}`")
                else:
                    st.success("🎉 No high-risk standby configuration flags detected!")

                st.divider()

                # 3. Radios, Display & Sensors (Responsive Cards)
                st.markdown("### 📡 Radios, Ambient Display & Power Tuning")
                r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns(5)
                
                wifi_active = k_settings.get("wifi_scan_always_enabled") == "1"
                ble_active = k_settings.get("ble_scan_always_enabled") == "1"
                tilt_active = k_settings.get("ambient_tilt_to_wake") == "1"
                touch_active = k_settings.get("ambient_touch_to_wake") == "1"
                timeout_sec = int(k_settings.get("screen_off_timeout_ms", "15000")) // 1000
                refresh = float(k_settings.get("peak_refresh_rate", "60.0"))

                with r_col1:
                    st.markdown(f"""
                    <div style="background: rgba(148, 163, 184, 0.08); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 12px 14px; min-height: 105px;">
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">📶 Wi-Fi Always Scanning</div>
                        <div style="font-size: 1.05rem; font-weight: 600; color: {'#f59e0b' if wifi_active else '#10b981'}; word-break: break-word;">
                            {'⚠️ Enabled (Continuous)' if wifi_active else '✅ Disabled (Safe)'}
                        </div>
                        <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">Location scanning</div>
                    </div>
                    """, unsafe_allow_html=True)

                with r_col2:
                    st.markdown(f"""
                    <div style="background: rgba(148, 163, 184, 0.08); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 12px 14px; min-height: 105px;">
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">📡 BLE Always Scanning</div>
                        <div style="font-size: 1.05rem; font-weight: 600; color: {'#f59e0b' if ble_active else '#10b981'}; word-break: break-word;">
                            {'⚠️ Enabled' if ble_active else '✅ Disabled'}
                        </div>
                        <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">Bluetooth beacon scan</div>
                    </div>
                    """, unsafe_allow_html=True)

                with r_col3:
                    st.markdown(f"""
                    <div style="background: rgba(148, 163, 184, 0.08); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 12px 14px; min-height: 105px;">
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">🖐️ Ambient Wake Gestures</div>
                        <div style="font-size: 0.95rem; font-weight: 600; line-height: 1.35; word-break: break-word;">
                            Tilt: <span style="color: {'#3b82f6' if tilt_active else '#64748b'};">{'On' if tilt_active else 'Off'}</span> &nbsp;|&nbsp; 
                            Touch: <span style="color: {'#3b82f6' if touch_active else '#64748b'};">{'On' if touch_active else 'Off'}</span>
                        </div>
                        <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">Hardware sensor polling</div>
                    </div>
                    """, unsafe_allow_html=True)

                with r_col4:
                    st.markdown(f"""
                    <div style="background: rgba(148, 163, 184, 0.08); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 12px 14px; min-height: 105px;">
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">⏱️ Screen Timeout</div>
                        <div style="font-size: 1.05rem; font-weight: 600; color: {'#10b981' if timeout_sec <= 30 else '#f59e0b'}; word-break: break-word;">
                            {timeout_sec} seconds
                        </div>
                        <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">Display off delay</div>
                    </div>
                    """, unsafe_allow_html=True)

                with r_col5:
                    st.markdown(f"""
                    <div style="background: rgba(148, 163, 184, 0.08); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 12px 14px; min-height: 105px;">
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">📺 Peak Refresh Rate</div>
                        <div style="font-size: 1.05rem; font-weight: 600; color: {'#10b981' if refresh <= 60 else '#3b82f6'}; word-break: break-word;">
                            {refresh:.0f} Hz
                        </div>
                        <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">Display panel limit</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.divider()

                # 4. Detailed Drill-downs: Doze Whitelists, App Standby & Raw Key-Value Explorer
                n_allowed = len(p_data.get('appops_allowed', []))
                n_restricted = len(p_data.get('appops_restricted', []))
                tab_doze, tab_appops, tab_kv = st.tabs([
                    f"🛡️ Doze Whitelist ({len(p_data.get('user_whitelisted', []))} User Apps)",
                    f"⚡ AppOps & Battery Restrictions ({n_allowed} allowed, {n_restricted} restricted)",
                    f"🔍 System Settings Explorer ({p_data.get('raw_counts', {}).get('global_count', 0) + p_data.get('raw_counts', {}).get('secure_count', 0) + p_data.get('raw_counts', {}).get('system_count', 0)} keys)"
                ])

                with tab_doze:
                    st.markdown("#### User-Installed Apps Exempt from Android Doze Deep Sleep")
                    st.caption("These user apps have been granted permission to ignore Doze optimizations, wake the CPU at will, and access the network during sleep.")
                    u_wl = p_data.get("user_whitelisted", [])
                    if u_wl:
                        df_uwl = pd.DataFrame(u_wl).rename(columns={"friendly": "App Name", "package": "Package Identifier", "uid": "Linux UID", "type": "Whitelist Scope"})
                        st.dataframe(df_uwl, use_container_width=True)
                    else:
                        st.info("No user apps are exempt from Doze! All user apps enter deep sleep normally.")

                    with st.expander(f"System & OEM Exemption Whitelist ({p_data.get('system_whitelisted_count', 0)} packages)"):
                        st.caption("Internal Android OS and carrier packages whitelisted by the OEM ROM:")
                        s_wl = p_data.get("system_whitelisted", [])
                        if s_wl:
                            st.dataframe(pd.DataFrame(s_wl)[["friendly", "package", "uid"]].rename(columns={"friendly": "System Service", "package": "Package Identifier", "uid": "UID"}), use_container_width=True)

                with tab_appops:
                    st.markdown("#### ⚡ Android AppOps Execution & Battery Policies")
                    st.caption("Ground truth from Android AppOps policies defining background execution, battery restrictions, and location access.")

                    subtab_allowed, subtab_restr, subtab_loc, subtab_wake = st.tabs([
                        f"🟢 Unrestricted ({len(p_data.get('appops_allowed', []))})",
                        f"🚫 Explicitly Restricted ({len(p_data.get('appops_restricted', []))})",
                        f"📍 Location Access ({len(p_data.get('appops_location_allowed', []))})",
                        f"⏰ Wakelock Exemptions ({len(p_data.get('appops_wakelock_allowed', []))})"
                    ])

                    with subtab_allowed:
                        st.markdown("##### Applications Granted `RUN_IN_BACKGROUND` AppOps Permission")
                        st.caption("These packages have been granted permission to execute background services without standard Android OS battery throttling.")
                        a_ops = p_data.get("appops_allowed", [])
                        if a_ops:
                            df_aops = pd.DataFrame(a_ops).rename(columns={"friendly": "App Name", "package": "Package Identifier"})
                            st.dataframe(df_aops, use_container_width=True)
                        else:
                            st.info("No apps explicitly granted unrestricted background execution.")

                    with subtab_restr:
                        st.markdown("##### Applications Explicitly Restricted (`RUN_IN_BACKGROUND ignore`)")
                        st.caption("These apps are set to 'Restricted' battery mode in Android Settings. If any of these apps still exhibit energy consumption, it is driven by Foreground Services, user interaction, or FCM high-priority push, NOT background polling.")
                        r_ops = p_data.get("appops_restricted", [])
                        if r_ops:
                            df_rops = pd.DataFrame(r_ops).rename(columns={"friendly": "App Name", "package": "Package Identifier"})
                            st.dataframe(df_rops, use_container_width=True)
                        else:
                            st.info("No apps marked as explicitly restricted in the current profile snapshot. (Run the updated ADB script to audit).")

                    with subtab_loc:
                        st.markdown("##### Applications with Active Location Permissions")
                        st.caption("Packages permitted to request `FINE_LOCATION`, `COARSE_LOCATION`, or `MONITOR_LOCATION`. Background GPS/GNSS scans prevent modem and SoC low-power sleep states.")
                        l_ops = p_data.get("appops_location_allowed", [])
                        if l_ops:
                            df_lops = pd.DataFrame(l_ops).rename(columns={"friendly": "App Name", "package": "Package Identifier"})
                            st.dataframe(df_lops, use_container_width=True)
                        else:
                            st.info("No user-level location permissions captured in this snapshot.")

                    with subtab_wake:
                        st.markdown("##### Applications Granted `WAKE_LOCK` AppOps Exemption")
                        st.caption("Packages explicitly authorized to acquire partial wakelocks keeping CPU active.")
                        w_ops = p_data.get("appops_wakelock_allowed", [])
                        if w_ops:
                            df_wops = pd.DataFrame(w_ops).rename(columns={"friendly": "App Name", "package": "Package Identifier"})
                            st.dataframe(df_wops, use_container_width=True)
                        else:
                            st.info("No apps granted explicit WAKE_LOCK AppOps exemption.")

                with tab_kv:
                    st.markdown("#### Comprehensive Android Settings Registry")
                    st.caption("Search across all raw key-value pairs stored in Android `Global`, `Secure`, and `System` settings providers.")
                    
                    all_kv = []
                    for k, v in p_data.get("global_settings", {}).items():
                        all_kv.append({"Scope": "Global", "Key": k, "Value": v})
                    for k, v in p_data.get("secure_settings", {}).items():
                        all_kv.append({"Scope": "Secure", "Key": k, "Value": v})
                    for k, v in p_data.get("system_settings", {}).items():
                        all_kv.append({"Scope": "System", "Key": k, "Value": v})

                    if all_kv:
                        df_all_kv = pd.DataFrame(all_kv)
                        search_query = st.text_input("🔎 Search settings by key or value:", placeholder="e.g. wifi, sync, doze, refresh, wake, bluetooth...", key="kv_search_input")
                        if search_query:
                            df_all_kv = df_all_kv[df_all_kv["Key"].str.contains(search_query, case=False, na=False) | df_all_kv["Value"].str.contains(search_query, case=False, na=False)]
                        st.dataframe(df_all_kv, use_container_width=True, height=450)
                    else:
                        st.info("No raw settings data available for this profile.")

            with tab_prof_routers:
                render_wifi_routers_management_ui()

            with tab_prof_chat:
                # --- FULL-SCREEN PROFILE AUDIT CHAT WORKSPACE (FRAGMENT ISOLATED) ---
                prof_rep_id = -current_profile["id"]
                def _build_prof_sys_prompt():
                    prof_telemetry_summary = parser.get_inventory_summary_for_llm(p_data)
                    active_routers = db.get_active_wifi_routers()
                    router_summary = parser.format_router_context_for_llm(active_routers)
                    if router_summary:
                        prof_telemetry_summary = f"{router_summary}\n\n{prof_telemetry_summary}"
                    prof_chat_tmpl = llm_manager.get_prompt_template("profile_chat")
                    return prof_chat_tmpl.format(
                        device_model=p_data.get("device_model", "Unknown Device"),
                        os_build=p_data.get("os_build", "Unknown Build"),
                        android_version=p_data.get("android_version", "Unknown"),
                        doze_deep=p_data.get("doze_deep_state", "UNKNOWN"),
                        doze_light=p_data.get("doze_light_state", "UNKNOWN"),
                        audit_report=p_analysis,
                        profile_telemetry=prof_telemetry_summary
                    )

                render_ai_chat_panel(
                    scope_key=f"profile_{current_profile['id']}",
                    panel_title=f"Configuration & Doze Consultation • {current_profile['profile_name']}",
                    scope_badge=f"📱 Device: {p_data.get('device_model', 'Unknown')} • Android {p_data.get('android_version', 'Unknown')}",
                    report_id=prof_rep_id,
                    active_thread_state_key=f"active_prof_thread_{current_profile['id']}",
                    sys_prompt_builder=_build_prof_sys_prompt,
                    action_type="profile_chat",
                    filter_label=f"Profile: {current_profile['profile_name']}"
                )
        else:
            tab_no_prof, tab_no_prof_routers = st.tabs([
                "🛡️ Device Configuration Audit",
                "📡 WiFi Router Environment ✨"
            ])
            with tab_no_prof:
                st.info("No device profile snapshot selected or available. Connect your device via ADB and upload a `full_device_inventory.txt` using the buttons above to begin the audit.")
            with tab_no_prof_routers:
                render_wifi_routers_management_ui()

    elif view_mode == "🔀 Compare Profiles":
        st.markdown("### 🔀 Device Configuration Snapshot Comparison")
        st.caption("Compare settings, Doze exemptions, and AppOps permissions between two device profile snapshots.")
        
        c_prof_a, c_prof_b = st.columns(2)
        prof_dict = {p["id"]: f"{p['profile_name']} ({p['updated_at'][:16]})" for p in profiles}
        p_ids = list(prof_dict.keys())
        
        with c_prof_a:
            p_a_id = st.selectbox("Baseline Profile (Before):", options=p_ids, index=1 if len(p_ids) > 1 else 0, format_func=lambda x: prof_dict[x], key="sel_cmp_prof_a")
        with c_prof_b:
            p_b_id = st.selectbox("Target Profile (After):", options=p_ids, index=0, format_func=lambda x: prof_dict[x], key="sel_cmp_prof_b")
            
        profile_a = db.get_device_profile(p_a_id)
        profile_b = db.get_device_profile(p_b_id)
        
        if profile_a and profile_b:
            diff = parser.compute_profile_diff(profile_a, profile_b)
            
            # KPI Delta Row
            kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
            kpi_c1.metric("🏗️ OS Build Changed", "YES" if diff["build_changed"] else "NO", f"{diff['build_a'][:14]} → {diff['build_b'][:14]}" if diff["build_changed"] else "Identical")
            
            wl_delta = len(diff["wl_added"]) - len(diff["wl_removed"])
            kpi_c2.metric("🛡️ Doze Whitelist Δ", f"{len(diff['wl_added'])} added / {len(diff['wl_removed'])} removed", delta=f"{wl_delta:+d} apps", delta_color="inverse")
            
            ao_delta = len(diff["ao_bg_added"]) - len(diff["ao_bg_removed"])
            kpi_c3.metric("⚡ AppOps Background Δ", f"{len(diff['ao_bg_added'])} added / {len(diff['ao_bg_removed'])} removed", delta=f"{ao_delta:+d} apps", delta_color="inverse")
            
            kpi_c4.metric("⚙️ Modified Settings", f"{len(diff['settings_diff'])} keys")
            
            st.divider()
            
            # --- AI Configuration Delta Analysis ---
            st.markdown('### ✨ Oracle Configuration Delta Analysis <span class="ai-badge">✨ AI GENERATED</span>', unsafe_allow_html=True)
            cmp_cache_key = f"profile_cmp_ai_{min(p_a_id, p_b_id)}_{max(p_a_id, p_b_id)}_{p_a_id}"
            cached_cmp_analysis = db.get_setting(cmp_cache_key)
            
            # Action Command Bar: Primary trigger on left + status pill
            cmp_action_key = f"prof_cmp_{p_a_id}_{p_b_id}"
            btn_cmp_label = "🔄 Refresh AI Delta Audit" if cached_cmp_analysis else "✨ Run AI Delta Audit"
            
            c_act1, c_act2 = st.columns([1.5, 4], vertical_alignment="center")
            with c_act1:
                if st.button(btn_cmp_label, key=f"btn_run_cmp_ai_{p_a_id}_{p_b_id}", type="primary" if not cached_cmp_analysis else "secondary", use_container_width=True):
                    confirm_ai_analysis_dialog(
                        action_key=cmp_action_key,
                        action_title=f"{'Refresh' if cached_cmp_analysis else 'Run'} Profile Delta Audit",
                        target_desc=f"Compare configuration changes between **{profile_a['profile_name']}** and **{profile_b['profile_name']}** and evaluate power impacts.",
                        details_dict={
                            "Baseline Profile": profile_a["profile_name"],
                            "Target Profile": profile_b["profile_name"],
                            "OS Build": f"{diff['build_a'][:14]} → {diff['build_b'][:14]}" if diff["build_changed"] else "Identical",
                            "Doze Whitelist Δ": f"{len(diff['wl_added'])} added / {len(diff['wl_removed'])} removed",
                            "AppOps BG Δ": f"{len(diff['ao_bg_added'])} added / {len(diff['ao_bg_removed'])} removed",
                            "Modified Settings": f"{len(diff['settings_diff'])} keys"
                        },
                        action_type="profile_comparison",
                        action_payload={
                            "p_a_id": p_a_id,
                            "p_b_id": p_b_id,
                            "cmp_cache_key": cmp_cache_key
                        }
                    )
            with c_act2:
                if cached_cmp_analysis:
                    st.caption("✅ **Analysis Ready** &nbsp;•&nbsp; Cached evaluation grounded in profile deltas & system policies.")
                else:
                    st.caption("⏳ **Not Yet Generated** &nbsp;•&nbsp; Click above to evaluate battery risk, Doze regressions & AppOps changes.")
                            
            if st.session_state.get(f"err_prof_cmp_{p_a_id}_{p_b_id}"):
                c_err_obj, c_err_act = st.session_state[f"err_prof_cmp_{p_a_id}_{p_b_id}"]
                render_ai_error(c_err_obj, action_description=c_err_act, key_suffix=f"prof_cmp_{p_a_id}_{p_b_id}")

            if cached_cmp_analysis:
                render_ai_block(cached_cmp_analysis, key_suffix=f"cmp_{p_a_id}_{p_b_id}")
                st.divider()

            # Side-by-Side Whitelist and AppOps changes
            col_wl_diff, col_ao_diff = st.columns(2)
            with col_wl_diff:
                st.markdown("#### 🛡️ Doze Deep Sleep Whitelist Changes")
                if diff["wl_added"]:
                    st.markdown("**Added (Newly Exempted from Doze):**")
                    for itm in diff["wl_added"]:
                        st.markdown(f"- 🔴 `{itm['friendly']}` (`{itm['package']}`)")
                if diff["wl_removed"]:
                    st.markdown("**Removed (Now entering Doze normally):**")
                    for itm in diff["wl_removed"]:
                        st.markdown(f"- 🟢 `{itm['friendly']}` (`{itm['package']}`)")
                if not diff["wl_added"] and not diff["wl_removed"]:
                    st.info("No changes in Doze deep sleep whitelist between profiles.")
                    
            with col_ao_diff:
                st.markdown("#### ⚡ AppOps RUN_IN_BACKGROUND Changes")
                if diff["ao_bg_added"]:
                    st.markdown("**Granted Background Permission:**")
                    for itm in diff["ao_bg_added"]:
                        st.markdown(f"- 🔴 `{itm['friendly']}` (`{itm['package']}`)")
                if diff["ao_bg_removed"]:
                    st.markdown("**Revoked / Restricted:**")
                    for itm in diff["ao_bg_removed"]:
                        st.markdown(f"- 🟢 `{itm['friendly']}` (`{itm['package']}`)")
                if not diff["ao_bg_added"] and not diff["ao_bg_removed"]:
                    st.info("No changes in AppOps background permissions between profiles.")

            st.divider()

            # Modified Android Settings Table
            st.markdown("#### ⚙️ Modified Android Settings Registry")
            if diff["settings_diff"]:
                df_diff_settings = pd.DataFrame(diff["settings_diff"]).rename(columns={
                    "scope": "Scope",
                    "key": "Setting Key",
                    "val_a": f"Baseline ({profile_a['profile_name'][:15]})",
                    "val_b": f"Target ({profile_b['profile_name'][:15]})"
                })
                st.dataframe(df_diff_settings, use_container_width=True, height=400)
            else:
                st.info("All recorded Global, Secure, and System settings are identical between these two profiles.")

# ==============================================================================
# VIEW 3: MASTER EXPERIMENT SYNTHESIS
# ==============================================================================
elif st.session_state.active_tab == "master":
    st.markdown("## 🧪 Master Battery Experiment Synthesis")
    st.caption("An executive retrospective and definitive blueprint synthesizing all multi-day test runs, overnight standby windows, and optimizations.")
    
    if not all_reports:
        st.info("No bugreports found. Please upload bugreports to generate the master synthesis.")
    else:
        # Multi-day scorecard
        st.markdown("### 📊 Experiment Scorecard & Chronology")
        scorecard = []
        for r in all_reports:
            df_h = r.get("history_data")
            kpi_full = parser.compute_window_kpis(df_h)
            
            # Night window calculation
            if df_h is not None and not df_h.empty and "Time" in df_h.columns:
                db_c_s = r.get("custom_night_start")
                db_c_e = r.get("custom_night_end")
                if db_c_s and db_c_e:
                    s_dt, e_dt = db_c_s, db_c_e
                else:
                    s_dt, e_dt = parser.get_latest_night_window(df_h["Time"].min(), df_h["Time"].max(), night_start_cfg, night_end_cfg)
                df_night = parser.slice_timeline_range(df_h, s_dt, e_dt)
                kpi_night = parser.compute_window_kpis(df_night)
            else:
                kpi_night = parser.compute_window_kpis(None)
                
            scorecard.append({
                "Session / Bugreport": r["custom_name"],
                "Recorded Interval": f"{kpi_full['start_time']} → {kpi_full['end_time']}",
                "Full Drop Rate": f"{kpi_full['rate_per_hr']:.2f}% / hr",
                "🌙 Night Standby Rate": f"{kpi_night['rate_per_hr']:.2f}% / hr",
                "Total Loss": f"{kpi_full['drop_pct']}% ({kpi_full['duration_hrs']:.1f} hrs)",
                "Night Drop": f"{kpi_night['drop_pct']}% ({kpi_night['duration_hrs']:.1f} hrs)",
                "Notes / State": r.get("description", "Baseline")
            })
            
        st.dataframe(pd.DataFrame(scorecard), use_container_width=True)
        
        st.divider()
        
        # Two dedicated top-level tabs: Blueprint & Scorecard vs Master Chat
        tab_master_blueprint, tab_master_chat = st.tabs([
            "📜 Master Retrospective & Action Plan",
            "💬 Master Experiment Consultation Chat ✨"
        ])

        with tab_master_blueprint:
            # Synthesis Generator
            saved_synthesis = db.get_master_synthesis()
            # Action Command Bar: Primary trigger + export button adjacent on left
            master_action_key = "master_experiment_synthesis"
            btn_synth_label = "🔄 Refresh Master Synthesis" if saved_synthesis else "✨ Synthesize Grand Master Experiment"
            synthesis_text = saved_synthesis["text"] if saved_synthesis else ""
            
            c_synth_act1, c_synth_act2, c_synth_status = st.columns([1.6, 1.3, 3], vertical_alignment="center")
            with c_synth_act1:
                if st.button(btn_synth_label, key="btn_run_master_synth", type="primary" if not saved_synthesis else "secondary", use_container_width=True):
                    confirm_ai_analysis_dialog(
                        action_key=master_action_key,
                        action_title=f"{'Refresh' if saved_synthesis else 'Generate'} Grand Master Experiment Synthesis",
                        target_desc=f"Synthesize an executive retrospective and definitive blueprint across all **{len(all_reports)}** recorded bugreport sessions.",
                        details_dict={
                            "Total Sessions": f"{len(all_reports)} bugreports",
                            "Telemetry Scope": "Night Standby Windows & Full Sessions",
                            "Latest Device Profile": (db.get_latest_device_profile() or {}).get("profile_name", "None")
                        },
                        action_type="master_synthesis",
                        action_payload={
                            "night_start_cfg": night_start_cfg,
                            "night_end_cfg": night_end_cfg
                        }
                    )
            with c_synth_act2:
                if synthesis_text:
                    st.download_button(
                        label="📥 Export Synthesis (.md)",
                        data=synthesis_text,
                        file_name=f"Master_Battery_Experiment_Synthesis_{datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown",
                        key="dl_master_synth_md",
                        use_container_width=True
                    )
            with c_synth_status:
                if saved_synthesis:
                    updated_ts = saved_synthesis.get('updated_at', '')[:16]
                    st.caption(f"🕒 **Last Synthesized:** `{updated_ts}` &nbsp;•&nbsp; Covering {len(all_reports)} multi-day test runs.")
                else:
                    st.caption(f"🧪 **Synthesis Ready:** {len(all_reports)} bugreport test runs ready for multi-day retrospective.")

            if st.session_state.get("err_master_synth"):
                m_err_obj, m_err_act = st.session_state["err_master_synth"]
                render_ai_error(m_err_obj, action_description=m_err_act, key_suffix="master_synth")
                    
            if synthesis_text:
                st.markdown('### ✨ Master Retrospective Blueprint <span class="ai-badge">✨ AI GENERATED</span>', unsafe_allow_html=True)
                render_ai_block(synthesis_text, key_suffix="master_synthesis")
            else:
                st.info("Click **'✨ Synthesize Grand Master Experiment'** above to generate the overarching retrospective across all sessions.")

        with tab_master_chat:
            def _build_master_sys_prompt():
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

                for idx, r in enumerate(all_rep):
                    chronicle_lines.append(f"SESSION {idx+1}: {r['custom_name']} ({r['timestamp_str']}) - {r.get('description', '')}")
                    chronicle_lines.append(build_compact_summary(r, filter_mode='night', n_start=night_start_cfg, n_end=night_end_cfg))

                context_prompt = (
                    "You are a Principal Android Battery & Performance Architect.\n"
                    "You are consulting with the user regarding their overarching multi-day battery experiment synthesis and long-term optimization blueprint.\n\n"
                    "=== EXECUTIVE MASTER SYNTHESIS ===\n"
                    f"{synth_ctx}\n\n"
                    "=== COMPLETE MULTI-DAY TEST RUN CHRONICLE ===\n"
                    + "\n".join(chronicle_lines)
                )
                return context_prompt

            render_ai_chat_panel(
                scope_key="master_experiment_synthesis",
                panel_title="Master Experiment Consultation Chat",
                scope_badge=f"🧪 {len(all_reports)} Test Runs • Grand Blueprint",
                report_id=-999999,
                active_thread_state_key="active_master_thread_id",
                sys_prompt_builder=_build_master_sys_prompt,
                action_type="master_experiment_chat",
                filter_label=f"Grand Master Experiment ({len(all_reports)} sessions)"
            )


# ==============================================================================
# VIEW 3: TOKEN & COST ACCOUNTING DASHBOARD
# ==============================================================================
elif st.session_state.active_tab == "accounting":
    st.markdown("## 📊 Token & Cost Accounting Dashboard")
    st.caption("Detailed breakdown of prompt tokens, completion tokens, cached tokens, and USD costs across all sessions.")
    
    totals = db.get_token_totals()
    
    # KPI Row
    kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5, kpi_c6 = st.columns(6)
    kpi_c1.metric("🪙 Total Tokens", f"{totals['total_tokens']:,}")
    kpi_c2.metric("📥 Prompt Tokens", f"{totals['total_prompt']:,}")
    kpi_c3.metric("📤 Completion", f"{totals['total_completion']:,}")
    kpi_c4.metric("⚡ Cached Tokens", f"{totals['total_cached']:,}")
    kpi_c5.metric("💵 Total Cost", f"${totals['total_cost']:.4f}")
    kpi_c6.metric("🔄 LLM Requests", f"{totals['request_count']:,}")
    
    st.divider()
    
    acc_tab1, acc_tab2, acc_tab3 = st.tabs(["📁 Breakdown by Bugreport", "🧵 Breakdown by Thread", "📅 Activity Over Time"])
    
    with acc_tab1:
        st.markdown("### Token & Cost Consumption per Bugreport")
        by_rep = db.get_token_summary_by_report()
        if by_rep:
            df_rep = pd.DataFrame(by_rep)
            st.dataframe(
                df_rep[["report_name", "request_count", "total_tokens", "prompt_tokens", "completion_tokens", "cached_tokens", "total_cost"]].rename(columns={
                    "report_name": "Report / Scope",
                    "request_count": "Requests",
                    "total_tokens": "Total Tokens",
                    "prompt_tokens": "Prompt",
                    "completion_tokens": "Completion",
                    "cached_tokens": "Cached",
                    "total_cost": "Cost ($ USD)"
                }),
                use_container_width=True
            )
            fig_rep_cost = px.bar(df_rep, x="report_name", y="total_cost", color="report_name", title="Cost by Bugreport ($ USD)")
            st.plotly_chart(fig_rep_cost, use_container_width=True, key="cost_rep_chart")
        else:
            st.info("No token activity logged yet.")
            
    with acc_tab2:
        st.markdown("### Token Consumption by Conversation Thread")
        by_th = db.get_token_summary_by_thread()
        if by_th:
            df_th = pd.DataFrame(by_th)
            st.dataframe(
                df_th[["thread_title", "report_name", "request_count", "total_tokens", "total_cost"]].rename(columns={
                    "thread_title": "Conversation Thread",
                    "report_name": "Associated Bugreport",
                    "request_count": "Messages",
                    "total_tokens": "Total Tokens",
                    "total_cost": "Cost ($ USD)"
                }),
                use_container_width=True
            )
        else:
            st.info("No thread activity logged yet.")
            
    with acc_tab3:
        st.markdown("### Daily Token Usage Trends")
        by_time = db.get_token_summary_over_time()
        if by_time:
            df_time = pd.DataFrame(by_time)
            fig_time = px.bar(
                df_time, x="date", y="total_tokens", color="model",
                title="Daily Token Consumption by Model"
            )
            st.plotly_chart(fig_time, use_container_width=True, key="token_time_chart")
        else:
            st.info("No daily history available yet.")
