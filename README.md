# 🍬 Candy Detect - 糖果瑕疵影像偵測系統

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)](https://opencv.org/)
[![YOLOv4](https://img.shields.io/badge/YOLO-v4--tiny-orange.svg)](https://github.com/AlexeyAB/darknet)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

使用 **OpenCV** 與 **YOLOv4-tiny / YOLOv8** 進行雙攝影機即時糖果瑕疵偵測，並透過 HTTP 介面控制繼電器進行自動分選。

## ✨ 功能特色

- 🎥 **雙攝影機即時偵測** - 支援同時監控多路攝影機
- 🤖 **YOLOv4-tiny / YOLOv8 模型** - 輕量高效與現代化訓練流程皆支援
- 🌐 **Web 管理介面** - Flask 網頁應用程式，方便監控與設定
- ⚡ **繼電器控制** - HTTP API 觸發，實現自動化分選
- 📊 **即時統計** - 偵測數據記錄與分析
- 🔧 **高度可配置** - 透過 config.ini 靈活調整參數

## 📁 專案結構

```
candy_detect/
├── run_detector.py      # 主要偵測腳本
├── web_app.py           # Flask Web 應用
├── config.ini           # 設定檔（模型路徑、攝影機、偵測參數）
├── requirements.txt     # Python 套件依賴
├── run_all.bat          # 啟動雙攝影機偵測
├── run_web.bat          # 快速啟動 Web（不檢查環境）
├── start_web_app.bat    # 啟動 Web 應用（使用虛擬環境）
│
├── candy_detector/      # 核心模組
│   ├── __init__.py
│   ├── config.py        # 設定載入
│   ├── constants.py     # 常數定義
│   ├── logger.py        # 日誌模組
│   ├── models.py        # 資料模型
│   └── optimization.py  # 效能優化
│
├── templates/           # Web 介面模板
├── static/              # 靜態資源 (CSS/JS)
├── docs/                # 專案文檔
└── utils/               # 工具模組
```

## 🚀 快速開始

### 1. 環境需求

- Python 3.11+
- OpenCV 4.x
- 支援的攝影機設備
- (可選) CUDA/cuDNN 用於 GPU 加速

### 2. 安裝

```bash
# 克隆專案
git clone https://github.com/Lei-TzuY/candy_detect.git
cd candy_detect

# 建立虛擬環境
python -m venv .venv

# 啟用虛擬環境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 3. 設定模型

可使用兩種模型格式：

- YOLOv4-tiny（Darknet）
  ```ini
  [Paths]
  weights = Yolo/your_model.weights
  cfg = Yolo/your_model.cfg
  classes = Yolo/classes.txt
  ```
  - 權重 `.weights` 與設定 `.cfg` 檔案需手動提供。

- YOLOv8（Ultralytics）
  ```ini
  [Paths]
  weights = runs/train/exp/weights/best.pt  ; 或指向自訂的 .pt
  ```
  - 專案會自動掃描 `runs/train/**/weights/best.pt` 與專案根目錄的 `.pt` 檔。
  - 可透過 Web API 列出與切換模型（見下方「模型管理」）。

> ⚠️ **注意**: 模型權重檔案（`.weights`/`.pt`）因檔案較大未包含於版本庫，請自行訓練或另行取得。

### 4. 執行

**啟動偵測程式：**
```bash
# 雙攝影機模式
python run_detector.py Camera1 Camera2

# 或使用批次檔
run_all.bat
```

**啟動 Web 介面：**
```bash
python web_app.py
# 或
start_web_app.bat
```

## ⚙️ 設定說明

編輯 `config.ini` 調整系統參數：

| 區段 | 說明 |
|------|------|
| `[Paths]` | 模型權重、設定檔、類別檔路徑 |
| `[Detection]` | 置信度門檻、NMS、輸入尺寸 |
| `[Camera1/2]` | 攝影機索引、解析度、ROI、繼電器 API |
| `[Display]` | 顯示視窗大小設定 |

## 📚 文檔

詳細文檔請參閱 [`docs/`](docs/) 資料夾：

- 📖 [入門指南](docs/getting-started/) - 快速開始使用
- 🔧 [安裝配置](docs/installation/) - 環境設置指南
- 🌐 [Web 應用](docs/web-app/) - Web 介面說明
- ⚡ [優化指南](docs/optimization/) - 效能調校
- 🏗️ [技術文檔](docs/technical/) - 架構設計

## 🛠️ 技術架構

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Camera    │────▶│  YOLOv4-    │────▶│   Relay     │
│   Input     │     │   tiny      │     │   Control   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   OpenCV    │     │  Detection  │     │    HTTP     │
│   Capture   │     │   Result    │     │    API      │
└─────────────┘     └─────────────┘     └─────────────┘
```

## 📝 注意事項

- 灰階 YOLO 模型僅接受單通道輸入，推論端已自動將畫面轉灰階
- 大型資料集與模型權重已由 `.gitignore` 排除
- 若需新增攝影機，只要在 `config.ini` 增加對應區塊即可

## 🧠 模型管理與訓練

- 列出可用模型：
  - `GET /api/models` → 回傳已發現的 YOLOv4（.weights/.cfg）與 YOLOv8（.pt）模型清單。
  - `GET /api/models/current` → 取得目前使用中的模型資訊。
- 切換模型：
  - `POST /api/models/change`
  - JSON 範例（YOLOv4）：
    ```json
    {"type":"yolov4","weights":"Yolo/.../best.weights","cfg":"Yolo/.../yolov4-tiny.cfg"}
    ```
  - JSON 範例（YOLOv8）：
    ```json
    {"type":"yolov8","weights":"runs/train/exp/weights/best.pt"}
    ```
- YOLOv8 訓練 API（需安裝 `ultralytics`）：
  - `POST /api/training/start`、`GET /api/training/status`、`POST /api/training/stop`
  - `POST /api/training/prepare-dataset` 可根據資料夾建立訓練資料集與 `data.yaml`

## 📈 歷史紀錄與匯出

- 即時統計：`GET /api/stats`
- 歷史查詢：`GET /api/history?hours=24&camera=Camera1`
  - 參數：`hours`（整數，小時數）、`camera`（可選）
  - 查詢已改用參數化 SQL，避免注入風險
- 匯出 CSV：`GET /api/history/export?hours=24&camera=Camera1`
  - 下載含欄位 `camera,timestamp,total,normal,abnormal,defect_rate(%)` 的 CSV 檔

## 📄 授權

本專案採用 MIT 授權條款

## 👤 作者

- **Lei-TzuY** - [GitHub](https://github.com/Lei-TzuY)

---

<p align="center">
  Made with ❤️ for candy quality control
</p>

## 🚀 啟動方式

- **完整系統運行** → 使用 `run_all.bat` (Relay 服務 + Camera 偵測器)
- **Web 介面（快速）** → 使用 `run_web.bat` (直接啟動，無環境檢查)
- **Web 介面（穩定）** → 使用 `start_web_app.bat` (使用虛擬環境，含錯誤檢查)

> 小提示：若當前機器沒有連接攝影機，請先確認 `config.ini` 中未使用的攝影機區塊（如 `Camera2`）可暫時註解或調整，避免初始化失敗。
