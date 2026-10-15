#!/usr/bin/env bash
# ==============================================================================
# Launcher for Deprecated Battery Oracle 1.0 (Streamlit)
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "⚠️  WARNING: Battery Oracle 1.0 (Streamlit) is deprecated."
echo "👉 Use Battery Oracle 2.0 (FastAPI + React) by running: ./run.sh"
echo ""

if [ -f ".venv/bin/streamlit" ]; then
    exec .venv/bin/streamlit run legacy/app.py
elif command -v streamlit &>/dev/null; then
    exec streamlit run legacy/app.py
else
    echo "❌ Error: streamlit is not installed in .venv or system PATH."
    exit 1
fi
