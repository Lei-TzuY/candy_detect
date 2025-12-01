🎯 **Web 應用 - 立即開始 (30 秒)**

## 最快啟動方式

### ⚡ 第 1 步 - 雙擊啟動 (推薦)
```
📍 文件位置: C:\Users\st313\Desktop\candy\start_web_app.bat
⚡ 操作: 雙擊即可
⏱️ 耗時: 5-10 秒
```

### 🌐 第 2 步 - 打開瀏覽器
```
訪問地址: http://localhost:5000
```

### ✨ 完成！
- 您將看到實時影像和檢測框
- 統計信息實時更新
- 系統已完全就緒

---

## 或者使用命令行

```powershell
# 打開 PowerShell 並執行
cd C:\Users\st313\Desktop\candy
.venv\Scripts\python.exe web_app.py

# 然後訪問: http://localhost:5000
```

---

## 📚 詳細文檔

| 文檔 | 閱讀時間 | 內容 |
|------|---------|------|
| [QUICK_START.md](QUICK_START.md) | 3 分鐘 | 快速參考卡 |
| [WEB_APP_SETUP.md](WEB_APP_SETUP.md) | 10 分鐘 | 詳細配置指南 |
| [INSTALLATION_COMPLETE.md](INSTALLATION_COMPLETE.md) | 15 分鐘 | 完整安裝報告 |
| [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md) | 5 分鐘 | 檢查清單 |

---

## 🎯 驗證清單

啟動後檢查以下項目：

- [ ] 終端顯示 `Running on http://0.0.0.0:5000`
- [ ] 瀏覽器訪問 http://localhost:5000 成功
- [ ] 影像流正常顯示
- [ ] 檢測框出現在缺陷上
- [ ] FPS > 15
- [ ] 統計信息實時更新

全部✅ → 恭喜，系統已準備就緒！

---

## ❓ 常見問題 (30 秒解決)

**Q: Port 5000 被占用？**
A: 編輯 `web_app.py` 最後一行，改 `port=5001`

**Q: 無法看到影像？**
A: 檢查 `config.ini` 的攝像頭配置

**Q: 應用啟動失敗？**
A: 查看 `app/logs/app.log` 檢查錯誤信息

---

## 🛑 停止應用

按 `Ctrl+C` 即可停止

---

**更新時間**: 2025-11-21  
**狀態**: ✅ 生產環境就緒

