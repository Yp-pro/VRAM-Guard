@echo off
cd /d "%~dp0"
echo ==========================================
echo    VRAM Guard Environment Installer
echo ==========================================
echo.
echo [1/2] Creating virtual environment (venv)...
python -m venv venv
echo [2/2] Installing required libraries...
call venv\Scripts\activate
pip install psutil requests pystray Pillow
echo.
echo Done! Use Start_Protection.bat to run.
pause