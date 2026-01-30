# 🍬 Candy Defect Detection System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8%20%7C%20v11-green.svg)](https://github.com/ultralytics/ultralytics)

基於 YOLOv8/YOLO11 的即時糖果瑕疵偵測系統，專為產線品檢設計。

## ✨ 核心功能

### 🎥 即時偵測
- 多鏡頭支援與動態管理
- 高 FPS 即時瑕疵檢測
- 獨立控制曝光、焦距與噴氣延遲
- 即時統計與瑕疵率分析

### 🤖 模型管理
- YOLOv8/YOLO11 多版本支援 (n/s/m)
- 動態模型切換
- 內建訓練介面
- 自動模型版本管理

### 📹 錄影與標註
- 智能錄影（手動/自動）
- LabelImg 整合
- 自動標註輔助
- 標註品質檢查

### 📊 數據分析
- 即時圖表與趨勢分析
- 歷史記錄查詢
- CSV 報表匯出

## 🛠️ 快速開始

### 系統需求
- Windows 10/11
- Python 3.9+
- (建議) NVIDIA GPU with CUDA
- USB Camera with DirectShow support

### 安裝

```bash
# 1. 克隆專案
git clone https://github.com/Lei-TzuY/candy_detect.git
cd candy_detect

# 2. 建立虛擬環境
python -m venv .venv
.venv\Scripts\activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 啟動系統
start_all.bat
```

系統會自動：
- 啟動 Flask 後端伺服器
- 開啟瀏覽器至 http://localhost:5000
- 下載所需的 YOLO 模型（首次執行）

## 📂 專案結構

```
candy_detect/
├── src/                    # 後端核心程式
│   ├── web_app.py         # Flask 主應用
│   ├── run_detector.py    # 偵測引擎
│   ├── video_recorder.py  # 錄影模組
│   └── yolov8_trainer.py  # 訓練模組
├── candy_detector/        # 核心偵測套件
│   ├── config.py         # 配置管理
│   ├── models.py         # 數據模型
│   └── logger.py         # 日誌系統
├── static/               # 前端資源
├── templates/            # HTML 模板
├── tools/               # 實用工具
├── scripts/             # 批次處理腳本
├── docs/                # 文件
├── config.ini          # 系統配置
├── requirements.txt    # 依賴列表
└── start_all.bat      # 啟動腳本
```

## ⚙️ 配置

編輯 [config.ini](config.ini) 設定攝影機參數：

```ini
[Camera1]
camera_index = 0
frame_width = 1280
frame_height = 720
default_focus = 128
exposure_value = -7
relay_delay_ms = 1600
```

更多配置選項請參考 [文件](docs/)

## � 常見問題

<details>
<summary><b>攝影機無法開啟</b></summary>

- 確認攝影機已連接
- 檢查是否有其他程式佔用
- 更新驅動程式
- 使用 `tools/diagnose_camera.py` 診斷
</details>

<details>
<summary><b>Port 5000 被佔用</b></summary>

```bash
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```
</details>

<details>
<summary><b>模型載入失敗</b></summary>

- 確認模型檔案完整
- 檢查 `logs/` 目錄錯誤日誌
- 重新下載模型文件
</details>

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！請參考 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📝 授權

MIT License - 詳見 [LICENSE](LICENSE)

## 👨‍💻 作者

[@Lei-TzuY](https://github.com/Lei-TzuY)

---

**注意**：本系統為工業應用設計，請在適當環境下使用並遵守安全規範。
