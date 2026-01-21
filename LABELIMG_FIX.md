# ✅ LabelImg 啟動問題 - 已完全解決

## 🔍 問題診斷

原本的問題：
1. **虛擬環境路徑損壞** - 從其他位置複製導致 Python 路徑錯誤
2. **編碼問題** - bat/ps1 檔案編碼導致中文亂碼
3. **視窗閃退** - 執行檔找不到正確的 Python 環境

## ✅ 解決方案

### 1. 重新安裝虛擬環境

已經重新創建了完整的虛擬環境：
```powershell
cd LabelImg
python -m venv .venv_labelimg
.\.venv_labelimg\Scripts\Activate.ps1
pip install labelimg pyqt5
```

### 2. 改進的啟動腳本

**根目錄快速啟動** (`start_labelimg.ps1`):
- UTF-8 編碼，支援中文
- 自動檢測檔案和目錄
- 友善的錯誤訊息
- 自動載入預設資料夾

**詳細啟動腳本** (`LabelImg/run_labelimg.ps1`):
- 完整的環境檢查
- 視覺化的執行步驟
- 安裝指引提示

**一鍵安裝腳本** (`LabelImg/install_labelimg.ps1`):
- 自動創建虛擬環境
- 自動安裝所有依賴
- 驗證安裝結果
- 可選立即啟動

## 🚀 現在如何使用

### 方法 1: 從專案根目錄（最簡單）

```powershell
.\start_labelimg.ps1
```

### 方法 2: 從 LabelImg 目錄

```powershell
cd LabelImg
.\run_labelimg.ps1
```

### 首次使用或重新安裝

```powershell
cd LabelImg
.\install_labelimg.ps1
```

## 📝 預設配置

啟動腳本會自動載入：
- **影像目錄**: `datasets/extracted_frames/`
- **標籤目錄**: `datasets/annotated/labels/`
- **類別檔案**: `models/classes.txt`

如果這些目錄不存在，LabelImg 會以空白狀態啟動，你可以手動選擇資料夾。

## 🎯 測試結果

✅ 虛擬環境創建成功  
✅ labelimg 和 pyqt5 安裝完成  
✅ labelImg.exe 存在且可執行  
✅ 啟動腳本正常運作  
✅ 可以正常開啟 LabelImg 視窗  
✅ 已推送到 GitHub

## 💡 常見問題

### Q: PowerShell 執行政策錯誤？

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: 想要使用不同的資料夾？

直接執行 LabelImg 並手動選擇：
```powershell
LabelImg\.venv_labelimg\Scripts\labelImg.exe
```

或修改腳本中的路徑變數。

### Q: 需要重新安裝？

```powershell
cd LabelImg
.\install_labelimg.ps1
```

腳本會自動移除舊環境並重新安裝。

## 📚 相關文件

- [LabelImg/README.md](LabelImg/README.md) - 完整使用指南
- [LabelImg/install_labelimg.ps1](LabelImg/install_labelimg.ps1) - 安裝腳本
- [LabelImg/run_labelimg.ps1](LabelImg/run_labelimg.ps1) - 詳細啟動腳本
- [start_labelimg.ps1](start_labelimg.ps1) - 快速啟動腳本

---

**狀態**: ✅ 已解決  
**提交**: ba3c69d  
**日期**: 2026-01-21
