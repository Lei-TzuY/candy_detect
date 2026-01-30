# 模型與類別不匹配問題說明

## 問題描述

**錯誤訊息：** `IndexError: list index out of range` at `label = class_names[classid]`

## 原因分析

這個錯誤發生在以下情況：

### 1. **使用預訓練的 YOLO 模型**
   - 預訓練模型（如 yolo11n.pt）是在 COCO 數據集上訓練的
   - COCO 數據集有 **80 個類別**（人、車、狗等）
   - 但您的 `classes.txt` 只定義了 **2 個類別**（normal, abnormal）
   - 當模型偵測到類別 ID > 1 時，就會超出範圍

### 2. **使用不同數據集訓練的模型**
   - 如果模型是用其他數據集訓練的（例如有 10 個類別）
   - 但 `classes.txt` 只有 2 個類別
   - 同樣會導致索引超出範圍

## 已實施的修正

✅ **添加了類別範圍檢查**（`run_detector.py`）

```python
# 檢查類別 ID 是否在有效範圍內
if classid < 0 or classid >= len(class_names):
    # 跳過不在定義類別範圍內的偵測
    continue

label = class_names[classid]
```

**效果：**
- 系統現在會自動跳過超出範圍的類別
- 不會崩潰，但也不會顯示這些偵測結果
- 在日誌中不會有額外的警告（靜默處理）

## 正確使用模型的方式

### 方式 1：使用自己訓練的模型（推薦）

在 `runs/detect/*/weights/best.pt` 中的模型：
- ✅ 這些是用您的糖果數據集訓練的
- ✅ 只有 2 個類別（normal, abnormal）
- ✅ 與 `classes.txt` 完全匹配

**示例路徑：**
```
runs/detect/runs/train/candy_detector3/weights/best.pt
```

### 方式 2：使用預訓練模型進行遷移學習

如果要使用預訓練模型（yolo11n.pt, yolov8m.pt 等）：
1. **不要直接用於偵測** - 這些模型偵測 COCO 類別（人、車等）
2. **用於訓練起點** - 在訓練時使用 `--pretrained yolo11n.pt`
3. **訓練後使用生成的模型** - 使用 `runs/.../best.pt`

## 如何選擇正確的模型

### ✅ 正確的模型選擇

在網頁界面 🤖 模型版本選單中：
- 選擇標記為 **[已訓練]** 的模型
- 例如：`[已訓練] candy_detector3 (5.7MB)`

### ❌ 錯誤的模型選擇

避免選擇預訓練模型：
- yolo11n (5.6MB) - COCO 模型，80 類
- yolo11s (19.3MB) - COCO 模型，80 類
- yolo11m (40.7MB) - COCO 模型，80 類
- yolov8n (6.5MB) - COCO 模型，80 類
- yolov8s (22.6MB) - COCO 模型，80 類
- yolov8m (52.1MB) - COCO 模型，80 類

**注意：** 雖然現在不會崩潰，但這些模型會偵測錯誤的物體（人、車等），不會偵測糖果。

## 驗證模型是否正確

### 檢查模型類別數量

```python
from ultralytics import YOLO

# 載入模型
model = YOLO('path/to/model.pt')

# 檢查類別名稱
print(f"類別數量: {len(model.names)}")
print(f"類別名稱: {model.names}")
```

**期望輸出（正確的糖果模型）：**
```
類別數量: 2
類別名稱: {0: 'normal', 1: 'abnormal'}
```

**COCO 模型輸出：**
```
類別數量: 80
類別名稱: {0: 'person', 1: 'bicycle', 2: 'car', ...}
```

## 系統行為說明

### 當前行為（修正後）

1. **使用正確的糖果模型**
   - ✅ 所有偵測都正常工作
   - ✅ 顯示 normal 和 abnormal 標籤
   - ✅ 統計數據正確

2. **使用 COCO 預訓練模型**
   - ⚠️ 系統不會崩潰
   - ⚠️ 大部分偵測會被靜默跳過（classid > 1）
   - ⚠️ 只有極少數符合 classid 0 或 1 的會被顯示（但標籤錯誤）
   - ⚠️ 統計數據不準確

## 最佳實踐

1. **訓練專用模型**
   ```bash
   # 使用預訓練權重作為起點
   python scripts/train_yolo.py
   ```

2. **總是使用訓練後的模型**
   - 在 `config.ini` 中設置正確的模型路徑
   - 或在網頁界面選擇 [已訓練] 模型

3. **定期備份訓練的模型**
   ```bash
   # 備份到安全位置
   cp runs/detect/runs/train/candy_detector3/weights/best.pt backups/
   ```

## 故障排除

### 症狀：切換模型後沒有任何偵測

**原因：** 可能使用了 COCO 模型，所有偵測都因類別不匹配被跳過

**解決：**
1. 在網頁界面重新選擇 [已訓練] 模型
2. 或在終端檢查當前模型：
   ```python
   from ultralytics import YOLO
   model = YOLO('config.ini 中的 weights 路徑')
   print(model.names)  # 應該是 {0: 'normal', 1: 'abnormal'}
   ```

### 症狀：偵測結果標籤錯誤

**原因：** 模型和 classes.txt 不匹配

**解決：**
1. 確保使用正確訓練的模型
2. 檢查 `models/classes.txt` 內容是否為：
   ```
   normal
   abnormal
   ```
