"""
训练 YOLOv8l (Large) - 压榨GPU性能
"""
from ultralytics import YOLO
import torch

def train_large_model():
    """使用 YOLOv8l 训练，充分利用GPU"""
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🖥️  使用設備: {device.upper()}")
    
    if device == 'cuda':
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   顯存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    # 使用 YOLOv8l - 大型模型
    print("\n📥 載入 YOLOv8l 預訓練模型...")
    model = YOLO('yolov8l.pt')  # 43.6M 參數
    
    data_yaml = 'datasets/candy_merged_20260116_154158/dataset.yaml'
    
    print("\n🚀 開始訓練 (Large Model)...")
    print(f"   數據集: {data_yaml}")
    print(f"   模型: YOLOv8l (43.6M 參數)")
    print(f"   Epochs: 150")
    print(f"   Batch Size: 32 (充分利用GPU)")
    print(f"   Image Size: 640")
    
    results = model.train(
        data=data_yaml,
        epochs=150,              # 增加训练轮数
        imgsz=640,
        batch=32,                # 增加batch size
        device=device,
        project='runs/train',
        name='candy_large',
        patience=30,             # 增加耐心值
        save=True,
        plots=True,
        
        # 数据增强
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=5,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0,
        copy_paste=0.0,
        
        # 优化器
        optimizer='Adam',
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        
        box=7.5,
        cls=0.5,
        dfl=1.5,
        
        val=True,
        verbose=True,
    )
    
    print("\n✅ 訓練完成！")
    print(f"   最佳模型: runs/train/candy_large/weights/best.pt")
    print(f"   最終模型: runs/train/candy_large/weights/last.pt")
    
    # 验证
    print("\n📊 驗證模型性能...")
    metrics = model.val()
    
    print("\n📈 性能指標:")
    print(f"   mAP@0.5: {metrics.box.map50:.4f}")
    print(f"   mAP@0.5:0.95: {metrics.box.map:.4f}")
    print(f"   Precision: {metrics.box.p:.4f}")
    print(f"   Recall: {metrics.box.r:.4f}")
    
    # 导出模型
    print("\n📦 導出 ONNX 模型...")
    model.export(format='onnx', simplify=True)
    
    print("\n✅ 全部完成！")


if __name__ == '__main__':
    train_large_model()
