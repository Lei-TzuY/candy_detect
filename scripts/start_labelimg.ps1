# LabelImg Launcher
# Quick start script from project root

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   LabelImg Annotation Tool" -ForegroundColor Green  
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$LABELIMG_EXE = "LabelImg\.venv_labelimg\Scripts\labelImg.exe"

if (-not (Test-Path $LABELIMG_EXE)) {
    Write-Host "ERROR: LabelImg not found" -ForegroundColor Red
    Write-Host "Path: $LABELIMG_EXE" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Please install LabelImg:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  cd LabelImg" -ForegroundColor White
    Write-Host "  .\install_labelimg.ps1" -ForegroundColor White
    Write-Host ""
    pause
    exit 1
}

Write-Host "Found LabelImg executable" -ForegroundColor Green

$imgDir = "datasets\extracted_frames"
$lblDir = "datasets\annotated\labels"
$clsTxt = "models\classes.txt"

if ((Test-Path $imgDir) -and (Test-Path $clsTxt)) {
    Write-Host "Found image directory: $imgDir" -ForegroundColor Green
    Write-Host "Found classes file: $clsTxt" -ForegroundColor Green
    Write-Host ""
    Write-Host "Starting LabelImg with default folders..." -ForegroundColor Cyan
    
    try {
        Start-Process $LABELIMG_EXE -ArgumentList $imgDir, $lblDir, $clsTxt -ErrorAction Stop
        Write-Host "LabelImg started successfully!" -ForegroundColor Green
    } catch {
        Write-Host "Failed to start: $_" -ForegroundColor Red
        Write-Host "Trying without arguments..."
        Start-Process $LABELIMG_EXE
    }
} else {
    Write-Host "Default folders not found, starting with defaults" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Starting LabelImg..." -ForegroundColor Cyan
    
    try {
        Start-Process $LABELIMG_EXE -ErrorAction Stop
        Write-Host "LabelImg started successfully!" -ForegroundColor Green
    } catch {
        Write-Host "Failed to start: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Tip: You can close this window now" -ForegroundColor Gray
