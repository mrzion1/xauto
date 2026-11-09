@echo off
REM Postdeck launcher: creates a local virtualenv on first run, then starts the app.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [postdeck] First run: creating virtual environment...
    python -m venv .venv || goto :error
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)
".venv\Scripts\python.exe" main.py
exit /b 0

:error
echo [postdeck] Setup failed. Make sure Python 3.11+ is installed and on PATH.
pause
exit /b 1
