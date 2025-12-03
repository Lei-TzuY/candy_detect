@echo off
chcp 65001 >nul
title Candy Detection System

echo ========================================
echo   Candy Detection System - Starting
echo ========================================
echo.

echo Current directory: %~dp0
cd /d "%~dp0"
echo Working directory: %CD%
echo.

echo [0/2] Closing old processes...
taskkill /FI "WINDOWTITLE eq Relay*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Candy*" /F >nul 2>&1
timeout /t 2 /nobreak >nul
echo      Done
echo.

echo [1/2] Starting Relay Service...
cd /d "%~dp0app"
if exist "jdk-17.0.6\bin\java.exe" (
    start "Relay Service" cmd /c "jdk-17.0.6\bin\java.exe -jar modbus-gateway.jar"
    echo      Relay service started
) else (
    echo      [WARN] Java not found, skipping relay service
)
cd /d "%~dp0"
timeout /t 3 /nobreak >nul
echo.

echo [2/2] Starting Detection System...
echo.

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo [ERROR] Virtual environment not found!
    pause
    exit /b 1
)

if exist "src\web_app.py" (
    echo Starting web_app.py...
    python src\web_app.py
) else (
    echo [ERROR] src\web_app.py not found!
    pause
    exit /b 1
)

echo.
echo Closing Relay Service...
taskkill /FI "WINDOWTITLE eq Relay*" /F >nul 2>&1

echo.
echo All services stopped.
pause
