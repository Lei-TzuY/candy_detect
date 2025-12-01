# 🚀 Web 應用快速參考卡

## ⚡ 一鍵啟動

### **最簡單的方法 - 雙擊批處理文件**
```
start_web_app.bat
```

### 或使用命令行
```powershell
cd C:\Users\st313\Desktop\candy
.venv\Scripts\python.exe web_app.py
```

## 🌐 訪問應用

| 訪問方式 | 地址 |
|---------|------|
| 本機訪問 | http://localhost:5000 |
| 同網絡訪問 | http://192.168.x.x:5000 |

## 📊 功能一覽

| 功能 | 地址 | 說明 |
|------|------|------|
| 主儀表板 | / | 即時影像和統計 |
| 統計 API | /api/stats | JSON 格式統計數據 |
| 攝像頭列表 | /api/cameras | 所有攝像頭信息 |
| 歷史記錄 | /api/history | 檢測記錄查詢 |
| 配置管理 | /api/config | 動態參數調整 |

## ✅ 檢查清單

啟動前檢查：
- [ ] 攝像頭已連接
- [ ] `config.ini` 已配置
- [ ] 虛擬環境 `.venv` 存在
- [ ] Flask 已安裝

啟動時檢查：
- [ ] 終端顯示 `Running on http://0.0.0.0:5000`
- [ ] 瀏覽器能訪問 http://localhost:5000
- [ ] 影像流已加載
- [ ] 檢測框正常顯示

## 🔧 常用命令

### 檢查 Flask 狀態
```powershell
.venv\Scripts\python.exe -c "import flask; print(f'Flask {flask.__version__}')"
```

### 查看實時日誌
```powershell
Get-Content app/logs/app.log -Tail 20 -Wait
```

### 更改端口
編輯 `web_app.py` 最後一行：
```python
app.run(host='0.0.0.0', port=5001)  # 改為 5001
```

### 允許外網訪問
編輯 `web_app.py`：
```python
app.run(host='0.0.0.0', port=5000)  # 0.0.0.0 允許所有 IP
```

## ⚠️ 快速故障排查

| 錯誤 | 解決方案 |
|------|---------|
| Port 5000 in use | 改變端口或終止占用進程 |
| Module not found | `.venv\Scripts\python.exe -m pip install flask` |
| 攝像頭無法連接 | 檢查 `config.ini` 的 `camera_id` |
| FPS 低 | 減少解析度或禁用優化 |
| 無法訪問 | 檢查防火牆，確認應用已啟動 |

## 📁 文件結構

```
candy/
├── web_app.py              主應用文件
├── config.ini              配置文件
├── start_web_app.bat       快速啟動
├── WEB_APP_SETUP.md        詳細配置指南
├── WEB_APP_INSTALLATION.md 安裝報告
├── .venv/                  虛擬環境
├── app/
│   ├── logs/app.log        日誌文件
│   └── templates/          Web 模板 (可選)
├── candy_detector/
│   ├── __init__.py
│   ├── config.py           配置管理
│   ├── models.py           數據模型
│   ├── constants.py        常量定義
│   ├── logger.py           日誌系統
│   └── optimization.py     優化模塊
└── run_detector.py         檢測主程序
```

## 🎯 典型工作流程

```
1. 啟動應用
   → 雙擊 start_web_app.bat

2. 打開瀏覽器
   → http://localhost:5000

3. 監視統計信息
   → 檢查 FPS、檢測數、異常數

4. 調整參數 (如需要)
   → 編輯 config.ini
   → 重啟應用

5. 查看歷史記錄
   → 訪問 /api/history

6. 停止應用
   → 按 Ctrl+C
```

## 📞 技術詳情

| 項目 | 值 |
|------|-----|
| Flask 版本 | 2.x+ |
| Python 版本 | 3.11.4 |
| OpenCV 版本 | 4.x+ |
| 數據庫 | SQLite |
| 端口 | 5000 (可修改) |
| 多線程 | 已啟用 |
| CORS | 已啟用 |

## 🔗 有用的鏈接

- Flask 文檔: https://flask.palletsprojects.com/
- OpenCV 文檔: https://docs.opencv.org/
- SQLite 教程: https://www.sqlite.org/docs.html

---

**版本**: 1.0  
**更新**: 2025-11-21  
**狀態**: ✅ 準備就緒

Keep it simple! 🎉
