@echo off
setlocal

set ICON=icon.ico
if not exist %ICON% (
  if exist icon.png set ICON=icon.png
  if exist dddPyIcon.png set ICON=dddPyIcon.png
)

python -m PyInstaller --noconfirm --clean --onefile --windowed --name dddPy --icon %ICON% app.py
endlocal
