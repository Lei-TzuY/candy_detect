# 錄影檔案無法開啟問題修復
**日期**: 2025-12-03  
**錯誤**: `0xC00D36C4` - 檔案類型不支援、副檔名不正確或檔案已損毀

![錯誤截圖](file:///C:/Users/st313/.gemini/antigravity/brain/1ce7b601-7b05-4bc4-80a4-d39ff6fe92b7/uploaded_image_1764746759110.png)

## 問題分析

### 根本原因
錄影檔案使用了 `mp4v` 編碼器，這個編碼器在 Windows Media Player 上可能不被支援或無法正確解碼。

### 錯誤代碼說明
- **0xC00D36C4**: Windows Media Player 無法播放此檔案
- **常見原因**:
  1. 視頻編碼器不相容
  2. 檔案損壞或未正確結束錄影
  3. 缺少必要的編解碼器

## 實施的修復方案

### 修復 1: 改進編碼器選擇 ✅
**文件**: `src/video_recorder.py` (第 233-270 行)

#### 新的編碼器選擇邏輯
系統現在會依序嘗試多種編碼器，直到找到可用的為止：

```python
codec_list = [
    ('avc1', 'H.264'),      # 最佳品質，Windows 10+ 原生支援
    ('H264', 'H.264'),      # H.264 替代編碼
    ('XVID', 'XVID'),       # 高相容性，大多數播放器支援
    ('MJPG', 'Motion JPEG'), # 動態 JPEG，通用性高
    ('mp4v', 'MPEG-4')      # 備用選項
]
```

#### 優先順序說明

| 編碼器 | 支援度 | 檔案大小 | 畫質 | 推薦程度 |
|--------|--------|----------|------|----------|
| **H.264 (avc1)** | ⭐⭐⭐⭐⭐ | 小 | 高 | 最推薦 |
| **XVID** | ⭐⭐⭐⭐⭐ | 中 | 中 | 高相容性 |
| **MJPG** | ⭐⭐⭐⭐ | 大 | 高 | 備用選項 |
| **mp4v** | ⭐⭐⭐ | 中 | 中 | 最後選項 |

### 修復 2: 轉換工具 ✅
**文件**: `convert_video.py`

為已經錄製的無法播放檔案提供轉換工具。

## 使用方法

### 方法 A: 重新錄影（推薦）
1. **重啟應用程式**使編碼器修改生效
2. 開始新的錄影
3. 系統會自動選擇最佳的可用編碼器
4. 錄影完成後檔案應該可以正常播放

### 方法 B: 轉換現有檔案

#### 轉換單一檔案
```bash
# 基本用法（使用 XVID 編碼器）
python convert_video.py "recordings/recording_1_20251203_151453.mp4"

# 指定輸出檔案
python convert_video.py "recordings/recording_1_20251203_151453.mp4" -o "recordings/fixed.mp4"

# 使用不同編碼器
python convert_video.py "recordings/recording_1_20251203_151453.mp4" -c MJPG
```

#### 批次轉換整個目錄
```bash
# 轉換 recordings 目錄中的所有 mp4 檔案
python convert_video.py recordings --all

# 使用特定編碼器
python convert_video.py recordings --all -c XVID
```

#### 轉換完成後
- 原始檔案: `recording_1_20251203_151453.mp4`
- 轉換檔案: `recording_1_20251203_151453_converted.mp4`
- 原始檔案會保留，轉換後的檔案應該可以播放

### 方法 C: 使用第三方播放器
如果不想轉換，可以使用支援更多編碼器的播放器：

推薦播放器：
- **VLC Media Player** (免費) - https://www.videolan.org/
- **PotPlayer** (免費)
- **MPC-HC** (免費)

這些播放器通常能播放 Windows Media Player 無法播放的檔案。

## 驗證修復

### 測試新錄影功能
1. 重啟應用程式
2. 前往錄影頁面
3. 開始錄影
4. 錄影幾秒後停止
5. 查看控制台輸出，應該會看到類似：
   ```
   錄影器: 成功使用 XVID 編碼器
   ```
6. 嘗試播放錄影檔案

### 檢查編碼器可用性
在 Python 中測試：
```python
import cv2

codecs = ['avc1', 'H264', 'XVID', 'MJPG', 'mp4v']
for codec in codecs:
    try:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter('test.mp4', fourcc, 30, (640, 480))
        if writer.isOpened():
            print(f"✓ {codec} 可用")
            writer.release()
        else:
            print(f"✗ {codec} 不可用")
    except Exception as e:
        print(f"✗ {codec} 錯誤: {e}")
```

## 其他建議

### 安裝完整的編解碼器包
如果系統缺少編碼器，可以安裝：

**Windows**:
- **K-Lite Codec Pack** (推薦)
  - 下載: https://codecguide.com/download_kl.htm
  - 選擇 "Standard" 或 "Mega" 版本
  - 安裝後重啟電腦

**或使用 ffmpeg**:
```bash
# 使用 chocolatey 安裝
choco install ffmpeg

# 或從官網下載
# https://ffmpeg.org/download.html
```

### 調整錄影參數
如果檔案太大，可以在 `video_recorder.py` 中調整：

```python
# 降低 FPS (第 236 行)
fps = 20  # 原本是 30

# 降低解析度 (在 start_recording 前設定)
recorder.set_resolution(1280, 720)  # 或 640x480
```

## 故障排除

### 問題 1: 所有編碼器都失敗
**症狀**: 看到錯誤 "無法建立錄影檔案 - 所有編碼器都失敗"

**解決方案**:
1. 確認 OpenCV 已正確安裝: `pip install opencv-python`
2. 嘗試安裝完整版: `pip install opencv-contrib-python`
3. 安裝 K-Lite Codec Pack
4. 重啟電腦

### 問題 2: 轉換後檔案仍無法播放
**症狀**: 使用 `convert_video.py` 轉換後仍無法播放

**解決方案**:
1. 嘗試不同的編碼器:
   ```bash
   python convert_video.py input.mp4 -c MJPG
   python convert_video.py input.mp4 -c H264
   ```
2. 使用 VLC 等第三方播放器
3. 檢查原始檔案是否完整（錄影是否正確停止）

### 問題 3: 錄影時當機或崩潰
**症狀**: 開始錄影後應用程式當機

**解決方案**:
1. 檢查磁碟空間是否充足
2. 確認攝影機未被其他程式使用
3. 嘗試降低解析度或 FPS
4. 查看控制台錯誤訊息

## 相關文件
- 錄影器源碼: `src/video_recorder.py`
- 轉換工具: `convert_video.py`
- 錄影 API: `src/web_app.py` (檢測整合部分)

## 技術細節

### 編碼器比較
```
H.264 (avc1/H264):
  ✓ 最佳壓縮率
  ✓ 高畫質
  ✓ Windows 10+ 原生支援
  ✗ 需要硬體或軟體編碼器

XVID:
  ✓ 高相容性
  ✓ 適中檔案大小
  ✓ 大多數系統預裝
  ~ 壓縮率中等

MJPG:
  ✓ 最高相容性
  ✓ 不需特殊編碼器
  ✗ 檔案較大
  ~ 畫質略低於 H.264

mp4v:
  ~ 舊版 MPEG-4
  ~ 相容性一般
  ✗ Windows Media Player 支援不穩定
```

### 為什麼選擇這個順序？
1. **avc1/H264**: 優先嘗試最佳品質
2. **XVID**: 若 H.264 不可用，退而求其次
3. **MJPG**: 保證能正常工作的選項
4. **mp4v**: 最後備用

這樣可以在品質和相容性之間取得最佳平衡。
