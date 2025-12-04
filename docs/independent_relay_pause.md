# Camera1 和 Camera2 暫停噴氣獨立控制
**日期**: 2025-12-03  
**功能**: 每個攝影機的暫停噴氣功能完全獨立

## ✅ 已實現功能

### 1. 獨立的暫停狀態
每個攝影機都有自己獨立的 `relay_paused` 狀態：
- **Camera1** 的暫停噴氣不會影響 **Camera2**
- **Camera2** 的暫停噴氣不會影響 **Camera1**
- 每個攝影機可以獨立啟用/暫停噴氣功能

### 2. 後端實現
**文件**: `src/web_app.py`

#### API 端點: `/api/cameras/<camera_index>/relay/pause`
- **方法**: POST
- **功能**: 切換指定攝影機的暫停狀態
- **參數**: `camera_index` (0 或 1)
- **回應**:
  ```json
  {
    "success": true,
    "camera": "Camera 1",
    "paused": true
  }
  ```

#### 攝影機列表 API 增強
**端點**: `/api/cameras`

**新增欄位**: `relay_paused`
```json
[
  {
    "index": 0,
    "name": "Camera 1",
    "relay_paused": false
  },
  {
    "index": 1,
    "name": "Camera 2",
    "relay_paused": true
  }
]
```

### 3. 前端實現
**文件**: `static/script.js`

#### 按鈕狀態恢復
頁面加載時會自動恢復每個攝影機的暫停狀態：
```javascript
// 恢復暫停噴氣按鈕的狀態
const relayBtn = document.getElementById(`btn-pause-relay-${camera.index}`);
if (relayBtn && camera.relay_paused) {
    relayBtn.innerHTML = '▶️ 恢復噴氣';
    relayBtn.classList.add('btn-danger');
    relayBtn.classList.remove('btn-pause-relay');
}
```

#### 切換功能
`toggleRelayPause(cameraIndex)` 函數：
- 向後端發送 POST 請求
- 根據回應更新按鈕狀態
- 只影響指定的攝影機

### 4. 偵測邏輯
**文件**: `src/run_detector.py` (第 438 行)

每個攝影機在觸發噴氣前都會檢查自己的暫停狀態：
```python
if not getattr(cam_ctx, 'relay_paused', False):
    # 觸發噴氣
    threading.Thread(
        target=trigger_relay,
        args=(cam_ctx.relay_url, cam_ctx.relay_delay_ms),
        daemon=True,
    ).start()
else:
    print(f"[{cam_ctx.name}] 檢測到異常但噴氣已暫停，略過觸發")
```

## 使用方法

### 暫停 Camera1 的噴氣
1. 在 Camera1 的控制面板找到「⏸️ 暫停噴氣」按鈕
2. 點擊按鈕
3. 按鈕變為「▶️ 恢復噴氣」，顏色變紅
4. Camera1 檢測到異常時不會觸發噴氣
5. **Camera2 不受影響**，繼續正常噴氣

### 暫停 Camera2 的噴氣
1. 在 Camera2 的控制面板找到「⏸️ 暫停噴氣」按鈕
2. 點擊按鈕
3. 按鈕變為「▶️ 恢復噴氣」，顏色變紅
4. Camera2 檢測到異常時不會觸發噴氣
5. **Camera1 不受影響**，繼續正常噴氣

### 恢復噴氣功能
點擊「▶️ 恢復噴氣」按鈕即可恢復該攝影機的噴氣功能

## 狀態持久化

### 目前實現
- 狀態保存在記憶體中（`cam_ctx.relay_paused`）
- 頁面重新加載時會恢復狀態
- **應用程式重啟後**狀態會重置為未暫停

### 未來改進（可選）
如需在應用程式重啟後保持狀態，可以：
1. 將狀態保存到 `config.ini`
2. 或保存到資料庫
3. 或使用獨立的狀態檔案

## 測試場景

### 場景 1: 獨立暫停測試
1. 暫停 Camera1 的噴氣
2. Camera1 檢測到異常 → **不噴氣** ✅
3. Camera2 檢測到異常 → **正常噴氣** ✅

### 場景 2: 同時暫停
1. 暫停 Camera1 和 Camera2 的噴氣
2. 兩個攝影機都不會觸發噴氣
3. 可以獨立恢復任一個

### 場景 3: 狀態恢復
1. 暫停 Camera1
2. 刷新頁面
3. Camera1 的按鈕應顯示「▶️ 恢復噴氣」（紅色）✅
4. Camera2 的按鈕應顯示「⏸️ 暫停噴氣」（正常）✅

## 相關文件
- 後端 API: `src/web_app.py` (第 737-755 行)
- 前端控制: `static/script.js` (第 977-1007 行)
- 偵測邏輯: `src/run_detector.py` (第 438-445 行)

## 控制台日誌
暫停/恢復時會在伺服器日誌看到：
```
INFO - Camera 1 噴氣功能已暫停
INFO - Camera 2 噴氣功能已恢復
INFO - [Camera 1] 檢測到異常但噴氣已暫停，略過觸發
```
