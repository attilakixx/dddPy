@echo off
setlocal

set VENV=.venv-build
if not exist "%VENV%\\Scripts\\python.exe" (
  python -m venv "%VENV%"
)

call "%VENV%\\Scripts\\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

set ICON=assets\\icon.ico
if not exist %ICON% (
  if exist assets\\icon.png set ICON=assets\\icon.png
  if exist assets\\dddPyIcon.png set ICON=assets\\dddPyIcon.png
)

python -m PyInstaller --noconfirm --clean --onefile --windowed --name dddPy --icon %ICON% --add-data "assets;assets" src\\app.py
endlocal
