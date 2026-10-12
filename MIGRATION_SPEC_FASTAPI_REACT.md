# BatteryOracle 2.0: Complete Architectural Specification & Migration Blueprint
**From Streamlit to FastAPI + React SPA with Unified Docker Deployment**

---

## 1. Executive Summary & Objective

### 1.1 Context
**BatteryOracle** is an Android telemetry diagnostic and AI consultation platform. It parses raw Android `bugreport` archives (`dumpsys batterystats`, `procstats`, Wi-Fi router logs, device inventory), calculates standby drain rates, visualizes discharge timelines, and orchestrates multi-model LLM reasoning (Google Gemini 3.x, OpenRouter) to diagnose battery drain regressions.

### 1.2 Motivation for Migration
The original prototype was built with **Streamlit**. While Streamlit enabled fast prototyping of Python scripts, its linear execution model and rigid Emotion CSS layout engine caused severe architectural friction for complex application UX:
- **No Native Desktop Layouts**: Lack of real resizable split panes, true dockable views, or draggable floating windows.
- **Rerun Inefficiencies**: Every UI click or input rerun the whole page or fragment, disrupting fine-grained interaction states and scrolling.
- **DOM/CSS Fighting**: Requiring dozens of fragile `!important` CSS overrides and injected JavaScript wrappers just to control textarea heights, Enter key behavior, button alignments, and modal margins.

### 1.3 Target Vision
Migrate the user-facing application to a **FastAPI + Modern React Single-Page Application (SPA)** packaged in a **single, self-contained Docker container**:
1. **Preserve 100% of Python Business Logic**: The existing, thoroughly tested parsing (`parser.py`), database layer (`db.py`), and AI orchestration (`llm_manager.py`) are reused directly.
2. **Production-Grade UX**: Modern component-based frontend (Vite, React 19, TypeScript, Tailwind CSS, Shadcn UI / Radix UI) providing native resizable panes, floating draggable modals, and keyboard-friendly chat.
3. **Zero Local Engine Dependencies**: Run everything via Docker (`docker compose up`), persisting all reports and chat histories via an external volume mount.
4. **Seamless Database Migration**: Direct drop-in compatibility for the existing SQLite database (`battery_oracle.db`).

---

## 2. System Architecture Blueprint

```
+-----------------------------------------------------------------------------------+
|                            Docker Container (Single Image)                        |
|                                                                                   |
|  +-----------------------------------+     +-----------------------------------+  |
|  |       React SPA (Vite/TS)         |     |       FastAPI Backend             |  |
|  | - Tailwind CSS + Shadcn UI        |     | - Python 3.12+ (Uvicorn)          |  |
|  | - Resizable Split Panes           |     | - StaticFiles mounts dist/ at /   |  |
|  | - Movable/Floating Chat Modal     |     | - REST & SSE Streaming Endpoints  |  |
|  | - Recharts / Plotly.js Visualizer |     | - CORS & Background Task Workers  |  |
|  +-----------------+-----------------+     +-----------------+-----------------+  |
|                    | HTTP / JSON / SSE                       |                    |
|                    +---------------------------------------->+                    |
|                                                              |                    |
|                                            +-----------------+-----------------+  |
|                                            |    Existing Python Modules        |  |
|                                            | - parser.py (Telemetry Extract)   |  |
|                                            | - llm_manager.py (Gemini 3.x API) |  |
|                                            | - db.py (SQLite DB Connector)     |  |
|                                            +-----------------+-----------------+  |
|                                                              |                    |
+--------------------------------------------------------------|--------------------+
                                                               v
                                             +-----------------------------------+
                                             |   Host Volume Mount: ./data       |
                                             |   - battery_oracle.db (SQLite)    |
                                             |   - raw_bugreports/ (Optional)    |
                                             +-----------------------------------+
```

---

## 3. Database Specification & Migration Strategy

### 3.1 Existing SQLite Database Architecture
The platform stores all state in SQLite (`battery_oracle.db`). The database schema consists of 8 primary tables:

1. **`reports`**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `file_hash` (TEXT UNIQUE NOT NULL - SHA256 of bugreport zip)
   - `filename` (TEXT NOT NULL)
   - `custom_name` (TEXT NOT NULL)
   - `description` (TEXT DEFAULT '')
   - `timestamp_str` (TEXT)
   - `device_info` (TEXT)
   - `summary_text` (TEXT NOT NULL - Raw telemetry extract)
   - `chart_data_json` (TEXT NOT NULL - Component drain breakdown)
   - `history_data_json` (TEXT NOT NULL - Sliced timeline samples)
   - `initial_analysis` (TEXT NOT NULL - Baseline LLM diagnosis markdown)
   - `reasoning_trace` (TEXT DEFAULT '')
   - `custom_night_start` (TEXT DEFAULT NULL - ISO timestamp override)
   - `custom_night_end` (TEXT DEFAULT NULL - ISO timestamp override)
   - `analysis_updated_at` (TEXT DEFAULT NULL)
   - `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

2. **`chat_threads`**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `report_id` (INTEGER REFERENCES reports(id) ON DELETE CASCADE - NULL for global comparison threads)
   - `title` (TEXT NOT NULL)
   - `created_at`, `updated_at` (TIMESTAMP)

3. **`chat_messages`**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `report_id` (INTEGER REFERENCES reports(id) ON DELETE CASCADE)
   - `thread_id` (INTEGER REFERENCES chat_threads(id) ON DELETE CASCADE)
   - `role` (TEXT NOT NULL - `'user'` | `'assistant'`)
   - `content` (TEXT NOT NULL)
   - `filter_context` (TEXT DEFAULT '' - e.g. `'🎯 Scope: Night Standby'`)
   - `is_collapsed` (INTEGER DEFAULT 0)
   - `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

4. **`token_ledger`**:
   - Tracks LLM tokens, model versions, cache hits, and estimated USD cost.

5. **`settings`**:
   - Key-value configuration (`device_timezone`, `night_start_hour`, `night_end_hour`, `chat_enter_mode`, `active_llm_provider`, `active_llm_model`, `gemini_api_key`, `openrouter_api_key`, etc.).

6. **`combined_analyses`**:
   - Multi-report comparative diagnoses (`report_ids_key`, `analysis_text`, `reasoning_trace`).

7. **`device_profiles`**:
   - Android system inventory files (`dumpsys package`, system settings, installed apps).

8. **`wifi_routers`**:
   - Wi-Fi AP registry (`router_name`, `brand`, `model`, `location_tag`, `specs_json`).

### 3.2 Migration Strategy (Zero Data Loss)
`db.py` already respects `BATTERY_ORACLE_DB_PATH`. Migration requires zero manual schema transformation:
1. When starting the Docker container, point `BATTERY_ORACLE_DB_PATH=/data/battery_oracle.db`.
2. Existing users simply copy their current `battery_oracle.db` into the host's `./data` folder before starting `docker compose`.
3. On FastAPI startup (`lifespan`), `db.init_db()` runs automatically. It executes non-destructive `PRAGMA table_info` checks and applies missing columns cleanly without altering existing data.

---

## 4. Backend API Contract (FastAPI)

FastAPI will serve both the REST API under `/api/v1` and static frontend assets under `/`.

### 4.1 Reports Management (`/api/v1/reports`)
- `GET /api/v1/reports`: List all saved reports with high-level KPIs, timestamps, and custom names.
- `POST /api/v1/reports/upload`: Multipart upload (`.zip` or `.txt` bugreport). Parses telemetry via `parser.parse_bugreport_zip` and saves to SQLite. Returns report object.
- `GET /api/v1/reports/{id}`: Full report details including summary, initial analysis, device info, and default bounds.
- `PUT /api/v1/reports/{id}`: Update custom name, description, or custom night window (`custom_night_start`, `custom_night_end`).
- `DELETE /api/v1/reports/{id}`: Delete report and cascade-delete its threads and messages.
- `GET /api/v1/reports/{id}/export-md`: Export formatted diagnostic report as Markdown.

### 4.2 Telemetry Slicing & Metrics (`/api/v1/reports/{id}/telemetry`)
- `GET /api/v1/reports/{id}/telemetry?scope={full|night|custom|screen_off}&start={iso}&end={iso}`:
  - Returns sliced timeline points for charting (`timestamp`, `battery_level`, `screen_state`).
  - Returns computed KPIs: `start_time`, `end_time`, `start_level`, `end_level`, `drop_pct`, `duration_hrs`, `rate_per_hr`, `status` (`Optimal`, `Elevated`, `Severe Drain`).
  - Returns top battery consumer component list (name, mAh, percentage).

### 4.3 AI Diagnosis Generation (`/api/v1/reports/{id}/diagnose`)
- `POST /api/v1/reports/{id}/diagnose`:
  - Body: `{ scope: "night" | "full" | "custom" | "screen_off", custom_start?: string, custom_end?: string }`
  - Streams or returns AI diagnosis markdown generated by `llm_manager.call_llm_tracked` with reasoning trace.

### 4.4 Chat & Consultation Threads (`/api/v1/reports/{id}/threads` & `/api/v1/threads`)
- `GET /api/v1/reports/{id}/threads`: List all threads for a report (id, title, message count, updated_at).
- `POST /api/v1/reports/{id}/threads`: Create a new thread (`title`).
- `PUT /api/v1/threads/{thread_id}`: Rename thread.
- `DELETE /api/v1/threads/{thread_id}`: Delete thread and all messages.
- `POST /api/v1/threads/{thread_id}/clear`: Clear messages in thread without deleting the thread.
- `GET /api/v1/threads/{thread_id}/messages`: List all messages in thread (role, content, filter_context, is_collapsed, created_at).
- `POST /api/v1/threads/{thread_id}/messages`: Send user message and stream/await assistant response:
  - Body: `{ content: string, filter_context?: string }`
  - Invocations trigger `llm_manager.call_llm_tracked` using structured history + telemetry context prompt.
  - Automatically titles new thread based on the first prompt if untitled.
- `PUT /api/v1/messages/{message_id}/collapse`: Toggle message collapsed state.
- `DELETE /api/v1/messages/{message_id}`: Delete specific message from conversation history.
- `POST /api/v1/threads/{thread_id}/fork`: Fork conversation from a specific `message_id` into a new thread.
- `GET /api/v1/threads/{thread_id}/export-md`: Export entire thread transcript as clean Markdown.

### 4.5 Comparative Multi-Report Analysis (`/api/v1/comparative`)
- `POST /api/v1/comparative/analyze`:
  - Body: `{ report_ids: number[], scope: string }`
  - Generates cross-report regression diagnosis comparing discharge slopes, wakelocks, and battery drain delta.

### 4.6 System Settings & LLM Configuration (`/api/v1/settings`)
- `GET /api/v1/settings`: Retrieve timezone, night hours, active provider, active model, and API key statuses (masked).
- `POST /api/v1/settings`: Update settings in SQLite.
- `GET /api/v1/models`: List active valid Gemini & OpenRouter models:
  - `gemini-3.8-flash` (Default standard)
  - `gemini-3.6-flash`
  - `gemini-3.5-flash-lite`
  - `gemini-3.1-flash-lite`

---

## 5. Frontend UI/UX Architecture (React + Tailwind + Shadcn UI)

### 5.1 Technology Stack
- **Framework**: Vite + React 19 + TypeScript.
- **Styling**: Tailwind CSS v3/v4 + Shadcn UI (accessible Radix UI primitives).
- **Icons**: `lucide-react`.
- **Layout Panes**: `react-resizable-panels` (smooth, persistent side-by-side dockable splits).
- **Charts**: `recharts` or `@observablehq/plot` (interactive battery discharge timelines with night shading and bar charts).
- **Markdown & Code**: `react-markdown` + `rehype-highlight` + `remark-gfm`.

### 5.2 Key Layout Views & UX Solved Out of the Box

#### View 1: Integrated AI Workspace (Resolving All Streamlit Layout Flaws)
The core workspace combines the **Diagnostic Report** and the **Investigation Chat** with an intuitive 3-state switcher:
1. **Side-by-side Mode (`👥`)**:
   - Uses `PanelGroup` and `PanelResizeHandle` from `react-resizable-panels`.
   - Left panel: Diagnostic report, discharge KPI cards, telemetry graphs.
   - Right panel: Investigation chat drawer.
   - User can drag the divider freely; pane widths are saved to `localStorage`.
2. **Stacked Mode (`📑`)**:
   - Report occupies full width on top; chat drawer occupies full width below.
3. **Floating Window Mode (`🪟`)**:
   - Report occupies 100% full width.
   - Chat window converts to a modern draggable and resizable modal overlay:
     - Header bar allows dragging anywhere on screen with boundary clamping.
     - Corner/edges allow standard CSS/JS resizing.
     - Geometry (`x`, `y`, `width`, `height`) is stored in `localStorage`.
     - Top-right of drag bar features a single, clean **"🗗 Dock to View"** button that seamlessly snaps the chat back to Side-by-side mode without page reloads.

#### View 2: Clean Chat Input & Keyboard Control
- **Auto-expanding Textarea**: Uses native textarea with auto-height adjustment up to a capped 35% viewport height, with smooth vertical scrolling when exceeded.
- **Shortcut Mode**:
  - `newline` mode (Default): `Enter` creates a clean new line. `Ctrl+Enter` (Windows/Linux) or `⌘+Enter` (macOS) submits the message.
  - `send` mode: `Enter` submits; `Shift+Enter` creates a new line.
  - **Togglable Control**: Directly above the textarea sits a subtle text link:
    `⌨️ Enter: New Line • Ctrl+Enter / ⌘+Enter: Send ⇄` (Clicking toggles mode and text flips immediately).
  - Absolutely positioned send button anchored in bottom-right corner without reserving empty space below multiline text.

#### View 3: Chat Message Cards & Controls
- **Card Layout**:
  - Left: Clean colored avatar pill (Vibrant green `#10b981` for User; Purple/Indigo `#8b5cf6` for Oracle AI).
  - Header: Timestamp (`YYYY-MM-DD HH:MM`), Scope pill, Token metrics, and Collapsible chevron (`▼` / `▶`).
  - Right-Anchored Actions: Both `🔀 Fork` and `🗑️ Delete` buttons are pinned flush against the far right edge using standard Tailwind `flex justify-end ml-auto gap-2`. No floating or displaced elements.
- **Smart Reading Scroll**:
  - Sending a message scrolls to show the sent message and live reasoning indicator.
  - When the assistant completes generation, the container scrolls smoothly to align with the **first line** of the assistant response, allowing immediate top-down reading.

#### View 4: Scope & Time Filter Bar
- Horizontal radio/pill group: `🌐 Full Session`, `🌙 Night Standby (Preset)`, `⏱️ Custom Window`, `📴 Screen-Off Only`.
- Detailed scope explanation panel sits **full-width directly below** the selector pills (eliminating awkward side-by-side squeezing).

---

## 6. Docker Containerization & Deployment Specification

### 6.1 Multi-Stage `Dockerfile`
A single Dockerfile builds the React frontend and packages the Python FastAPI backend:

```dockerfile
# Stage 1: Build Frontend SPA
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Backend
FROM python:3.12-slim
WORKDIR /app

# Prevent Python from writing .pyc and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BATTERY_ORACLE_DB_PATH=/data/battery_oracle.db

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY . .

# Copy compiled frontend from Stage 1 into backend's static directory
COPY --from=frontend-builder /app/frontend/dist /app/static

# Create data directory for volume mounting
RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 `docker-compose.yml`
```yaml
version: "3.8"

services:
  battery-oracle:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: battery_oracle_app
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      # Persistent host directory for SQLite DB and uploaded bugreport store
      - ./data:/data
    environment:
      - BATTERY_ORACLE_DB_PATH=/data/battery_oracle.db
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
```

### 6.3 Database Migration / Run Instructions for Users
1. Ensure existing `battery_oracle.db` is copied into `./data`:
   ```bash
   mkdir -p ./data
   cp /path/to/existing/battery_oracle.db ./data/
   ```
2. Start the container:
   ```bash
   docker compose up -d --build
   ```
3. Open browser at `http://localhost:8000`. All existing reports, threads, chat histories, and custom night windows load instantly.

---

## 7. Implementation Roadmap for the Coding Agent

Follow this phased checklist during the migration session:

### Phase 1: FastAPI Server & REST Wrapper (`api_server.py`)
- [ ] Create `api_server.py` and Pydantic schemas (`schemas.py`).
- [ ] Implement report endpoints: list, upload (`.zip`/`.txt`), get, update, delete, export.
- [ ] Implement telemetry slicing endpoints using `parser.get_filtered_telemetry_for_llm` and `parser.compute_kpis`.
- [ ] Implement diagnosis and chat endpoints using `llm_manager.call_llm_tracked` with thread and message CRUD.
- [ ] Implement settings, models, device profiles, and Wi-Fi router endpoints.
- [ ] Mount `/static` to serve SPA with catch-all fallback to `index.html`.
- [ ] Verify test suite with `pytest`.

### Phase 2: Frontend Scaffolding (`/frontend`)
- [ ] Initialize Vite + React + TypeScript in `frontend/`.
- [ ] Install Tailwind CSS, Shadcn UI (`button`, `card`, `dialog`, `dropdown-menu`, `input`, `textarea`, `tabs`, `badge`), and `lucide-react`.
- [ ] Install `react-resizable-panels` and `recharts`.
- [ ] Configure Axios / Fetch API client with base URL `/api/v1`.

### Phase 3: Telemetry & Report Components
- [ ] Report list sidebar / upload dropzone with progress bar.
- [ ] Battery discharge timeline chart with night interval shaded bands (`ReferenceArea`).
- [ ] KPI overview cards (discharge rate %/hr, drop %, health badge).
- [ ] Top energy consumers bar chart (`recharts` BarChart).
- [ ] Scope radio selector with full-width detail drawer.

### Phase 4: Integrated AI Workspace & Chat Drawer
- [ ] Side-by-side dockable panel using `PanelGroup` from `react-resizable-panels`.
- [ ] Draggable floating window modal with `localStorage` geometry persistence and "🗗 Dock to View" button.
- [ ] Auto-expanding textarea with Enter/Ctrl+Enter shortcut interceptor and swap toggle link.
- [ ] Thread selector, New Thread popover, Rename, and Clear/Delete actions.
- [ ] Chat message cards with green user avatar, right-aligned `🔀 Fork` and `🗑️ Delete` buttons, and smooth top-of-response scroll.

### Phase 5: Containerization & Verification
- [ ] Create multi-stage `Dockerfile` and `docker-compose.yml`.
- [ ] Test container build locally: verify volume mounting of existing `battery_oracle.db`.
- [ ] Verify full end-to-end functionality: file upload, telemetry slicing, AI consultation, thread branching, export.
