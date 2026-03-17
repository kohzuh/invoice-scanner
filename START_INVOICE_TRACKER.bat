@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" -m pip install -r requirements.txt
start "Invoice Tracker" cmd /k ""%~dp0.venv\Scripts\python.exe" "%~dp0app.py""
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:5000