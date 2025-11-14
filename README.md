# Candy 影像偵測專案

使用 OpenCV 與 YOLOv4-tiny 進行雙攝影機即時瑕疵偵測，並透過 HTTP 介面控制繼電器。

## 專案結構重點
- `run_detector.py`：主要偵測腳本，支援一或多個攝影機，畫面會整合到同一視窗。
- `config.ini`：設定檔，包含模型路徑、偵測參數、各攝影機與顯示設定。
- `run_all.bat`：Windows 批次檔，於單一命令視窗啟動兩路攝影機偵測。
- `requirements.txt`：安裝所需 Python 套件清單。
- `Yolo/`、`訓練集資料/` 等大型目錄已在 `.gitignore` 排除，避免誤傳到 GitHub。

## 快速開始
1. **安裝環境**  
   安裝 Python 3.11、Git for Windows（若需要上傳版本控管）。如需 GPU 加速請先安裝 CUDA/cuDNN 對應版本。
2. **安裝套件**  
   在專案路徑執行 `pip install -r requirements.txt`。
3. **檢查設定**  
   編輯 `config.ini`，依現場環境調整：
   - `[Paths]`：模型權重、cfg、類別檔路徑。
   - `[Detection]`：置信度、NMS 門檻、輸入尺寸。
   - `[Camera1]` / `[Camera2]`：攝影機索引、畫面大小、繼電器 API、ROI 線位置。
   - `[Display]`：`target_height` 控制拼接畫面高度，`max_width` 限制視窗最大寬度（0 代表自動使用螢幕寬度）。
4. **執行偵測**  
   - 直接雙擊 `run_all.bat`（或執行 `python run_detector.py Camera1 Camera2`）即可在單一 OpenCV 視窗中同時監看兩路攝影機，按 `q` 結束。
   - 若只想啟動單一攝影機，可執行 `python run_detector.py Camera1`。

## 上傳到 GitHub
1. 在 GitHub 建立空的 repository。
2. 於專案資料夾內執行：
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <repo-url>
   git push -u origin main
   ```
3. 大型資料集與模型權重已由 `.gitignore` 排除；若需分享權重，建議改用 Git LFS 或發佈頁面。

## 其他注意事項
- 灰階 YOLO 模型僅接受單通道輸入，推論端已自動將畫面轉灰階並共用同一個模型。
- 觸發繼電器時使用 `requests`，若需更嚴謹的錯誤處理，可在 `trigger_relay` 中加入重試或更完整的日誌。
- 若需要更高的彈性（例如新增 Camera3），只要在 `config.ini` 增加對應區塊並在啟動指令加入區塊名稱即可。
