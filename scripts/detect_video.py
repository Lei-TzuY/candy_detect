"""
對錄製的影片檔案進行 YOLOv4 偵測
可以批次處理多個影片，輸出帶標註的影片
"""
import cv2
import os
import sys
import configparser
from pathlib import Path
import tempfile
import shutil
import time


# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_yolo_model(config_file='config.ini'):
    """載入 YOLO 模型"""
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    
    weights_path = os.path.normpath(os.path.join(PROJECT_ROOT, config.get('Paths', 'weights')))
    cfg_path = os.path.normpath(os.path.join(PROJECT_ROOT, config.get('Paths', 'cfg')))
    classes_path = os.path.normpath(os.path.join(PROJECT_ROOT, config.get('Paths', 'classes')))
    
    if not all(os.path.exists(p) for p in [weights_path, cfg_path, classes_path]):
        raise FileNotFoundError("找不到模型檔案，請檢查 config.ini")
    
    with open(classes_path, 'r', encoding='utf-8') as f:
        class_names = [cname.strip() for cname in f.readlines()]
    
    # 處理中文路徑問題
    temp_dir = os.path.join(tempfile.gettempdir(), 'candy_yolo_models')
    os.makedirs(temp_dir, exist_ok=True)
    temp_cfg = os.path.join(temp_dir, 'model.cfg')
    temp_weights = os.path.join(temp_dir, 'model.weights')
    
    if not os.path.exists(temp_cfg) or os.path.getsize(temp_cfg) != os.path.getsize(cfg_path):
        shutil.copy2(cfg_path, temp_cfg)
    
    if not os.path.exists(temp_weights) or os.path.getsize(temp_weights) != os.path.getsize(weights_path):
        shutil.copy2(weights_path, temp_weights)
    
    net = cv2.dnn.readNet(temp_weights, temp_cfg)
    model = cv2.dnn_DetectionModel(net)
    
    input_size = config.getint('Detection', 'input_size', fallback=416)
    confidence = config.getfloat('Detection', 'confidence_threshold', fallback=0.4)
    nms = config.getfloat('Detection', 'nms_threshold', fallback=0.4)
    
    model.setInputParams(size=(input_size, input_size), scale=1/255, swapRB=False)
    
    print(f"✓ 模型載入成功")
    print(f"  類別: {class_names}")
    print(f"  輸入大小: {input_size}x{input_size}")
    print(f"  信心閾值: {confidence}")
    print(f"  NMS 閾值: {nms}")
    
    return model, class_names, confidence, nms


def detect_video(video_path, output_path, model, class_names, 
                 confidence_threshold=0.4, nms_threshold=0.4,
                 show_preview=False, skip_frames=0):
    """
    對影片進行偵測並輸出結果
    
    Args:
        video_path: 輸入影片路徑
        output_path: 輸出影片路徑
        model: YOLO 模型
        class_names: 類別名稱
        confidence_threshold: 信心閾值
        nms_threshold: NMS 閾值
        show_preview: 是否顯示即時預覽
        skip_frames: 跳過幀數（加快處理，0=不跳過）
    """
    video_path = Path(video_path)
    output_path = Path(output_path)
    
    if not video_path.exists():
        print(f"❌ 找不到影片: {video_path}")
        return False
    
    # 開啟影片
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ 無法開啟影片: {video_path}")
        return False
    
    # 取得影片資訊
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"\n📹 影片資訊:")
    print(f"   檔案: {video_path.name}")
    print(f"   解析度: {width}x{height}")
    print(f"   FPS: {fps:.1f}")
    print(f"   總幀數: {total_frames}")
    print(f"   時長: {duration:.1f} 秒")
    if skip_frames > 0:
        print(f"   跳幀設定: 每 {skip_frames+1} 幀處理 1 幀")
    
    # 建立輸出影片
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"❌ 無法建立輸出影片: {output_path}")
        cap.release()
        return False
    
    print(f"\n🎬 開始處理...")
    print(f"   輸出: {output_path}")
    print("=" * 60)
    
    frame_count = 0
    processed_count = 0
    detection_count = 0
    normal_count = 0
    abnormal_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # 跳幀處理
            if skip_frames > 0 and frame_count % (skip_frames + 1) != 0:
                out.write(frame)  # 寫入原始幀
                continue
            
            # 轉灰階進行偵測
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 偵測
            classes, scores, boxes = model.detect(gray, confidence_threshold, nms_threshold)
            
            # 繪製偵測框
            output_frame = frame.copy()
            if len(classes) > 0:
                detection_count += len(classes)
                for class_id, score, box in zip(classes.flatten(), scores.flatten(), boxes):
                    x, y, w, h = box
                    class_name = class_names[class_id] if class_id < len(class_names) else f"Class {class_id}"
                    
                    # 根據類別選擇顏色
                    if class_id == 0:  # normal
                        color = (0, 255, 0)  # 綠色
                        normal_count += 1
                    else:  # abnormal
                        color = (0, 0, 255)  # 紅色
                        abnormal_count += 1
                    
                    # 繪製框和標籤
                    cv2.rectangle(output_frame, (x, y), (x+w, y+h), color, 2)
                    
                    # 標籤背景
                    label = f"{class_name}: {score:.2f}"
                    (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(output_frame, (x, y-label_h-10), (x+label_w, y), color, -1)
                    cv2.putText(output_frame, label, (x, y-5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # 添加幀資訊
            info_text = f"Frame: {frame_count}/{total_frames} | Detections: {len(classes)}"
            cv2.putText(output_frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # 寫入輸出影片
            out.write(output_frame)
            processed_count += 1
            
            # 顯示預覽
            if show_preview:
                cv2.imshow('Detection Preview (press Q to quit)', output_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n⏸️ 使用者中斷處理")
                    break
            
            # 進度顯示
            if frame_count % 100 == 0 or frame_count == total_frames:
                elapsed = time.time() - start_time
                fps_processing = frame_count / elapsed if elapsed > 0 else 0
                progress = (frame_count / total_frames) * 100
                eta = (total_frames - frame_count) / fps_processing if fps_processing > 0 else 0
                print(f"進度: {progress:.1f}% ({frame_count}/{total_frames}) | "
                      f"處理速度: {fps_processing:.1f} FPS | "
                      f"預計剩餘: {eta:.0f}秒")
    
    except KeyboardInterrupt:
        print("\n⏸️ 處理被中斷")
    
    finally:
        cap.release()
        out.release()
        if show_preview:
            cv2.destroyAllWindows()
    
    elapsed_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print(f"✅ 處理完成！")
    print(f"   處理幀數: {processed_count}/{frame_count}")
    print(f"   總偵測數: {detection_count}")
    print(f"   正常: {normal_count} | 瑕疵: {abnormal_count}")
    print(f"   處理時間: {elapsed_time:.1f} 秒")
    print(f"   平均速度: {frame_count/elapsed_time:.1f} FPS")
    print(f"\n📁 輸出檔案: {output_path}")
    print(f"   大小: {output_path.stat().st_size / (1024*1024):.1f} MB")
    
    return True


def batch_detect_videos(input_dir, output_dir, model, class_names,
                        confidence_threshold=0.4, nms_threshold=0.4,
                        skip_frames=0):
    """批次處理多個影片"""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 找到所有影片檔案
    video_files = list(input_dir.glob("*.mp4")) + list(input_dir.glob("*.avi"))
    
    if not video_files:
        print(f"❌ 在 {input_dir} 中找不到影片檔案")
        return
    
    print(f"\n📁 找到 {len(video_files)} 個影片檔案")
    print("=" * 60)
    
    success_count = 0
    for i, video_file in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] 處理: {video_file.name}")
        output_file = output_dir / f"{video_file.stem}_detected{video_file.suffix}"
        
        success = detect_video(
            video_file, output_file, model, class_names,
            confidence_threshold, nms_threshold,
            show_preview=False, skip_frames=skip_frames
        )
        
        if success:
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"🎉 批次處理完成！")
    print(f"   成功: {success_count}/{len(video_files)}")
    print(f"   輸出目錄: {output_dir}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='使用 YOLOv4 對影片進行偵測')
    parser.add_argument('--video', type=str, help='單個影片檔案路徑')
    parser.add_argument('--batch', type=str, help='批次處理目錄（如 recordings）')
    parser.add_argument('--output', type=str, default='results/detected_videos',
                        help='輸出目錄（預設: results/detected_videos）')
    parser.add_argument('--confidence', type=float, default=None,
                        help='信心閾值（預設使用 config.ini 的設定）')
    parser.add_argument('--nms', type=float, default=None,
                        help='NMS 閾值（預設使用 config.ini 的設定）')
    parser.add_argument('--preview', action='store_true',
                        help='顯示即時預覽（按 Q 停止）')
    parser.add_argument('--skip-frames', type=int, default=0,
                        help='跳幀處理（0=不跳過，1=每2幀處理1幀，加快處理）')
    
    args = parser.parse_args()
    
    if not args.video and not args.batch:
        print("請指定 --video 或 --batch 參數")
        print("\n範例:")
        print("  單個影片: python detect_video.py --video recordings/recording_0.mp4")
        print("  批次處理: python detect_video.py --batch recordings")
        print("  即時預覽: python detect_video.py --video recordings/recording_0.mp4 --preview")
        sys.exit(1)
    
    try:
        print("🚀 載入 YOLOv4 模型...")
        model, class_names, default_conf, default_nms = load_yolo_model()
        
        confidence = args.confidence if args.confidence is not None else default_conf
        nms = args.nms if args.nms is not None else default_nms
        
        if args.video:
            # 處理單個影片
            output_path = Path(args.output) / f"{Path(args.video).stem}_detected.mp4"
            detect_video(
                args.video, output_path, model, class_names,
                confidence, nms, args.preview, args.skip_frames
            )
        elif args.batch:
            # 批次處理
            batch_detect_videos(
                args.batch, args.output, model, class_names,
                confidence, nms, args.skip_frames
            )
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
