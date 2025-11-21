@echo off
chcp 65001 > nul
REM Candy Defect Detection Web App Launcher
REM Created: 2025-11-21

echo.
echo ========================================
echo  Candy Web App - Starting...
echo ========================================
echo.

REM Set working directory
cd /d "C:\Users\st313\Desktop\candy"

REM Check virtual environment
if not exist ".venv" (
    echo.
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv .venv
    echo.
    pause
    exit /b 1
)

REM Start virtual environment and run Web app
echo [1] Activating virtual environment...
echo [2] Loading Flask app...
echo.
echo Starting Web app, please wait...
echo.

.venv\Scripts\python.exe web_app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Web app startup failed!
    echo Check app/logs/app.log for details.
    echo.
    pause
    exit /b 1
)
