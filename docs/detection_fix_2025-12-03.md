# 檢測過度計數問題修復
**日期**: 2025-12-03  
**問題**: 系統出現瘋狂檢測，每秒計數超過一千顆糖果

## 問題根因分析

### 1. 計數邏輯缺陷
**位置**: `src/run_detector.py` 第 430 行

**原始代碼**:
```python
if not track.counted and (crossed or (inside_zone and track.age >= 2)):
```

**問題**:
- 條件 `inside_zone and track.age >= 2` 會導致靜止或緩慢移動的物體被重複計數
- 只要物體在偵測區內存在超過 2 幀（約 0.06 秒），就會被計數
- 同一個物體可能被計數數百次

### 2. 信心度閾值過低
**位置**: `config.ini` [Detection] 區段

**原始值**: `confidence_threshold = 0.2`

**問題**:
- 低閾值導致大量誤檢（false positives）
- 每個誤檢都會建立新的追蹤物件
- 誤檢物件也會被計數，加劇過度計數問題

### 3. 追蹤距離閾值不足
**位置**: `candy_detector/constants.py` 第 31 行

**原始值**: `TRACK_DISTANCE_THRESHOLD_PX = 120`

**問題**:
- 閾值太小可能導致同一個物體被識別為多個不同的追蹤物件
- 產生重複追蹤，增加計數次數

## 實施的修復方案

### 修復 1: 移除靜態物體計數條件 ✅
**文件**: `src/run_detector.py`

**修改**:
```python
# 移除前
if not track.counted and (crossed or (inside_zone and track.age >= 2)):

# 移除後
if not track.counted and crossed:
```

**效果**:
- ✅ 只有真正穿越偵測線的物體才會被計數
- ✅ 消除靜止或緩慢移動物體的重複計數
- ✅ 確保每個物體只被計數一次

### 修復 2: 提高信心度閾值 ✅
**文件**: `config.ini`

**修改**:
```ini
# 從 0.2 提高到 0.4
confidence_threshold = 0.4
```

**效果**:
- ✅ 減少誤檢，降低假陽性率
- ✅ 只保留高置信度的檢測結果
- ✅ 減少無效追蹤物件的產生

### 修復 3: 增加追蹤距離閾值 ✅
**文件**: `candy_detector/constants.py`

**修改**:
```python
# 從 120 增加到 150
TRACK_DISTANCE_THRESHOLD_PX = 150
```

**效果**:
- ✅ 同一物體在相鄰幀間更容易被正確匹配
- ✅ 減少重複追蹤物件的產生
- ✅ 提高追蹤穩定性

## 驗證建議

重啟系統後，請驗證以下指標：

1. **檢測速率**: 應該降至合理範圍（例如每秒 1-10 個物體，取決於輸送帶速度）
2. **計數準確性**: 觀察是否有漏計或重複計數
3. **追蹤穩定性**: 每個物體應該只有一個追蹤 ID
4. **誤檢率**: 確認是否還有大量非糖果物體被檢測

## 後續調整

如果問題仍然存在，可以進一步調整：

### 選項 A: 進一步提高信心度閾值
```ini
confidence_threshold = 0.5  # 甚至 0.6
```

### 選項 B: 增加最小移動距離檢查
在 `run_detector.py` 中添加：
```python
# 計算移動距離
move_distance = math.hypot(curr_x - prev_x, track.center[1] - track.prev_center[1])
MIN_MOVE_DISTANCE = 30  # 像素

if not track.counted and crossed and move_distance >= MIN_MOVE_DISTANCE:
    # 計數邏輯
```

### 選項 C: 調整 NMS 閾值
```ini
nms_threshold = 0.3  # 降低 NMS 閾值以合併重疊的偵測框
```

## 重啟指令

修改完成後，請重啟系統使變更生效：
```bash
# 停止當前運行的程序
# 然後執行
start_all.bat
```
