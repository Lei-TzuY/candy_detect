"""
重新命名檔案 - 移除 recording_ 前綴
適用於影片和圖片檔案
"""
from pathlib import Path
import sys


def rename_files_remove_prefix(directory, prefix='recording_', dry_run=True):
    """
    移除檔案的指定前綴
    
    Args:
        directory: 要處理的目錄
        prefix: 要移除的前綴
        dry_run: True=僅預覽，False=實際執行
    """
    directory = Path(directory)
    
    if not directory.exists():
        print(f"❌ 目錄不存在: {directory}")
        return
    
    # 尋找所有以前綴開頭的檔案
    files_to_rename = []
    for ext in ['*.mp4', '*.avi', '*.jpg', '*.png']:
        files_to_rename.extend(directory.rglob(f"{prefix}*{ext.replace('*', '')}"))
    
    if not files_to_rename:
        print(f"✅ 沒有找到需要重新命名的檔案（前綴: {prefix}）")
        return
    
    print(f"找到 {len(files_to_rename)} 個需要重新命名的檔案")
    print(f"{'=' * 80}")
    
    renamed_count = 0
    error_count = 0
    
    for file_path in sorted(files_to_rename):
        old_name = file_path.name
        
        # 移除前綴
        if old_name.startswith(prefix):
            new_name = old_name[len(prefix):]
            new_path = file_path.parent / new_name
            
            # 檢查目標檔案是否已存在
            if new_path.exists():
                print(f"⚠️  略過（目標已存在）: {old_name} -> {new_name}")
                error_count += 1
                continue
            
            if dry_run:
                print(f"📝 預覽: {old_name} -> {new_name}")
                renamed_count += 1
            else:
                try:
                    file_path.rename(new_path)
                    print(f"✅ 已重新命名: {old_name} -> {new_name}")
                    renamed_count += 1
                except Exception as e:
                    print(f"❌ 錯誤: {old_name} - {e}")
                    error_count += 1
    
    print(f"{'=' * 80}")
    if dry_run:
        print(f"📋 預覽完成")
        print(f"   將重新命名: {renamed_count} 個檔案")
        print(f"   衝突/錯誤: {error_count} 個")
        print(f"\n如果確認無誤，請加上 --execute 參數執行實際重新命名")
    else:
        print(f"✅ 重新命名完成")
        print(f"   成功: {renamed_count} 個檔案")
        print(f"   失敗: {error_count} 個")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='移除檔案名稱的 recording_ 前綴')
    parser.add_argument('--recordings', action='store_true', 
                       help='處理 recordings 目錄中的影片檔案')
    parser.add_argument('--frames', action='store_true', 
                       help='處理 datasets/extracted_frames 目錄中的圖片檔案')
    parser.add_argument('--all', action='store_true', 
                       help='處理兩個目錄的所有檔案')
    parser.add_argument('--execute', action='store_true', 
                       help='實際執行重新命名（預設只預覽）')
    parser.add_argument('--directory', type=str, 
                       help='指定自訂目錄')
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        print("🔍 預覽模式 - 不會實際重新命名檔案")
        print("   如果確認要執行，請加上 --execute 參數")
        print()
    else:
        print("⚠️  執行模式 - 將實際重新命名檔案")
        print()
    
    if args.directory:
        # 處理自訂目錄
        rename_files_remove_prefix(args.directory, dry_run=dry_run)
    elif args.all or (not args.recordings and not args.frames):
        # 預設：處理所有
        print("📹 處理 recordings 目錄...")
        rename_files_remove_prefix('recordings', dry_run=dry_run)
        print()
        print("🖼️  處理 datasets/extracted_frames 目錄...")
        rename_files_remove_prefix('datasets/extracted_frames', dry_run=dry_run)
    else:
        if args.recordings:
            print("📹 處理 recordings 目錄...")
            rename_files_remove_prefix('recordings', dry_run=dry_run)
        if args.frames:
            print("🖼️  處理 datasets/extracted_frames 目錄...")
            rename_files_remove_prefix('datasets/extracted_frames', dry_run=dry_run)


if __name__ == '__main__':
    main()
