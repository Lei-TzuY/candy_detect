"""
測試訓練好的 YOLOv8 模型
"""
from ultralytics import YOLO
from pathlib import Path
import cv2

def test_model():
    """測試模型"""
    
    # 載入訓練好的模型
    model_path = 'runs/train/candy_detector/weights/best.pt'
    
    if not Path(model_path).exists():
        print(f"❌ 找不到模型: {model_path}")
        print("   請先執行 train_yolo.py 訓練模型")
        return
    
    print(f"📥 載入模型: {model_path}")
    model = YOLO(model_path)
    
    # 從驗證集隨機選幾張圖片測試
    val_images_dir = Path('datasets/yolo_dataset/images/val')
    
    if not val_images_dir.exists():
        print(f"❌ 找不到驗證集: {val_images_dir}")
        return
    
    test_images = list(val_images_dir.glob('*.jpg'))[:5]  # 取前5張
    
    if not test_images:
        test_images = list(val_images_dir.glob('*.png'))[:5]
    
    if not test_images:
        print("❌ 找不到測試圖片")
        return
    
    print(f"\n🔍 測試 {len(test_images)} 張圖片...")
    
    # 預測
    results = model.predict(
        source=test_images,
        conf=0.25,              # 信心閾值
        iou=0.45,               # NMS IOU 閾值
        save=True,              # 保存結果
        project='runs/predict', # 保存目錄
        name='test',            # 實驗名稱
        show_labels=True,       # 顯示標籤
        show_conf=True,         # 顯示信心分數
    )
    
    # 顯示結果統計
    print("\n📊 預測結果:")
    for i, result in enumerate(results):
        boxes = result.boxes
        print(f"\n   圖片 {i+1}: {test_images[i].name}")
        print(f"   偵測到 {len(boxes)} 個物體")
        
        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            label = '正常' if cls == 0 else '瑕疵'
            print(f"      - {label}: {conf:.2%}")
    
    print(f"\n✅ 測試完成！")
    print(f"   結果已保存到: runs/predict/test/")

if __name__ == '__main__':
    test_model()
