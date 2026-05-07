#!/bin/bash
set -e

cd "$(dirname "$0")"

clear
echo
echo "============================================"
echo "  Contrarian 10-Bagger Engine"
echo "  Ranked speculative research, not advice"
echo "============================================"
echo

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Python was not found on this Mac."
    echo "Install Python 3 from https://www.python.org/downloads/macos/"
    echo "Then double-click this launcher again."
    echo
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating the local app environment..."
    "$PYTHON_CMD" -m venv .venv
fi

echo "Installing or updating the app packages..."
".venv/bin/python" -m pip install --disable-pip-version-check --upgrade pip -q
".venv/bin/python" -m pip install --disable-pip-version-check -q -r requirements.txt

echo
echo "Opening saved research workspace..."
".venv/bin/python" "main.py" --quick

echo
echo "Opening Contrarian 10-Bagger Engine..."
echo "Keep this Terminal window open while you use the dashboard."
".venv/bin/python" -m streamlit run "app/dashboard.py"

