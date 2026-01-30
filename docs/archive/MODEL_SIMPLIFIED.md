# 模型選擇簡化更新

## ✅ 已完成的修改

### 🎯 簡化目標

將 🤖 模型版本下拉選單**只顯示** 6 個糖果專用訓練模型，移除所有其他模型。

### 📋 現在只顯示這些模型

```
candy_yolo11n.pt  (5.5 MB)   ← 最快、最小
candy_yolo11s.pt  (19.2 MB)  ← 平衡型
candy_yolo11m.pt  (40.5 MB)  ← 最準確、較慢
candy_yolov8n.pt  (6.2 MB)   ← 最快、最小
candy_yolov8s.pt  (22.5 MB)  ← 平衡型  
candy_yolov8m.pt  (52.0 MB)  ← 最準確、較慢
```

所有模型都是：
- ✅ 糖果專用訓練模型
- ✅ 2 個類別（abnormal, normal）
- ✅ 可以直接用於偵測

### ❌ 已移除的模型

以下模型**不再**出現在下拉選單中：

1. **COCO 預訓練模型**
   - yolo11n.pt, yolo11s.pt, yolo11m.pt
   - yolov8n.pt, yolov8s.pt, yolov8m.pt

2. **runs/ 目錄下的訓練模型**
   - runs/detect/.../best.pt
   - runs/train/.../best.pt

3. **datasets/ 目錄下的模型**
   - datasets/最新資料集/best_candy_model.pt
   - datasets/最新資料集/yolo*.pt

### 💡 為什麼這樣做？

#### 優點：

1. **簡化選擇** - 只有 6 個經過訓練的模型可選
2. **避免混淆** - 不會誤選 COCO 預訓練模型
3. **清晰對比** - 6 個模型提供不同的速度/準確度權衡
4. **易於管理** - 所有模型在根目錄，方便查找

#### 模型對比：

| 模型 | 大小 | 速度 | 準確度 | 適用場景 |
|------|------|------|--------|---------|
| candy_yolo11n | 5.5 MB | ⚡⚡⚡ 最快 | ⭐⭐ | 高速生產線、邊緣設備 |
| candy_yolo11s | 19.2 MB | ⚡⚡ 快 | ⭐⭐⭐ | 大多數應用、平衡型 |
| candy_yolo11m | 40.5 MB | ⚡ 較慢 | ⭐⭐⭐⭐ 最準 | 品質要求嚴格 |
| candy_yolov8n | 6.2 MB | ⚡⚡⚡ 最快 | ⭐⭐ | 高速生產線、邊緣設備 |
| candy_yolov8s | 22.5 MB | ⚡⚡ 快 | ⭐⭐⭐ | 大多數應用、平衡型 |
| candy_yolov8m | 52.0 MB | ⚡ 較慢 | ⭐⭐⭐⭐ 最準 | 品質要求嚴格 |

### 🔧 技術細節

#### 修改的文件

**`src/web_app.py`** - `/api/models` 端點

#### 修改內容

**之前：** 掃描 4 個位置
```python
# 1a. candy_*.pt
# 1b. yolo*.pt
# 2. runs/
# 3. datasets/最新資料集/
```

**之後：** 只掃描 1 個位置
```python
# 只掃描根目錄的 candy_*.pt
for model_path in project_root.glob('candy_*.pt'):
    ...
```

#### 排序邏輯

```python
# 按修改時間排序（較新的在前），當前使用的排最前面
models_list.sort(key=lambda x: (
    -1 if x.get('is_current', False) else 0,  # 當前使用優先
    x['modified']  # 修改時間
), reverse=True)
```

### 🎨 界面效果

重啟應用後，🤖 模型版本下拉選單會顯示：

```
🤖 模型版本：
┌─────────────────────────────────────┐
│ ✅ candy_yolo11m (40.5MB)           │ ← 當前使用
│    candy_yolo11s (19.2MB)           │
│    candy_yolo11n (5.5MB)            │
│    candy_yolov8m (52.0MB)           │
│    candy_yolov8s (22.5MB)           │
│    candy_yolov8n (6.2MB)            │
└─────────────────────────────────────┘
```

**特點：**
- 簡潔清爽，無前綴標記
- 當前使用的帶 ✅ 標記
- 按修改時間排序（較新的在前）

### 🚀 使用方法

#### 1. 重啟應用

```batch
# 停止當前程式 (Ctrl+C)
start_all.bat
```

#### 2. 選擇模型

1. 打開 http://localhost:5000
2. 在"🤖 模型版本"下拉選單中選擇
3. 系統自動切換模型

#### 3. 模型選擇建議

**高速度需求：**
```
candy_yolo11n 或 candy_yolov8n
→ 適合高速生產線、即時處理
```

**平衡型需求：**
```
candy_yolo11s 或 candy_yolov8s
→ 適合大多數實際應用
```

**高準確度需求：**
```
candy_yolo11m 或 candy_yolov8m
→ 適合品質檢測要求嚴格的場景
```

### 📊 YOLO11 vs YOLOv8

兩個版本都有 n, s, m 三種大小：

**YOLO11 系列：**
- 最新版本（2024）
- 架構更優化
- 通常速度更快、準確度相當或更好

**YOLOv8 系列：**
- 成熟穩定（2023）
- 可作為對照組
- 如果 YOLO11 有問題可回退

**建議：** 優先選擇 YOLO11 系列

### ⚙️ 如果需要使用其他模型

如果您需要測試其他位置的模型（如 runs/ 或 datasets/），有兩個選項：

#### 選項 1：直接修改 config.ini

```ini
[Paths]
weights = runs/detect/runs/train/candy_detector3/weights/best.pt
```

然後重啟應用。

#### 選項 2：複製模型到根目錄並重命名

```batch
# 複製並重命名為 candy_*.pt
copy "datasets\最新資料集\best_candy_model.pt" candy_best_model.pt

# 重啟應用，新模型會自動出現
start_all.bat
```

### 📁 文件組織建議

建議將所有糖果訓練模型統一放在根目錄，命名為 `candy_*.pt`：

```
candy/
├── candy_yolo11n.pt       ✅ 訓練模型（顯示）
├── candy_yolo11s.pt       ✅ 訓練模型（顯示）
├── candy_yolo11m.pt       ✅ 訓練模型（顯示）
├── candy_yolov8n.pt       ✅ 訓練模型（顯示）
├── candy_yolov8s.pt       ✅ 訓練模型（顯示）
├── candy_yolov8m.pt       ✅ 訓練模型（顯示）
│
├── pretrained/            ℹ️  移動預訓練模型到這裡
│   ├── yolo11n.pt
│   ├── yolo11s.pt
│   └── ...
│
├── runs/                  ℹ️  保留訓練輸出
│   └── detect/...
│
└── datasets/              ℹ️  保留數據集
    └── 最新資料集/
```

### ✅ 總結

現在系統更加簡潔：
- ✅ 只顯示 6 個真正可用的糖果模型
- ✅ 避免誤選 COCO 模型導致無偵測框
- ✅ 提供清晰的速度/準確度選擇
- ✅ 界面更簡潔易用

**重啟應用後即可看到新的模型選擇界面！** 🎉
