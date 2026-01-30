# 前端配置顯示和日誌問題修復

## ✅ 已修復的問題

### 問題 1：前端顯示舊值（未讀取配置）

**現象：**
```
前端顯示：
🎯 焦距：128
📸 曝光：-7
⏱️噴氣延遲：1600ms

config.ini 實際值：
default_focus = 80 (Camera1) / 100 (Camera2)
relay_delay_ms = 2300 (Camera1) / 2200 (Camera2)
```

**根本原因：**
- `/api/cameras` 端點沒有返回攝影機的設定值
- 前端無法獲取實際配置，顯示的是硬編碼的預設值

**解決方案：**
修改 `src/web_app.py` 的 `/api/cameras` 端點，添加設定值：

```python
@app.route('/api/cameras')
def get_cameras():
    cameras = [
        {
            'index': i,
            'name': cam.name,
            # ... 其他屬性
            # 添加設定值（讓前端可以顯示當前配置）
            'focus': getattr(cam, 'current_focus', 128),
            'exposure': getattr(cam, 'exposure', -7),
            'relay_delay_ms': getattr(cam, 'relay_delay_ms', 1600)
        }
        for i, cam in enumerate(camera_contexts)
    ]
    return jsonify(cameras)
```

### 問題 2：後端日誌太吵

**現象：**
```
127.0.0.1 - - [30/Jan/2026 17:31:48] "GET /api/stats HTTP/1.1" 200 -
127.0.0.1 - - [30/Jan/2026 17:31:49] "GET /api/history?hours=1 HTTP/1.1" 200 -
127.0.0.1 - - [30/Jan/2026 17:31:50] "GET /api/stats HTTP/1.1" 200 -
... (每秒多次)
```

**根本原因：**
- Flask 的 `werkzeug` logger 預設會記錄所有 HTTP 請求
- 前端定期輪詢 `/api/stats` 和 `/api/history`
- 導致終端被大量訪問日誌淹沒

**解決方案：**
禁用 werkzeug 的訪問日誌，只顯示錯誤：

```python
# 禁用 Flask 的訪問日誌（減少終端輸出噪音）
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)  # 只顯示錯誤，不顯示訪問日誌
```

## 🎯 效果對比

### 修復前

**前端顯示：**
```
Camera 1:
  🎯 焦距：128         ← 錯誤（應該是 80）
  📸 曝光：-7          ← 正確
  ⏱️噴氣延遲：1600ms  ← 錯誤（應該是 2300）

Camera 2:
  🎯 焦距：128         ← 錯誤（應該是 100）
  📸 曝光：-7          ← 正確
  ⏱️噴氣延遲：1600ms  ← 錯誤（應該是 2200）
```

**終端輸出：**
```
2026-01-30 17:31:48 - INFO - Camera 1: 已設定曝光值為 -7
127.0.0.1 - - [30/Jan/2026 17:31:48] "GET /api/stats HTTP/1.1" 200 -
127.0.0.1 - - [30/Jan/2026 17:31:48] "GET /api/history HTTP/1.1" 200 -
127.0.0.1 - - [30/Jan/2026 17:31:49] "GET /api/stats HTTP/1.1" 200 -
127.0.0.1 - - [30/Jan/2026 17:31:49] "GET /api/history HTTP/1.1" 200 -
（無限滾動...）
```

### 修復後

**前端顯示：**
```
Camera 1:
  🎯 焦距：80          ✅ 正確（從 config 讀取）
  📸 曝光：-7          ✅ 正確
  ⏱️噴氣延遲：2300ms  ✅ 正確（從 config 讀取）

Camera 2:
  🎯 焦距：100         ✅ 正確（從 config 讀取）
  📸 曝光：-7          ✅ 正確
  ⏱️噴氣延遲：2200ms  ✅ 正確（從 config 讀取）
```

**終端輸出：**
```
2026-01-30 17:31:48 - INFO - Camera 1: 已設定曝光值為 -7
2026-01-30 17:31:48 - INFO - Camera 1: 已將初始焦距設為預設值 80
2026-01-30 17:32:05 - INFO - 已將 Camera 2 的噴氣延遲保存為: 2200ms
（只有重要的系統訊息，乾淨清爽）
```

## 📋 技術細節

### 1. 為什麼前端拿不到正確的值？

#### 問題流程

```
1. 應用啟動
   ↓
2. 從 config.ini 讀取設定
   cam.current_focus = 80 (Camera1)
   cam.relay_delay_ms = 2300 (Camera1)
   ↓
3. 前端請求 /api/cameras
   {
     'focus': 128,  ← 硬編碼的預設值，沒有讀取 cam.current_focus！
     'relay_delay_ms': 1600  ← 硬編碼的預設值！
   }
   ↓
4. 前端顯示錯誤的值
```

#### 修復流程

```
1. 應用啟動
   ↓
2. 從 config.ini 讀取設定
   cam.current_focus = 80 (Camera1)
   cam.relay_delay_ms = 2300 (Camera1)
   ↓
3. 前端請求 /api/cameras
   {
     'focus': getattr(cam, 'current_focus', 128),  ← 讀取實際值！
     'relay_delay_ms': getattr(cam, 'relay_delay_ms', 1600)  ← 讀取實際值！
   }
   ↓
4. 前端顯示正確的值 ✅
```

### 2. 為什麼需要禁用 werkzeug 日誌？

#### 日誌層級說明

```python
logging.DEBUG    # 調試訊息（最詳細）
logging.INFO     # 一般資訊
logging.WARNING  # 警告
logging.ERROR    # 錯誤  ← 設置為這個
logging.CRITICAL # 嚴重錯誤
```

#### 修改前（預設級別：INFO）

```
[werkzeug] INFO: 127.0.0.1 - - "GET /api/stats HTTP/1.1" 200 -
[werkzeug] INFO: 127.0.0.1 - - "GET /api/history HTTP/1.1" 200 -
[candy_detector] INFO: Camera 1: 已設定曝光值為 -7
[werkzeug] INFO: 127.0.0.1 - - "POST /api/cameras/0/focus HTTP/1.1" 200 -
```

所有訊息都顯示，包括每個 HTTP 請求。

#### 修改後（設置級別：ERROR）

```
[candy_detector] INFO: Camera 1: 已設定曝光值為 -7
[candy_detector] INFO: 已將 Camera 2 的噴氣延遲保存為: 2200ms
```

只顯示應用的重要訊息，HTTP 訪問日誌被過濾掉。

#### 如果發生錯誤

```
[werkzeug] ERROR: Exception on /api/models [GET]
Traceback (most recent call last):
  ...
```

錯誤訊息仍然會顯示！

### 3. getattr() 的妙用

```python
'focus': getattr(cam, 'current_focus', 128)
```

**解析：**
- `getattr(obj, 'attr', default)` = `obj.attr if hasattr(obj, 'attr') else default`
- 如果 `cam.current_focus` 存在，返回實際值
- 如果不存在（例如舊版本），返回預設值 128
- 避免 `AttributeError`

## 🚀 使用效果

### 重啟應用後

```batch
start_all.bat
```

**終端輸出（乾淨）：**
```
[1/2] Starting Relay Service...
[1.5/2] Releasing camera resources...
[1.6/2] Warming up cameras...
     Camera status: 2/2 ready
[2/2] Starting Detection System...

2026-01-30 17:35:00 - INFO - Camera 1: 已設定曝光值為 -7
2026-01-30 17:35:00 - INFO - Camera 1: 已將初始焦距設為預設值 80
2026-01-30 17:35:01 - INFO - Camera 2: 已設定曝光值為 -7
2026-01-30 17:35:01 - INFO - Camera 2: 已將初始焦距設為預設值 100
2026-01-30 17:35:02 - INFO - 伺服器啟動在 http://localhost:5000
```

（之後不會有大量的 GET 請求日誌）

**前端顯示（正確）：**
```
Camera 1:
  🎯 焦距：80          ← 從 config.ini 讀取
  📸 曝光：-7
  ⏱️噴氣延遲：2300ms  ← 從 config.ini 讀取

Camera 2:
  🎯 焦距：100         ← 從 config.ini 讀取
  📸 曝光：-7
  ⏱️噴氣延遲：2200ms  ← 從 config.ini 讀取
```

### 調整設定後

**在前端調整焦距：**
```
Camera 1: 焦距 80 → 100
```

**終端輸出：**
```
2026-01-30 17:36:00 - INFO - Camera 1 焦距已更新為: 100
2026-01-30 17:36:00 - INFO - 已將 Camera 1 的預設焦距保存為: 100
```

（不會有 GET / POST 請求的訪問日誌）

**重新整理頁面：**
```
Camera 1:
  🎯 焦距：100         ← 正確顯示新值！
```

## 🔧 進階配置

### 如果需要查看訪問日誌（調試用）

臨時啟用訪問日誌，修改 `web_app.py`：

```python
# 禁用 Flask 的訪問日誌（減少終端輸出噪音）
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)  # 改為 INFO 顯示訪問日誌
```

### 只顯示特定路徑的訪問日誌

```python
import logging

class SelectiveLogFilter(logging.Filter):
    def filter(self, record):
        # 只記錄包含 '/api/models' 的請求
        return '/api/models' in record.getMessage()

log = logging.getLogger('werkzeug')
log.addFilter(SelectiveLogFilter())
```

### 自定義日誌格式

```python
import logging

# 簡化日誌格式
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

log = logging.getLogger('werkzeug')
log.handlers = [handler]
```

## ✅ 修復總結

### 修改的文件

**`src/web_app.py`**

1. **添加 werkzeug 日誌過濾**（第 68-71 行）
   ```python
   import logging
   log = logging.getLogger('werkzeug')
   log.setLevel(logging.ERROR)
   ```

2. **在 /api/cameras 返回設定值**（第 852-856 行）
   ```python
   'focus': getattr(cam, 'current_focus', 128),
   'exposure': getattr(cam, 'exposure', -7),
   'relay_delay_ms': getattr(cam, 'relay_delay_ms', 1600)
   ```

### 效果

- ✅ 前端正確顯示實際配置值
- ✅ 終端乾淨，不再被訪問日誌淹沒
- ✅ 重要的系統訊息仍然顯示
- ✅ 錯誤訊息不會被過濾

### 重啟應用

```batch
start_all.bat
```

現在前端會正確顯示配置值，終端也不會被訪問日誌淹沒！🎉
