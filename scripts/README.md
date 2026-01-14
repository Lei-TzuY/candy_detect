# Candy Defect Detection System - Scripts Directory

## 📁 工具腳本說明

此目錄包含各種資料處理和工具腳本。

### 🏷️ 標註相關
- `auto_label.py` - AI 自動標註工具
- `fix_labels_class.py` - 修正標籤類別
- `fix_old_dataset_labels.py` - 修正舊資料集標籤
- `swap_ai_label_classes.py` - 交換 AI 標籤類別
- `restore_ai_labels.py` - 還原 AI 標籤

### 🧹 資料清理
- `clean_extreme_boxes.py` - 清理極端標記框
- `remove_blank_images.py` - 移除空白圖片
- `remove_duplicates.py` - 移除重複圖片
- `remove_duplicates_with_preview.py` - 移除重複圖片(預覽版)

### 📹 影片處理
- `convert_video.py` - 影片格式轉換
- `detect_video.py` - 影片偵測
- `extract_frames.py` - 擷取影格

### 🗂️ 資料組織
- `organize_frames.py` - 組織影格
- `prepare_yolo_dataset.py` - 準備 YOLO 資料集
- `rename_remove_prefix.py` - 重新命名移除前綴
- `append_assets.py` - 附加資源
- `atomic_update.py` - 原子更新

### 🧪 測試
- `test_load.py` - 測試載入
- `test_old_yolo_model.py` - 測試舊 YOLO 模型
- `test_yolo_model.py` - 測試 YOLO 模型
- `test_yolo_and_generate_report.py` - 測試 YOLO 並生成報告

### 🤖 訓練
- `train_yolo.py` - YOLOv8 訓練腳本 (CLI)

### 🗃️ 舊資料
- `create_old_dataset_metadata.py` - 建立舊資料集元數據

### ⚙️ 輔助工具
- `insert_function.py` - 插入功能
- `fix_and_update_recorder.py` - 修正並更新錄影器

## 📝 使用建議

大部分工具已整合到 Web 介面中，建議優先使用 Web 介面操作。
這些腳本主要用於批次處理或特殊需求。
