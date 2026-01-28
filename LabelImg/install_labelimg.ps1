# LabelImg 一鍵安裝腳本
# 自動設置 LabelImg 虛擬環境和依賴

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   📦 LabelImg 一鍵安裝程式" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_DIR = "D:\專案\candy\LabelImg"
$VENV_DIR = "$PROJECT_DIR\.venv_labelimg"

# 切換到 LabelImg 目錄
Set-Location $PROJECT_DIR
Write-Host "✓ 工作目錄: $PROJECT_DIR" -ForegroundColor Green
Write-Host ""

# 步驟 1: 移除舊的虛擬環境（如果存在）
if (Test-Path $VENV_DIR) {
    Write-Host "📁 偵測到舊的虛擬環境，正在移除..." -ForegroundColor Yellow
    Remove-Item -Path $VENV_DIR -Recurse -Force
    Write-Host "✓ 已移除舊環境" -ForegroundColor Green
    Write-Host ""
}

# 步驟 2: 創建新的虛擬環境（使用 Python 3.10）
Write-Host "🔨 步驟 1/3: 創建虛擬環境（Python 3.10）..." -ForegroundColor Cyan
try {
    # 優先使用 Python 3.10（LabelImg 相容性最佳）
    $pyCommand = "py -3.10"
    $testPy = & $pyCommand --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Python 3.10 not found, trying default python..." -ForegroundColor Yellow
        $pyCommand = "python"
    } else {
        Write-Host "  Using Python 3.10" -ForegroundColor Green
    }
    
    & $pyCommand -m venv .venv_labelimg
    Write-Host "✓ 虛擬環境創建成功" -ForegroundColor Green
} catch {
    Write-Host "❌ 創建虛擬環境失敗: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "請確認已安裝 Python 3.10 或更高版本" -ForegroundColor Yellow
    pause
    exit 1
}
Write-Host ""

# 步驟 3: 升級 pip
Write-Host "📦 步驟 2/3: 升級 pip..." -ForegroundColor Cyan
& "$VENV_DIR\Scripts\python.exe" -m pip install --upgrade pip --quiet
Write-Host "✓ pip 已升級" -ForegroundColor Green
Write-Host ""

# 步驟 4: 安裝 labelimg 和 pyqt5
Write-Host "📥 步驟 3/3: 安裝 labelimg 和 PyQt5..." -ForegroundColor Cyan
Write-Host "   (這可能需要幾分鐘，請稍候...)" -ForegroundColor Gray
Write-Host ""

try {
    & "$VENV_DIR\Scripts\pip.exe" install labelimg pyqt5
    Write-Host ""
    Write-Host "✓ LabelImg 安裝成功！" -ForegroundColor Green
} catch {
    Write-Host "❌ 安裝失敗: $_" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   ✅ 安裝完成！" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 驗證安裝
$EXE = "$VENV_DIR\Scripts\labelImg.exe"
if (Test-Path $EXE) {
    Write-Host "✓ 驗證: labelImg.exe 已就緒" -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 現在可以使用以下方式啟動 LabelImg：" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   方法 1 (從專案根目錄):" -ForegroundColor White
    Write-Host "   .\start_labelimg.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   方法 2 (從 LabelImg 目錄):" -ForegroundColor White
    Write-Host "   cd LabelImg" -ForegroundColor Yellow
    Write-Host "   .\run_labelimg.ps1" -ForegroundColor Yellow
    Write-Host ""
    
    # 詢問是否立即啟動
    Write-Host "是否現在啟動 LabelImg? (Y/N): " -ForegroundColor Cyan -NoNewline
    $response = Read-Host
    if ($response -eq 'Y' -or $response -eq 'y') {
        Write-Host ""
        Write-Host "🚀 啟動 LabelImg..." -ForegroundColor Green
        & ".\run_labelimg.ps1"
    } else {
        Write-Host ""
        Write-Host "好的！隨時使用上述命令啟動 LabelImg" -ForegroundColor Gray
    }
} else {
    Write-Host "❌ 驗證失敗: labelImg.exe 不存在" -ForegroundColor Red
}

Write-Host ""
Write-Host "按任意鍵退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
