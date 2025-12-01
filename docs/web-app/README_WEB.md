# Web 應用啟動指南 (簡化版)

## 快速啟動 (最簡單)

### 方法 1: 雙擊批處理文件 ⭐ 推薦

在資料夾中找到以下其中一個文件，雙擊即可：

- **start_web.bat** ← 推薦使用 (無亂碼問題)
- **start_web_app.bat** ← 備選

2-3 秒後，Web 應用將啟動。

### 方法 2: 使用 PowerShell

打開 PowerShell 並執行：

```powershell
cd C:\Users\st313\Desktop\candy
.venv\Scripts\python.exe web_app.py
```

---

## 訪問應用

啟動後，在瀏覽器中訪問：

```
http://localhost:5000
```

您將看到：
- 左側：Camera 1 實時影像
- 右側：Camera 2 實時影像
- 下方：統計數據和性能指標

---

## 如何停止

在終端/命令提示符中按 **Ctrl+C**

---

## 常見問題

### Q: 看到亂碼？
**A**: 使用 `start_web.bat` 而不是 `start_web_app.bat`

### Q: Port 5000 被占用？
**A**: 編輯 `web_app.py` 的最後一行，改 `port=5001`

### Q: 無法看到影像？
**A**: 檢查 `config.ini` 中的攝像頭配置

### Q: 應用啟動失敗？
**A**: 查看 `app/logs/app.log` 檢查錯誤

---

## 詳細文檔

需要更多信息，請查看：
- **START_HERE.md** - 30秒快速上手
- **QUICK_START.md** - 快速參考
- **WEB_APP_SETUP.md** - 詳細配置

---

**提示**: 建議先閱讀 START_HERE.md
