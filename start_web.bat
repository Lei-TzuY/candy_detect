@echo off
chcp 65001 > nul
REM ==================================
REM Candy Web App Launcher (Chinese)
REM ==================================

setlocal enabledelayedexpansion

cd /d "C:\Users\st313\Desktop\candy"

if not exist ".venv" (
    echo.
    echo Error: Virtual environment not found
    echo.
    pause
    exit /b 1
)

echo.
echo Starting Web App...
echo Web address: http://localhost:5000
echo.

.venv\Scripts\python.exe web_app.py

if errorlevel 1 (
    echo.
    echo Error: Web app startup failed
    echo Check app/logs/app.log for details
    echo.
    pause
    exit /b 1
)
