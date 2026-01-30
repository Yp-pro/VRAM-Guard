@echo off
cd /d "%~dp0"
echo Starting VRAM Guard...
:: Clean up old processes
taskkill /F /IM "pythonw.exe" >nul 2>&1
taskkill /F /IM "LibreHardwareMonitor.exe" >nul 2>&1
timeout /t 1 /nobreak >nul
:: Launch using venv pythonw (no console window)
start "" "venv\Scripts\pythonw.exe" "vram_guard.py"
exit