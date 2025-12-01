# 🍬 Candy Detect - 糖果瑕疵影像偵測系統

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)](https://opencv.org/)
[![YOLOv4](https://img.shields.io/badge/YOLO-v4--tiny-orange.svg)](https://github.com/AlexeyAB/darknet)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

使用 **OpenCV** 與 **YOLOv4-tiny** 進行雙攝影機即時糖果瑕疵偵測，並透過 HTTP 介面控制繼電器進行自動分選。

## ✨ 功能特色

- 🎥 **雙攝影機即時偵測** - 支援同時監控多路攝影機
- 🤖 **YOLOv4-tiny 模型** - 高效能輕量化物件偵測
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
├── start_web.bat        # 啟動 Web 應用
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

在 `config.ini` 中設定 YOLO 模型路徑：

```ini
[Paths]
weights = Yolo/your_model.weights
cfg = Yolo/your_model.cfg
classes = Yolo/classes.txt
```

> ⚠️ **注意**: 模型權重檔案 (`.weights`) 因檔案過大未包含在此 repo 中。
> 請自行訓練模型或從其他來源取得。

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
start_web.bat
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

## 📄 授權

本專案採用 MIT 授權條款

## 👤 作者

- **Lei-TzuY** - [GitHub](https://github.com/Lei-TzuY)

---

<p align="center">
  Made with ❤️ for candy quality control
</p>
