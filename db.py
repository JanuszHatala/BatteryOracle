import os
import sqlite3
import json
import io
import pandas as pd
from datetime import datetime

DB_PATH = os.environ.get("BATTERY_ORACLE_DB_PATH", "battery_oracle.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_hash TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            custom_name TEXT NOT NULL,
            description TEXT DEFAULT '',
            timestamp_str TEXT,
            device_info TEXT,
            summary_text TEXT NOT NULL,
            chart_data_json TEXT NOT NULL,
            history_data_json TEXT NOT NULL,
            initial_analysis TEXT NOT NULL,
            reasoning_trace TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Safe migrations for reports if custom night window columns are missing
    cursor.execute("PRAGMA table_info(reports)")
    r_cols = [col["name"] for col in cursor.fetchall()]
    if "custom_night_start" not in r_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN custom_night_start TEXT DEFAULT NULL")
    if "custom_night_end" not in r_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN custom_night_end TEXT DEFAULT NULL")
    
    # 2. Chat Threads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
        )
    """)
    
    # 3. Chat Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            thread_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            filter_context TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE,
            FOREIGN KEY(thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
        )
    """)
    
    # Safe migrations for chat_messages if columns missing
    cursor.execute("PRAGMA table_info(chat_messages)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "thread_id" not in columns:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN thread_id INTEGER")
    if "filter_context" not in columns:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN filter_context TEXT DEFAULT ''")
    if "is_collapsed" not in columns:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN is_collapsed INTEGER DEFAULT 0")
    
    # 4. Token Ledger table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            thread_id INTEGER,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            cached_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER NOT NULL,
            cost_usd REAL DEFAULT 0.0,
            action_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 5. Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    # 6. Combined analyses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS combined_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_ids_key TEXT UNIQUE NOT NULL,
            analysis_text TEXT NOT NULL,
            reasoning_trace TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 7. Device Profiles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_name TEXT NOT NULL,
            device_model TEXT,
            os_build TEXT,
            raw_content TEXT NOT NULL,
            parsed_json TEXT NOT NULL,
            ai_analysis TEXT DEFAULT '',
            ai_analysis_trace TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("PRAGMA table_info(device_profiles)")
    dp_cols = [col["name"] for col in cursor.fetchall()]
    if "ai_analysis" not in dp_cols:
        cursor.execute("ALTER TABLE device_profiles ADD COLUMN ai_analysis TEXT DEFAULT ''")
    if "ai_analysis_trace" not in dp_cols:
        cursor.execute("ALTER TABLE device_profiles ADD COLUMN ai_analysis_trace TEXT DEFAULT ''")
    
    conn.commit()
    conn.close()

# --- Report CRUD ---

def save_report(file_hash, filename, custom_name, description, timestamp_str, device_info,
                summary_text, chart_df, history_df, initial_analysis, reasoning_trace=""):
    conn = get_connection()
    cursor = conn.cursor()
    
    chart_json = chart_df.to_json(orient='split') if chart_df is not None and not chart_df.empty else "{}"
    hist_json = history_df.to_json(orient='split', date_format='iso') if history_df is not None and not history_df.empty else "{}"
    
    cursor.execute("""
        INSERT INTO reports (
            file_hash, filename, custom_name, description, timestamp_str, device_info,
            summary_text, chart_data_json, history_data_json, initial_analysis, reasoning_trace
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_hash, filename, custom_name, description, timestamp_str, device_info,
        summary_text, chart_json, hist_json, initial_analysis, reasoning_trace
    ))
    
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    invalidate_report_cache()
    # Create default initial thread for this report
    create_thread(report_id, "General Diagnostics")
    return report_id

# In-memory report cache to prevent redundant heavy JSON parsing
_REPORT_CACHE = {}

def invalidate_report_cache(report_id=None):
    global _REPORT_CACHE
    if report_id is not None:
        _REPORT_CACHE.pop(report_id, None)
    else:
        _REPORT_CACHE.clear()

def get_report_by_hash(file_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE file_hash = ?", (file_hash,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return _deserialize_report(dict(row))
    return None

def get_report_by_id(report_id):
    if report_id in _REPORT_CACHE:
        return _REPORT_CACHE[report_id]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        rep = _deserialize_report(dict(row))
        _REPORT_CACHE[report_id] = rep
        return rep
    return None

def get_all_reports_summary():
    """Retrieve metadata summary for all reports without deserializing heavy JSON data."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, file_hash, filename, custom_name, description, timestamp_str, 
               device_info, created_at, custom_night_start, custom_night_end 
        FROM reports 
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_reports():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM reports ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [get_report_by_id(r["id"]) for r in rows]

def update_report_metadata(report_id, custom_name, description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE reports 
        SET custom_name = ?, description = ? 
        WHERE id = ?
    """, (custom_name, description, report_id))
    conn.commit()
    conn.close()
    invalidate_report_cache(report_id)

def update_report_night_window(report_id, start_dt, end_dt):
    """Persist custom night window boundaries for a report, or reset to NULL."""
    conn = get_connection()
    cursor = conn.cursor()
    s_val = start_dt.isoformat() if hasattr(start_dt, "isoformat") else (str(start_dt) if start_dt is not None else None)
    e_val = end_dt.isoformat() if hasattr(end_dt, "isoformat") else (str(end_dt) if end_dt is not None else None)
    cursor.execute("""
        UPDATE reports
        SET custom_night_start = ?, custom_night_end = ?
        WHERE id = ?
    """, (s_val, e_val, report_id))
    conn.commit()
    conn.close()
    invalidate_report_cache(report_id)

def update_report_analysis(report_id, analysis_text, reasoning_trace=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE reports 
        SET initial_analysis = ?, reasoning_trace = ? 
        WHERE id = ?
    """, (analysis_text, reasoning_trace, report_id))
    conn.commit()
    conn.close()
    invalidate_report_cache(report_id)


def delete_report(report_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE report_id = ?", (report_id,))
    cursor.execute("DELETE FROM chat_threads WHERE report_id = ?", (report_id,))
    cursor.execute("DELETE FROM token_ledger WHERE report_id = ?", (report_id,))
    cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    invalidate_report_cache(report_id)

# --- Thread Management ---

def create_thread(report_id, title="New Investigation"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_threads (report_id, title)
        VALUES (?, ?)
    """, (report_id, title))
    thread_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return thread_id

def get_threads_for_report(report_id, sort_by="updated_at"):
    conn = get_connection()
    cursor = conn.cursor()
    
    order_clause = "updated_at DESC"
    if sort_by == "created_at":
        order_clause = "created_at ASC"
    elif sort_by == "title":
        order_clause = "title ASC"
        
    if report_id is None:
        cursor.execute(f"SELECT * FROM chat_threads WHERE report_id IS NULL ORDER BY {order_clause}")
    else:
        cursor.execute(f"SELECT * FROM chat_threads WHERE report_id = ? ORDER BY {order_clause}", (report_id,))
        
    rows = cursor.fetchall()
    conn.close()
    
    threads = [dict(r) for r in rows]
    # Ensure at least one thread exists
    if not threads:
        if report_id is None:
            default_title = "Comparative Investigation"
        elif isinstance(report_id, int) and report_id < 0:
            default_title = "Profile Consultation"
        else:
            default_title = "General Diagnostics"
        new_id = create_thread(report_id, default_title)
        threads = [{"id": new_id, "report_id": report_id, "title": default_title, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}]
    return threads

def get_thread_by_id(thread_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def rename_thread(thread_id, new_title):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE chat_threads 
        SET title = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (new_title, thread_id))
    conn.commit()
    conn.close()

def delete_thread(thread_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE thread_id = ?", (thread_id,))
    cursor.execute("DELETE FROM chat_threads WHERE id = ?", (thread_id,))
    conn.commit()
    conn.close()

def fork_thread(source_thread_id, from_message_id, new_title="Forked Investigation"):
    """Create a new thread branching from source_thread_id up to from_message_id."""
    source_thread = get_thread_by_id(source_thread_id)
    if not source_thread:
        return None
        
    new_thread_id = create_thread(source_thread["report_id"], new_title)
    
    conn = get_connection()
    cursor = conn.cursor()
    # Get all messages up to from_message_id
    cursor.execute("""
        SELECT role, content, filter_context FROM chat_messages
        WHERE thread_id = ? AND id <= ?
        ORDER BY id ASC
    """, (source_thread_id, from_message_id))
    messages = cursor.fetchall()
    
    for msg in messages:
        cursor.execute("""
            INSERT INTO chat_messages (report_id, thread_id, role, content, filter_context)
            VALUES (?, ?, ?, ?, ?)
        """, (source_thread["report_id"], new_thread_id, msg["role"], msg["content"], msg["filter_context"]))
        
    conn.commit()
    conn.close()
    return new_thread_id

# --- Chat Messages ---

def save_chat_message(report_id, role, content, thread_id=None, filter_context=""):
    conn = get_connection()
    cursor = conn.cursor()
    
    if thread_id is None:
        threads = get_threads_for_report(report_id)
        thread_id = threads[0]["id"]
        
    cursor.execute("""
        INSERT INTO chat_messages (report_id, thread_id, role, content, filter_context)
        VALUES (?, ?, ?, ?, ?)
    """, (report_id, thread_id, role, content, filter_context))
    
    # Touch updated_at on thread
    cursor.execute("UPDATE chat_threads SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (thread_id,))
    
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return msg_id

def get_chat_messages(report_id, thread_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if thread_id is not None:
        cursor.execute("""
            SELECT id, report_id, thread_id, role, content, filter_context, is_collapsed, created_at 
            FROM chat_messages 
            WHERE thread_id = ? 
            ORDER BY id ASC
        """, (thread_id,))
    elif report_id is None:
        cursor.execute("""
            SELECT id, report_id, thread_id, role, content, filter_context, is_collapsed, created_at 
            FROM chat_messages 
            WHERE report_id IS NULL 
            ORDER BY id ASC
        """)
    else:
        cursor.execute("""
            SELECT id, report_id, thread_id, role, content, filter_context, is_collapsed, created_at 
            FROM chat_messages 
            WHERE report_id = ? 
            ORDER BY id ASC
        """, (report_id,))
        
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def toggle_message_collapsed(message_id, is_collapsed):
    """Update the persistent collapsed state of a specific chat message."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE chat_messages
        SET is_collapsed = ?
        WHERE id = ?
    """, (1 if is_collapsed else 0, message_id))
    conn.commit()
    conn.close()

def set_thread_messages_collapsed(thread_id, is_collapsed):
    """Update the persistent collapsed state for all messages in a specific thread."""
    conn = get_connection()
    cursor = conn.cursor()
    val = 1 if is_collapsed else 0
    if thread_id is not None:
        cursor.execute("""
            UPDATE chat_messages
            SET is_collapsed = ?
            WHERE thread_id = ?
        """, (val, thread_id))
    else:
        cursor.execute("""
            UPDATE chat_messages
            SET is_collapsed = ?
            WHERE thread_id IS NULL
        """, (val,))
    conn.commit()
    conn.close()

def clear_thread_messages(thread_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE thread_id = ?", (thread_id,))
    cursor.execute("UPDATE chat_threads SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (thread_id,))
    conn.commit()
    conn.close()

def delete_chat_message(message_id):
    """Delete a single chat message by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()

# --- Token & Cost Ledger ---

def log_token_usage(report_id, thread_id, provider, model, prompt_tokens,
                    completion_tokens, cached_tokens, total_tokens, cost_usd, action_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO token_ledger (
            report_id, thread_id, provider, model, prompt_tokens,
            completion_tokens, cached_tokens, total_tokens, cost_usd, action_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_id, thread_id, provider, model, prompt_tokens,
        completion_tokens, cached_tokens, total_tokens, cost_usd, action_type
    ))
    conn.commit()
    conn.close()

def get_token_totals():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as request_count,
            COALESCE(SUM(prompt_tokens), 0) as total_prompt,
            COALESCE(SUM(completion_tokens), 0) as total_completion,
            COALESCE(SUM(cached_tokens), 0) as total_cached,
            COALESCE(SUM(total_tokens), 0) as total_tokens,
            COALESCE(SUM(cost_usd), 0.0) as total_cost
        FROM token_ledger
    """)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {
        "request_count": 0, "total_prompt": 0, "total_completion": 0,
        "total_cached": 0, "total_tokens": 0, "total_cost": 0.0
    }

def get_token_summary_by_report():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            tl.report_id,
            COALESCE(r.custom_name, 'Global / Comparative') as report_name,
            COUNT(*) as request_count,
            SUM(tl.prompt_tokens) as prompt_tokens,
            SUM(tl.completion_tokens) as completion_tokens,
            SUM(tl.cached_tokens) as cached_tokens,
            SUM(tl.total_tokens) as total_tokens,
            SUM(tl.cost_usd) as total_cost
        FROM token_ledger tl
        LEFT JOIN reports r ON tl.report_id = r.id
        GROUP BY tl.report_id, r.custom_name
        ORDER BY total_tokens DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_token_summary_by_thread():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            tl.thread_id,
            COALESCE(ct.title, 'System / Non-Threaded') as thread_title,
            COALESCE(r.custom_name, 'Global') as report_name,
            COUNT(*) as request_count,
            SUM(tl.total_tokens) as total_tokens,
            SUM(tl.cost_usd) as total_cost
        FROM token_ledger tl
        LEFT JOIN chat_threads ct ON tl.thread_id = ct.id
        LEFT JOIN reports r ON tl.report_id = r.id
        GROUP BY tl.thread_id, ct.title, r.custom_name
        ORDER BY total_tokens DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_token_summary_over_time():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            model,
            COUNT(*) as request_count,
            SUM(prompt_tokens) as prompt_tokens,
            SUM(completion_tokens) as completion_tokens,
            SUM(cached_tokens) as cached_tokens,
            SUM(total_tokens) as total_tokens,
            SUM(cost_usd) as total_cost
        FROM token_ledger
        GROUP BY DATE(created_at), model
        ORDER BY date ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Settings ---

def get_setting(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["value"]
    return default

def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

# --- Combined Analysis ---

def save_combined_analysis(report_ids_key, analysis_text, reasoning_trace="", scope_key=None):
    key = f"{report_ids_key}_scope_{scope_key}" if scope_key else report_ids_key
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO combined_analyses (report_ids_key, analysis_text, reasoning_trace, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(report_ids_key) DO UPDATE SET
            analysis_text = excluded.analysis_text,
            reasoning_trace = excluded.reasoning_trace,
            updated_at = CURRENT_TIMESTAMP
    """, (key, analysis_text, reasoning_trace))
    conn.commit()
    conn.close()

def get_combined_analysis(report_ids_key, scope_key=None):
    key = f"{report_ids_key}_scope_{scope_key}" if scope_key else report_ids_key
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT analysis_text, reasoning_trace, updated_at FROM combined_analyses WHERE report_ids_key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "analysis_text": row["analysis_text"],
            "reasoning_trace": row["reasoning_trace"],
            "updated_at": row["updated_at"]
        }
    return None

# --- Master Experiment Synthesis ---

def save_master_synthesis(synthesis_text, reasoning_trace=""):
    set_setting("master_experiment_synthesis", synthesis_text)
    if reasoning_trace:
        set_setting("master_experiment_synthesis_trace", reasoning_trace)

def get_master_synthesis():
    text = get_setting("master_experiment_synthesis", "")
    trace = get_setting("master_experiment_synthesis_trace", "")
    return {"text": text, "trace": trace} if text else None

# --- Device Profiles CRUD ---

def save_device_profile(profile_name, raw_content, parsed_data, profile_id=None):
    """Insert or update a device configuration inventory profile."""
    conn = get_connection()
    cursor = conn.cursor()
    parsed_json = json.dumps(parsed_data, default=str)
    device_model = parsed_data.get("device_model", "Unknown Device")
    os_build = parsed_data.get("os_build", "Unknown OS")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if profile_id:
        cursor.execute("""
            UPDATE device_profiles
            SET profile_name = ?, device_model = ?, os_build = ?, raw_content = ?, parsed_json = ?, updated_at = ?
            WHERE id = ?
        """, (profile_name, device_model, os_build, raw_content, parsed_json, now_str, profile_id))
        saved_id = profile_id
    else:
        cursor.execute("""
            INSERT INTO device_profiles (profile_name, device_model, os_build, raw_content, parsed_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (profile_name, device_model, os_build, raw_content, parsed_json, now_str, now_str))
        saved_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return saved_id

def get_all_device_profiles():
    """Retrieve all device inventory profiles ordered by update time descending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM device_profiles ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    profiles = []
    for r in rows:
        p = dict(r)
        try:
            p["parsed_data"] = json.loads(p.get("parsed_json") or "{}")
        except Exception:
            p["parsed_data"] = {}
        profiles.append(p)
    return profiles

def get_device_profile(profile_id):
    """Retrieve single device profile by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM device_profiles WHERE id = ?", (profile_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    p = dict(row)
    try:
        p["parsed_data"] = json.loads(p.get("parsed_json") or "{}")
    except Exception:
        p["parsed_data"] = {}
    return p

def get_latest_device_profile():
    """Retrieve the most recently saved or updated device profile."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM device_profiles ORDER BY updated_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    p = dict(row)
    try:
        p["parsed_data"] = json.loads(p.get("parsed_json") or "{}")
    except Exception:
        p["parsed_data"] = {}
    return p

def update_device_profile_name(profile_id, new_name):
    """Rename a device profile."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE device_profiles
        SET profile_name = ?, updated_at = ?
        WHERE id = ?
    """, (new_name.strip(), now_str, profile_id))
    conn.commit()
    conn.close()

def update_device_profile_analysis(profile_id, analysis_text, reasoning_trace=""):
    """Update persisted AI analysis for a device profile."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE device_profiles
        SET ai_analysis = ?, ai_analysis_trace = ?, updated_at = ?
        WHERE id = ?
    """, (analysis_text, reasoning_trace, now_str, profile_id))
    conn.commit()
    conn.close()

def delete_device_profile(profile_id):
    """Delete a device profile by ID and clean up associated threads, messages, and token logs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM device_profiles WHERE id = ?", (profile_id,))
    # Profile threads are indexed by report_id = -profile_id
    prof_rep_id = -profile_id
    cursor.execute("DELETE FROM chat_messages WHERE report_id = ?", (prof_rep_id,))
    cursor.execute("DELETE FROM chat_threads WHERE report_id = ?", (prof_rep_id,))
    cursor.execute("DELETE FROM token_ledger WHERE report_id = ?", (prof_rep_id,))
    conn.commit()
    conn.close()



# --- Helpers ---

def _deserialize_report(report_dict):
    try:
        if report_dict.get("chart_data_json") and report_dict["chart_data_json"] != "{}":
            df_c = pd.read_json(io.StringIO(report_dict["chart_data_json"]), orient='split')
            try:
                import parser
                report_dict["chart_data"] = parser.clean_chart_dataframe(df_c, report_dict.get("summary_text", ""))
            except Exception:
                report_dict["chart_data"] = df_c
        else:
            report_dict["chart_data"] = pd.DataFrame()
    except Exception:
        report_dict["chart_data"] = pd.DataFrame()

    try:
        if report_dict.get("history_data_json") and report_dict["history_data_json"] != "{}":
            df_hist = pd.read_json(io.StringIO(report_dict["history_data_json"]), orient='split')
            if not df_hist.empty and "Time" in df_hist.columns:
                df_hist["Time"] = pd.to_datetime(df_hist["Time"])
            report_dict["history_data"] = df_hist
        else:
            report_dict["history_data"] = pd.DataFrame()
    except Exception:
        report_dict["history_data"] = pd.DataFrame()

    # Parse custom night window if stored
    if report_dict.get("custom_night_start"):
        try:
            report_dict["custom_night_start"] = pd.to_datetime(report_dict["custom_night_start"]).to_pydatetime()
        except Exception:
            report_dict["custom_night_start"] = None
    else:
        report_dict["custom_night_start"] = None

    if report_dict.get("custom_night_end"):
        try:
            report_dict["custom_night_end"] = pd.to_datetime(report_dict["custom_night_end"]).to_pydatetime()
        except Exception:
            report_dict["custom_night_end"] = None
    else:
        report_dict["custom_night_end"] = None

    return report_dict
