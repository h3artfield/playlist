@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  where py >nul 2>nul && ( py -3 -m venv venv ) || ( python -m venv venv )
  if errorlevel 1 (
    echo Install Python 3.10+ from https://www.python.org/downloads/ ^(check "Add python.exe to PATH"^).
    pause
    exit /b 1
  )
)

call "%~dp0venv\Scripts\activate.bat"
python -m pip install -q --upgrade pip
pip install -q -r "%~dp0requirements.txt"

echo.
echo Opening BINGE UI in your browser...
python -m streamlit run "%~dp0streamlit_app.py" --server.headless true --browser.gatherUsageStats false

pause
