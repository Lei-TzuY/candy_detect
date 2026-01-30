# YOLO 模型兼容性問題解決方案

## 問題描述
錯誤訊息：`Can't get attribute 'C3k2' on <module 'ultralytics.nn.modules.block'>`

**原因：** 您嘗試加載的模型是用較新版本的 YOLO（YOLO11）訓練的，但當前安裝的 `ultralytics` 包版本較舊（8.1.0），不支持新的架構組件如 `C3k2`。

## 解決方案

### 方法 1：升級 Ultralytics（推薦）

已為您創建升級腳本 `upgrade_ultralytics.bat`，可以：

1. **直接運行腳本：**
   ```
   upgrade_ultralytics.bat
   ```

2. **或手動升級：**
   ```bash
   # 激活虛擬環境
   .venv\Scripts\activate.bat
   
   # 升級 ultralytics
   pip install --upgrade ultralytics
   
   # 確認版本（應該是 8.3.0 或更高）
   python -c "import ultralytics; print(ultralytics.__version__)"
   ```

3. **重啟應用程式**
   ```
   start_all.bat
   ```

### 方法 2：使用兼容的模型

如果不想升級，可以使用與 ultralytics 8.1.0 兼容的模型：
- YOLOv8n, YOLOv8s, YOLOv8m, YOLOv8l, YOLOv8x
- 避免使用 YOLO11 訓練的模型

## YOLO 版本對應關係

| ultralytics 版本 | 支援的模型 |
|-----------------|-----------|
| 8.0.x - 8.2.x   | YOLOv8    |
| 8.3.0+          | YOLOv8, YOLO11 |

## 驗證升級

升級完成後，您可以：

1. 在網頁界面選擇任何 YOLO11 模型
2. 切換模型應該成功，不會出現 C3k2 錯誤
3. 系統會顯示「✅ 切換成功」

## 如果遇到問題

### 回退到舊版本：
```bash
pip install ultralytics==8.1.0
```

### 清除快取後重新安裝：
```bash
pip cache purge
pip install --upgrade --force-reinstall ultralytics
```

## 注意事項

✅ **升級是安全的** - ultralytics 向後兼容，仍可使用 YOLOv8 模型
✅ **不影響現有模型** - 您訓練的模型不需要重新訓練
✅ **性能可能改善** - 新版本通常包含性能優化和錯誤修復

## 相關檔案

- `requirements.txt` - 已更新為 `ultralytics>=8.3.0`
- `upgrade_ultralytics.bat` - 一鍵升級腳本
