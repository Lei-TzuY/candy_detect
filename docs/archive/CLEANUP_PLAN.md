# 專案清理計劃

## 🔴 強烈建議刪除（冗餘/過時）

### 根目錄
- [ ] `LabelImg_2/` - 與 `LabelImg/` 重複
- [ ] `annotation_issues_visualization/` - 舊的可視化結果
- [ ] `relabeled_visualization/` - 舊的標註可視化
- [ ] `visualizations/` - 舊的可視化結果
- [ ] `之前訓練的 yolov8/` - 過時的訓練結果

### datasets/ 資料夾（共約 1.5 GB 冗餘）
- [ ] `失敗的標記/` (365 MB) - 失敗的標註，保留價值低
- [ ] `最新資料/` (248 MB) - 名稱不明確
- [ ] `最新資料集/` (49 MB) - 與 `最新資料集(1)/` 重複
- [ ] `最新資料集.zip` - 已解壓，可刪除壓縮檔
- [ ] `最新資料集 (1).7z` - 壓縮檔案冗餘
- [ ] `candy_merged_20260116_154158_backup_1379/` (193 MB) - 備份資料夾
- [ ] `Elon-candy-Uploaded on 01-21-26 at 3-32 pm.coco (1) - 複製/` (69 MB) - 重複的複製
- [ ] `annotation_report_20260121_152002/` (92 MB) - 舊報告
- [ ] `annotation_report_20260121_152144/` (92 MB) - 舊報告
- [ ] `annotation_report_20260121_163102/` (60 MB) - 舊報告
- [ ] `annotation_report_20260121_163501/` (91 MB) - 舊報告
- [ ] `annotation_report_20260121_165528/` (0 MB) - 空報告
- [ ] `2026-01-16_14-41_手動紀錄_whitebg_20260116_152143/` (36 MB) - 舊紀錄

### 保留但可考慮清理
- [ ] `recordings/` - 如果不需要舊的錄影，可清空
- [ ] `logs/` - 如果不需要舊的日誌，可清空
- [ ] `reports/` - 如果不需要舊的報告，可清空
- [ ] `results/` - 舊的測試結果
- [ ] `runs/` - 舊的訓練執行記錄

## 🟡 建議保留的資料夾

### datasets/ 保留
- ✅ `candy/` (68 MB) - 主要數據集
- ✅ `yolo_dataset/` (47 MB) - YOLO 格式數據集
- ✅ `最新資料集(1)/` (528 MB) - 最新完整數據集
- ✅ `Elon-candy-Uploaded on 01-21-26 at 3-32 pm.coco (1)/` (105 MB) - 已上傳版本
- ✅ `annotation_report_20260121_165552/` (92 MB) - 最新報告（只保留這個）
- ✅ `extracted_frames/` (80 MB) - 提取的影格
- ✅ `New_annotated_defect/` (24 MB) - 新標註的瑕疵
- ✅ `2026-01-16_14-41_手動紀錄/` (12 MB) - 手動記錄
- ✅ Python 工具腳本（.py 檔案）

### 根目錄保留
- ✅ `LabelImg/` - 主要標註工具
- ✅ `models/` - 訓練好的模型
- ✅ `src/`, `static/`, `templates/` - 核心程式碼
- ✅ `candy_detector/` - 偵測器模組
- ✅ `scripts/`, `tools/`, `utils/` - 工具程式
- ✅ `docs/` - 文件
- ✅ `app/` - 應用程式

## 📊 預估節省空間

| 類別 | 大小 |
|------|------|
| datasets 冗餘資料 | ~1.3 GB |
| 舊的可視化結果 | ~100 MB |
| 舊的訓練結果 | ~200 MB |
| **總計** | **~1.6 GB** |

## 🔧 清理指令

### 1. 刪除 datasets 冗餘（謹慎執行！）
```powershell
# 先備份重要資料！
# 然後執行：
Remove-Item -Path ".\datasets\失敗的標記" -Recurse -Force
Remove-Item -Path ".\datasets\最新資料" -Recurse -Force
Remove-Item -Path ".\datasets\最新資料集" -Recurse -Force
Remove-Item -Path ".\datasets\最新資料集.zip" -Force
Remove-Item -Path ".\datasets\最新資料集 (1).7z" -Force
Remove-Item -Path ".\datasets\candy_merged_20260116_154158_backup_1379" -Recurse -Force
Remove-Item -Path ".\datasets\Elon-candy-Uploaded on 01-21-26 at 3-32 pm.coco (1) - 複製" -Recurse -Force
Remove-Item -Path ".\datasets\annotation_report_20260121_152002" -Recurse -Force
Remove-Item -Path ".\datasets\annotation_report_20260121_152144" -Recurse -Force
Remove-Item -Path ".\datasets\annotation_report_20260121_163102" -Recurse -Force
Remove-Item -Path ".\datasets\annotation_report_20260121_163501" -Recurse -Force
Remove-Item -Path ".\datasets\annotation_report_20260121_165528" -Recurse -Force
Remove-Item -Path ".\datasets\2026-01-16_14-41_手動紀錄_whitebg_20260116_152143" -Recurse -Force
```

### 2. 刪除根目錄冗餘
```powershell
Remove-Item -Path ".\LabelImg_2" -Recurse -Force
Remove-Item -Path ".\annotation_issues_visualization" -Recurse -Force
Remove-Item -Path ".\relabeled_visualization" -Recurse -Force
Remove-Item -Path ".\visualizations" -Recurse -Force
Remove-Item -Path ".\之前訓練的 yolov8" -Recurse -Force
```

### 3. 清空可選資料夾（選擇性）
```powershell
# 清空但保留資料夾結構
Get-ChildItem -Path ".\recordings" -File | Remove-Item -Force
Get-ChildItem -Path ".\logs" -File | Remove-Item -Force
Get-ChildItem -Path ".\reports" -File | Remove-Item -Force
Get-ChildItem -Path ".\results" -Recurse | Remove-Item -Force
```

## ⚠️ 注意事項

1. **執行前請先備份重要資料！**
2. 確認不需要舊的標註、訓練結果或報告
3. 建議分批執行，先刪除最明顯的冗餘
4. 刪除後記得更新 .gitignore 避免未來再次加入

## 🎯 清理後的專案結構

```
candy_detect/
├── src/              # 核心程式碼
├── static/           # 前端資源
├── templates/        # HTML 模板
├── candy_detector/   # 偵測器模組
├── datasets/         # 精簡後的數據集
│   ├── candy/
│   ├── yolo_dataset/
│   └── 最新資料集(1)/
├── models/           # 訓練好的模型
├── LabelImg/         # 標註工具
├── docs/             # 文件
├── scripts/          # 工具腳本
└── app/              # 應用程式
```
