# Battery Oracle 🔋🔮

An AI-powered local web application that parses complex Android bug reports and uses an LLM to explain battery drains in plain English, providing actionable optimization advice.

## Overview
Battery Oracle extracts key metrics (like CPU usage, wake locks, and alarms) from standard Android `dumpsys batterystats` and uses a Large Language Model to act as a Chat Assistant for your bug report.

## Setup & Installation

### Prerequisites
- Python 3.10+ (tested up to Python 3.13)
- ADB (Android Debug Bridge) installed and added to your system `PATH` (optional for GUI analysis, required for capturing bug reports and device inventory)

### 1. Install Dependencies
In your terminal, navigate to the project directory and install the required dependencies:

```bash
cd C:\DevWorkspaces\jh\ProjektyIT\Android\BatteryOracle
pip install -r requirements.txt
```

### 2. Configure API Key
Configure your AI model provider key in a `.env` file in the project root (or set it directly inside the app's **⚙️ AI & LLM Settings** dialog):

```env
GEMINI_API_KEY="AIzaSy..."
# Or for OpenRouter / OpenAI:
# OPENROUTER_API_KEY="sk-or-..."
# OPENAI_API_KEY="sk-..."
```

---

## Running the App

Start the Streamlit application from your terminal:

```bash
cd C:\DevWorkspaces\jh\ProjektyIT\Android\BatteryOracle
streamlit run app.py
```

Or via Python directly:

```bash
python -m streamlit run app.py
```

Once started, open your web browser and navigate to:
**`http://localhost:8501`**

---

## 🐳 Docker Deployment

Battery Oracle can be run as a containerized service with persistent data storage for SQLite reports and thread histories.

### Option A: Using Docker Compose (Recommended)

1. Ensure your `.env` file exists with your `GEMINI_API_KEY` (or other provider key).
2. Start the container:
   ```bash
   docker compose up -d
   ```
3. Open **`http://localhost:8501`** in your browser.
4. To stop the service:
   ```bash
   docker compose down
   ```

### Option B: Build and Run with Docker CLI

1. **Build the image locally:**
   ```bash
   docker build -t battery-oracle:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name battery-oracle \
     -p 8501:8501 \
     -e GEMINI_API_KEY="AIzaSy..." \
     -v battery_oracle_data:/app/data \
     battery-oracle:latest
   ```
   *(Replace `GEMINI_API_KEY` with your actual key, or pass `--env-file .env`)*.

3. Access the application at **`http://localhost:8501`**.

### Option C: Pulling from GitHub Container Registry (GHCR)

Once built by the automated GitHub Actions pipeline, you can pull and run directly:

```bash
docker run -d \
  --name battery-oracle \
  -p 8501:8501 \
  --env-file .env \
  -v battery_oracle_data:/app/data \
  ghcr.io/januszhatala/batteryoracle:latest
```

---

## How to Capture an Android Bug Report

To analyze your device's battery, you need a bug report. Follow these steps:

### 1. Enable Developer Options
1. On your Android device, go to **Settings > About phone**.
2. Tap on **Build number** 7 times until you see the message "You are now a developer!"
3. Go back to the main Settings menu and open **System > Developer options**.

### 2. Enable USB Debugging
1. In Developer options, scroll down to the Debugging section.
2. Toggle on **USB debugging**.

### 3. Generate the Bug Report via ADB
You will need ADB (Android Debug Bridge) installed on your computer.

1. Connect your phone to your computer via USB.
2. Open a terminal/command prompt and verify the connection:
   ```bash
   adb devices
   ```
   *(You may need to accept the RSA fingerprint prompt on your phone's screen).*
3. Reset the battery stats (optional, but highly recommended for a clean test):
   ```bash
   adb shell dumpsys batterystats --reset
   ```
4. Use your phone normally for a few hours (or overnight) to let it drain.
5. Capture the bug report:
   ```bash
   adb bugreport bugreport.zip
   ```
   This will save a `bugreport.zip` file to your current directory.

### 4. Analyze
Drag and drop the generated `bugreport.zip` into the Battery Oracle web interface to get your AI-powered diagnosis!

## Environment Variables
Since this tool uses an LLM, you will need to provide an API key. We use `LiteLLM` to support multiple providers (Gemini, OpenAI, Anthropic, etc.).

A `.env` file has been created for you in the project root. You just need to paste your API key inside it.

### How to get a Gemini API Key (Free)
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google Account.
3. Click on **Get API key** in the left sidebar.
4. Click **Create API key** (you can create it in a new project).
5. Copy the generated key and paste it into your `.env` file like this:
   ```env
   GEMINI_API_KEY="AIzaSy..."
   ```

*(For OpenAI or others, just add `OPENAI_API_KEY="your-key"` to the `.env` file).*
