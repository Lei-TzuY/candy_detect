# 沒有顯示偵測框的問題解決

## 問題診斷

✅ **已找到問題！**

您的 `config.ini` 配置使用的是：
```ini
weights = yolo11s.pt  ❌ COCO 預訓練模型（80 類）
```

**結果：**
- 模型偵測的是 COCO 類別（人、車、狗等）
- 所有偵測的類別 ID 都 ≥ 2
- 被我們的安全檢查過濾掉了
- 畫面上沒有任何偵測框

## 已實施的修正

### 1. 切換回正確的模型

`config.ini` 已更新為：
```ini
weights = runs/detect/runs/train/candy_detector3/weights/best.pt  ✅ 糖果專用模型
```

### 2. 添加診斷日誌

現在當使用錯誤模型時，終端會顯示警告：
```
[警告] Camera 1: 偵測到類別 ID 5 超出範圍 (0-1)。
       這可能是因為使用了預訓練模型（COCO 有80類）而非糖果專用模型（2類）。
       建議切換到 runs/detect/.../weights/best.pt 等訓練好的模型。
```

## 立即解決

### 方法 1：重啟應用程式（推薦）

```batch
# 停止當前運行的程式（按 Ctrl+C）
# 然後執行：
start_all.bat
```

### 方法 2：在網頁界面切換模型

1. 打開瀏覽器 http://localhost:5000
2. 找到 🤖 模型版本 下拉選單
3. 選擇：`[已訓練] candy_detector3 ...`
4. 系統會自動重新加載

## 驗證修正

重啟後，您應該會看到：
- ✅ 畫面上顯示綠色/紅色的偵測框
- ✅ 標籤顯示 "normal" 或 "abnormal"
- ✅ 總數、正常品、瑕疵品統計開始增加
- ✅ 當偵測到瑕疵時觸發繼電器

## 如何避免此問題

### ✅ 正確的模型選擇

在網頁界面只選擇這些模型：
- `[已訓練] candy_detector3 (5.7MB)` ✅
- `[已訓練] candy_detector2 (...)` ✅
- `runs/detect/.../best.pt` ✅

### ❌ 避免選擇這些模型用於偵測

- `yolo11n (5.6MB)` ❌ COCO 模型
- `yolo11s (19.3MB)` ❌ COCO 模型
- `yolo11m (40.7MB)` ❌ COCO 模型
- `yolov8n (6.5MB)` ❌ COCO 模型
- `yolov8s (22.6MB)` ❌ COCO 模型
- `yolov8m (52.1MB)` ❌ COCO 模型

**注意：** 這些預訓練模型只應用於：
1. 訓練新模型時作為起點
2. 測試 YOLO 安裝是否正常
3. **不應用於實際的糖果偵測**

## 模型比較

| 模型類型 | 類別數 | 類別內容 | 用途 |
|---------|--------|---------|------|
| yolo11s.pt | 80 | person, car, dog, ... | 預訓練（通用物體偵測） |
| candy_detector3/best.pt | 2 | normal, abnormal | 糖果瑕疵偵測 ✅ |

## 技術細節

### 為什麼會被過濾掉？

```python
# run_detector.py 第 522-527 行
if classid < 0 or classid >= len(class_names):  # len = 2 (normal, abnormal)
    # COCO 模型偵測到的 classid 通常是 0-79
    # 當 classid >= 2 時，就會被跳過
    continue
```

### 為什麼需要這個檢查？

防止系統崩潰：
```python
label = class_names[classid]  # 如果 classid=5 但只有 2 個類別
# 沒有檢查 → IndexError: list index out of range ❌
# 有檢查 → 安全跳過，但沒有偵測框 ✅
```

## 長期解決方案

### 建議：鎖定模型配置

在網頁界面選擇正確模型後，系統會自動更新 `config.ini`。

### 備份訓練的模型

```batch
# 避免誤刪
mkdir backups
copy runs\detect\runs\train\candy_detector3\weights\best.pt backups\candy_detector3_backup.pt
```

## 相關文檔

- `MODEL_CLASS_MISMATCH.md` - 模型類別不匹配詳細說明
- `YOLO_COMPATIBILITY.md` - YOLO 版本兼容性
