# 糖果瑕疵偵測系統 - 優化版本

## 項目概述

本項目使用 **YOLOv4-tiny** 進行實時糖果瑕疵偵測，支援：
- 🎥 多攝影機同時處理
- 🎯 實時物體追蹤
- 🚨 自動異常檢測和繼電器控制
- 📊 實時統計顯示
- 🔧 焦距和延遲時間手動調整滑軌

---

## 快速開始

### 1. 環境準備

```bash
# 安裝依賴
pip install -r requirements.txt

# 確認 Python 版本
python --version  # 需要 3.11+
```

### 2. 運行程序

```bash
# 雙攝影機檢測
python run_detector.py Camera1 Camera2

# 單攝影機檢測
python run_detector.py Camera1
```

### 3. 實時控制

程序運行時，可通過 OpenCV 窗口中的滑軌調整：
- **焦距滑軌** - 手動調整攝影機焦距
- **繼電器延遲滑軌** - 調整檢測到瑕疵後吹嘴的延遲時間（0-5000ms）

按 `q` 鍵退出程序。

---

## 配置說明

編輯 `config.ini` 文件進行配置：

### [Paths] 区块
```ini
weights = Yolo/darknet-master/build/darknet/x64/train/backup/yolov4-tiny-myobj_final.weights
cfg = Yolo/darknet-master/build/darknet/x64/train/yolov4-tiny-myobj.cfg
classes = Yolo/darknet-master/build/darknet/x64/train/classes.txt
```

### [Detection] 区块
```ini
confidence_threshold = 0.2    # 檢測信心度閾值
nms_threshold = 0.4           # NMS 閾值
input_size = 416              # YOLO 輸入大小
```

### [Camera1] / [Camera2] 区块
```ini
camera_index = 0                                    # 攝影機索引
camera_name = Camera 1                              # 攝影機名稱
frame_width = 1920                                  # 幀寬度
frame_height = 1080                                 # 幀高度
relay_url = http://localhost:8080/api/relay/Relay2?value=1  # 繼電器 API
detection_line_x1 = 500                             # 偵測線起點
detection_line_x2 = 1100                            # 偵測線終點
use_startup_autofocus = 0                           # 啟動時是否自動對焦
autofocus_frames = 20                               # 自動對焦幀數
autofocus_delay_ms = 50                             # 自動對焦延遲
focus_min = 0                                       # 焦距最小值
focus_max = 255                                     # 焦距最大值
relay_delay_ms = 0                                  # 繼電器延遲（毫秒）
```

### [Display] 区块
```ini
target_height = 480           # 顯示影像目標高度
max_width = 0                 # 最大寬度（0=自動）
```

---

## 項目結構

```
candy/
├── candy_detector/              # 優化的模塊包
│   ├── __init__.py             # 包初始化
│   ├── constants.py            # 常數定義（顏色、閾值等）
│   ├── config.py               # 配置管理器類
│   ├── models.py               # 數據模型（TrackState, CameraContext）
│   └── logger.py               # 日誌系統
│
├── config.ini                  # 配置檔案
├── run_detector.py             # 主檢測程序
├── run_detector_backup.py      # 備份的舊版本
├── requirements.txt            # 依賴列表
├── README.md                   # 本檔案
├── OPTIMIZATION_SUMMARY.md     # 優化方案詳述
│
├── logs/                       # 日誌目錄（自動創建）
├── results/                    # 結果目錄（自動創建）
│
├── Yolo/                       # YOLO 模型文件
├── 訓練集資料/                  # 訓練數據
└── app/                        # 其他應用
```

---

## 代碼改進亮點

### ✨ 模塊化設計
- **constants.py** - 集中管理項目所有常數
- **config.py** - ConfigManager 統一配置讀取
- **models.py** - 數據結構清晰定義
- **logger.py** - 統一的日誌系統

### 📝 代碼質量
- ✅ 完整的**類型提示**（Type Hints）
- ✅ 詳細的**文檔字符串**（Docstrings）
- ✅ 統一的**代碼風格**（PEP 8）
- ✅ **錯誤處理**完善

### 📊 功能特性
- ✅ 自動日誌記錄（檔案 + 控制台）
- ✅ 統計數據追蹤
- ✅ 實時參數調整
- ✅ 清晰的控制流

---

## 日誌說明

程序運行時自動生成日誌檔案：

```
logs/candy_detector_20241121_143022.log
```

日誌包含：
- 程序啟動/關閉事件
- 攝影機初始化狀態
- 模型載入信息
- 檢測和繼電器觸發事件
- 錯誤和警告信息

查看日誌：
```bash
# 查看最新日誌
cat logs/candy_detector_*.log | tail -100

# 搜索特定錯誤
grep "ERROR" logs/candy_detector_*.log
```

---

## 常見問題

### Q: 無法打開攝影機
**A:** 檢查：
1. 攝影機是否正確連接
2. `config.ini` 中的 `camera_index` 是否正確（0 為第一個）
3. 其他程序是否佔用攝影機

### Q: YOLO 模型找不到
**A:** 確保：
1. 模型檔案路徑在 `config.ini` 中正確
2. 使用相對路徑（相對於項目根目錄）

### Q: 繼電器未觸發
**A:** 檢查：
1. `relay_url` 配置是否正確
2. HTTP 服務是否正常運行
3. 查看日誌中的繼電器觸發記錄

### Q: 焦距滑軌無效
**A:** 某些攝影機可能不支持手動焦距設置，這是正常的。

---

## 性能最佳化建議

1. **降低檢測閾值** - 在 `config.ini` 中減小 `confidence_threshold`
2. **增加追蹤距離** - 在 `constants.py` 中調整 `TRACK_DISTANCE_THRESHOLD_PX`
3. **使用 GPU** - 確保 CUDA 正確安裝和配置
4. **調整幀大小** - 減小 `frame_width` 和 `frame_height` 以提高速度

---

## 後續開發計畫

- [ ] Web UI 界面
- [ ] 結果數據庫存儲
- [ ] 性能統計分析
- [ ] 多進程並行處理
- [ ] 配置檔案驗證機制
- [ ] 單元測試覆蓋

---

## 技術支持

若遇到問題，請查看：
1. `logs/` 目錄中的日誌檔案
2. `OPTIMIZATION_SUMMARY.md` 優化說明
3. `config.ini` 中的配置說明

---

## 版本信息

- **版本**: 2.0.0（優化版）
- **Python**: 3.11+
- **主要依賴**: OpenCV, NumPy, Requests
- **最後更新**: 2025-11-21
