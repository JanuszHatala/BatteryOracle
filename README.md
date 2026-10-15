# Battery Oracle 2.0 🔋🔮

An AI-powered Android battery telemetry & regression analysis platform. Battery Oracle parses complex Android bug reports (`batterystats`, `dumpstate`) and device configuration profiles to diagnose background standby drain, wakelocks, radio hunting, and kernel overhead in plain English with actionable CLI/GUI optimization steps.

Built with a high-performance **FastAPI** backend and a reactive **React 19** single-page application (SPA).

---

## Key Features

- **Multi-Scope Telemetry Analysis:**
  - 🌐 **Full Timeline:** Entire bugreport duration discharge curves and system events.
  - 🌙 **Night Standby:** Deep dive into sleep windows (preset hours or custom boundaries) with automatic night shading.
  - 📱 **Screen-Off Only:** Isolates pure idle standby losses from active screen-on usage.
  - ⏱️ **Custom Time Window:** Granular date/time bounding clamped safely to battery session limits.
- **Scope-Specific AI Diagnostics:** Independent, cached AI diagnoses generated for each analysis scope with interactive terminal code blocks and 1-click ADB command copying.
- **Hierarchical Chat Consultation:** Side-by-side or stacked investigation threads where the AI assistant dynamically receives the active report telemetry, device hardware profile, registered Wi-Fi router parameters, and scope-specific diagnosis.
- **Device Profile & System Settings Audit:** Live parsing of `adb shell settings list system/global/secure` and hardware dumps to cross-reference reported battery drain against existing phone hardening.
- **Wi-Fi Router Environment Profiling:** Ground Wi-Fi beacon wakeups and DTIM interval recommendations against specific router models (AsusWRT, TP-Link Deco, AVM FRITZ!Box, UniFi).
- **Comparative Regression Analysis:** Side-by-side comparison across multiple test sessions and an Executive Master Synthesis chronicle.
- **Token & Cost Ledger:** Precise token accounting and USD expenditure tracking across all LLM operations.

---

## Getting Started (Local Development)

### Prerequisites

- **Python:** 3.10 to 3.14
- **Node.js:** 20+ and `npm` (required for building or modifying the React frontend)
- **ADB (Android Debug Bridge):** Optional for viewing reports; required for capturing dumps from a connected Android device.

---

### 1. Quick Launch (Automated)

The project includes an all-in-one runner script that automatically initializes the Python virtual environment (`.venv`), installs dependencies, builds the frontend if needed, and starts the server on port **8088**:

```bash
./run.sh
```

To force a fresh frontend build during launch:
```bash
./run.sh --build
```

Once running, access the web interface at:
👉 **`http://localhost:8088`**

---

### 2. Manual Source Build & Execution

#### A. Backend Setup
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Start FastAPI server
uvicorn api_server:app --host 0.0.0.0 --port 8088 --reload
```

#### B. Frontend Development (Hot-Reloading)
For live frontend development with instant hot-module replacement (Vite dev server proxies `/api` calls to FastAPI on port 8088):
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** for the Vite development server.

#### C. Frontend Production Build
To compile the React SPA into static assets served directly by FastAPI:
```bash
cd frontend
npm run build
cd ..
rm -rf static/*
cp -R frontend/dist/* static/
```

---

## 🐳 Docker Deployment

Battery Oracle is fully containerized using a multi-stage Dockerfile that builds the React SPA and packages it with the FastAPI production runtime.

### 1. Local Docker Compose (Build from Source)

The local [`docker-compose.yml`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/docker-compose.yml) builds the container from source and mounts the local `./data` folder to persist your SQLite database:

```bash
# Start container in background
docker compose up --build -d

# Check container status
docker compose ps

# View live logs
docker compose logs -f

# Stop container
docker compose down
```

The application will be accessible at:
👉 **`http://localhost:8088`**

#### Persistent Data Storage
Your database is preserved across container rebuilds under:
- **Host Path:** `./data/battery_oracle.db`
- **Container Path:** `/app/data/battery_oracle.db`

---

### 2. Synology NAS Deployment (DSM 7.x)

Battery Oracle can be deployed on any Synology NAS running **Container Manager** (Docker) in DSM 7.0+. Multi-architecture images (`linux/amd64` and `linux/arm64`) are published automatically to GitHub Container Registry (GHCR).

#### Step-by-Step Synology Setup:

1. **Create Shared Directory on Synology:**
   - Open **File Station** on your NAS.
   - Navigate to your `docker` shared folder (e.g., `/volume1/docker/`).
   - Create a new directory named `battery-oracle`, and a subfolder named `data`:
     ```text
     /volume1/docker/battery-oracle/
     └── data/
     ```
   - *(Optional)* If migrating existing reports, copy your local `battery_oracle.db` file directly into `/volume1/docker/battery-oracle/data/`.

2. **Deploy via Container Manager:**
   - Open **Container Manager** in DSM.
   - Go to **Project** in the left sidebar and click **Create**.
   - Fill in project settings:
     - **Project Name:** `battery-oracle`
     - **Path:** Select `/docker/battery-oracle`
     - **Source:** Choose **Upload docker-compose.yml** and upload [`docker-compose.synology.yml`](file:///Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/docker-compose.synology.yml) (or paste its content).
   - Click **Next** > **Next** > **Done**.
   - Container Manager will automatically pull the multi-arch image matching your NAS CPU architecture (`linux/amd64` for Intel/AMD Celeron/Ryzen models; `linux/arm64` for Realtek models) and launch the service.

3. **Port & Access:**
   - **Exposed Port:** `8088`
   - **Web UI URL:** `http://<YOUR_SYNOLOGY_IP>:8088`
   - Ensure port `8088` is permitted through the Synology DSM Firewall if enabled.

4. **Updating Container on Synology:**
   - In Container Manager > Project > `battery-oracle` > Action > **Build / Pull latest image** > **Restart**.

---

## 🤖 AI Provider Configuration

Battery Oracle supports multiple LLM backends via LiteLLM:
- **Google Gemini** (Gemini 2.5 Flash, 2.5 Pro, 1.5 Pro)
- **OpenRouter** (DeepSeek R1/V3, Claude 3.5 Sonnet, Llama 3.3, Mistral)
- **OpenAI** (GPT-4o, o3-mini)
- **Local Ollama / LM Studio** (Local models running on private hardware)

Configure your API keys in your environment, `.env` file, or directly inside the app's **⚙️ Settings > LLM & Model Settings** dialog:

```env
# Google AI Studio key (Free tier available)
GEMINI_API_KEY="AIzaSy..."

# Or OpenRouter key
OPENROUTER_API_KEY="sk-or-..."

# Or OpenAI key
OPENAI_API_KEY="sk-..."
```

---

## 📱 How to Capture Bug Reports & Device Profiles

### 1. Capture Standard Battery Bug Report (via ADB)
```bash
# Verify USB connection to Android device
adb devices

# Reset battery statistics (optional, recommended for clean baseline)
adb shell dumpsys batterystats --reset

# Allow device to drain over desired period (e.g. overnight sleep)
# Then pull full bugreport zip:
adb bugreport bugreport.zip
```
Drag and drop `bugreport.zip` into Battery Oracle to analyze.

### 2. Capture Device Profile & System Settings Audit
In the **Device Profile & Audit** view, Battery Oracle generates an automated command that checks device connection and exports system configuration into a timestamped file:
```bash
adb get-state >/dev/null 2>&1 && (F="device_profile_$(date +%Y%m%d_%H%M%S).txt"; echo "=== BUILD DUMP ===" > "$F" && adb shell getprop >> "$F" && echo -e "\n=== BATTERYSTATS SYSTEM ===" >> "$F" && adb shell dumpsys batterystats --checkin >> "$F" && echo -e "\n=== SYSTEM SETTINGS ===" >> "$F" && adb shell settings list system >> "$F" && echo -e "\n=== GLOBAL SETTINGS ===" >> "$F" && adb shell settings list global >> "$F" && echo -e "\n=== SECURE SETTINGS ===" >> "$F" && adb shell settings list secure >> "$F" && echo "Saved to $F") || echo "Error: No Android device detected."
```
Upload the resulting `device_profile_*.txt` file to audit Doze states, background permissions, and system toggles.

---

## 🏛️ Legacy Streamlit Version (Retired)

The original Streamlit implementation (Battery Oracle 1.0) has been retired in favor of the React 19 + FastAPI architecture. It is preserved for reference under the `legacy/` directory:

```bash
# Run legacy version (requires streamlit installed in environment)
./legacy/run_legacy.sh
```

---

## 🧪 Testing & Verification

Run the full automated test suite (backend unit tests, parser regressions, API lifecycle, and end-to-end integration):

```bash
# Run pytest test suite
.venv/bin/pytest -v

# Run frontend TypeScript and build verification
npm --prefix frontend run build
```

---

## License

This project is licensed under the Apache License 2.0.
