#!/usr/bin/env bash
set -e

# Determine project directory regardless of where script is called from
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
PROJECT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
cd "$PROJECT_DIR"

echo "⚡ Starting Battery Oracle..."

# Locate or create virtual environment
VENV_PATH=""
if [ -d ".venv" ]; then
    VENV_PATH=".venv"
elif [ -d "venv" ]; then
    VENV_PATH="venv"
fi

if [ -z "$VENV_PATH" ]; then
    echo "📦 Virtual environment not found. Creating .venv..."
    PYTHON_CMD=""
    for cmd in python3.14 python3.13 python3.12 python3.11 python3; do
        if command -v "$cmd" >/dev/null 2>&1; then
            PYTHON_CMD="$cmd"
            break
        fi
    done
    if [ -z "$PYTHON_CMD" ]; then
        echo "❌ Python 3 was not found on your system. Please install Python 3."
        exit 1
    fi
    echo "Using $PYTHON_CMD to create virtual environment..."
    "$PYTHON_CMD" -m venv .venv
    VENV_PATH=".venv"
    source "$VENV_PATH/bin/activate"
    echo "📥 Installing dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source "$VENV_PATH/bin/activate"
fi

# Ensure frontend is built and synced to static/
BUILD_FRONTEND=0
ARGS=()

for arg in "$@"; do
    if [ "$arg" == "--build" ]; then
        BUILD_FRONTEND=1
    else
        ARGS+=("$arg")
    fi
done

if [ ! -f "static/index.html" ] || [ "$BUILD_FRONTEND" -eq 1 ]; then
    echo "🏗️ Building React SPA frontend..."
    if command -v npm >/dev/null 2>&1; then
        (cd frontend && npm install && npm run build)
        mkdir -p static
        rm -rf static/*
        cp -R frontend/dist/* static/
        echo "✅ Frontend built and copied to static/."
    else
        echo "⚠️ npm not found. Skipping frontend build. Using existing static bundle if available."
    fi
fi

PORT="${PORT:-8088}"
echo "🚀 Launching Battery Oracle FastAPI + React Server on http://localhost:$PORT..."
exec uvicorn api_server:app --host 0.0.0.0 --port "$PORT" "${ARGS[@]}"
