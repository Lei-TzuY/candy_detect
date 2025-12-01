@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"

ECHO =================================================
ECHO  Candy Defect Detection System
ECHO =================================================
ECHO.
ECHO This script will start:
ECHO   1) Relay control service (Modbus gateway)
ECHO   2) Detector for Camera 1 and Camera 2 in a single window.
ECHO.
ECHO Make sure you have installed the required libraries by running:
ECHO     pip install -r requirements.txt
ECHO.

REM Start relay control service in a separate window
ECHO Starting relay control service...
start "Relay Service" cmd /k "cd /d "%SCRIPT_DIR%app" ^&^& call run.bat"

set "RETRIES=12"
set "WAIT_SECONDS=1"

ECHO Waiting for relay service to open port 8080 ...
for /L %%i in (1,1,%RETRIES%) do (
    powershell -NoProfile -Command "if ((Test-NetConnection -ComputerName 'localhost' -Port 8080).TcpTestSucceeded) { exit 0 } else { exit 1 }"
    if NOT ERRORLEVEL 1 (
        ECHO Relay service is up (attempt %%i^).
        goto START_DETECTOR
    )
    timeout /t %WAIT_SECONDS% > nul
)

ECHO.
ECHO ERROR: Relay service did not respond after %RETRIES% attempts.
ECHO Please check the \"Relay Service\" window for errors, then press any key to exit.
pause > nul
popd
endlocal
exit /b 1

:START_DETECTOR

REM Start detectors
ECHO Starting detectors for Camera1 and Camera2...
python run_detector.py Camera1 Camera2

ECHO.
ECHO Detector has been stopped. Press any key to close this window.
pause > nul
popd
endlocal
