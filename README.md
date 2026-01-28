# 🍬 Candy Defect Detection System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8%20%7C%20v11-green.svg)](https://github.com/ultralytics/ultralytics)

基於 YOLOv8/YOLO11 的即時糖果瑕疵偵測系統，專為產線品檢設計。系統提供即時影像串流、動態攝影機管理、模型訓練與管理、以及錄影與標註功能。

## ✨ 主要功能

### 🎥 即時偵測與監控
- **多鏡頭支援**：同時運作多個攝影機，獨立監控不同產線
- **即時偵測**：使用 YOLOv8/YOLO11 進行高 FPS 的瑕疵檢測
- **動態攝影機管理**：
  - 熱插拔支援：可動態新增/移除攝影機
  - 即時切換攝影機來源
  - 獨立控制曝光、焦距與噴氣延遲（自動儲存）
- **即時統計**：每個攝影機獨立顯示總偵測數、正常品、瑕疵品、瑕疵率

### 🤖 模型管理
- **多模型支援**：支援 YOLOv8 (n/s/m) 和 YOLO11 (n/s/m) 共 6 種預訓練模型
- **動態切換**：無需重啟即可切換模型
- **模型訓練**：內建訓練介面，支援自定義參數
- **版本管理**：自動識別並列出所有可用模型

### 📹 錄影與標註
- **智能錄影**：
  - 手動/自動錄影模式
  - 影格率、編碼格式可調
  - 錄影檔管理與回放
- **資料標註**：
  - 整合 LabelImg 標註工具
  - 從錄影中擷取影像
  - 自動標註輔助
  - 標註品質檢查

### 📊 數據分析
- **即時圖表**：瑕疵率趨勢、產品分布
- **歷史記錄**：可查詢任意時間範圍的檢測記錄
- **報表匯出**：支援 CSV 格式匯出

## 🛠️ 安裝說明

### 系統需求
- **作業系統**：Windows 10/11
- **Python**：3.9 或更高版本
- **硬體**（建議）：
  - NVIDIA GPU (用於 TensorRT 加速)
  - 至少 8GB RAM
  - 支援 DirectShow 的 USB 攝影機

### 安裝步驟

1. **複製專案**
   ```bash
   git clone https://github.com/Lei-TzuY/candy_detect.git
   cd candy_detect
   ```

2. **建立虛擬環境**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   ```

4. **準備模型檔案**
   
   系統支援 6 種預訓練模型，首次執行時會自動下載：
   - YOLOv8: `yolov8n.pt`, `yolov8s.pt`, `yolov8m.pt`
   - YOLO11: `yolo11n.pt`, `yolo11s.pt`, `yolo11m.pt`
   
   或手動下載後放置於專案根目錄。

## 🚀 使用方式

### 快速啟動

執行根目錄下的批次檔案：

```bat
start_all.bat
```

該腳本會自動：
1. 啟動後端 Flask 伺服器
2. 開啟瀏覽器至 `http://localhost:5000`

### 功能說明

#### 1. 儀表板（Dashboard）
- 即時監控所有攝影機
- 調整焦距、曝光、噴氣延遲
- 切換模型版本
- 查看即時統計

#### 2. 錄影模式（Recorder）
- 開始/停止錄影
- 調整錄影參數
- 管理錄影檔案

#### 3. 訓練模式（Trainer）
- 選擇訓練模型（YOLOv8/YOLO11）
- 設定訓練參數（epochs, batch size, image size）
- 監控訓練進度
- 評估模型效能

#### 4. 標註工具（Annotate）
- 從錄影擷取影像
- 手動標註瑕疵
- 自動標註輔助
- 標註品質檢查

## 📂 專案結構

```
candy_detect/
├── src/                    # 後端核心程式碼
│   ├── web_app.py         # Flask 主應用程式
│   ├── run_detector.py    # 偵測引擎
│   ├── video_recorder.py  # 錄影模組
│   └── yolov8_trainer.py  # 訓練模組
├── candy_detector/        # 核心偵測套件
│   ├── config.py         # 配置管理
│   ├── models.py         # 數據模型
│   ├── logger.py         # 日誌系統
│   └── constants.py      # 常數定義
├── static/               # 前端靜態資源
│   ├── script.js        # 主要 JavaScript
│   ├── style.css        # 樣式表
│   └── annotate.js      # 標註工具腳本
├── templates/           # HTML 模板
│   ├── index.html      # 主頁面
│   ├── recorder.html   # 錄影介面
│   ├── trainer.html    # 訓練介面
│   └── annotate.html   # 標註介面
├── tools/              # 實用工具
├── scripts/            # 批次處理腳本
├── docs/              # 專案文件
├── config.ini         # 系統配置檔
├── requirements.txt   # Python 依賴
└── start_all.bat     # 啟動腳本
```

## ⚙️ 配置說明

### config.ini

系統配置檔案，包含：
- 攝影機參數（索引、解析度、焦距、曝光）
- 繼電器設定（URL、延遲時間）
- 模型路徑
- 偵測參數（信心度閾值、距離閾值）

範例：
```ini
[Camera1]
camera_index = 0
frame_width = 1280
frame_height = 720
default_focus = 128
exposure_value = -7
relay_delay_ms = 1600
```

## 🔧 進階功能

### 自動標註
系統支援使用預訓練模型自動標註影像：
```python
# 在標註介面選擇資料夾
# 設定信心度閾值（建議 0.3-0.5）
# 點擊「開始自動標註」
```

### 模型訓練
1. 準備標註好的資料集（YOLO 格式）
2. 進入訓練模式
3. 選擇基礎模型（yolov8n/s/m 或 yolo11n/s/m）
4. 設定訓練參數
5. 開始訓練
6. 訓練完成後模型會自動出現在模型選單中

### API 端點

系統提供 RESTful API 供整合：

```
GET  /api/cameras          # 取得攝影機列表
POST /api/cameras/add      # 新增攝影機
GET  /api/models           # 取得可用模型
POST /api/models/switch    # 切換模型
GET  /api/stats            # 取得統計資料
GET  /api/history          # 取得歷史記錄
```

## 🐛 問題排除

### 攝影機無法開啟
- 確認攝影機已連接並可被系統識別
- 檢查是否有其他程式佔用攝影機
- 嘗試更新攝影機驅動程式

### 模型載入失敗
- 確認模型檔案存在於正確位置
- 檢查模型檔案是否完整（未損壞）
- 查看 logs 資料夾中的錯誤日誌

### Port 5000 被佔用
系統啟動時會自動清理 Port 5000，如仍有問題：
```bash
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

## 📝 授權

本專案採用 MIT License - 詳見 [LICENSE](LICENSE) 檔案

## 👨‍💻 作者

Lei-TzuY

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📧 聯絡方式

如有問題或建議，請透過 GitHub Issues 聯絡。

---

**注意**：本系統為工業應用設計，請確保在適當的環境下使用，並遵守相關安全規範。
