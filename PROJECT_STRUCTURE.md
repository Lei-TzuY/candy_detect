# Candy Defect Detection System - Project Organization

## 最近更新 (2026-01-21)

本專案已重新整理，結構更清晰，方便維護和擴展。

## 目錄結構

### 核心模組 (`src/`)
- **web_app.py** - Flask Web 應用主程式
- **run_detector.py** - 即時偵測系統
- **video_recorder.py** - 多攝影機錄影管理
- **yolov8_trainer.py** - YOLOv8 訓練模組

### 腳本目錄 (`scripts/`)
包含訓練和資料處理腳本：
- `train_yolo.py` - 標準 YOLOv8 訓練
- `train_yolo_large.py` - 大型模型訓練
- `train_yolov8s_max_performance.py` - 最高效能訓練
- `prepare_yolo_dataset.py` - 資料集準備
- `auto_labeling/` - 自動標註工具集

### 工具目錄 (`tools/`)
輔助工具和腳本：
- **檢查工具**: `check_*.py` - 檢查訓練資料、標註品質、模型資訊等
- **修復工具**: `fix_*.py` - 修復標註問題、LabelImg 等
- **報告工具**: `generate_*.py` - 生成準確度報告、標註報告、訓練報告
- **視覺化**: `visualize_*.py` - 視覺化標註、驗證結果、合併資料等
- **其他**: 資料合併、重新標註等工具

### 套件模組 (`candy_detector/`)
核心功能封裝：
- `config.py` - 設定檔載入與管理
- `logger.py` - 統一日誌系統
- `models.py` - 資料模型定義
- `optimization.py` - 效能優化工具

### 工具函式庫 (`utils/`)
共用工具函式：
- `yolo_utils.py` - YOLO 格式標註處理（NEW）
- `performance_optimizer.py` - 效能優化器

## 重複程式碼整合

### YOLO 標註處理
所有 `load_yolo_annotations` 函數已整合到 `utils/yolo_utils.py`：
- ✅ 統一的標註載入函數
- ✅ YOLO 格式轉換
- ✅ 標註驗證
- ✅ 視覺化繪製

使用範例：
```python
from utils.yolo_utils import load_yolo_annotations, draw_annotations

# 載入標註
annotations = load_yolo_annotations(label_path, img_width, img_height)

# 繪製標註
annotated_img = draw_annotations(image, annotations)
```

## 開發建議

### 新增功能
1. **核心功能** → 添加到 `src/` 或 `candy_detector/`
2. **訓練腳本** → 添加到 `scripts/`
3. **工具腳本** → 添加到 `tools/`
4. **共用函式** → 添加到 `utils/`

### 程式碼重構
- 盡量使用 `utils/yolo_utils.py` 中的函數
- 避免複製貼上相同的程式碼
- 新增共用功能時，考慮加入 `candy_detector/` 或 `utils/`

### 測試
- 測試腳本可放在 `scripts/test_*.py`
- 單元測試可建立 `tests/` 目錄

## Git 工作流程

### 分支管理
- `main` - 穩定版本
- `dev` - 開發分支
- `feature/*` - 新功能分支

### 提交訊息規範
```
feat: 新增功能
fix: 修復錯誤
refactor: 重構程式碼
docs: 文件更新
style: 格式調整
test: 測試相關
chore: 雜項更新
```

## 下一步計畫

- [ ] 將重複的 auto_label 程式碼整合
- [ ] 創建單元測試
- [ ] API 文件自動生成
- [ ] Docker 容器化
- [ ] CI/CD 流程設置
