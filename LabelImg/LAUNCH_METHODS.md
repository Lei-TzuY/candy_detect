# LabelImg 啟動方式總結

## ✅ 現在可以使用的啟動方式

### 1. 使用 BAT 檔案（推薦給習慣雙擊的用戶）

```cmd
# 從 LabelImg 目錄
cd LabelImg
run_labelimg.bat

# 或直接雙擊
LabelImg\run_labelimg.bat
```

**特點**：
- ✅ 可以雙擊執行
- ✅ 自動調用 PowerShell 處理中文路徑
- ✅ 無需設定執行政策

### 2. 使用 PowerShell 腳本（最可靠）

```powershell
# 從專案根目錄
.\start_labelimg.ps1

# 或從 LabelImg 目錄
cd LabelImg
.\run_labelimg.ps1
```

**特點**：
- ✅ 完整的錯誤檢查和提示
- ✅ 彩色輸出更易讀
- ✅ 支援中文路徑

### 3. 直接執行（最快速）

```powershell
LabelImg\.venv_labelimg\Scripts\labelImg.exe
```

## 🔧 技術說明

### BAT 檔案的解決方案

原本的問題：
- Windows CMD 無法正確處理中文路徑
- UTF-8 編碼在 bat 檔案中支援不完整

解決方法：
```batch
@echo off
REM 使用 PowerShell 處理中文路徑
powershell.exe -ExecutionPolicy Bypass -File "%~dp0run_labelimg.ps1"
```

這個簡單的 bat 檔案：
1. 不包含任何中文字符（避免編碼問題）
2. 調用 PowerShell 腳本（PowerShell 完美支援 UTF-8）
3. 使用 `%~dp0` 自動取得腳本所在目錄

### PowerShell 腳本的改進

- 使用 `Split-Path` 和 `Join-Path` 處理路徑
- 所有訊息都用英文（避免終端機編碼問題）
- UTF-8 BOM 編碼確保相容性

## 📝 建議

**如果你想要：**
- 🖱️ **雙擊就能用** → 使用 `run_labelimg.bat`
- 💻 **最佳體驗** → 使用 PowerShell 腳本
- ⚡ **最快啟動** → 直接執行 exe

**所有方式都已測試通過！** ✅
