@echo off
REM LabelImg Launcher - Simple version without Unicode paths
REM This script uses PowerShell internally to handle Chinese paths correctly

echo Starting LabelImg...
echo.

powershell.exe -ExecutionPolicy Bypass -NoExit -File "%~dp0run_labelimg.ps1"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start LabelImg
    pause
)
