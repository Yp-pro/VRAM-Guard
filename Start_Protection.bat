@echo off
:: Ensure we are in the script directory
cd /d "%~dp0"

echo [VRAM Guard] Initializing stealth protection...

:: 1. Check if virtual environment exists
if not exist "venv\Scripts\pythonw.exe" (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    pause
    exit /b
)

:: 2. Launch using pythonw.exe (no console window)
:: 'start /b' runs it in background
start "" "venv\Scripts\pythonw.exe" vram_guard.py

echo [SUCCESS] VRAM Guard is now running in the system tray.
echo This window will close in 3 seconds.
timeout /t 3 >nul
exit