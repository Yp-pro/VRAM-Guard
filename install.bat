:: 1st time setup
@echo off 
echo [ACTION] Creating virtual environment... 
python -m venv venv 
echo [ACTION] Installing dependencies... 
call venv\Scripts\activate 
pip install -r requirements.txt 
echo [SUCCESS] Installation complete 
pause 
