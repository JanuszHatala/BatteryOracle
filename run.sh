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

# Ensure streamlit is installed
if ! command -v streamlit >/dev/null 2>&1; then
    echo "⚠️ Streamlit not found in virtual environment. Installing dependencies..."
    pip install -r requirements.txt
fi

echo "🚀 Launching Battery Oracle in browser..."
exec streamlit run app.py "$@"
