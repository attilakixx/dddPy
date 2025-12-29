@echo off
setlocal

set VENV=.venv-build
if not exist "%VENV%\\Scripts\\python.exe" (
  python -m venv "%VENV%"
)

call "%VENV%\\Scripts\\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

set ICON=icon.ico
if not exist %ICON% (
  if exist icon.png set ICON=icon.png
  if exist dddPyIcon.png set ICON=dddPyIcon.png
)

python -m PyInstaller --noconfirm --clean --onefile --windowed --name dddPy --icon %ICON% app.py
endlocal
