"""
測試之前訓練的 YOLOv8 模型效果
"""
from ultralytics import YOLO
from pathlib import Path
import cv2
import numpy as np

def test_old_model():
    """測試之前的模型"""
    
    # 模型路徑
    old_model_path = Path('之前訓練的 yolov8/runs/detect/train2/weights/best.pt')
    
    if not old_model_path.exists():
        # 嘗試其他可能的路徑
        possible_paths = [
            Path('之前訓練的 yolov8/runs/detect/train/weights/best.pt'),
            Path('之前訓練的 yolov8/train/weights/best.pt'),
        ]
        for path in possible_paths:
            if path.exists():
                old_model_path = path
                break
        else:
            print(f"❌ 找不到模型文件")
            return
    
    print(f"📥 載入模型: {old_model_path}")
    model = YOLO(str(old_model_path))
    
    # 使用目前新標註的驗證集測試
    val_images_dir = Path('datasets/yolo_dataset/images/val')
    
    if not val_images_dir.exists():
        print(f"❌ 找不到驗證集: {val_images_dir}")
        return
    
    # 取前 10 張圖片測試
    test_images = list(val_images_dir.glob('*.jpg'))[:10]
    if not test_images:
        test_images = list(val_images_dir.glob('*.png'))[:10]
    
    if not test_images:
        print("❌ 找不到測試圖片")
        return
    
    print(f"\n🔍 測試 {len(test_images)} 張新標註的圖片...")
    print("=" * 60)
    
    # 預測
    results = model.predict(
        source=[str(img) for img in test_images],
        conf=0.25,              # 信心閾值
        iou=0.45,               # NMS IOU 閾值
        save=True,              # 保存結果
        project='runs/test_old_model',
        name='results',
        show_labels=True,
        show_conf=True,
        verbose=False,
    )
    
    # 統計結果
    total_detections = 0
    normal_count = 0
    defect_count = 0
    
    print(f"\n📊 預測結果詳情:")
    for i, (result, img_path) in enumerate(zip(results, test_images), 1):
        boxes = result.boxes
        detections = len(boxes)
        total_detections += detections
        
        print(f"\n   [{i}] {img_path.name}")
        
        if detections == 0:
            print(f"      ⚪ 未偵測到任何物體")
        else:
            print(f"      偵測到 {detections} 個物體:")
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                label = '正常' if cls == 0 else '瑕疵'
                
                if cls == 0:
                    normal_count += 1
                else:
                    defect_count += 1
                
                # 顯示顏色標記
                icon = '🟢' if cls == 0 else '🔴'
                print(f"         {icon} {label}: {conf:.1%}")
    
    print("\n" + "=" * 60)
    print(f"\n📈 總體統計:")
    print(f"   測試圖片數: {len(test_images)}")
    print(f"   總偵測數: {total_detections}")
    print(f"   🟢 正常: {normal_count} ({normal_count/max(total_detections,1)*100:.1f}%)")
    print(f"   🔴 瑕疵: {defect_count} ({defect_count/max(total_detections,1)*100:.1f}%)")
    print(f"   平均每張: {total_detections/len(test_images):.1f} 個偵測")
    
    print(f"\n✅ 測試完成！")
    print(f"   結果已保存: runs/test_old_model/results/")
    print(f"\n💡 提示:")
    print(f"   - 如果偵測效果不佳，可能是因為:")
    print(f"     1. 舊模型用黑白圖片訓練，新資料是彩色的")
    print(f"     2. 類別對調後與舊模型不一致")
    print(f"     3. 圖片特徵差異太大")
    
    # 檢查第一張圖片是黑白還是彩色
    first_img = cv2.imread(str(test_images[0]))
    if len(first_img.shape) == 2:
        print(f"\n   📷 測試圖片格式: 黑白")
    else:
        # 檢查是否為灰階轉換的彩色
        if np.allclose(first_img[:,:,0], first_img[:,:,1]) and np.allclose(first_img[:,:,1], first_img[:,:,2]):
            print(f"   📷 測試圖片格式: 灰階 (儲存為彩色)")
        else:
            print(f"   📷 測試圖片格式: 彩色")

if __name__ == '__main__':
    test_old_model()
