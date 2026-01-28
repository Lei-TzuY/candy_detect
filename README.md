# 🍬 Candy Defect Detection System (糖果瑕疵偵測系統)

這是一個基於 YOLOv8 的即時糖果瑕疵偵測系統，專為產線品檢設計。系統包含即時影像串流、動態攝影機管理、模型訓練與管理、以及錄影與標註功能。

## ✨ 主要功能

*   **即時偵測 (Real-time Detection)**：使用 YOLOv8 模型進行高 FPS 的即時瑕疵檢測。
*   **動態攝影機管理 (Dynamic Camera Management)**：
    *   支援多鏡頭同時運作。
    *   可動態新增/移除攝影機。
    *   即時切換攝影機來源 (Source Switching)。
    *   獨立控制曝光、焦距與噴氣延遲。
*   **模型管理 (Model Management)**：
    *   支援多版本模型切換 (YOLOv8/YOLOv4)。
    *   自動偵測並列出可用的模型權重。
*   **錄影與回放 (Recording & Playback)**：
    *   支援手動/自動錄影。
    *   內建錄影檔管理與回放功能。
*   **資料標註 (Data Annotation)**：
    *   整合影像標註工具，支援從錄影中擷取影像並進行標註。
    *   支援自動標註 (Auto-labeling) 輔助。

## 🛠️ 安裝說明

### 系統需求
*   Windows 10/11
*   Python 3.9+
*   NVIDIA GPU (建議，用於 TensorRT 加速)
*   CUDA Toolkit (若使用 GPU)

### 安裝步驟

1.  **複製專案**
    ```bash
    git clone https://github.com/Lei-TzuY/candy_detect.git
    cd candy_detect
    ```

2.  **建立虛擬環境**
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```

3.  **安裝依賴**
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 啟動方式

直接執行根目錄下的批次檔案即可啟動所有服務：

```bat
start_all.bat
```

該腳本會自動：
1.  清理舊的程序與釋放 Port 5000。
2.  啟動後端 Flask 伺服器。
3.  開啟瀏覽器至 `http://localhost:5000`。

## 📂 專案結構

*   `src/`: 後端核心程式碼 (Flask App, Detector, Recorder)。
*   `static/`: 前端靜態資源 (JS, CSS)。
*   `templates/`: HTML 模板。
*   `tools/`: 各種實用工具腳本 (效能測試、資料清理)。
*   `scripts/`: 批次處理腳本。
*   `docs/`: 專案相關文件。

## 📝 授權

[MIT License](LICENSE)
