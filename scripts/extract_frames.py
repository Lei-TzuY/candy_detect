"""
從錄影檔中提取影像幀，用於訓練資料準備
"""
import cv2
import os
from pathlib import Path
import argparse


def extract_frames(video_path, output_dir, interval=30, max_frames=None):
    """
    從影片提取影像幀
    
    Args:
        video_path: 影片檔案路徑
        output_dir: 輸出目錄（每個影片會建立獨立子資料夾）
        interval: 每隔多少幀提取一次（預設30，即每秒1幀 @30fps）
        max_frames: 最多提取多少幀（None表示不限制）
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    
    if not video_path.exists():
        print(f"❌ 找不到影片檔案: {video_path}")
        return 0
    
    
    # 使用影片檔名作為資料夾名稱（不需要移除前綴，因為新影片已經沒有前綴了）
    video_name = video_path.stem
    
    # 為每個影片建立獨立的子資料夾
    video_output_dir = output_dir / video_name
    video_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 同時建立 "All pictures" 資料夾用於存放所有圖片
    all_pictures_dir = output_dir / "All pictures"
    all_pictures_dir.mkdir(parents=True, exist_ok=True)
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ 無法開啟影片: {video_path}")
        return 0
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"📹 影片資訊:")
    print(f"   檔案: {video_path.name}")
    print(f"   輸出資料夾: {video_output_dir.name}")
    print(f"   總幀數: {total_frames}")
    print(f"   FPS: {fps:.1f}")
    print(f"   時長: {total_frames/fps:.1f} 秒")
    print(f"   提取間隔: 每 {interval} 幀")
    print(f"   預計提取: {min(total_frames//interval, max_frames or float('inf'))} 張")
    print()
    
    frame_count = 0
    extracted_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % interval == 0:
            if max_frames and extracted_count >= max_frames:
                break
            
            # 儲存到影片專屬資料夾（使用簡潔的檔名）
            simple_filename = f"frame_{extracted_count:04d}.jpg"
            video_output_path = video_output_dir / simple_filename
            cv2.imwrite(str(video_output_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # 同時儲存到 "All pictures" 資料夾（包含影片名稱以避免衝突）
            all_pictures_filename = f"{video_name}_frame_{extracted_count:04d}.jpg"
            all_pictures_path = all_pictures_dir / all_pictures_filename
            cv2.imwrite(str(all_pictures_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            extracted_count += 1
            if extracted_count % 10 == 0:
                print(f"✓ 已提取 {extracted_count} 張 ({frame_count}/{total_frames} 幀)")
        
        frame_count += 1
    
    cap.release()
    
    print(f"\n✅ 完成！共提取 {extracted_count} 張影像")
    print(f"   📁 影片專屬: {video_output_dir}")
    print(f"   📁 全部圖片: {all_pictures_dir}")
    return extracted_count


def batch_extract(recordings_dir, output_dir, interval=30, max_frames_per_video=100):
    """
    批次處理 recordings 目錄中的所有影片
    
    Args:
        recordings_dir: 錄影檔目錄
        output_dir: 輸出目錄
        interval: 提取間隔
        max_frames_per_video: 每個影片最多提取多少幀
    """
    recordings_dir = Path(recordings_dir)
    output_dir = Path(output_dir)
    
    video_files = list(recordings_dir.glob("*.mp4")) + list(recordings_dir.glob("*.avi"))
    
    if not video_files:
        print(f"❌ 在 {recordings_dir} 中找不到影片檔案")
        return
    
    print(f"📁 找到 {len(video_files)} 個影片檔案")
    print(f"📂 輸出目錄: {output_dir}")
    print("=" * 60)
    print()
    
    total_extracted = 0
    for i, video_file in enumerate(video_files, 1):
        print(f"[{i}/{len(video_files)}] 處理: {video_file.name}")
        count = extract_frames(video_file, output_dir, interval, max_frames_per_video)
        total_extracted += count
        print()
    
    print("=" * 60)
    print(f"🎉 全部完成！共提取 {total_extracted} 張影像")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='從錄影檔提取影像幀')
    parser.add_argument('--video', type=str, help='單個影片檔案路徑')
    parser.add_argument('--batch', action='store_true', help='批次處理 recordings 目錄')
    parser.add_argument('--output', type=str, default='datasets/extracted_frames', 
                        help='輸出目錄（預設: datasets/extracted_frames）')
    parser.add_argument('--interval', type=int, default=30, 
                        help='提取間隔（幀數，預設: 30）')
    parser.add_argument('--max-frames', type=int, default=100, 
                        help='每個影片最多提取多少幀（預設: 100）')
    
    args = parser.parse_args()
    
    if args.batch:
        # 批次處理
        batch_extract('recordings', args.output, args.interval, args.max_frames)
    elif args.video:
        # 處理單個影片
        extract_frames(args.video, args.output, args.interval, args.max_frames)
    else:
        # 預設：批次處理
        print("未指定參數，使用批次模式處理 recordings 目錄")
        print()
        batch_extract('recordings', args.output, args.interval, args.max_frames)
