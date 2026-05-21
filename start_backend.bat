@echo off
echo ========================================
echo  AI Job Portal - Backend Setup
echo ========================================

cd /d "%~dp0backend"

echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Starting FastAPI backend...
echo API Docs: http://localhost:8000/docs
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
