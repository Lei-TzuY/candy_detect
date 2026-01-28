# LabelImg 使用指南

## 🚀 快速開始

### 一鍵安裝（推薦新手）

如果是第一次使用，執行自動安裝腳本：

```powershell
cd LabelImg
.\install_labelimg.ps1
```

腳本會自動完成：
- ✅ 創建虛擬環境
- ✅ 安裝 LabelImg 和相關依賴
- ✅ 驗證安裝
- ✅ 提供啟動選項

### 快速啟動

安裝完成後，使用以下方式啟動：

### 方法 1: 使用 PowerShell 腳本（推薦）

從專案根目錄：
```powershell
.\start_labelimg.ps1
```

或從 LabelImg 目錄：
```powershell
cd LabelImg
.\run_labelimg.ps1
```

### 方法 2: 透過 Web 介面

1. 啟動 Web 應用：`python src/web_app.py`
2. 開啟瀏覽器：http://localhost:5000
3. 點選「標註」頁面

## 首次安裝

如果 LabelImg 尚未安裝，請執行以下步驟：

**重要：建議使用 Python 3.10（LabelImg 最佳相容版本）**

```powershell
# 1. 進入 LabelImg 目錄
cd LabelImg

# 2. 建立虛擬環境（使用 Python 3.10）
py -3.10 -m venv .venv_labelimg

# 3. 啟用虛擬環境
.\.venv_labelimg\Scripts\Activate.ps1

# 4. 安裝 labelimg
pip install labelimg pyqt5

# 5. 測試安裝
labelImg
```

> 💡 **為什麼要用 Python 3.10？**  
> Python 3.12+ 移除了 `distutils` 模組，可能導致 LabelImg 啟動失敗。  
> Python 3.10 提供最佳的相容性和穩定性。

## 預設目錄配置

腳本會自動載入以下目錄：

- **影像目錄**: `datasets/extracted_frames/`
- **標籤目錄**: `datasets/annotated/labels/`
- **類別檔案**: `models/classes.txt`

## 常見問題

### Q: PowerShell 無法執行腳本？

**問題**: 出現「因為這個系統上已停用指令碼執行」錯誤

**解決方法**:
```powershell
# 以管理員身份開啟 PowerShell，執行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: 找不到 labelImg.exe？

**檢查步驟**:
1. 確認虛擬環境已建立：`LabelImg\.venv_labelimg\`
2. 確認已安裝 labelimg：`pip list | findstr labelimg`
3. 重新安裝：參考「首次安裝」步驟

### Q: 中文路徑或檔名顯示亂碼？

**解決方法**:
- 確保系統編碼設為 UTF-8
- 或將檔案移至英文路徑

### Q: 想使用不同的資料夾？

**自訂啟動**:
```powershell
# 直接執行 exe 並指定路徑
LabelImg\.venv_labelimg\Scripts\labelImg.exe "你的影像目錄" "你的標籤目錄" "你的classes.txt"
```

## 標註快捷鍵

- `W` - 創建矩形框
- `D` - 下一張影像
- `A` - 上一張影像
- `Del` - 刪除選中的框
- `Ctrl+S` - 儲存
- `Ctrl+D` - 複製當前框

## 標註完成後

1. 標註檔案會自動儲存在標籤目錄
2. 可以在 Web 介面的「標註」頁面查看
3. 使用「匯出資料集」功能準備訓練資料

## 相關文檔

- [Web 標註介面使用](../docs/annotation_guide.md)
- [自動標註工具](../scripts/auto_labeling/README.md)
- [資料集準備](../docs/dataset_preparation.md)
