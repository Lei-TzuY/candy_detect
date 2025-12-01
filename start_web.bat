@echo off
chcp 65001 > nul
REM ==================================
REM Candy Web App Launcher (Chinese)
REM ==================================

setlocal enabledelayedexpansion

REM 自動獲取腳本所在目錄
cd /d "%~dp0"

if not exist ".venv" (
    echo.
    echo 錯誤：找不到虛擬環境
    echo 請先執行：python -m venv .venv
    echo 或直接使用：run_web.bat
    echo.
    pause
    exit /b 1
)

echo.
echo 正在啟動 Web 應用...
echo 網址：http://localhost:5000
echo.

.venv\Scripts\python.exe web_app.py

if errorlevel 1 (
    echo.
    echo 錯誤：Web 應用啟動失敗
    echo 請檢查 app/logs/app.log 查看詳細錯誤
    echo.
    pause
    exit /b 1
)

