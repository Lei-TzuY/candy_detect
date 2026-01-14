@echo off
chcp 65001 >nul
title LabelImg 標註工具

echo ========================================
echo   LabelImg 影像標註工具
echo ========================================
echo.

REM 設定 Qt 插件路徑
set QT_PLUGIN_PATH=%~dp0.venv\Lib\site-packages\PyQt5\Qt5\plugins
set QT_QPA_PLATFORM_PLUGIN_PATH=%QT_PLUGIN_PATH%

REM 啟動 LabelImg
if "%~1"=="" (
    echo 啟動 LabelImg...
    echo 請在介面中選擇影像和標註目錄
    echo.
    .venv\Scripts\labelImg.exe
) else if "%~2"=="" (
    echo 啟動 LabelImg（影像目錄: %~1）
    echo.
    .venv\Scripts\labelImg.exe "%~1"
) else (
    echo 啟動 LabelImg
    echo   影像目錄: %~1
    echo   標註目錄: %~2
    echo.
    .venv\Scripts\labelImg.exe "%~1" "%~2"
)

if errorlevel 1 (
    echo.
    echo [錯誤] LabelImg 啟動失敗
    pause
)
