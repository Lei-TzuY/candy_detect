"""
錄影檔案轉換工具
將無法播放的 mp4 檔案轉換為相容格式
"""

import cv2
from pathlib import Path
import sys

def convert_video(input_file, output_file=None, codec='XVID'):
    """
    轉換視頻檔案為相容格式
    
    Args:
        input_file: 輸入檔案路徑
        output_file: 輸出檔案路徑（可選，預設在原檔案名後加 _converted）
        codec: 使用的編碼器（XVID, MJPG, H264, avc1, mp4v）
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"錯誤: 找不到檔案 {input_file}")
        return False
    
    if output_file is None:
        output_file = input_path.parent / f"{input_path.stem}_converted{input_path.suffix}"
    
    print(f"開始轉換: {input_file}")
    print(f"輸出檔案: {output_file}")
    print(f"使用編碼器: {codec}")
    
    # 開啟輸入檔案
    cap = cv2.VideoCapture(str(input_file))
    
    if not cap.isOpened():
        print("錯誤: 無法開啟輸入檔案")
        return False
    
    # 取得影片資訊
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"影片資訊: {width}x{height} @ {fps}fps, 總幀數: {total_frames}")
    
    # 建立輸出檔案
    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(str(output_file), fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"錯誤: 無法建立輸出檔案（編碼器 {codec} 可能不支援）")
        cap.release()
        return False
    
    # 轉換影片
    frame_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            out.write(frame)
            frame_count += 1
            
            # 顯示進度
            if frame_count % 30 == 0:
                progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
                print(f"進度: {frame_count}/{total_frames} ({progress:.1f}%)", end='\r')
        
        print(f"\n轉換完成! 總共處理 {frame_count} 幀")
        
    except Exception as e:
        print(f"\n錯誤: {e}")
        return False
    finally:
        cap.release()
        out.release()
    
    # 驗證輸出檔案
    test_cap = cv2.VideoCapture(str(output_file))
    if test_cap.isOpened():
        test_frames = int(test_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"驗證: 輸出檔案包含 {test_frames} 幀")
        test_cap.release()
        return True
    else:
        print("警告: 無法驗證輸出檔案")
        return False


def convert_all_in_directory(directory, codec='XVID', pattern='*.mp4'):
    """
    轉換目錄中的所有視頻檔案
    
    Args:
        directory: 目錄路徑
        codec: 使用的編碼器
        pattern: 檔案匹配模式
    """
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"錯誤: 找不到目錄 {directory}")
        return
    
    video_files = list(dir_path.glob(pattern))
    
    if not video_files:
        print(f"在 {directory} 中找不到符合 {pattern} 的檔案")
        return
    
    print(f"找到 {len(video_files)} 個視頻檔案")
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] 處理: {video_file.name}")
        
        # 跳過已轉換的檔案
        if '_converted' in video_file.stem:
            print("跳過（已轉換）")
            continue
        
        output_file = video_file.parent / f"{video_file.stem}_converted{video_file.suffix}"
        
        if output_file.exists():
            print(f"跳過（輸出檔案已存在）: {output_file.name}")
            continue
        
        success = convert_video(video_file, output_file, codec)
        
        if success:
            print(f"✓ 成功轉換: {output_file.name}")
        else:
            print(f"✗ 轉換失敗: {video_file.name}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='轉換視頻檔案為相容格式')
    parser.add_argument('input', help='輸入檔案或目錄路徑')
    parser.add_argument('-o', '--output', help='輸出檔案路徑（僅用於單一檔案）')
    parser.add_argument('-c', '--codec', default='XVID', 
                       choices=['XVID', 'MJPG', 'H264', 'avc1', 'mp4v'],
                       help='視頻編碼器（預設: XVID）')
    parser.add_argument('--all', action='store_true', 
                       help='轉換目錄中的所有 mp4 檔案')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if args.all or input_path.is_dir():
        # 轉換整個目錄
        convert_all_in_directory(args.input, codec=args.codec)
    else:
        # 轉換單一檔案
        convert_video(args.input, args.output, codec=args.codec)
