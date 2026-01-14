"""
使用現有 YOLOv4 或 YOLOv8 模型自動標註影像
可用於快速生成初步標註，之後再手動修正
"""
import cv2
import os
import sys
import configparser
from pathlib import Path
import tempfile
import shutil
import numpy as np
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_yolov8_model(model_path='yolov8n.pt'):
    """載入 YOLOv8 模型（使用 COCO 預訓練模型進行快速標註）"""
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("請安裝 ultralytics: pip install ultralytics")
    
    # 使用 COCO 預訓練模型 yolov8n.pt（自動下載或使用本地檔案）
    print(f"[LOAD] 載入 YOLOv8 COCO 預訓練模型: {model_path}")
    print(f"  說明: 使用 80 類別 COCO 模型進行快速標註，邊界框精準度高")
    
    # 檢查是否存在本地模型
    local_path = Path(PROJECT_ROOT) / model_path
    if local_path.exists():
        print(f"  使用本地模型: {local_path}")
        model = YOLO(str(local_path))
    else:
        print(f"  從 Ultralytics 下載模型...")
        model = YOLO(model_path)  # 會自動下載
    
    # 獲取類別名稱
    class_names = list(model.names.values()) if hasattr(model, 'names') else []
    
    print(f"[OK] YOLOv8 COCO 模型載入成功")
    print(f"  類別數: {len(class_names)}")
    print(f"  主要類別: person, bicycle, car, motorcycle, airplane, bus, train...")
    print(f"  ⚠️ 注意: 所有檢測結果將統一標記為 class 0（正常）")
    
    return model, class_names


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
    model.setInputParams(size=(input_size, input_size), scale=1/255, swapRB=False)
    
    print(f"[OK] 模型載入成功")
    print(f"  類別: {class_names}")
    print(f"  輸入大小: {input_size}x{input_size}")
    
    return model, class_names


def convert_bbox_to_yolo(bbox, img_width, img_height):
    """
    將 OpenCV bbox 轉換為 YOLO 格式
    OpenCV: (x, y, w, h) - 左上角座標和寬高
    YOLO: (x_center, y_center, width, height) - 歸一化的中心點和寬高
    """
    x, y, w, h = bbox
    
    # 計算中心點
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    
    # 歸一化寬高
    width = w / img_width
    height = h / img_height
    
    # 確保在 0-1 範圍內
    x_center = max(0, min(1, x_center))
    y_center = max(0, min(1, y_center))
    width = max(0, min(1, width))
    height = max(0, min(1, height))
    
    return x_center, y_center, width, height


def auto_label_images(images_dir, output_labels_dir, model, class_names, 
                       confidence_threshold=0.4, nms_threshold=0.4,
                       overwrite=False, visualize=False):
    """
    自動標註影像（支援子資料夾結構）
    
    Args:
        images_dir: 影像目錄
        output_labels_dir: 標註輸出目錄
        model: YOLO 模型
        class_names: 類別名稱列表
        confidence_threshold: 信心閾值
        nms_threshold: NMS 閾值
        overwrite: 是否覆蓋已存在的標註
        visualize: 是否儲存視覺化結果
    """
    import json
    from datetime import datetime
    
    images_dir = Path(images_dir)
    output_labels_dir = Path(output_labels_dir)
    
    # 元數據目錄
    metadata_dir = output_labels_dir.parent / 'metadata'
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    if visualize:
        vis_dir = output_labels_dir.parent / 'visualizations'
        vis_dir.mkdir(exist_ok=True)
        print(f"[DIR] 視覺化結果將儲存到: {vis_dir}")
    
    # 搜尋影像（只搜尋當前資料夾，不遞迴子資料夾）
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    image_files = []
    for ext in image_extensions:
        image_files.extend(list(images_dir.glob(f'*{ext}')))
        image_files.extend(list(images_dir.glob(f'*{ext.upper()}')))
    
    if not image_files:
        print(f"[ERROR] 在 {images_dir} 中找不到影像檔案")
        return
    
    print(f"\n[INFO] 找到 {len(image_files)} 張影像")
    print(f"[DIR] 標註輸出: {output_labels_dir}")
    print(f"[CFG] 信心閾值: {confidence_threshold}")
    print(f"[CFG] NMS 閾值: {nms_threshold}")
    print(f"[INFO] 使用批次優化處理...")
    print("=" * 60)
    
    # 預先過濾 - 找出需要處理的檔案
    files_to_process = []
    files_skipped = []
    
    for image_path in image_files:
        relative_path = image_path.relative_to(images_dir)
        label_dir = output_labels_dir / relative_path.parent
        label_path = label_dir / f"{image_path.stem}.txt"
        
        if label_path.exists() and not overwrite:
            files_skipped.append(image_path)
        else:
            files_to_process.append(image_path)
    
    skipped_count = len(files_skipped)
    total_to_process = len(files_to_process)
    
    if skipped_count > 0:
        print(f"[SKIP] 跳過 {skipped_count} 張已存在標註的影像")
    
    if total_to_process == 0:
        print("[INFO] 所有影像都已標註！")
        return
    
    print(f"[INFO] 需要處理 {total_to_process} 張影像\n")
    
    labeled_count = 0
    total_detections = 0
    start_time = time.time()
    
    for i, image_path in enumerate(files_to_process, 1):
        # 保留子資料夾結構
        relative_path = image_path.relative_to(images_dir)
        label_dir = output_labels_dir / relative_path.parent
        label_dir.mkdir(parents=True, exist_ok=True)
        label_path = label_dir / f"{image_path.stem}.txt"
        
        # 元數據路徑
        meta_dir = metadata_dir / relative_path.parent
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_path = meta_dir / f"{image_path.stem}.json"
        
        # 讀取影像 (使用 numpy 避免 Unicode 路徑問題)
        try:
            with open(str(image_path), 'rb') as f:
                img_array = np.frombuffer(f.read(), dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            img = None
        
        if img is None:
            print(f"[WARN] 無法讀取: {image_path.name}")
            continue
        
        # 轉灰階（如果模型是灰階訓練的）
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # 偵測
        try:
            classes, scores, boxes = model.detect(gray, confidence_threshold, nms_threshold)
            
            # 寫入標註檔案
            with open(label_path, 'w') as f:
                if len(classes) > 0:
                    for class_id, score, box in zip(classes.flatten(), scores.flatten(), boxes):
                        # 反轉類別：模型輸出 1 (abnormal) 實際是 0 (normal)
                        # 因為實際產品都是正常的，模型訓練時標籤可能顛倒了
                        corrected_class_id = 0 if class_id == 1 else class_id
                        
                        # 轉換為 YOLO 格式
                        x_center, y_center, w, h = convert_bbox_to_yolo(box, width, height)
                        # 寫入: class_id x_center y_center width height
                        f.write(f"{corrected_class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")
                    
                    # 保存元數據
                    metadata = {
                        'source': 'ai',  # AI 自動標註
                        'timestamp': datetime.now().isoformat(),
                        'image_path': str(relative_path).replace('\\', '/'),
                        'annotation_count': len(classes),
                        'confidence_threshold': confidence_threshold,
                        'model': 'YOLOv4'
                    }
                    
                    with open(meta_path, 'w', encoding='utf-8') as mf:
                        json.dump(metadata, mf, ensure_ascii=False, indent=2)
                    
                    total_detections += len(classes)
                    labeled_count += 1
                    
                    # 視覺化
                    if visualize:
                        vis_img = img.copy()
                        for class_id, score, box in zip(classes.flatten(), scores.flatten(), boxes):
                            # 使用修正後的類別（實際都是正常的）
                            corrected_class_id = 0 if class_id == 1 else class_id
                            x, y, w, h = box
                            class_name = class_names[corrected_class_id] if corrected_class_id < len(class_names) else f"Class {corrected_class_id}"
                            color = (0, 255, 0) if corrected_class_id == 0 else (0, 0, 255)  # normal=綠, abnormal=紅
                            
                            cv2.rectangle(vis_img, (x, y), (x+w, y+h), color, 2)
                            label_text = f"{class_name}: {score:.2f}"
                            cv2.putText(vis_img, label_text, (x, y-10), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
                        vis_path = vis_dir / f"{image_path.stem}_labeled.jpg"
                        cv2.imwrite(str(vis_path), vis_img)
                else:
                    # 沒有偵測到物件，創建空檔案
                    pass
                
                # 每 20 張或百分比變化時顯示進度
                if i % 20 == 0 or i == total_to_process:
                    elapsed = time.time() - start_time
                    speed = i / elapsed if elapsed > 0 else 0
                    remaining = (total_to_process - i) / speed if speed > 0 else 0
                    pct = i * 100 // total_to_process
                    print(f"[{i}/{total_to_process}] {pct}% - 速度: {speed:.1f} 張/秒, 剩餘: {remaining:.0f} 秒")
                    
        except Exception as e:
            print(f"[ERROR] 處理失敗 {image_path.name}: {e}")
            continue
    
    # 計算總耗時
    total_elapsed = time.time() - start_time
    final_speed = total_to_process / total_elapsed if total_elapsed > 0 else 0
    
    print("\n" + "=" * 60)
    print(f"[DONE] 完成!")
    print(f"   已標註: {labeled_count} 張")
    print(f"   跳過: {skipped_count} 張 (已存在)")
    print(f"   總偵測數: {total_detections} 個物件")
    print(f"   平均每張: {total_detections/labeled_count:.1f} 個物件" if labeled_count > 0 else "")
    print(f"   總耗時: {total_elapsed:.1f} 秒 ({final_speed:.1f} 張/秒)")
    print(f"\n[DIR] 標註檔案位置: {output_labels_dir}")
    
    if visualize:
        print(f"[DIR] 視覺化結果: {vis_dir}")
    
    print("\n[TIP] 下一步:")
    print("   1. 使用 LabelImg 檢查並修正標註")
    print("   2. 將影像和標註複製到訓練資料集目錄")
    print("   3. 執行訓練")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='使用 YOLOv4 模型自動標註影像')
    parser.add_argument('--images', type=str, default='datasets/extracted_frames',
                        help='影像目錄（預設: datasets/extracted_frames）')
    parser.add_argument('--output', type=str, default='datasets/annotated/labels',
                        help='標註輸出目錄（預設: datasets/annotated/labels）')
    parser.add_argument('--folder', type=str, default='',
                        help='只處理特定子資料夾（例如: 0_20251203_155742）')
    parser.add_argument('--image-list', type=str, default='',
                        help='JSON 檔案路徑，包含要處理的圖片列表')
    parser.add_argument('--model', type=str, default='yolov4',
                        choices=['yolov4', 'yolov8'],
                        help='使用的模型（預設: yolov4）')
    parser.add_argument('--confidence', type=float, default=0.3,
                        help='信心閾值（預設: 0.3，較低可標註更多物件）')
    parser.add_argument('--nms', type=float, default=0.4,
                        help='NMS 閾值（預設: 0.4）')
    parser.add_argument('--overwrite', action='store_true',
                        help='覆蓋已存在的標註')
    parser.add_argument('--visualize', action='store_true',
                        help='儲存視覺化結果')
    parser.add_argument('--task-id', type=str, default='',
                        help='任務 ID，用於進度追蹤')
    
    args = parser.parse_args()
    
    print(f"[DEBUG] 命令參數:")
    print(f"  --images: {args.images}")
    print(f"  --output: {args.output}")
    print(f"  --folder: {args.folder}")
    print(f"  --image-list: {args.image_list}")
    print(f"  --model: {args.model}")
    print(f"  --confidence: {args.confidence}")
    
    try:
        # 根據模型類型載入模型
        if args.model == 'yolov8':
            print("[LOAD] 載入 YOLOv8 模型...")
            model, class_names = load_yolov8_model()
            model_name = 'YOLOv8'
        else:
            print("[LOAD] 載入 YOLOv4 模型...")
            model, class_names = load_yolo_model()
            model_name = 'YOLOv4'
        
        # 如果指定了圖片列表，只處理這些圖片
        if args.image_list:
            import json
            with open(args.image_list, 'r', encoding='utf-8') as f:
                image_list = json.load(f)
            
            print(f"\n[LIST] 處理指定的 {len(image_list)} 張圖片")
            
            # 進度追蹤輔助函數
            def update_progress(current, total, labeled_count=0):
                if args.task_id:
                    try:
                        requests.put(
                            f'http://localhost:5000/api/progress/{args.task_id}',
                            json={
                                'current': current,
                                'total': total,
                                'labeled_count': labeled_count,
                                'status': 'processing' if current < total else 'completed'
                            },
                            timeout=1
                        )
                    except:
                        pass  # 忽略進度更新錯誤
            
            # 處理每張指定的圖片
            labeled_count = 0
            for idx, image_rel_path in enumerate(image_list, 1):
                image_path = os.path.join(args.images, image_rel_path)
                if not os.path.exists(image_path):
                    print(f"[SKIP] 圖片不存在: {image_path}")
                    update_progress(idx, len(image_list), labeled_count)
                    continue
                
                # 輸出標註到對應的路徑
                output_path = os.path.join(args.output, os.path.dirname(image_rel_path))
                os.makedirs(output_path, exist_ok=True)
                
                # 處理單張圖片 (使用 numpy 避免 Unicode 路徑問題)
                try:
                    with open(image_path, 'rb') as f:
                        img_array = np.frombuffer(f.read(), dtype=np.uint8)
                        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                except Exception as e:
                    img = None
                
                if img is None:
                    print(f"[SKIP] 無法讀取圖片: {image_path}")
                    update_progress(idx, len(image_list), labeled_count)
                    continue
                
                height, width = img.shape[:2]
                
                # 偵測 - 根據模型類型使用不同方法
                try:
                    if args.model == 'yolov8':
                        # YOLOv8 使用 predict 方法
                        results = model.predict(source=img, conf=args.confidence, iou=args.nms, verbose=False)
                        result = results[0]
                        boxes_data = result.boxes
                        
                        # 轉換格式
                        classes = boxes_data.cls.cpu().numpy().astype(int).reshape(-1, 1)
                        scores = boxes_data.conf.cpu().numpy().reshape(-1, 1)
                        boxes = boxes_data.xywh.cpu().numpy()  # x_center, y_center, w, h
                    else:
                        # YOLOv4 使用 detect 方法
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        classes, scores, boxes = model.detect(gray, args.confidence, args.nms)
                except Exception as e:
                    print(f"[ERROR] 偵測失敗: {e}")
                    update_progress(idx, len(image_list), labeled_count)
                    continue
                
                # 儲存標註
                label_file = os.path.join(output_path, os.path.splitext(os.path.basename(image_path))[0] + '.txt')
                if os.path.exists(label_file) and not args.overwrite:
                    update_progress(idx, len(image_list), labeled_count)
                    continue
                    
                if len(classes) > 0:
                    labeled_count += 1
                
                with open(label_file, 'w') as f:
                    if len(classes) > 0:
                        valid_count = 0
                        filtered_count = 0
                        
                        for class_id, score, box in zip(classes.flatten(), scores.flatten(), boxes):
                            # YOLOv8 COCO 模型：將所有檢測統一標記為 class 0（正常）
                            # 因為 COCO 有 80 個類別，但我們只需要檢測物體位置
                            if args.model == 'yolov8':
                                # 統一使用 class 0（正常），之後可以手動調整為瑕疵
                                final_class_id = 0
                            else:
                                # YOLOv4：對調類別 0↔1
                                final_class_id = 1 - class_id
                            
                            # YOLOv8 boxes 已經是 x_center, y_center, w, h 格式（像素值）
                            # YOLOv4 boxes 是 x, y, w, h 格式（左上角座標）
                            if args.model == 'yolov8':
                                # YOLOv8: box = [x_center, y_center, w, h] (像素值)
                                box_width_px = box[2]
                                box_height_px = box[3]
                                x_center = box[0] / width
                                y_center = box[1] / height
                                w = box[2] / width
                                h = box[3] / height
                            else:
                                # YOLOv4: box = [x, y, w, h] (左上角座標)
                                box_width_px = box[2]
                                box_height_px = box[3]
                                x_center = (box[0] + box[2] / 2) / width
                                y_center = (box[1] + box[3] / 2) / height
                                w = box[2] / width
                                h = box[3] / height
                            
                            # 過濾極端尺寸的標記框
                            # 正常尺寸約 350x350，允許範圍：50-800 像素
                            min_size = 50   # 最小尺寸（像素）
                            max_size = 800  # 最大尺寸（像素）
                            
                            if (box_width_px < min_size or box_height_px < min_size or 
                                box_width_px > max_size or box_height_px > max_size):
                                filtered_count += 1
                                continue  # 跳過此標記框
                            
                            # 格式: class_id x_center y_center width height confidence
                            f.write(f"{final_class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f} {score:.6f}\n")
                            valid_count += 1
                        
                        # 如果有過濾，輸出統計
                        if filtered_count > 0:
                            print(f"  [FILTER] {image_path.name}: 保留 {valid_count} 個，過濾 {filtered_count} 個極端尺寸標記框")
                
                # 儲存 metadata
                metadata_dir = os.path.join(args.output.replace('labels', 'metadata'), os.path.dirname(image_rel_path))
                os.makedirs(metadata_dir, exist_ok=True)
                
                # 內聯 metadata 儲存邏輯
                from datetime import datetime
                meta_path = os.path.join(metadata_dir, os.path.splitext(os.path.basename(image_path))[0] + '.json')
                metadata = {
                    'source': 'ai',
                    'timestamp': datetime.now().isoformat(),
                    'image_path': image_rel_path.replace('\\', '/'),
                    'annotation_count': len(classes) if len(classes) > 0 else 0,
                    'confidence_threshold': args.confidence,
                    'model': model_name
                }
                with open(meta_path, 'w', encoding='utf-8') as mf:
                    json.dump(metadata, mf, ensure_ascii=False, indent=2)
                
                # 更新進度
                update_progress(idx, len(image_list), labeled_count)
                
                print(f"[DONE] {os.path.basename(image_path)}: {len(classes)} 個偵測")
            
            # 清理臨時檔案
            try:
                os.remove(args.image_list)
            except:
                pass
                
        # 如果指定了特定資料夾，則只處理該資料夾
        elif args.folder:
            images_dir = os.path.join(args.images, args.folder)
            output_dir = os.path.join(args.output, args.folder)
            print(f"\n[DIR] 只處理資料夾: {args.folder}")
            
            print("\n[START] 開始自動標註...")
            auto_label_images(
                images_dir,
                output_dir,
                model,
                class_names,
                confidence_threshold=args.confidence,
                nms_threshold=args.nms,
                overwrite=args.overwrite,
                visualize=args.visualize
            )
        else:
            images_dir = args.images
            output_dir = args.output
            
            print("\n[START] 開始自動標註...")
            auto_label_images(
                images_dir,
                output_dir,
                model,
                class_names,
                confidence_threshold=args.confidence,
                nms_threshold=args.nms,
                overwrite=args.overwrite,
                visualize=args.visualize
            )
        
    except Exception as e:
        print(f"\n[ERROR] 錯誤: {e}")
        import traceback
        traceback.print_exc()

