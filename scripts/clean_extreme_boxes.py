"""
清理極端尺寸的標記框
過濾掉過小或過大的標記框，保留正常尺寸（約 350x350）
"""
from pathlib import Path
import shutil

# 配置
PROJECT_ROOT = Path(__file__).resolve().parent
LABELS_DIR = PROJECT_ROOT / 'datasets' / 'annotated' / 'labels'
BACKUP_DIR = PROJECT_ROOT / 'datasets' / 'annotated' / 'labels_backup_before_clean'

# 尺寸閾值（像素）
MIN_SIZE = 50   # 最小尺寸
MAX_SIZE = 800  # 最大尺寸

def clean_extreme_boxes(labels_dir, min_size=50, max_size=800, backup=True):
    """清理極端尺寸的標記框"""
    
    if not labels_dir.exists():
        print(f"❌ 標籤目錄不存在: {labels_dir}")
        return
    
    # 備份
    if backup and not BACKUP_DIR.exists():
        print(f"📦 建立備份: {BACKUP_DIR}")
        shutil.copytree(labels_dir, BACKUP_DIR)
        print(f"✅ 備份完成")
    
    # 統計
    total_files = 0
    modified_files = 0
    total_boxes = 0
    filtered_boxes = 0
    
    # 處理所有標籤檔案
    label_files = list(labels_dir.rglob('*.txt'))
    
    print(f"\n🔍 開始掃描 {len(label_files)} 個標籤檔案...")
    print(f"📏 尺寸範圍: {min_size} - {max_size} 像素\n")
    
    for label_file in label_files:
        if label_file.stat().st_size == 0:
            continue
        
        total_files += 1
        modified = False
        new_lines = []
        file_filtered = 0
        
        # 讀取圖片尺寸（從對應的圖片檔案）
        img_path = None
        images_dir = PROJECT_ROOT / 'datasets' / 'extracted_frames'
        relative_path = label_file.relative_to(labels_dir).parent
        
        for ext in ['.jpg', '.png', '.jpeg']:
            potential_path = images_dir / relative_path / (label_file.stem + ext)
            if potential_path.exists():
                img_path = potential_path
                break
        
        if not img_path:
            continue
        
        # 讀取圖片尺寸
        try:
            from PIL import Image
            with Image.open(img_path) as img:
                img_width, img_height = img.size
        except:
            continue
        
        # 處理標註
        with open(label_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) < 5:
                    new_lines.append(line)
                    continue
                
                total_boxes += 1
                
                # 解析標註
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                w = float(parts[3])
                h = float(parts[4])
                confidence = float(parts[5]) if len(parts) >= 6 else None
                
                # 計算像素尺寸
                box_width_px = w * img_width
                box_height_px = h * img_height
                
                # 檢查尺寸
                if (box_width_px < min_size or box_height_px < min_size or 
                    box_width_px > max_size or box_height_px > max_size):
                    filtered_boxes += 1
                    file_filtered += 1
                    modified = True
                    continue
                
                # 保留標註
                new_lines.append(line)
        
        # 更新檔案
        if modified:
            modified_files += 1
            with open(label_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
                if new_lines:
                    f.write('\n')
            
            print(f"  🔧 {label_file.name}: 過濾 {file_filtered} 個極端標記框")
    
    # 輸出結果
    print("\n" + "="*60)
    print("清理完成！")
    print("="*60)
    print(f"處理檔案: {total_files} 個")
    print(f"修改檔案: {modified_files} 個")
    print(f"總標記框: {total_boxes} 個")
    print(f"過濾數量: {filtered_boxes} 個 ({filtered_boxes/max(total_boxes,1)*100:.1f}%)")
    print(f"保留數量: {total_boxes - filtered_boxes} 個")
    print("="*60)
    
    if backup:
        print(f"\n💾 備份位置: {BACKUP_DIR}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='清理極端尺寸的標記框')
    parser.add_argument('--min-size', type=int, default=50, help='最小尺寸（像素）')
    parser.add_argument('--max-size', type=int, default=800, help='最大尺寸（像素）')
    parser.add_argument('--no-backup', action='store_true', help='不建立備份')
    
    args = parser.parse_args()
    
    print("🧹 極端標記框清理工具")
    print("="*60)
    print(f"標籤目錄: {LABELS_DIR}")
    print(f"尺寸範圍: {args.min_size} - {args.max_size} 像素")
    print(f"備份設定: {'否' if args.no_backup else '是'}")
    print("="*60)
    
    confirm = input("\n確定要繼續嗎？(y/n): ")
    if confirm.lower() != 'y':
        print("已取消")
        exit(0)
    
    clean_extreme_boxes(LABELS_DIR, args.min_size, args.max_size, not args.no_backup)
    
    print("\n✅ 完成！")
