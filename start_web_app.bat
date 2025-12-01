@echo off
chcp 65001 > nul
REM Candy Defect Detection Web App Launcher
REM Created: 2025-11-21
REM Updated: 2025-12-01 - 修正路徑自動偵測

echo.
echo ========================================
echo  Candy Web App - 正在啟動...
echo ========================================
echo.

REM 自動設定工作目錄為腳本所在位置
cd /d "%~dp0"

REM 檢查虛擬環境
if not exist ".venv" (
    echo.
    echo [錯誤] 找不到虛擬環境！
    echo 建議使用：run_web.bat（不需虛擬環境）
    echo 或執行：python -m venv .venv
    echo.
    pause
    exit /b 1
)

REM 啟動虛擬環境並運行 Web 應用
echo [1] 啟動虛擬環境中...
echo [2] 載入 Flask 應用...
echo.
echo 正在啟動 Web 應用，請稍候...
echo 啟動後請訪問：http://localhost:5000
echo.

.venv\Scripts\python.exe web_app.py

if errorlevel 1 (
    echo.
    echo [錯誤] Web 應用啟動失敗！
    echo 請檢查 app/logs/app.log 查看詳細錯誤訊息。
    echo.
    pause
    exit /b 1
)

