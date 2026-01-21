@echo off
chcp 65001 >nul
title Candy Detection System

REM 將終端機視窗最大化
mode con: cols=200 lines=50

echo ========================================
echo   Candy Detection System - Starting
echo ========================================
echo.

echo Current directory: %~dp0
cd /d "%~dp0"
echo Working directory: %CD%
echo.

echo [0/2] Closing old processes...
REM 只關閉特定的 Java 和 Python 程序，避免誤殺 IDE
taskkill /IM java.exe /F >nul 2>&1
taskkill /IM python.exe /FI "WINDOWTITLE eq *web_app*" /F >nul 2>&1
timeout /t 2 /nobreak >nul
echo      Done
echo.

echo [1/2] Starting Relay Service...
cd /d "%~dp0app"
if exist "jdk-17.0.6\bin\java.exe" (
    start /B "" cmd /c "jdk-17.0.6\bin\java.exe -jar modbus-gateway.jar >nul 2>&1"
    echo      Relay service started in background
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
    echo.
    echo ========================================
    echo   伺服器啟動中...
    echo   打開瀏覽器訪問: http://localhost:5000
    echo ========================================
    echo.
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
