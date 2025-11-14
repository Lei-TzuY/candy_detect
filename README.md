# Candy 影像偵測專案

本專案以 OpenCV + YOLOv4-tiny 執行雙攝影機的即時瑕疵偵測，並透過 HTTP 介面控制繼電器（Relay）。

## 核心架構

本專案採用一個可設定、可複用的偵測腳本，架構清晰且易於擴展：

-   **`run_detector.py`**: 核心偵測程式。它會根據命令列參數讀取對應的攝影機設定，並執行偵測任務。
-   **`config.ini`**: 唯一的設定檔。所有路徑、偵測參數、攝影機編號和繼電器網址都在此設定，實現了程式碼與設定的分離。
-   **`run_all.bat`**: Windows 批次檔，用於方便地同時啟動兩個攝影機的偵測程序。
-   **`requirements.txt`**: 專案所需的 Python 函式庫。

## 快速開始

1.  **安裝環境**
    -   安裝 Python (建議 3.8 或以上版本)。
    -   安裝 Git for Windows (若需上傳至 GitHub)。
    -   (可選) 如需 GPU 加速，請確保已安裝對應的 NVIDIA 驅動、CUDA 及 cuDNN。

2.  **安裝函式庫**
    在專案根目錄下開啟命令提示字元，執行以下指令：
    ```bash
    pip install -r requirements.txt
    ```

3.  **檢查設定**
    開啟 `config.ini` 檔案，根據您的實際環境修改以下設定：
    -   `[Paths]`: 確認 YOLO 模型相關檔案的路徑正確 (目前為相對路徑，通常不需修改)。
    -   `[Camera1]` / `[Camera2]`:
        -   `camera_index`: 攝影機的實體編號 (通常為 0, 1, 2...)。
        -   `relay_url`: 對應的繼電器觸發網址。

4.  **執行程式**
    直接雙擊 `run_all.bat` 即可啟動兩個偵測視窗。

## 上傳到 GitHub

1.  在 GitHub 建立一個新的 repository。
2.  在專案根目錄下執行 Git 指令：
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    git branch -M main
    git remote add origin <你的 Repository URL>
    git push -u origin main
    ```

## 注意事項

-   `.gitignore` 檔案已設定好，會自動忽略大型檔案 (如 `Yolo/`, `訓練集資料/`) 和本機設定。
-   若需要分享模型權重檔 (`.weights`)，建議使用 Git LFS 或在 GitHub Release 頁面提供下載連結。