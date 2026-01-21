"""
使用 YOLOv8 訓練糖果瑕疵偵測模型
"""
from ultralytics import YOLO
import torch
from pathlib import Path

def train_model():
    """訓練 YOLOv8 模型"""
    
    # 檢查 CUDA 可用性
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🖥️  使用設備: {device.upper()}")
    
    if device == 'cuda':
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   顯存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        print("   ⚠️  未偵測到 GPU，將使用 CPU 訓練（速度較慢）")
    
    # 載入預訓練模型 (使用 YOLOv8n - nano 版本，最輕量)
    print("\n📥 載入 YOLOv8n 預訓練模型...")
    model = YOLO('yolov8n.pt')  # 自動下載預訓練權重
    
    # 訓練參數
    data_yaml = 'datasets/candy_merged_20260116_154158/dataset.yaml'
    
    print("\n🚀 開始訓練...")
    print(f"   數據集配置: {data_yaml}")
    print(f"   模型: YOLOv8n")
    print(f"   Epochs: 100")
    print(f"   Batch Size: 16")
    print(f"   Image Size: 640")
    
    # 開始訓練
    results = model.train(
        data=data_yaml,           # 數據集配置文件
        epochs=100,               # 訓練輪數
        imgsz=640,                # 圖片大小
        batch=16,                 # 批次大小 (如果顯存不足可以降到 8)
        device=device,            # 使用的設備
        project='runs/train',     # 訓練結果保存目錄
        name='candy_detector',    # 實驗名稱
        patience=20,              # 早停耐心值 (20 epochs 沒改善就停止)
        save=True,                # 保存檢查點
        plots=True,               # 生成訓練圖表
        
        # 數據增強
        hsv_h=0.015,              # 色調增強
        hsv_s=0.7,                # 飽和度增強
        hsv_v=0.4,                # 亮度增強
        degrees=5,                # 旋轉角度
        translate=0.1,            # 平移
        scale=0.5,                # 縮放
        fliplr=0.5,               # 左右翻轉
        mosaic=1.0,               # Mosaic 數據增強
        
        # 優化器
        optimizer='Adam',         # 優化器
        lr0=0.001,                # 初始學習率
        lrf=0.01,                 # 最終學習率 (lr0 * lrf)
        momentum=0.937,           # SGD momentum
        weight_decay=0.0005,      # 權重衰減
        
        # 其他
        workers=8,                # 數據載入線程數
        seed=42,                  # 隨機種子
        verbose=True,             # 詳細輸出
    )
    
    print("\n✅ 訓練完成！")
    print(f"   最佳模型: runs/train/candy_detector/weights/best.pt")
    print(f"   最後模型: runs/train/candy_detector/weights/last.pt")
    print(f"   訓練結果: runs/train/candy_detector/")
    
    # 驗證模型
    print("\n📊 驗證模型性能...")
    metrics = model.val()
    
    print(f"\n📈 驗證結果:")
    print(f"   mAP50: {metrics.box.map50:.4f}")
    print(f"   mAP50-95: {metrics.box.map:.4f}")
    print(f"   Precision: {metrics.box.mp:.4f}")
    print(f"   Recall: {metrics.box.mr:.4f}")
    
    # 導出模型
    print("\n💾 導出模型...")
    
    # 導出為 ONNX 格式 (用於 OpenCV DNN)
    model.export(format='onnx', simplify=True)
    print("   ✅ ONNX 模型已導出")
    
    # 建議下一步
    print("\n📝 下一步:")
    print("   1. 查看訓練圖表: runs/train/candy_detector/results.png")
    print("   2. 測試模型: python test_yolo_model.py")
    print("   3. 使用最佳模型: runs/train/candy_detector/weights/best.pt")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', default='auto', choices=['auto', 'cpu', 'cuda', '0'], 
                        help='训练设备: auto(自动检测), cpu, cuda, 0(GPU 0)')
    args = parser.parse_args()
    
    # 根据参数设置设备
    import torch
    if args.device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    else:
        device = args.device
    
    # 覆盖train_model中的设备检测
    import sys
    original_train = train_model
    def train_with_device():
        # 修改全局变量来强制使用指定设备
        import ultralytics
        return original_train()
    
    train_model()
