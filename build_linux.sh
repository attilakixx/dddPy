#!/usr/bin/env bash
set -euo pipefail

ICON="dddPyIcon.png"
if [ -f "icon.png" ]; then
  ICON="icon.png"
elif [ -f "icon.ico" ]; then
  ICON="icon.ico"
fi

python3 -m PyInstaller --noconfirm --clean --onefile --windowed --name dddPy --icon "$ICON" app.py
