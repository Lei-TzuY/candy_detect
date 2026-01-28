# LabelImg 快速啟動指南

## 🚀 一鍵啟動（推薦）

**方法1：雙擊 bat 檔案**
```
LabelImg\start_labelimg.bat
```

**方法2：命令列**
```powershell
cd LabelImg
.\start_labelimg.bat
```

## 📁 預設路徑

- **圖片目錄**：`datasets\extracted_frames`
- **標記儲存**：`datasets\annotated\labels`
- **類別檔案**：`models\classes.txt`

## 🎯 參數說明

LabelImg 啟動參數順序：
```bash
labelImg.exe <圖片目錄> <classes.txt> <標記儲存目錄>
```

**範例**：
```bash
labelImg.exe "datasets\extracted_frames" "models\classes.txt" "datasets\annotated\labels"
```

⚠️ **重要**：第二個參數必須是 `classes.txt` 檔案路徑，不能是目錄！

## 🔧 手動啟動

如果預設啟動失敗，可以不帶參數啟動後手動選擇：
```powershell
LabelImg\.venv_labelimg\Scripts\labelImg.exe
```

## 📝 classes.txt 格式

```
normal
abnormal
```

每個類別名稱一行，不需要額外標點符號。

## ❓ 常見問題

### Q: 啟動後看不到視窗？
A: 檢查工作列，LabelImg 可能在背景。

### Q: 找不到圖片目錄？
A: 點選 "Open Dir" 手動選擇 `datasets\extracted_frames`

### Q: 標記檔案存在哪？
A: 預設存在 `datasets\annotated\labels` 目錄中的 YOLO 格式 .txt 檔案

## 🆘 需要重裝？

```powershell
cd LabelImg
Remove-Item .venv_labelimg -Recurse -Force
py -3.10 -m venv .venv_labelimg
.\.venv_labelimg\Scripts\pip.exe install labelimg pyqt5==5.15.9
```

## 📚 完整文件

- [安裝說明](README.md)
- [啟動方式](LAUNCH_METHODS.md)
- [疑難排解](LABELIMG_FIX.md)
