# Contributing to Candy Defect Detection System

感謝您對本專案的興趣！我們歡迎任何形式的貢獻。

## 如何貢獻

### 回報問題 (Reporting Issues)

如果您發現 bug 或有功能建議：

1. 先搜尋 [Issues](https://github.com/Lei-TzuY/candy_detect/issues) 確認問題是否已被回報
2. 如果沒有，請創建新的 Issue，並提供：
   - 清楚的標題和描述
   - 重現步驟
   - 預期行為 vs 實際行為
   - 系統環境資訊（OS、Python 版本等）
   - 相關的錯誤訊息或截圖

### 提交程式碼 (Pull Requests)

1. **Fork 專案**
   ```bash
   # 在 GitHub 上 fork 這個專案
   git clone https://github.com/YOUR_USERNAME/candy_detect.git
   cd candy_detect
   ```

2. **創建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

3. **開發與測試**
   - 遵循現有的程式碼風格
   - 添加必要的測試
   - 確保所有測試通過
   - 更新相關文件

4. **提交變更**
   ```bash
   git add .
   git commit -m "描述: 簡短說明你的更改"
   ```

5. **推送並創建 PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   然後在 GitHub 上創建 Pull Request

## 程式碼風格

### Python
- 遵循 [PEP 8](https://pep8.org/) 風格指南
- 使用 4 個空格縮排
- 函數和變數使用 snake_case
- 類別使用 PascalCase
- 添加適當的 docstrings

### JavaScript
- 使用 2 個空格縮排
- 使用 camelCase 命名變數和函數
- 使用 const/let，避免 var
- 添加適當的註解

### 提交訊息格式
```
類型: 簡短描述 (不超過 50 字)

詳細說明（可選）
- 項目 1
- 項目 2

相關 Issue: #123
```

**類型：**
- `feat`: 新功能
- `fix`: Bug 修復
- `docs`: 文件更新
- `style`: 格式調整（不影響程式碼運行）
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 建置過程或輔助工具的變動

## 開發環境設定

```bash
# 安裝開發依賴
pip install -r requirements.txt

# 執行測試（如果有）
python -m pytest

# 啟動開發伺服器
python src/web_app.py
```

## 專案結構說明

- `src/`: 後端 Python 程式碼
- `static/`: 前端 JS/CSS
- `templates/`: HTML 模板
- `candy_detector/`: 核心偵測套件
- `tools/`: 實用工具
- `scripts/`: 批次處理腳本
- `docs/`: 文件

## 需要幫助？

- 查看 [README.md](README.md) 了解專案概況
- 查看 [CHANGELOG.md](CHANGELOG.md) 了解版本歷史
- 在 [Issues](https://github.com/Lei-TzuY/candy_detect/issues) 提問

## 行為準則

- 尊重所有貢獻者
- 建設性的批評
- 專注於對專案最有利的事情
- 展現同理心

感謝您的貢獻！ 🎉
