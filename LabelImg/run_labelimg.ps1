# LabelImg Launcher
# Usage: .\run_labelimg.ps1

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   LabelImg Annotation Tool" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PYTHON_EXE = Join-Path $PROJECT_DIR ".venv_labelimg\Scripts\python.exe"
$EXE = Join-Path $PROJECT_DIR ".venv_labelimg\Scripts\labelImg.exe"

# Default directories
$IMG_DIR = Join-Path (Split-Path -Parent $PROJECT_DIR) "datasets\extracted_frames"
$SAVE_DIR = Join-Path (Split-Path -Parent $PROJECT_DIR) "datasets\annotated\labels"
$CLS_TXT = Join-Path (Split-Path -Parent $PROJECT_DIR) "models\classes.txt"

# Check if Python executable exists
Write-Host "Checking LabelImg installation..." -ForegroundColor Cyan
if (-not (Test-Path $PYTHON_EXE)) {
    Write-Host ""
    Write-Host "ERROR: Python not found in virtual environment" -ForegroundColor Red
    Write-Host "Path: $PYTHON_EXE" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Please install LabelImg:" -ForegroundColor Yellow
    Write-Host "  1. cd $PROJECT_DIR" -ForegroundColor White
    Write-Host "  2. py -3.10 -m venv .venv_labelimg" -ForegroundColor White
    Write-Host "  3. .\.venv_labelimg\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  4. pip install labelimg pyqt5" -ForegroundColor White
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host "Found: Python executable" -ForegroundColor Green
Write-Host "Working directory: $PROJECT_DIR" -ForegroundColor Green

Set-Location $PROJECT_DIR

Write-Host ""
Write-Host "Checking default directories..." -ForegroundColor Cyan

# Start LabelImg using Python directly (more reliable than .exe)
if ((Test-Path $IMG_DIR) -and (Test-Path $CLS_TXT)) {
    Write-Host "Found: Image directory" -ForegroundColor Green
    Write-Host "Found: Classes file" -ForegroundColor Green
    Write-Host ""
    Write-Host "Starting LabelImg with default folders..." -ForegroundColor Cyan
    
    try {
        Start-Process $PYTHON_EXE -ArgumentList "-m", "labelImg", $IMG_DIR, $CLS_TXT, $SAVE_DIR -ErrorAction Stop
        Write-Host "LabelImg started successfully!" -ForegroundColor Green
    } catch {
        Write-Host "Failed to start with folders: $_" -ForegroundColor Red
        Write-Host "Trying without arguments..." -ForegroundColor Yellow
        Start-Process $PYTHON_EXE -ArgumentList "-m", "labelImg"
    }
} else {
    Write-Host "Default folders not found" -ForegroundColor Yellow
    if (-not (Test-Path $IMG_DIR)) {
        Write-Host "  Missing: $IMG_DIR" -ForegroundColor Gray
    }
    if (-not (Test-Path $CLS_TXT)) {
        Write-Host "  Missing: $CLS_TXT" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "Starting LabelImg with default settings..." -ForegroundColor Cyan
    
    try {
        Start-Process $PYTHON_EXE -ArgumentList "-m", "labelImg" -ErrorAction Stop
        Write-Host "LabelImg started successfully!" -ForegroundColor Green
        Write-Host "Please select image folder manually" -ForegroundColor Yellow
    } catch {
        Write-Host "Failed to start: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Tip: You can close this window now" -ForegroundColor Gray
Write-Host "===============================================" -ForegroundColor Cyan