#!/bin/bash
set -e

cd "$(dirname "$0")"

clear
echo
echo "============================================"
echo "  Contrarian 10-Bagger Engine Data Refresh"
echo "  This may take several minutes"
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
echo "Refreshing the research watchlist..."
".venv/bin/python" "main.py"

echo
echo "Refresh complete."
read -n 1 -s -r -p "Press any key to close..."

