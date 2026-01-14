"""
"""                        更新 organize_frames.py 以支援 "All pictures" 資料夾
將現有圖片整理到子資料夾，同時複製到 All pictures
"""
from pathlib import Path
import re
import shutil
import send2trash


def organize_frames_with_all_pictures(frames_dir='datasets/extracted_frames', dry_run=True):
    """
    將圖片按照來源影片組織到子資料夾，同時複製到 All pictures
    
    檔名格式例：recording_0_20251203_155742_frame_000000.jpg
    將被移到：
    - datasets/extracted_frames/0_20251203_155742/frame_0000.jpg
    - datasets/extracted_frames/All pictures/0_20251203_155742_frame_0000.jpg
    """
    frames_dir = Path(frames_dir)
    
    if not frames_dir.exists():
        print(f"❌ 目錄不存在: {frames_dir}")
        return
    
    # 找出所有圖片檔案（只在根目錄，不包含子資料夾）
    image_files = []
    for ext in ['*.jpg', '*.png']:
        image_files.extend(frames_dir.glob(ext))
    
    # 過濾掉已經在子資料夾中的檔案
    image_files = [f for f in image_files if f.parent == frames_dir]
    
    if not image_files:
        print(f"✅ 沒有需要整理的圖片（所有圖片已經在子資料夾中）")
        return
    
    print(f"找到 {len(image_files)} 張圖片需要整理")
    print(f"{'=' * 80}")
    
    # 建立 All pictures 資料夾
    all_pictures_dir = frames_dir / "All pictures"
    if not dry_run:
        all_pictures_dir.mkdir(exist_ok=True)
    
    # 按影片來源分組
    video_groups = {}
    
    for img_file in image_files:
        filename = img_file.name
        
        # 解析檔名，提取影片資訊
        # 格式：recording_0_20251203_155742_frame_000000.jpg
        # 或：0_20251203_155742_frame_000000.jpg (新格式)
        match = re.match(r'^(?:recording_)?(\d+_\d+_\d+)_frame_(\d+)\.(jpg|png)$', filename)
        
        if match:
            video_id = match.group(1)  # 例如：0_20251203_155742
            frame_num = match.group(2)  # 例如：000000
            ext = match.group(3)
            
            if video_id not in video_groups:
                video_groups[video_id] = []
            
            # 新的檔名
            simple_filename = f"frame_{frame_num}.{ext}"  # 子資料夾中的簡潔檔名
            all_pictures_filename = f"{video_id}_frame_{frame_num}.{ext}"  # All pictures 中的完整檔名
            
            video_groups[video_id].append((img_file, simple_filename, all_pictures_filename))
        else:
            print(f"⚠️  無法解析檔名格式: {filename}")
    
    print(f"\n找到 {len(video_groups)} 個影片來源")
    print(f"{'=' * 80}\n")
    
    # 整理檔案
    total_moved = 0
    total_copied = 0
    total_errors = 0
    
    for video_id, files in sorted(video_groups.items()):
        # 建立子資料夾
        subfolder = frames_dir / video_id
        
        print(f"📁 {video_id}/ ({len(files)} 張圖片)")
        
        if not dry_run:
            subfolder.mkdir(exist_ok=True)
        
        for old_path, simple_filename, all_pictures_filename in files:
            subfolder_path = subfolder / simple_filename
            all_pictures_path = all_pictures_dir / all_pictures_filename
            
            if dry_run:
                print(f"   📝 {old_path.name}")
                print(f"      -> {video_id}/{simple_filename}")
                print(f"      -> All pictures/{all_pictures_filename}")
            else:
                try:
                    # 1. 複製到 All pictures
                    if not all_pictures_path.exists():
                        shutil.copy2(str(old_path), str(all_pictures_path))
                        total_copied += 1
                    
                    # 2. 移動到子資料夾
                    if not subfolder_path.exists():
                        shutil.move(str(old_path), str(subfolder_path))
                        total_moved += 1
                    else:
                        # 如果子資料夾中已存在，移到垃圾桶而非永久刪除
                        send2trash.send2trash(str(old_path))
                        total_moved += 1
                    
                    if (total_moved + total_copied) % 100 == 0:
                        print(f"   ✓ 已處理 {total_moved} 張...")
                        
                except Exception as e:
                    print(f"   ❌ 錯誤: {simple_filename} - {e}")
                    total_errors += 1
        
        if not dry_run and len(files) > 0:
            print(f"   ✅ 完成 {video_id}")
        print()
    
    print(f"{'=' * 80}")
    if dry_run:
        print(f"📋 預覽完成")
        print(f"   將移動到子資料夾: {sum(len(files) for files in video_groups.values())} 張")
        print(f"   將複製到 All pictures: {sum(len(files) for files in video_groups.values())} 張")
        print(f"   共 {len(video_groups)} 個子資料夾")
        print(f"\n如果確認無誤，請加上 --execute 參數執行實際整理")
    else:
        print(f"✅ 整理完成")
        print(f"   移動到子資料夾: {total_moved} 張")
        print(f"   複製到 All pictures: {total_copied} 張")
        print(f"   錯誤/略過: {total_errors} 張")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='將圖片按來源影片整理到子資料夾並複製到 All pictures')
    parser.add_argument('--directory', type=str, default='datasets/extracted_frames',
                       help='圖片目錄（預設：datasets/extracted_frames）')
    parser.add_argument('--execute', action='store_true',
                       help='實際執行整理（預設只預覽）')
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        print("🔍 預覽模式 - 不會實際移動檔案")
        print("   如果確認要執行，請加上 --execute 參數")
        print()
    else:
        print("⚠️  執行模式 - 將實際移動檔案到子資料夾並複製到 All pictures")
        print()
    
    organize_frames_with_all_pictures(args.directory, dry_run=dry_run)


if __name__ == '__main__':
    main()
