"""
為舊資料集創建 metadata 文件
"""
from pathlib import Path
import json
from datetime import datetime

def create_metadata_for_old_dataset():
    """為 old dataset 創建 metadata"""
    labels_dir = Path('datasets/annotated/labels/old dataset')
    metadata_dir = Path('datasets/annotated/metadata/old dataset')
    
    if not labels_dir.exists():
        print(f"❌ 找不到標註目錄: {labels_dir}")
        return
    
    print("📝 創建 metadata 文件...")
    
    count = 0
    for label_file in labels_dir.rglob('*.txt'):
        # 創建對應的 metadata
        relative_path = label_file.relative_to(labels_dir)
        metadata_file = metadata_dir / relative_path.parent / f"{label_file.stem}.json"
        
        # 創建目錄
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 計算標註數量
        with open(label_file, 'r') as f:
            annotation_count = len(f.readlines())
        
        # 創建 metadata
        metadata = {
            'source': 'manual',  # 舊資料標記為手動標註
            'timestamp': datetime.now().isoformat(),
            'image_path': f"old dataset/{relative_path.parent}/{label_file.stem}.jpg".replace('\\', '/'),
            'annotation_count': annotation_count,
            'model': 'YOLOv8 (舊訓練資料)',
            'note': '從舊資料集匯入'
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        count += 1
        if count % 100 == 0:
            print(f"  已處理 {count} 個...")
    
    print(f"\n✅ 完成！共創建 {count} 個 metadata 文件")

if __name__ == '__main__':
    create_metadata_for_old_dataset()
