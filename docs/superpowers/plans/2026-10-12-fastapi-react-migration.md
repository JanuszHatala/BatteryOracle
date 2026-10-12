# BatteryOracle 2.0: FastAPI + React SPA Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate BatteryOracle from a single-file Streamlit application to a high-performance FastAPI backend with a modern React 19 Single-Page Application (SPA) in a unified, multi-stage Docker container while preserving 100% of telemetry parsing and database history with zero data loss.

**Architecture:** A lightweight FastAPI server serves the REST API under `/api/v1` and static frontend assets under `/` with client-side fallback routing. The frontend is a modern React 19 SPA built with Vite, Tailwind CSS, and Radix/Lucide primitives, featuring a 3-state investigation workspace (side-by-side dockable panel via `react-resizable-panels`, stacked view, and floating draggable/resizable window with localStorage persistence). Data persistence connects directly to the existing SQLite database (`battery_oracle.db`) via volume mount at `/data`.

**Tech Stack:**
- Backend: Python 3.12+, FastAPI, Uvicorn, Pydantic v2, SQLite3, Pandas, LiteLLM.
- Frontend: Node 20+, Vite, React 19, TypeScript, Tailwind CSS, Recharts, `react-resizable-panels`, Lucide React, `react-markdown`.
- Packaging: Multi-stage Dockerfile (Node 20 alpine builder + Python 3.12 slim runtime), Docker Compose.

**Spec:** [`MIGRATION_SPEC_FASTAPI_REACT.md`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/MIGRATION_SPEC_FASTAPI_REACT.md)

## Global Constraints

- Preserve 100% of existing database contents in `battery_oracle.db`: zero destructive schema modifications or table drops.
- Preserve 100% of proven telemetry parsing logic in [`parser.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/parser.py), database layer in [`db.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/db.py), and AI orchestration in [`llm_manager.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/llm_manager.py).
- No em-dashes (`—`) in code, documentation, or response prose: use standard hyphens (`-`) or colons.
- Unified single-port deployment: FastAPI serves API at `/api/v1/*` and the compiled React SPA at `/*` on port 8000.
- Docker storage isolation: Host `./data` directory mapped to `/data` in container via `BATTERY_ORACLE_DB_PATH=/data/battery_oracle.db`.

## Review Focus

The five primary failure modes and edge cases addressed in this implementation:
1. Malformed or non-bugreport zip/txt uploads (empty zip, missing `bugreport-*.txt`): Server returns HTTP 400 Bad Request with an actionable diagnostic payload instead of unhandled 500 exceptions.
2. Inverted or out-of-bounds custom night bounds (`start_time >= end_time` or range outside recorded session): Telemetry service clamps to valid session bounds or falls back to preset night calculation without returning NaN or empty chart datasets.
3. Legacy SQLite database schema variations: Lifespan non-destructive `PRAGMA table_info` checks ensure all expected columns exist without truncating records.
4. LLM API errors or rate limits during consultation: Chat and diagnosis endpoints return structured error metadata with actionable suggestions while preserving the user's prompt in the database thread.
5. Large bugreport multipart upload buffering (>50MB): Endpoint uses spooling temporary files to prevent server memory exhaustion.

---

## User Review Required

> [!IMPORTANT]
> **Port Change from 8501 to 8000**: Streamlit previously ran on port 8501. The unified FastAPI + React container will run on port **8000**.
> **Database Location**: The default database path in Docker will be `/data/battery_oracle.db`, mounted from `./data/battery_oracle.db`. Existing databases in the repository root should be copied to `./data/` before running `docker compose up`.

> [!NOTE]
> During development, Vite dev server (`npm run dev`) runs on port 5173 with proxy configured to `http://localhost:8000` for FastAPI API calls. Production builds compile to `frontend/dist` which FastAPI serves directly.

---

## Open Questions

None currently blocking. Default behaviors adhere strictly to [`MIGRATION_SPEC_FASTAPI_REACT.md`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/MIGRATION_SPEC_FASTAPI_REACT.md).

---

## Proposed Changes and Bite-Sized Tasks

### Task 1: Core Telemetry Service & Pydantic Schemas

Extract presentation-agnostic telemetry calculation and Markdown formatting helpers from [`app.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/app.py) into a dedicated service module [`telemetry_service.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/telemetry_service.py), and define API Pydantic schemas in [`schemas.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/schemas.py).

**Files:**
- Create: [`schemas.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/schemas.py)
- Create: [`telemetry_service.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/telemetry_service.py)
- Create: [`tests/test_telemetry_service.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/tests/test_telemetry_service.py)
- Modify: [`requirements.txt`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/requirements.txt)

**Interfaces:**
- Consumes: [`parser.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/parser.py), [`db.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/db.py), [`llm_manager.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/llm_manager.py).
- Produces:
  - `schemas.ReportSummary`, `schemas.ReportDetail`, `schemas.TelemetryResponse`, `schemas.KpiMetrics`, `schemas.DiagnosisRequest`, `schemas.ThreadResponse`, `schemas.MessageResponse`, `schemas.SettingsResponse`.
  - `telemetry_service.process_bugreport_upload(filename: str, file_bytes: bytes, timezone: str, auto_diagnose: bool = False) -> dict`
  - `telemetry_service.get_effective_telemetry_bounds(report: dict, scope: str, custom_start_str: str | None = None, custom_end_str: str | None = None) -> tuple[datetime, datetime, pd.DataFrame]`
  - `telemetry_service.build_telemetry_payload(report: dict, scope: str, custom_start: str | None = None, custom_end: str | None = None) -> dict`
  - `telemetry_service.build_single_report_markdown(report: dict, filter_mode: str, kpis: dict, diagnosis_text: str) -> str`
  - `telemetry_service.build_comparative_markdown(reports: list[dict], filter_mode: str, analysis_text: str) -> str`

- [ ] **Step 1: Write failing tests in `tests/test_telemetry_service.py`**
  Cover `process_bugreport_upload` with synthetic bugreport content, invalid zip failure handling, bounds clamping with inverted timestamps, and markdown generation.

- [ ] **Step 2: Run test to verify it fails**
  Run: `.venv/bin/pytest tests/test_telemetry_service.py -v`
  Expected: FAIL (modules not found).

- [ ] **Step 3: Update `requirements.txt` and install dependencies**
  Add `fastapi>=0.115.0`, `uvicorn>=0.30.0`, `pydantic>=2.8.0`, `python-multipart>=0.0.9`. Run `.venv/bin/pip install -r requirements.txt`.

- [ ] **Step 4: Implement `schemas.py` and `telemetry_service.py`**
  Implement Pydantic models in `schemas.py` and decoupled business logic in `telemetry_service.py`.

- [ ] **Step 5: Run tests to verify they pass**
  Run: `.venv/bin/pytest tests/test_telemetry_service.py -v`
  Expected: PASS.

- [ ] **Step 6: Commit**
  Run: `git add schemas.py telemetry_service.py requirements.txt tests/test_telemetry_service.py && git commit -m "feat(telemetry): add telemetry service and schemas"`

---

### Task 2: FastAPI Application Setup & Report Management Endpoints

Implement [`api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/api_server.py) with CORS middleware, lifespan database initialization, health check, and full report CRUD endpoints (`/api/v1/reports`).

**Files:**
- Create: [`api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/api_server.py)
- Create: [`tests/test_api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/tests/test_api_server.py)

**Interfaces:**
- Consumes: [`telemetry_service.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/telemetry_service.py), [`schemas.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/schemas.py), [`db.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/db.py).
- Produces:
  - `GET /api/v1/health` -> `{"status": "ok", "version": "2.0.0"}`
  - `GET /api/v1/reports` -> `list[schemas.ReportSummary]`
  - `POST /api/v1/reports/upload` -> `schemas.ReportDetail`
  - `GET /api/v1/reports/{id}` -> `schemas.ReportDetail`
  - `PUT /api/v1/reports/{id}` -> `schemas.ReportDetail`
  - `DELETE /api/v1/reports/{id}` -> `{"deleted": true, "id": int}`
  - `GET /api/v1/reports/{id}/export-md` -> Markdown text / attachment

- [ ] **Step 1: Write failing tests in `tests/test_api_server.py`**
  Write tests for health check, listing reports, uploading a valid zip, rejecting invalid upload, updating report name/night bounds, and deleting a report.

- [ ] **Step 2: Run test to verify it fails**
  Run: `.venv/bin/pytest tests/test_api_server.py -k "test_health or test_reports" -v`
  Expected: FAIL (module not found).

- [ ] **Step 3: Implement `api_server.py` with report endpoints**
  Configure FastAPI app, lifespan invoking `db.init_db()`, CORS middleware, exception handlers, and `/api/v1/reports` router.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `.venv/bin/pytest tests/test_api_server.py -k "test_health or test_reports" -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add api_server.py tests/test_api_server.py && git commit -m "feat(api): scaffold fastapi and report endpoints"`

---

### Task 3: Telemetry Slicing, Diagnosis & Comparative Analysis Endpoints

Implement endpoints for telemetry calculations with different scopes (`full`, `night`, `custom`, `screen_off`), AI diagnosis triggers, and multi-report comparative evaluations.

**Files:**
- Modify: [`api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/api_server.py)
- Modify: [`tests/test_api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/tests/test_api_server.py)

**Interfaces:**
- Consumes: [`telemetry_service.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/telemetry_service.py), [`llm_manager.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/llm_manager.py), [`db.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/db.py).
- Produces:
  - `GET /api/v1/reports/{id}/telemetry` -> `schemas.TelemetryResponse`
  - `POST /api/v1/reports/{id}/diagnose` -> `schemas.DiagnosisResponse`
  - `POST /api/v1/comparative/analyze` -> `schemas.ComparativeResponse`
  - `GET /api/v1/comparative/export-md` -> Markdown text

- [ ] **Step 1: Write failing tests in `tests/test_api_server.py`**
  Add tests for telemetry slicing by scope (`full`, `night`, `custom`), out-of-bounds handling, mock LLM diagnosis generation, and comparative report analysis.

- [ ] **Step 2: Run test to verify it fails**
  Run: `.venv/bin/pytest tests/test_api_server.py -k "test_telemetry or test_diagnose or test_comparative" -v`
  Expected: FAIL.

- [ ] **Step 3: Implement endpoints in `api_server.py`**
  Implement `/api/v1/reports/{id}/telemetry`, `/api/v1/reports/{id}/diagnose`, and `/api/v1/comparative/*` routes with error handling.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `.venv/bin/pytest tests/test_api_server.py -k "test_telemetry or test_diagnose or test_comparative" -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add api_server.py tests/test_api_server.py && git commit -m "feat(api): add telemetry slicing and diagnosis endpoints"`

---

### Task 4: Chat Consultation Threads & Message Endpoints

Implement full thread management and interactive LLM consultation endpoints, supporting thread creation, auto-titling, fork, clear, message deletion, collapse toggles, and Markdown transcript export.

**Files:**
- Modify: [`api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/api_server.py)
- Modify: [`tests/test_api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/tests/test_api_server.py)

**Interfaces:**
- Consumes: [`db.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/db.py), [`llm_manager.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/llm_manager.py), [`telemetry_service.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/telemetry_service.py).
- Produces:
  - `GET /api/v1/reports/{id}/threads` -> `list[schemas.ThreadResponse]`
  - `POST /api/v1/reports/{id}/threads` -> `schemas.ThreadResponse`
  - `PUT /api/v1/threads/{id}` -> `schemas.ThreadResponse`
  - `DELETE /api/v1/threads/{id}` -> `{"deleted": true, "id": int}`
  - `POST /api/v1/threads/{id}/clear` -> `{"cleared": true, "id": int}`
  - `GET /api/v1/threads/{id}/messages` -> `list[schemas.MessageResponse]`
  - `POST /api/v1/threads/{id}/messages` -> `schemas.MessageResponse` (executes LLM with context and saves assistant response)
  - `PUT /api/v1/messages/{id}/collapse` -> `schemas.MessageResponse`
  - `DELETE /api/v1/messages/{id}` -> `{"deleted": true, "id": int}`
  - `POST /api/v1/threads/{id}/fork` -> `schemas.ThreadResponse`
  - `GET /api/v1/threads/{id}/export-md` -> Markdown transcript

- [ ] **Step 1: Write failing tests in `tests/test_api_server.py`**
  Test thread creation, sending a message with mocked LLM response, verifying auto-titling of first message, message collapse, thread fork from message, and markdown transcript export.

- [ ] **Step 2: Run test to verify it fails**
  Run: `.venv/bin/pytest tests/test_api_server.py -k "test_chat" -v`
  Expected: FAIL.

- [ ] **Step 3: Implement chat endpoints in `api_server.py`**
  Implement thread and message operations with robust error handling preserving user input on LLM failures.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `.venv/bin/pytest tests/test_api_server.py -k "test_chat" -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add api_server.py tests/test_api_server.py && git commit -m "feat(api): add chat threads and messages endpoints"`

---

### Task 5: System Settings, Models, Device Profiles & Wi-Fi Routers Endpoints

Implement API routes for settings, provider model listings, API key verification, device profile audits, and Wi-Fi router configurations.

**Files:**
- Modify: [`api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/api_server.py)
- Modify: [`tests/test_api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/tests/test_api_server.py)

**Interfaces:**
- Consumes: [`db.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/db.py), [`llm_manager.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/llm_manager.py), [`parser.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/parser.py).
- Produces:
  - `GET /api/v1/settings` & `POST /api/v1/settings`
  - `GET /api/v1/models` & `POST /api/v1/settings/test-connection`
  - `GET /api/v1/device-profiles` & `POST /api/v1/device-profiles/upload` & `DELETE /api/v1/device-profiles/{id}`
  - `GET /api/v1/wifi-routers` & `POST /api/v1/wifi-routers` & `PUT /api/v1/wifi-routers/{id}` & `DELETE /api/v1/wifi-routers/{id}`

- [ ] **Step 1: Write failing tests in `tests/test_api_server.py`**
  Test updating settings, fetching models list, device profile parsing/storage, and Wi-Fi router CRUD.

- [ ] **Step 2: Run test to verify it fails**
  Run: `.venv/bin/pytest tests/test_api_server.py -k "test_settings or test_profiles or test_routers" -v`
  Expected: FAIL.

- [ ] **Step 3: Implement settings, profile, and router endpoints in `api_server.py`**
  Wire handlers directly to `db.py` and `llm_manager.py`.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `.venv/bin/pytest tests/test_api_server.py -v`
  Expected: All API tests pass.

- [ ] **Step 5: Commit**
  Run: `git add api_server.py tests/test_api_server.py && git commit -m "feat(api): add settings, profiles, and router endpoints"`

---

### Task 6: Frontend Project Scaffolding, Design System & API Client

Initialize the React 19 + TypeScript SPA in `frontend/`, configure Tailwind CSS, set up styling variables and base UI components, and build the typed API client.

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/ui/` primitives (Button, Card, Input, Textarea, Badge, Tabs, Dialog)

**Interfaces:**
- Consumes: Backend `/api/v1/*` endpoints.
- Produces: Typed TypeScript definitions matching backend Pydantic schemas; reusable UI components; API client module with typed async methods.

- [ ] **Step 1: Create package.json and install frontend dependencies**
  Configure React 19, Vite, TypeScript, Tailwind CSS, Lucide React, `react-resizable-panels`, `recharts`, `react-markdown`, `remark-gfm`, and classnames utilities. Run `npm install` in `frontend/`.

- [ ] **Step 2: Configure Vite and Tailwind**
  Set up `vite.config.ts` with API proxy forwarding `/api/v1` to `http://localhost:8000`. Configure Tailwind CSS with dark slate theme and custom branding colors (`#10b981` green, `#8b5cf6` indigo).

- [ ] **Step 3: Implement TypeScript types in `frontend/src/types/api.ts`**
  Map all schemas: `ReportSummary`, `ReportDetail`, `TelemetryResponse`, `Thread`, `Message`, `Settings`, `Router`, `DeviceProfile`.

- [ ] **Step 4: Implement API client in `frontend/src/api/client.ts`**
  Implement typed Fetch/Axios helper functions with error unwrapping.

- [ ] **Step 5: Implement UI primitives in `frontend/src/components/ui/`**
  Create accessible Button, Card, Badge, Dialog/Modal, Input, Textarea.

- [ ] **Step 6: Verify frontend build**
  Run: `cd frontend && npm run build`
  Expected: Successful compilation to `frontend/dist/`.

- [ ] **Step 7: Commit**
  Run: `git add frontend/ && git commit -m "feat(frontend): scaffold react 19 spa with tailwind and api client"`

---

### Task 7: Report Navigation, Upload Dropzone & Comparative View

Build the main shell: Header with model badge, Report list sidebar with drain indicators, Drag-and-drop bugreport upload modal, Comparative multi-report view, and Settings modal.

**Files:**
- Create: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/reports/UploadModal.tsx`
- Create: `frontend/src/components/reports/ComparativeView.tsx`
- Create: `frontend/src/components/settings/SettingsModal.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `api/client.ts`, UI primitives.
- Produces: Report selection state, comparative multi-selection state, file upload trigger, modal controls.

- [ ] **Step 1: Implement `Sidebar.tsx` and `Header.tsx`**
  Include report search/filter, drain velocity badge pill, date display, comparative mode checkbox selection, and delete report button.

- [ ] **Step 2: Implement `UploadModal.tsx`**
  Drag-and-drop zone for `.zip` and `.txt` bugreports with active upload progress indicator and auto-redirect to newly imported report.

- [ ] **Step 3: Implement `ComparativeView.tsx`**
  Side-by-side metrics table, multi-report discharge chart, and "Synthesize Comparison" LLM button with scope selector.

- [ ] **Step 4: Implement `SettingsModal.tsx`**
  Tabs for LLM keys (Gemini, OpenRouter), model selector dropdown, timezone input, night window hours (start/end), and Enter shortcut mode preference.

- [ ] **Step 5: Verify frontend build**
  Run: `cd frontend && npm run build`
  Expected: PASS.

- [ ] **Step 6: Commit**
  Run: `git add frontend/src/ && git commit -m "feat(frontend): add sidebar, upload modal, comparative view and settings"`

---

### Task 8: Diagnostic Workspace: KPIs, Discharge Timeline Chart & Scope Selector

Implement the diagnostic report view: 4-scope radio selector with explanation panel, 5 KPI cards, Recharts battery timeline chart with night shading, top energy consumers bar chart, and AI diagnosis markdown viewer.

**Files:**
- Create: `frontend/src/components/reports/ReportWorkspace.tsx`
- Create: `frontend/src/components/reports/ScopeSelector.tsx`
- Create: `frontend/src/components/reports/KpiGrid.tsx`
- Create: `frontend/src/components/reports/DischargeChart.tsx`
- Create: `frontend/src/components/reports/TopConsumersChart.tsx`
- Create: `frontend/src/components/reports/DiagnosisCard.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `schemas.TelemetryResponse`, `schemas.ReportDetail`.
- Produces: Interactive telemetry visualizations, night reference area bands, re-diagnosis triggers.

- [ ] **Step 1: Implement `ScopeSelector.tsx`**
  Horizontal pill group (`🌐 Full Session`, `🌙 Night Standby`, `⏱️ Custom Window`, `📴 Screen-Off Only`) with informative explanation card rendered full-width below.

- [ ] **Step 2: Implement `KpiGrid.tsx`**
  Cards for Discharge Rate (%/hr) with health status badge (Optimal green, Elevated amber, Severe red), Total Drop %, Active Duration, and Battery Start/End levels.

- [ ] **Step 3: Implement `DischargeChart.tsx` and `TopConsumersChart.tsx`**
  Discharge chart with Recharts `ResponsiveContainer`, `LineChart`, tooltip, and `ReferenceArea` shading night standby periods. Bar chart showing top mAh drain components with resolved package labels.

- [ ] **Step 4: Implement `DiagnosisCard.tsx`**
  Markdown rendering with code syntax highlighting, copy markdown action, export report action, and "Re-diagnose Scope" trigger.

- [ ] **Step 5: Verify frontend build**
  Run: `cd frontend && npm run build`
  Expected: PASS.

- [ ] **Step 6: Commit**
  Run: `git add frontend/src/components/reports/ && git commit -m "feat(frontend): add report workspace, charts and kpis"`

---

### Task 9: AI Investigation Chat: 3-State Workspace (Side-by-side, Stacked, Draggable Floating Modal)

Implement the investigation chat experience solving all previous Streamlit layout flaws: side-by-side resizable panel (`react-resizable-panels`), stacked mode, and draggable/resizable floating modal with localStorage persistence and "Dock to View" button; keyboard-friendly auto-expanding textarea; message cards with right-aligned actions and top-of-response auto-scroll.

**Files:**
- Create: `frontend/src/components/chat/ChatWorkspace.tsx`
- Create: `frontend/src/components/chat/ChatMessageCard.tsx`
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/components/chat/ThreadManager.tsx`
- Create: `frontend/src/components/chat/FloatingWindow.tsx`
- Modify: `frontend/src/components/reports/ReportWorkspace.tsx`

**Interfaces:**
- Consumes: `api/client.ts`, thread and message state.
- Produces: 3-state workspace switcher, keyboard shortcuts interceptor, thread branching/forking, message collapse toggles.

- [ ] **Step 1: Implement `ThreadManager.tsx`**
  Thread selector dropdown, "+ New Investigation" trigger, inline rename, clear messages, and export transcript to Markdown.

- [ ] **Step 2: Implement `ChatInput.tsx`**
  Native textarea auto-expanding up to 35% viewport height; clickable toggle link: `⌨️ Enter: New Line • Ctrl+Enter / ⌘+Enter: Send ⇄`; Enter/Ctrl+Enter interceptor; absolutely positioned send button in bottom-right corner.

- [ ] **Step 3: Implement `ChatMessageCard.tsx`**
  Green user pill (`#10b981`), purple/indigo assistant pill (`#8b5cf6`), scope pill, token metrics, collapse toggle, right-aligned `🔀 Fork` and `🗑️ Delete` actions, and smooth scroll to first line of assistant reply.

- [ ] **Step 4: Implement `FloatingWindow.tsx` and 3-state workspace in `ChatWorkspace.tsx`**
  Integrate `react-resizable-panels` `PanelGroup` for Side-by-side mode (`👥`); Stacked mode (`📑`); Floating modal (`🪟`) with drag handle, boundary clamping, corner resizing, `localStorage` geometry persistence, and "🗗 Dock to View" button snapping back to side-by-side mode.

- [ ] **Step 5: Verify frontend build**
  Run: `cd frontend && npm run build`
  Expected: PASS.

- [ ] **Step 6: Commit**
  Run: `git add frontend/src/components/chat/ && git commit -m "feat(frontend): add 3-state chat workspace, keyboard control, and message cards"`

---

### Task 10: Static SPA Integration, Multi-Stage Dockerfile & End-to-End Verification

Configure FastAPI to serve compiled frontend assets with client-side routing fallback, package everything into a production multi-stage `Dockerfile` and `docker-compose.yml`, and verify complete end-to-end functionality on the real `battery_oracle.db`.

**Files:**
- Modify: [`api_server.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/api_server.py)
- Modify: [`Dockerfile`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/Dockerfile)
- Modify: [`docker-compose.yml`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/docker-compose.yml)
- Create: [`tests/test_e2e_integration.py`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/tests/test_e2e_integration.py)

**Interfaces:**
- Consumes: `frontend/dist/`, `api_server.py`, `battery_oracle.db`.
- Produces: Single Docker container image serving API and frontend on port 8000 with volume-mounted database.

- [ ] **Step 1: Configure static file serving and SPA fallback in `api_server.py`**
  Mount `static/` at `/`. Add catch-all route serving `static/index.html` for unknown routes not beginning with `/api/`.

- [ ] **Step 2: Update `Dockerfile` to multi-stage build**
  Stage 1: `node:20-alpine` builds frontend SPA to `frontend/dist`.
  Stage 2: `python:3.12-slim` installs python dependencies, copies backend code and compiled frontend to `static/`, exposes port 8000 with healthcheck.

- [ ] **Step 3: Update `docker-compose.yml`**
  Map port 8000:8000, volume mount `./data:/data`, environment variable `BATTERY_ORACLE_DB_PATH=/data/battery_oracle.db`.

- [ ] **Step 4: Write and run end-to-end integration tests in `tests/test_e2e_integration.py`**
  Test static asset serving, SPA fallback, full report and chat flow on an isolated test database.
  Run: `.venv/bin/pytest tests/ -v`
  Expected: All unit and integration tests pass.

- [ ] **Step 5: Build frontend and verify Docker container build**
  Run `npm run build` in `frontend/`.
  Run: `docker compose build` to verify the multi-stage build finishes with 0 errors.

- [ ] **Step 6: Commit**
  Run: `git add Dockerfile docker-compose.yml api_server.py tests/test_e2e_integration.py && git commit -m "feat(deploy): add multi-stage dockerfile, spa static mounting, and e2e tests"`

---

## Verification Plan

### Automated Tests
1. **Telemetry & Schemas Unit Tests**:
   ```bash
   .venv/bin/pytest tests/test_telemetry_service.py -v
   ```
2. **FastAPI REST API Tests**:
   ```bash
   .venv/bin/pytest tests/test_api_server.py -v
   ```
3. **End-to-End Integration Tests**:
   ```bash
   .venv/bin/pytest tests/test_e2e_integration.py -v
   ```
4. **Complete Python Test Suite**:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
5. **Frontend Typecheck & Build**:
   ```bash
   cd frontend && npm run build
   ```
6. **Docker Multi-Stage Build**:
   ```bash
   docker compose build
   ```

### Manual Verification
1. **Container Launch & DB Verification**:
   - Copy `battery_oracle.db` into `./data/`.
   - Run `docker compose up -d`.
   - Verify `curl -f http://localhost:8000/api/v1/health` returns status `ok`.
2. **Browser Exploration (`http://localhost:8000`)**:
   - Verify all 34 existing reports appear in the sidebar with proper timestamps and drain rate badges.
   - Select a report: verify discharge timeline chart renders with night standby shaded bands and top consumers bar chart renders.
   - Switch scopes (`🌐 Full Session`, `🌙 Night Standby`, `⏱️ Custom Window`, `📴 Screen-Off Only`): verify KPIs and chart update immediately.
   - Test Investigation Chat:
     - Toggle Side-by-side mode (`👥`): drag panel separator to resize.
     - Toggle Stacked mode (`📑`): check vertical layout.
     - Toggle Floating Window mode (`🪟`): drag header around screen, resize from corner, reload page to verify geometry persists in `localStorage`, and click "🗗 Dock to View" to snap back to Side-by-side.
     - Type in chat input: verify `Enter: New Line` creates line break without submitting; click shortcut toggle to flip to `Enter: Send`; test submitting a question and verify AI responds with top-of-message auto-scroll.
     - Click `🔀 Fork` on a message: verify new branched thread is created.
     - Click `Export Report Markdown` and `Export Chat Markdown`: verify clean download without HTML artifacts.
