"""
準備 YOLOv8 訓練數據集
- 收集所有已標註的圖片和標籤
- 分割成 train (80%) 和 val (20%)
- 建立 YOLO 格式的目錄結構
"""
import os
import shutil
from pathlib import Path
import random

def prepare_yolo_dataset():
    """準備 YOLO 訓練數據集"""
    
    # 路徑設定
    annotated_images_dir = Path('datasets/extracted_frames')
    annotated_labels_dir = Path('datasets/annotated/labels')
    output_dir = Path('datasets/yolo_dataset')
    
    # 創建輸出目錄
    train_images_dir = output_dir / 'images' / 'train'
    train_labels_dir = output_dir / 'labels' / 'train'
    val_images_dir = output_dir / 'images' / 'val'
    val_labels_dir = output_dir / 'labels' / 'val'
    
    for dir_path in [train_images_dir, train_labels_dir, val_images_dir, val_labels_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    print("📁 掃描已標註的文件...")
    
    # 收集所有有標註的圖片
    labeled_files = []
    for label_file in annotated_labels_dir.rglob('*.txt'):
        # 檢查標註文件是否有內容
        if label_file.stat().st_size > 0:
            # 找對應的圖片
            relative_path = label_file.relative_to(annotated_labels_dir)
            
            # 嘗試不同的圖片副檔名
            for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                image_file = annotated_images_dir / relative_path.parent / f"{label_file.stem}{ext}"
                if image_file.exists():
                    labeled_files.append({
                        'image': image_file,
                        'label': label_file,
                        'name': f"{relative_path.parent}_{label_file.stem}".replace('\\', '_').replace('/', '_')
                    })
                    break
    
    if not labeled_files:
        print("❌ 找不到任何已標註的圖片！")
        return
    
    print(f"✅ 找到 {len(labeled_files)} 個已標註的文件")
    
    # 隨機打亂
    random.seed(42)
    random.shuffle(labeled_files)
    
    # 分割數據集 (80% train, 20% val)
    split_idx = int(len(labeled_files) * 0.8)
    train_files = labeled_files[:split_idx]
    val_files = labeled_files[split_idx:]
    
    print(f"📊 訓練集: {len(train_files)} 張")
    print(f"📊 驗證集: {len(val_files)} 張")
    
    # 複製文件
    print("\n📋 複製訓練集...")
    for i, file_info in enumerate(train_files, 1):
        # 使用唯一的檔名避免衝突
        new_name = file_info['name']
        image_ext = file_info['image'].suffix
        
        shutil.copy2(file_info['image'], train_images_dir / f"{new_name}{image_ext}")
        shutil.copy2(file_info['label'], train_labels_dir / f"{new_name}.txt")
        
        if i % 100 == 0:
            print(f"  已複製 {i}/{len(train_files)}...")
    
    print("📋 複製驗證集...")
    for i, file_info in enumerate(val_files, 1):
        new_name = file_info['name']
        image_ext = file_info['image'].suffix
        
        shutil.copy2(file_info['image'], val_images_dir / f"{new_name}{image_ext}")
        shutil.copy2(file_info['label'], val_labels_dir / f"{new_name}.txt")
        
        if i % 100 == 0:
            print(f"  已複製 {i}/{len(val_files)}...")
    
    print(f"\n✅ 數據集準備完成！")
    print(f"   訓練集: {train_images_dir}")
    print(f"   驗證集: {val_images_dir}")
    
    # 統計類別分佈
    print("\n📊 統計類別分佈...")
    class_counts = {0: 0, 1: 0}  # 0: 正常, 1: 瑕疵
    
    for label_file in train_labels_dir.glob('*.txt'):
        with open(label_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    class_counts[class_id] = class_counts.get(class_id, 0) + 1
    
    total = sum(class_counts.values())
    print(f"   訓練集標註總數: {total}")
    print(f"   - 正常: {class_counts.get(0, 0)} ({class_counts.get(0, 0)/max(total,1)*100:.1f}%)")
    print(f"   - 瑕疵: {class_counts.get(1, 0)} ({class_counts.get(1, 0)/max(total,1)*100:.1f}%)")

if __name__ == '__main__':
    prepare_yolo_dataset()
