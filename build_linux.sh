#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"
VENV=".venv-build"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python not found. Set PYTHON=/path/to/python3 and retry." >&2
  exit 1
fi

if [ ! -d "$VENV" ]; then
  "$PYTHON" -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

ICON="dddPyIcon.png"
if [ -f "icon.png" ]; then
  ICON="icon.png"
elif [ -f "icon.ico" ]; then
  ICON="icon.ico"
fi

python -m PyInstaller --noconfirm --clean --onefile --windowed --name dddPy --icon "$ICON" app.py
