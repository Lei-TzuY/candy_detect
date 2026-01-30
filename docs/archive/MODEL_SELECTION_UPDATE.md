# 模型選擇界面更新說明

## ✅ 已完成的改進

### 新增糖果專用模型掃描

在 `/api/models` 端點中新增了對 `datasets/最新資料集/` 目錄的掃描。

### 掃描範圍

系統現在會掃描以下三個位置的模型：

#### 1. 🍬 糖果專用模型（優先顯示）
```
datasets/最新資料集/
├── best_candy_model.pt       [糖果專用] best_candy_model (5.4MB)
└── *.pt（非 yolo 開頭）
```

**特點：**
- 標記為 `[糖果專用]`
- 排除 COCO 預訓練模型（yolo*.pt）
- 顯示在列表最前面

#### 2. 📦 已訓練模型
```
runs/detect/
├── runs/detect/candy_*/weights/best.pt
└── runs/train/candy_*/weights/best.pt
```

**特點：**
- 標記為 `[已訓練]`
- 從路徑提取訓練名稱
- 顯示在糖果專用模型之後

#### 3. 🔧 預訓練模型（訓練起點）
```
根目錄/
├── yolo11n.pt
├── yolo11s.pt
├── yolo11m.pt
├── yolov8n.pt
├── yolov8s.pt
└── yolov8m.pt
```

**特點：**
- 無特殊標記
- COCO 預訓練模型（80 類）
- 顯示在列表最後
- ⚠️ 不應用於糖果偵測

## 📋 顯示順序

模型列表按以下優先級排序：

1. **類型優先級**
   - 🥇 糖果專用模型（candy）
   - 🥈 已訓練模型（trained）
   - 🥉 預訓練模型（pretrained）

2. **當前使用標記**
   - ✅ 當前使用的模型排在同類型最前面

3. **修改時間**
   - 同類型模型按修改時間排序（較新的在前）

## 🎨 界面效果

重啟應用後，🤖 模型版本下拉選單會顯示：

```
🤖 模型版本：
┌─────────────────────────────────────────┐
│ ✅ [糖果專用] best_candy_model (5.4MB)  │ ← 當前使用
│    [糖果專用] best_candy_model_v2       │
│    [已訓練] candy_detector3 (5.7MB)     │
│    [已訓練] candy_detector2 (5.5MB)     │
│    [已訓練] candy_detector (5.6MB)      │
│    yolo11n (5.6MB)                      │ ← COCO 模型
│    yolo11s (19.3MB)                     │
│    ...                                  │
└─────────────────────────────────────────┘
```

## 🔍 排除邏輯

### datasets/最新資料集/ 目錄

只掃描**非 yolo 開頭**的 .pt 文件：

```python
# ✅ 會被掃描
best_candy_model.pt
candy_model_v2.pt
trained_model.pt

# ❌ 會被排除（COCO 預訓練）
yolo11n.pt
yolo11s.pt
yolov8m.pt
```

## 🚀 使用方法

### 重啟應用

```batch
# 停止當前程式 (Ctrl+C)
start_all.bat
```

### 選擇模型

1. 打開 http://localhost:5000
2. 在"🤖 模型版本"下拉選單中
3. 選擇 `✅ [糖果專用] best_candy_model (5.4MB)`
4. 系統自動切換並重新加載

### 驗證模型

選擇後檢查：
- ✅ 偵測框正常顯示
- ✅ 標籤為 "abnormal" 或 "normal"
- ✅ 統計數據累計

## 💡 推薦使用順序

### 第一優先：糖果專用模型
```
[糖果專用] best_candy_model
```
- 最新訓練的糖果專用模型
- 類別匹配（abnormal, normal）
- 專門為糖果偵測優化

### 第二選擇：已訓練模型
```
[已訓練] candy_detector3
[已訓練] candy_detector2
```
- 早期訓練版本
- 可用於比較性能
- 同樣是糖果專用

### 避免使用：預訓練模型
```
yolo11n, yolo11s, yolov8m...
```
- ❌ 這些是 COCO 模型
- ❌ 不會偵測糖果
- ❌ 只作為訓練起點

## 📊 技術細節

### API 端點修改

**文件：** `src/web_app.py`

**路由：** `/api/models`

**新增掃描邏輯：**
```python
# 3. 掃描 datasets/最新資料集/ 目錄中的糖果訓練模型
datasets_dir = project_root / 'datasets' / '最新資料集'
if datasets_dir.exists():
    for model_path in datasets_dir.glob('*.pt'):
        if model_path.is_file():
            # 排除 COCO 預訓練模型
            if model_path.name.startswith('yolo'):
                continue
            
            # 添加到模型列表
            models_list.append({
                'name': f"[糖果專用] {model_name} ({size_mb:.1f}MB)",
                'type': 'candy',
                ...
            })
```

### 排序邏輯

```python
type_order = {'candy': 0, 'trained': 1, 'pretrained': 2}
models_list.sort(key=lambda x: (
    type_order.get(x['type'], 999),              # 類型優先級
    -1 if x.get('is_current', False) else 0,    # 當前使用優先
    x['modified']                                 # 修改時間
))
```

## 🎯 預期效果

重啟後：

1. ✅ `best_candy_model.pt` 出現在下拉選單中
2. ✅ 標記為 `[糖果專用]`
3. ✅ 顯示在列表最前面
4. ✅ 帶有 ✅ 標記（如果是當前使用）
5. ✅ 選擇後正常切換模型

## ⚠️ 注意事項

### 如果模型未顯示

檢查以下項目：

1. **文件是否存在**
   ```
   datasets/最新資料集/best_candy_model.pt
   ```

2. **文件名是否正確**
   - 不應以 "yolo" 開頭
   - 必須以 ".pt" 結尾

3. **目錄權限**
   - 確保應用程式可以讀取該目錄

4. **重啟應用**
   - 模型列表在應用啟動時掃描
   - 需要重啟才能看到新模型

## 🔄 添加更多糖果模型

如果您想在 `datasets/最新資料集/` 添加更多模型：

1. **將模型文件放入目錄**
   ```
   datasets/最新資料集/
   ├── best_candy_model.pt
   ├── candy_model_v2.pt      ← 新增
   └── experimental_model.pt   ← 新增
   ```

2. **確保不以 "yolo" 開頭**
   - ✅ candy_*.pt
   - ✅ best_*.pt
   - ✅ model_*.pt
   - ❌ yolo*.pt（會被排除）

3. **重啟應用**
   ```batch
   start_all.bat
   ```

4. **在下拉選單中選擇**
   所有新模型都會自動出現並標記為 `[糖果專用]`

---

**更新完成！** 🎉

重啟應用後，`best_candy_model.pt` 就會出現在模型選擇列表的最前面了！
