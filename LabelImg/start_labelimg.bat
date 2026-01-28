@echo off
REM LabelImg launcher with Qt plugin path fix
REM Sets required environment variables before launching

setlocal

REM Set Qt plugin path
set "VENV_DIR=%~dp0.venv_labelimg"
set "QT_PLUGIN_PATH=%VENV_DIR%\Lib\site-packages\PyQt5\Qt5\plugins"
set "QT_QPA_PLATFORM_PLUGIN_PATH=%QT_PLUGIN_PATH%"

REM Set Python path
set "PYTHONPATH=%VENV_DIR%\Lib\site-packages"

REM Default directories
set "IMG_DIR=%~dp0..\datasets\extracted_frames"
set "SAVE_DIR=%~dp0..\datasets\annotated\labels"
set "CLS_TXT=%~dp0..\models\classes.txt"

echo Starting LabelImg...
echo Qt Plugin Path: %QT_PLUGIN_PATH%
echo Image Dir: %IMG_DIR%
echo Save Dir: %SAVE_DIR%
echo Classes: %CLS_TXT%
echo.

REM Check if classes file exists
if not exist "%CLS_TXT%" (
    echo Warning: Classes file not found: %CLS_TXT%
    echo LabelImg will start without predefined classes
    echo.
)

REM Launch LabelImg
if exist "%IMG_DIR%" (
    "%VENV_DIR%\Scripts\labelImg.exe" "%IMG_DIR%" "%CLS_TXT%" "%SAVE_DIR%"
) else (
    "%VENV_DIR%\Scripts\labelImg.exe"
)

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start LabelImg
    pause
)

endlocal
