@echo off
echo ========================================
echo  AI Job Portal - Frontend
echo ========================================

cd /d "%~dp0frontend"

echo Starting React dev server...
echo App: http://localhost:5173
echo.
npm run dev
