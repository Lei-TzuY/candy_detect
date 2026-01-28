# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-01-28

### Added
- 🎥 即時多攝影機瑕疵偵測系統
- 🤖 支援 YOLOv8 (n/s/m) 和 YOLO11 (n/s/m) 共 6 種模型
- 📹 錄影與回放功能
- 🏷️ 資料標註工具整合
- 📊 即時統計圖表（瑕疵率趨勢、產品分布）
- ⚙️ 動態攝影機管理（熱插拔、來源切換）
- 🎯 焦距、曝光、噴氣延遲自動儲存
- 📈 模型訓練介面
- 🗄️ 歷史記錄查詢與匯出
- 🔄 模型動態切換（無需重啟）

### Changed
- 💾 移除手動儲存按鈕，改為自動儲存
- 📍 統計數據移至攝影機卡片內部
- 🎨 優化 UI/UX（按鈕間距、字體顏色、提示框）
- 🔧 改進模型識別顯示（使用檔案名稱而非路徑）

### Fixed
- 🐛 修復新增攝影機時的 `camera_index` 屬性錯誤
- 🔍 修復攝影機來源選單初始化問題
- 📱 修復攝影機卡片按鈕佈局

### Technical
- 🏗️ 重構專案結構
- 📝 更新完整的 README.md
- 🗂️ 優化 .gitignore 配置
- 📦 更新 requirements.txt
- 🔒 排除大型檔案和資料夾（模型、資料集、日誌）

## Roadmap

### Planned Features
- [ ] 支援更多 YOLO 版本（YOLOv9, YOLOv10）
- [ ] 增加雲端同步功能
- [ ] 支援 Linux 系統
- [ ] 增加 REST API 文件
- [ ] 支援多語言界面
- [ ] 增加模型評估工具
- [ ] 支援自定義類別訓練
