# GPU 訓練無法選擇 - 診斷與解決方案

## 🔍 問題診斷

訓練裝置無法選擇 GPU 通常有以下幾個原因：

### 1️⃣ **PyTorch 未安裝 CUDA 版本**

**檢查方法：**
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

**如果顯示 `False`：**
- 您安裝的是 CPU 版本的 PyTorch
- 需要重新安裝 CUDA 版本

### 2️⃣ **NVIDIA 驅動未安裝或版本過舊**

**檢查方法：**
```bash
nvidia-smi
```

**如果出現錯誤：**
- NVIDIA 驅動未安裝
- 或者沒有 NVIDIA GPU

### 3️⃣ **CUDA Toolkit 版本不匹配**

PyTorch 需要特定版本的 CUDA。

## 🚀 解決方案

### 方案 1：安裝 CUDA 版本的 PyTorch

1. **卸載現有的 PyTorch：**
```bash
pip uninstall torch torchvision torchaudio
```

2. **安裝 CUDA 版本：**

訪問 https://pytorch.org/get-started/locally/

根據您的系統選擇：
- PyTorch Build: Stable
- Your OS: Windows
- Package: Pip
- Language: Python
- Compute Platform: CUDA 11.8 或 CUDA 12.1（根據您的驅動）

然後執行顯示的命令，例如：
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 方案 2：更新 NVIDIA 驅動

1. 訪問 [NVIDIA 驅動下載頁面](https://www.nvidia.com/Download/index.aspx)
2. 選擇您的顯卡型號
3. 下載並安裝最新驅動
4. 重啟電腦

### 方案 3：檢查 CUDA安裝

```bash
# 檢查 CUDA 版本
nvcc --version

# 如果未安裝，需要從 NVIDIA 網站下載
# https://developer.nvidia.com/cuda-downloads
```

## 📝 驗證安裝

安裝完成後，執行以下命令驗證：

```python
python -c "import torch; print('CUDA可用:', torch.cuda.is_available()); print('GPU數量:', torch.cuda.device_count()); [print(f'GPU {i}: {torch.cuda.get_device_name(i)}') for i in range(torch.cuda.device_count())]"
```

**預期輸出：**
```
CUDA可用: True
GPU數量: 1
GPU 0: NVIDIA GeForce RTX 3060
```

##快速檢查清單

- [ ] 確認有 NVIDIA 顯卡
- [ ] 安裝最新的 NVIDIA 驅動
- [ ] 安裝 CUDA Toolkit
- [ ] 安裝 CUDA 版本的 PyTorch
- [ ] 驗證 `torch.cuda.is_available()` 返回 True

## ⚠️ 常見問題

**Q: 我有 NVIDIA 顯卡，但 `torch.cuda.is_available()` 還是 False？**
- A: 可能是安裝了 CPU 版本的 PyTorch，需要重新安裝 CUDA 版本

**Q: 安裝哪個 CUDA 版本？**
- A: `運行 nvidia-smi` 查看驅動支持的最高 CUDA 版本，然後選擇對應的 PyTorch CUDA 版本

**Q: 我沒有 NVIDIA 顯卡怎麼辦？**
- A: 只能使用 CPU 訓練，速度會較慢，但仍然可以訓練小模型

## 💡 臨時解決方案

如果無法啟用 GPU，可以先使用 CPU 訓練：
- 在訓練設定中選擇 "CPU"
- 減小 batch_size（例如設為 4 或 8）
- 減少訓練輪數進行測試
