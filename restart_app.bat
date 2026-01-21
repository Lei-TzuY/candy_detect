@echo off
chcp 65001 >nul
REM 重啟腳本：等待舊程序結束後啟動新程序

REM 等待舊程序完全結束
timeout /t 2 /nobreak >nul

REM 啟動新實例
cd /d "%~dp0"
start "" cmd /c "start_all.bat"

REM 關閉此視窗
exit
