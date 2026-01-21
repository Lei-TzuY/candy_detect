"""
YOLOv8s 極限性能訓練腳本
針對 RTX 5070 Ti 優化，最大化 GPU 利用率
"""
from ultralytics import YOLO
import torch
from pathlib import Path
import gc

def get_optimal_batch_size():
    """根據 GPU 記憶體自動計算最佳 batch size"""
    if not torch.cuda.is_available():
        return 16
    
    # RTX 5070 Ti Laptop 有 12GB VRAM
    total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    
    # YOLOv8s + 640px 圖片大約需要：
    # batch=24: ~5.5GB (當前使用)
    # batch=40: ~9GB
    # batch=48: ~11GB (極限)
    # batch=56: ~12.5GB (會爆)
    
    if total_vram_gb >= 15:
        return 56  # 桌面版極限
    elif total_vram_gb >= 11:
        return 48  # 筆電版極限 (充分利用 12GB)
    elif total_vram_gb >= 8:
        return 32
    else:
        return 24

def train_yolov8s_max():
    """使用 YOLOv8s 進行極限性能訓練"""
    
    # 禁用線上檢查和修復終端編碼
    import os
    os.environ['YOLO_OFFLINE'] = '1'
    os.environ['TERM'] = 'dumb'  # 使用 ASCII 進度條避免亂碼
    
    # 清理 GPU 記憶體
    gc.collect()
    torch.cuda.empty_cache()
    
    # 檢查 CUDA
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    print("=" * 70)
    print("🚀 YOLOv8s 極限性能訓練")
    print("=" * 70)
    print(f"\n🖥️  硬體資訊:")
    
    if device == 'cuda':
        gpu_name = torch.cuda.get_device_name(0)
        total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"   ✅ GPU: {gpu_name}")
        print(f"   ✅ VRAM: {total_vram:.1f} GB")
        print(f"   ✅ CUDA 版本: {torch.version.cuda}")
        print(f"   ✅ PyTorch 版本: {torch.__version__}")
    else:
        print("   ❌ 未偵測到 GPU - 無法進行極限訓練")
        print("   建議: 請確保已安裝 CUDA 和 GPU 版本的 PyTorch")
        return
    
    # 自動計算最佳 batch size
    optimal_batch = get_optimal_batch_size()
    
    # 載入 YOLOv8s 模型
    print(f"\n📥 載入模型:")
    print(f"   模型: YOLOv8s (Small)")
    print(f"   參數量: ~11.2M (比 YOLOv8n 的 3.2M 大 3.5 倍)")
    print(f"   精度提升: 通常比 nano 版本高 3-5%")
    
    model = YOLO('yolov8s.pt')
    
    # 訓練配置
    data_yaml = 'datasets/candy_merged_20260116_154158/dataset.yaml'
    
    print(f"\n⚡ 極限性能配置:")
    print(f"   📊 Batch Size: {optimal_batch} (自動優化)")
    print(f"   🖼️  Image Size: 640px")
    print(f"   🔄 Workers: 0 (主進程載入，避免多進程問題)")
    print(f"   🎯 Epochs: 150 (更多訓練輪數)")
    print(f"   💾 Cache: True (圖片預載入記憶體)")
    print(f"   🔥 AMP: True (混合精度訓練)")
    print(f"   📈 Patience: 30 (更長的早停耐心)")
    
    print("\n" + "=" * 70)
    print("🚀 開始訓練 - 全力壓榨 GPU！")
    print("=" * 70 + "\n")
    
    # 開始訓練
    results = model.train(
        # === 基本配置 ===
        data=data_yaml,
        epochs=150,                    # 更多訓練輪數
        imgsz=640,                     # 標準輸入大小
        batch=optimal_batch,           # 極限 batch size
        device=0,                      # 使用 GPU 0
        
        # === 保存配置 ===
        project='runs/train',
        name='candy_detector_yolov8s_max',
        exist_ok=True,
        save=True,
        save_period=10,                # 每 10 epochs 保存一次
        plots=True,
        
        # === 性能優化 ===
        workers=0,                     # 使用主進程載入數據 (避免 Python 3.13 多進程問題)
        cache=True,                    # 將圖片預載入記憶體 (需要足夠 RAM)
        amp=True,                      # 混合精度訓練 (加速 + 節省顯存)
        close_mosaic=10,               # 最後 10 epochs 關閉 mosaic
        
        # === 早停配置 ===
        patience=30,                   # 30 epochs 沒改善才停止
        
        # === 數據增強 (適中，不要過度) ===
        hsv_h=0.015,                   # 色調
        hsv_s=0.7,                     # 飽和度
        hsv_v=0.4,                     # 亮度
        degrees=10,                    # 旋轉 ±10°
        translate=0.1,                 # 平移 10%
        scale=0.5,                     # 縮放 ±50%
        shear=0.0,                     # 不使用剪切
        perspective=0.0,               # 不使用透視變換
        flipud=0.0,                    # 不上下翻轉
        fliplr=0.5,                    # 50% 左右翻轉
        mosaic=1.0,                    # Mosaic 增強
        mixup=0.1,                     # 10% MixUp 增強
        copy_paste=0.0,                # 不使用 copy-paste
        
        # === 優化器配置 ===
        optimizer='AdamW',             # AdamW 優化器
        lr0=0.001,                     # 初始學習率
        lrf=0.01,                      # 最終學習率因子
        momentum=0.937,                # SGD momentum
        weight_decay=0.0005,           # 權重衰減
        warmup_epochs=3,               # 預熱 epochs
        warmup_momentum=0.8,           # 預熱 momentum
        warmup_bias_lr=0.1,            # 預熱偏置學習率
        
        # === 損失權重 ===
        box=7.5,                       # 邊界框損失權重
        cls=0.5,                       # 分類損失權重
        dfl=1.5,                       # DFL 損失權重
        
        # === 其他 ===
        seed=42,                       # 隨機種子
        deterministic=False,           # 不使用確定性模式 (會降低性能)
        single_cls=False,              # 多類別檢測
        rect=False,                    # 不使用矩形訓練 (會降低增強效果)
        cos_lr=True,                   # 使用餘弦學習率調度
        label_smoothing=0.0,           # 不使用標籤平滑
        nbs=64,                        # 名義 batch size
        overlap_mask=True,             # 允許遮罩重疊
        mask_ratio=4,                  # 遮罩下採樣比率
        dropout=0.0,                   # 不使用 dropout
        val=True,                      # 訓練時進行驗證
        verbose=True,                  # 詳細輸出
    )
    
    print("\n" + "=" * 70)
    print("✅ 訓練完成！")
    print("=" * 70)
    
    # 顯示結果路徑
    save_dir = Path('runs/train/candy_detector_yolov8s_max')
    print(f"\n📁 訓練結果:")
    print(f"   最佳模型: {save_dir}/weights/best.pt")
    print(f"   最後模型: {save_dir}/weights/last.pt")
    print(f"   訓練曲線: {save_dir}/results.png")
    print(f"   混淆矩陣: {save_dir}/confusion_matrix.png")
    
    # 載入最佳模型並驗證
    print(f"\n📊 使用最佳模型進行驗證...")
    best_model = YOLO(save_dir / 'weights' / 'best.pt')
    metrics = best_model.val(data=data_yaml)
    
    print(f"\n📈 最終驗證結果:")
    print(f"   {'=' * 50}")
    print(f"   mAP@0.5      : {metrics.box.map50:.4f} ({metrics.box.map50*100:.2f}%)")
    print(f"   mAP@0.5:0.95 : {metrics.box.map:.4f} ({metrics.box.map*100:.2f}%)")
    print(f"   Precision    : {metrics.box.mp:.4f} ({metrics.box.mp*100:.2f}%)")
    print(f"   Recall       : {metrics.box.mr:.4f} ({metrics.box.mr*100:.2f}%)")
    print(f"   {'=' * 50}")
    
    # 性能估算
    print(f"\n⚡ 性能估算 (RTX 5070 Ti):")
    print(f"   推理速度: ~150 FPS (640x640)")
    print(f"   模型大小: ~22 MB")
    print(f"   精度提升: 比 YOLOv8n 高 3-5%")
    
    # 導出 ONNX
    print(f"\n💾 導出 ONNX 格式...")
    try:
        best_model.export(format='onnx', simplify=True, dynamic=False)
        print(f"   ✅ ONNX 模型已導出: {save_dir}/weights/best.onnx")
    except Exception as e:
        print(f"   ⚠️  ONNX 導出失敗: {e}")
    
    # 下一步建議
    print(f"\n📝 下一步操作:")
    print(f"   1. 查看訓練報告:")
    print(f"      python generate_training_report.py --train-dir {save_dir}")
    print(f"   ")
    print(f"   2. 視覺化驗證結果:")
    print(f"      python visualize_validation_results.py --model {save_dir}/weights/best.pt")
    print(f"   ")
    print(f"   3. 更新 config.ini 使用新模型:")
    print(f"      weights = {save_dir}/weights/best.pt")
    print(f"   ")
    print(f"   4. 重啟 Web 應用測試:")
    print(f"      python src/web_app.py")
    
    print("\n🎉 訓練完成！GPU 已被充分壓榨！")
    
    return results

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='YOLOv8s 極限性能訓練')
    parser.add_argument('--batch', type=int, default=None, 
                        help='手動指定 batch size (留空則自動計算)')
    parser.add_argument('--epochs', type=int, default=150,
                        help='訓練輪數 (預設: 150)')
    parser.add_argument('--imgsz', type=int, default=640,
                        help='圖片大小 (預設: 640)')
    
    args = parser.parse_args()
    
    # 如果手動指定 batch size，覆蓋自動計算
    if args.batch is not None:
        original_func = get_optimal_batch_size
        get_optimal_batch_size = lambda: args.batch
        print(f"\n⚠️  手動指定 batch size: {args.batch}")
    
    train_yolov8s_max()
