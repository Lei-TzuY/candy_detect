@echo off
ECHO =================================================
ECHO  Candy Defect Detection System
ECHO =================================================
ECHO.
ECHO This script will start two detector instances for Camera 1 and Camera 2.
ECHO Make sure you have installed the required libraries by running:
ECHO pip install -r requirements.txt
ECHO.

REM 啟動第一個偵測器，對應 config.ini 中的 [Camera1]
ECHO Starting detector for Camera 1...
start "Camera 1 Detector" cmd /k "python run_detector.py Camera1"

REM 稍作延遲，避免資源競爭
timeout /t 3 > nul

REM 啟動第二個偵測器，對應 config.ini 中的 [Camera2]
ECHO Starting detector for Camera 2...
start "Camera 2 Detector" cmd /k "python run_detector.py Camera2"

ECHO.
ECHO Both detector windows have been launched.
ECHO To stop the detectors, close their respective windows or press 'q' in each window.
