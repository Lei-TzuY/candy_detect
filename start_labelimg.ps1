# 啟動 LabelImg 標註工具
# 快速啟動腳本

$LABELIMG_EXE = "LabelImg\.venv_labelimg\Scripts\labelImg.exe"

if (Test-Path $LABELIMG_EXE) {
    Write-Host "🏷️  啟動 LabelImg 標註工具..." -ForegroundColor Green
    
    # 預設目錄
    $imgDir = "datasets\extracted_frames"
    $lblDir = "datasets\annotated\labels"
    $clsTxt = "models\classes.txt"
    
    if ((Test-Path $imgDir) -and (Test-Path $clsTxt)) {
        Start-Process $LABELIMG_EXE -ArgumentList $imgDir, $lblDir, $clsTxt
        Write-Host "✅ 已開啟預設資料夾" -ForegroundColor Cyan
    } else {
        Start-Process $LABELIMG_EXE
        Write-Host "ℹ️  使用預設設定啟動" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ 找不到 LabelImg 執行檔" -ForegroundColor Red
    Write-Host ""
    Write-Host "請先安裝 LabelImg：" -ForegroundColor Yellow
    Write-Host "  cd LabelImg" -ForegroundColor Gray
    Write-Host "  python -m venv .venv_labelimg" -ForegroundColor Gray
    Write-Host "  .\.venv_labelimg\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "  pip install labelimg" -ForegroundColor Gray
    pause
}
