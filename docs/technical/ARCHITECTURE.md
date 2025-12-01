# 項目優化架構詳述

## 🏗️ 整體架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                    run_detector.py (主程序)                  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  main() - 主程序流程                                  │   │
│  │  ├─ 載入配置 (ConfigManager)                         │   │
│  │  ├─ 初始化日誌系統                                    │   │
│  │  ├─ 載入 YOLO 模型                                   │   │
│  │  ├─ 初始化攝影機 (CameraContext)                     │   │
│  │  ├─ 建立 UI 滑軌                                     │   │
│  │  └─ 主檢測迴圈 (process_camera_frame)              │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│         ┌─────────────────┼─────────────────┐               │
│         ↓                 ↓                 ↓               │
│    ┌─────────┐      ┌──────────┐      ┌──────────┐         │
│    │Constants │      │ Config   │      │ Models   │         │
│    │         │      │ Manager  │      │          │         │
│    │ - 顏色  │      │          │      │- Track   │         │
│    │ - 閾值  │      │ - get()  │      │- Camera  │         │
│    │ - 路徑  │      │ - getint │      │ Context  │         │
│    └─────────┘      └──────────┘      └──────────┘         │
│         ↑                 ↑                 ↑               │
│         └─────────────────┼─────────────────┘               │
│                           ↓                                  │
│                    ┌──────────────┐                         │
│                    │    Logger    │                         │
│                    │              │                         │
│                    │ - get_logger │                         │
│                    │ - setup_log  │                         │
│                    └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## 📦 模塊說明

### 1️⃣ **constants.py** - 常數定義中心

**職責**: 集中管理所有常數和配置參數

```python
# 路徑配置
PROJECT_ROOT       # 項目根目錄
CONFIG_FILE        # 配置檔案路徑
LOGS_DIR          # 日誌目錄

# 影像處理
DEFAULT_DISPLAY_HEIGHT  # 預設顯示高度
AUTO_SCREEN_MARGIN      # 螢幕邊距

# 追蹤參數
TRACK_DISTANCE_THRESHOLD_PX    # 追蹤距離閾值
MAX_MISSED_FRAMES              # 最大遺漏幀數

# 顏色配置
DISPLAY_COLORS = {
    "normal": (0, 255, 0),           # 綠色
    "abnormal": (0, 0, 255),         # 紅色
    "detection_line": (200, 100, 0), # 藍橙色
    ...
}
```

**優點**:
- ✅ 所有常數集中在一處
- ✅ 易於修改和維護
- ✅ 減少魔術數字（magic numbers）
- ✅ 提高代碼可讀性

---

### 2️⃣ **config.py** - 配置管理器

**職責**: 統一讀取和管理 config.ini 配置

**主要類**: `ConfigManager`

```python
class ConfigManager:
    def __init__(self, config_path):
        # 初始化配置
        
    def get(section, key, fallback=None):
        # 讀取字符串配置
        
    def getint(section, key, fallback=None):
        # 讀取整數配置
        
    def getfloat(section, key, fallback=None):
        # 讀取浮點數配置
        
    def get_camera_config(camera_name):
        # 讀取完整的攝影機配置
        
    def get_detection_config():
        # 讀取檢測配置
```

**使用示例**:
```python
config = ConfigManager()
camera_config = config.get_camera_config("Camera1")
detection = config.get_detection_config()
```

**優點**:
- ✅ 統一的配置讀取接口
- ✅ 自動類型轉換
- ✅ 提供默認值支持
- ✅ 集中的錯誤處理

---

### 3️⃣ **models.py** - 數據模型

**職責**: 定義項目中的核心數據結構

#### **TrackState** - 物體追蹤狀態
```python
@dataclass
class TrackState:
    center: tuple[int, int]        # 當前位置
    prev_center: tuple[int, int]   # 前一幀位置
    seen_abnormal: bool = False    # 是否異常
    counted: bool = False          # 是否計數
    triggered: bool = False        # 是否觸發
    missed_frames: int = 0         # 遺漏幀數
    last_class: str = ""           # 最後類別
    age: int = 0                   # 追蹤年齡
```

#### **CameraContext** - 攝影機上下文
```python
@dataclass
class CameraContext:
    # 配置參數
    name: str                      # 攝影機名稱
    index: int                     # 攝影機索引
    frame_width: int               # 幀寬
    frame_height: int              # 幀高
    
    # 運行時狀態
    tracking_objects: dict         # 追蹤物體字典
    total_num: int = 0             # 總數
    normal_num: int = 0            # 正常數
    abnormal_num: int = 0          # 異常數
    
    # 方法
    def release(self):             # 釋放資源
    def get_stats(self) -> dict:   # 取得統計
```

**優點**:
- ✅ 使用 dataclass 簡潔定義
- ✅ 類型明確，易於理解
- ✅ 支持額外方法（如 get_stats）
- ✅ 便於序列化和日誌記錄

---

### 4️⃣ **logger.py** - 日誌系統

**職責**: 提供統一的日誌記錄功能

**主要函數**:
```python
def setup_logger(name, log_file=None):
    # 設置日誌記錄器
    # 返回配置好的 logger 對象
    
def get_logger(name):
    # 取得現有或新建的 logger
```

**使用示例**:
```python
# 初始化
setup_logger("candy_detector", "logs/detector.log")
logger = get_logger("candy_detector.detector")

# 記錄消息
logger.info("程序啟動")
logger.warning("警告信息")
logger.error("錯誤信息")
```

**日誌格式**:
```
2025-11-21 14:30:22 - candy_detector.detector - INFO - 已啟動攝影機: Camera 1
```

**優點**:
- ✅ 統一的日誌接口
- ✅ 支持檔案和控制台雙輸出
- ✅ 自動時間戳記錄
- ✅ 易於搜索和分析

---

## 🔄 數據流向

```
┌──────────────────────────────────────────────┐
│         讀取 config.ini                      │
│         (ConfigManager)                      │
└────────────────┬─────────────────────────────┘
                 │
                 ↓
┌──────────────────────────────────────────────┐
│    初始化 CameraContext                      │
│    (包含所有攝影機配置)                       │
└────────────────┬─────────────────────────────┘
                 │
                 ↓
┌──────────────────────────────────────────────┐
│    逐幀處理 (process_camera_frame)            │
│    ├─ 讀取幀                                │
│    ├─ YOLO 檢測                             │
│    ├─ 物體追蹤 (TrackState)                │
│    ├─ 計數統計                              │
│    └─ 繼電器控制                            │
└────────────────┬─────────────────────────────┘
                 │
         ┌───────┴────────┐
         ↓                ↓
    ┌────────────┐   ┌─────────────┐
    │ 顯示影像   │   │ 記錄日誌    │
    │ (OpenCV) │   │ (logger)   │
    └────────────┘   └─────────────┘
```

---

## 💡 設計原則

### 1. **關注點分離 (Separation of Concerns)**
- 配置管理 → `config.py`
- 常數定義 → `constants.py`
- 數據模型 → `models.py`
- 日誌系統 → `logger.py`
- 檢測邏輯 → `run_detector.py`

### 2. **單一責任原則 (Single Responsibility)**
- 每個模塊只負責一個職責
- ConfigManager 只管理配置
- Logger 只處理日誌

### 3. **開閉原則 (Open/Closed Principle)**
- 新增功能時無需修改現有代碼
- 通過繼承或組合擴展功能

### 4. **依賴反轉 (Dependency Inversion)**
- 高層模塊不依賴低層模塊
- 都依賴抽象（配置接口等）

---

## 📊 代碼統計

| 模塊 | 行數 | 功能 |
|------|------|------|
| constants.py | ~80 | 常數定義 |
| config.py | ~120 | 配置管理 |
| models.py | ~80 | 數據模型 |
| logger.py | ~70 | 日誌系統 |
| run_detector.py | ~600 | 主程序 |
| **總計** | **~950** | - |

---

## 🎯 改進對比

### 優化前 vs 優化後

| 項目 | 優化前 | 優化後 |
|------|--------|--------|
| 代碼結構 | 單文件 | 模塊化 5 個檔案 |
| 常數管理 | 分散 | 集中在 constants.py |
| 配置讀取 | configparser | ConfigManager 類 |
| 日誌系統 | print() | logging 模塊 |
| 類型提示 | 部分 | 完整 |
| 文檔字符串 | 少量 | 全覆蓋 |
| 錯誤處理 | 基礎 | 完善 |
| 可維護性 | 中等 | 高 |
| 可測試性 | 低 | 高 |

---

## 🚀 未來擴展

基於當前模塊化架構，可以輕鬆添加：

1. **新模塊**
   ```
   candy_detector/
   ├── database.py      # 數據庫管理
   ├── api.py          # REST API
   └── ui.py           # Web 界面
   ```

2. **功能擴展**
   - 多線程處理
   - 數據庫持久化
   - Web 儀表板
   - 郵件告警

3. **測試框架**
   ```
   tests/
   ├── test_config.py
   ├── test_models.py
   └── test_detector.py
   ```

---

## 📚 參考資源

- **Python PEP 8**: https://www.python.org/dev/peps/pep-0008/
- **Type Hints**: https://docs.python.org/3/library/typing.html
- **Dataclasses**: https://docs.python.org/3/library/dataclasses.html
- **Logging**: https://docs.python.org/3/library/logging.html

---

**優化完成於**: 2025-11-21  
**版本**: 2.0.0  
**作者**: Candy Detection Team
