"""
YOLOv8 訓練模組
提供模型訓練、資料集準備、訓練監控等功能
"""

import os
import sys
import json
import shutil
import threading
import time
from pathlib import Path
from datetime import datetime
import cv2
import yaml

# 訓練狀態
training_status = {
    'is_training': False,
    'current_epoch': 0,
    'total_epochs': 100,
    'progress': 0,
    'loss': 0,
    'map50': 0,
    'map50_95': 0,
    'status': 'idle',
    'message': '',
    'start_time': None,
    'log': []
}

_training_thread = None
_stop_training = False


def get_training_status():
    """取得訓練狀態"""
    return training_status.copy()


def add_log(message):
    """新增日誌訊息"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    training_status['log'].append(log_entry)
    # 只保留最近 100 條日誌
    if len(training_status['log']) > 100:
        training_status['log'] = training_status['log'][-100:]
    print(log_entry)


def prepare_dataset(data_dir, output_dir, train_ratio=0.8):
    """
    準備 YOLOv8 訓練資料集
    
    Args:
        data_dir: 原始資料目錄（包含 normal/ 和 abnormal/ 子目錄）
        output_dir: 輸出目錄
        train_ratio: 訓練集比例
    """
    data_path = Path(data_dir)
    output_path = Path(output_dir)
    
    # 建立目錄結構
    (output_path / 'images' / 'train').mkdir(parents=True, exist_ok=True)
    (output_path / 'images' / 'val').mkdir(parents=True, exist_ok=True)
    (output_path / 'labels' / 'train').mkdir(parents=True, exist_ok=True)
    (output_path / 'labels' / 'val').mkdir(parents=True, exist_ok=True)
    
    # 類別對應
    classes = {'normal': 0, 'abnormal': 1}
    
    stats = {'total': 0, 'train': 0, 'val': 0}
    
    for class_name, class_id in classes.items():
        class_dir = data_path / class_name
        if not class_dir.exists():
            add_log(f"警告: 找不到 {class_name} 目錄")
            continue
            
        # 取得所有圖片
        images = list(class_dir.glob('*.jpg')) + list(class_dir.glob('*.png')) + list(class_dir.glob('*.jpeg'))
        
        if not images:
            add_log(f"警告: {class_name} 目錄中沒有圖片")
            continue
            
        # 分割訓練集和驗證集
        import random
        random.shuffle(images)
        split_idx = int(len(images) * train_ratio)
        train_images = images[:split_idx]
        val_images = images[split_idx:]
        
        # 複製圖片並建立標籤
        for img_path in train_images:
            _copy_image_and_create_label(img_path, output_path, 'train', class_id)
            stats['train'] += 1
            
        for img_path in val_images:
            _copy_image_and_create_label(img_path, output_path, 'val', class_id)
            stats['val'] += 1
            
        stats['total'] += len(images)
        add_log(f"{class_name}: {len(images)} 張圖片 (訓練: {len(train_images)}, 驗證: {len(val_images)})")
    
    # 建立 data.yaml
    data_yaml = {
        'path': str(output_path.absolute()),
        'train': 'images/train',
        'val': 'images/val',
        'names': {0: 'normal', 1: 'abnormal'}
    }
    
    yaml_path = output_path / 'data.yaml'
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data_yaml, f, allow_unicode=True)
    
    add_log(f"資料集準備完成: {stats['total']} 張圖片")
    add_log(f"訓練集: {stats['train']} 張, 驗證集: {stats['val']} 張")
    add_log(f"data.yaml 已建立: {yaml_path}")
    
    return stats


def _copy_image_and_create_label(img_path, output_path, split, class_id):
    """複製圖片並建立 YOLO 格式標籤"""
    # 複製圖片
    dest_img = output_path / 'images' / split / img_path.name
    shutil.copy2(img_path, dest_img)
    
    # 建立標籤（整張圖片作為一個物件，中心點在正中央，寬高為 0.9）
    label_name = img_path.stem + '.txt'
    label_path = output_path / 'labels' / split / label_name
    
    # YOLO 格式: class_id center_x center_y width height (normalized)
    with open(label_path, 'w') as f:
        f.write(f"{class_id} 0.5 0.5 0.9 0.9\n")


def start_training(config):
    """
    開始訓練
    
    Args:
        config: 訓練配置字典
            - data_yaml: 資料集配置檔路徑
            - model: 基礎模型 (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)
            - epochs: 訓練輪數
            - batch_size: 批次大小
            - img_size: 圖片大小
            - device: 訓練裝置 (cpu, 0, 1, ...)
            - project: 輸出專案目錄
            - name: 訓練名稱
    """
    global _training_thread, _stop_training, training_status
    
    if training_status['is_training']:
        return {'success': False, 'error': '已有訓練正在進行中'}
    
    _stop_training = False
    _training_thread = threading.Thread(target=_training_worker, args=(config,), daemon=True)
    _training_thread.start()
    
    return {'success': True, 'message': '訓練已開始'}


def _training_worker(config):
    """訓練工作執行緒"""
    global training_status, _stop_training
    
    training_status['is_training'] = True
    training_status['status'] = 'starting'
    training_status['message'] = '正在初始化...'
    training_status['start_time'] = time.time()
    training_status['log'] = []
    training_status['current_epoch'] = 0
    training_status['total_epochs'] = config.get('epochs', 100)
    
    try:
        add_log("正在載入 YOLOv8...")
        
        # 嘗試導入 ultralytics
        try:
            from ultralytics import YOLO
        except ImportError:
            add_log("錯誤: 未安裝 ultralytics，正在嘗試安裝...")
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'ultralytics'])
            from ultralytics import YOLO
        
        # 載入模型
        model_name = config.get('model', 'yolov8n.pt')
        if not model_name.endswith('.pt'):
            model_name += '.pt'
        
        add_log(f"載入模型: {model_name}")
        model = YOLO(model_name)
        
        training_status['status'] = 'training'
        training_status['message'] = '訓練中...'
        
        # 開始訓練
        add_log("開始訓練...")
        results = model.train(
            data=config.get('data_yaml'),
            epochs=config.get('epochs', 100),
            batch=config.get('batch_size', 16),
            imgsz=config.get('img_size', 640),
            device=config.get('device', 'cpu'),
            project=config.get('project', 'runs/train'),
            name=config.get('name', 'candy_detect'),
            exist_ok=True,
            verbose=True
        )
        
        if _stop_training:
            add_log("訓練已被使用者中止")
            training_status['status'] = 'stopped'
            training_status['message'] = '訓練已中止'
        else:
            add_log("訓練完成!")
            training_status['status'] = 'completed'
            training_status['message'] = '訓練完成'
            training_status['progress'] = 100
            
            # 取得最終結果
            if hasattr(results, 'results_dict'):
                training_status['map50'] = results.results_dict.get('metrics/mAP50(B)', 0)
                training_status['map50_95'] = results.results_dict.get('metrics/mAP50-95(B)', 0)
        
    except Exception as e:
        add_log(f"訓練錯誤: {str(e)}")
        training_status['status'] = 'error'
        training_status['message'] = f'錯誤: {str(e)}'
    
    finally:
        training_status['is_training'] = False


def stop_training():
    """停止訓練"""
    global _stop_training
    _stop_training = True
    training_status['status'] = 'stopping'
    training_status['message'] = '正在停止訓練...'
    add_log("收到停止訓練請求")
    return {'success': True, 'message': '正在停止訓練...'}


def list_models(models_dir='runs/train'):
    """列出已訓練的模型"""
    models_path = Path(models_dir)
    models = []
    
    if models_path.exists():
        for run_dir in models_path.iterdir():
            if run_dir.is_dir():
                best_pt = run_dir / 'weights' / 'best.pt'
                last_pt = run_dir / 'weights' / 'last.pt'
                
                if best_pt.exists() or last_pt.exists():
                    # 取得訓練資訊
                    results_csv = run_dir / 'results.csv'
                    info = {
                        'name': run_dir.name,
                        'path': str(run_dir),
                        'best_pt': str(best_pt) if best_pt.exists() else None,
                        'last_pt': str(last_pt) if last_pt.exists() else None,
                        'created': datetime.fromtimestamp(run_dir.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 嘗試讀取訓練結果
                    if results_csv.exists():
                        try:
                            import csv
                            with open(results_csv, 'r') as f:
                                reader = csv.DictReader(f)
                                rows = list(reader)
                                if rows:
                                    last_row = rows[-1]
                                    info['epochs'] = len(rows)
                                    info['map50'] = float(last_row.get('metrics/mAP50(B)', 0))
                                    info['map50_95'] = float(last_row.get('metrics/mAP50-95(B)', 0))
                        except:
                            pass
                    
                    models.append(info)
    
    return sorted(models, key=lambda x: x['created'], reverse=True)


def get_available_devices():
    """取得可用的訓練裝置"""
    devices = [{'id': 'cpu', 'name': 'CPU'}]
    
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                devices.append({'id': str(i), 'name': f'GPU {i}: {name}'})
    except:
        pass
    
    return devices



def test_model(model_path: str, image_path: str, conf: float = 0.25) -> dict:
    """
    ???????????????????????????
    """
    model_path = Path(model_path)
    image_path = Path(image_path)

    if not model_path.exists():
        return {'success': False, 'error': f'Model file not found: {model_path}'}
    if not image_path.exists():
        return {'success': False, 'error': f'Image file not found: {image_path}'}

    try:
        from ultralytics import YOLO
    except Exception as e:
        return {'success': False, 'error': f'ultralytics not installed: {e}'}

    try:
        model = YOLO(str(model_path))
        results = model.predict(str(image_path), conf=conf, verbose=False)
        if not results:
            return {'success': False, 'error': 'No results returned'}

        res = results[0]
        annotated = res.plot()  # numpy array with drawings

        save_dir = Path('static') / 'test_results'
        save_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        output_path = save_dir / f'result_{ts}.jpg'
        cv2.imwrite(str(output_path), annotated)

        detections = []
        names = res.names
        if hasattr(res, 'boxes') and res.boxes is not None:
            for box in res.boxes:
                cls_id = int(box.cls.item()) if hasattr(box.cls, 'item') else int(box.cls)
                detections.append({
                    'class_id': cls_id,
                    'class_name': names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id),
                    'confidence': float(box.conf.item()) if hasattr(box.conf, 'item') else float(box.conf),
                    'xyxy': [float(x) for x in box.xyxy[0].tolist()]
                })

        return {
            'success': True,
            'output_image': f'/static/test_results/{output_path.name}',
            'detections': detections,
            'num_detections': len(detections)
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}




def evaluate_model(model_path: str, data_yaml: str, device: str = 'cpu', conf: float = 0.25, iou: float = 0.6) -> dict:
    """使用驗證集計算模型準確度 (mAP / precision / recall)"""
    model_path = Path(model_path)
    data_file = Path(data_yaml)

    if not model_path.exists():
        return {'success': False, 'error': f'Model file not found: {model_path}'}
    if not data_file.exists():
        return {'success': False, 'error': f'Data yaml not found: {data_file}'}

    try:
        from ultralytics import YOLO
    except Exception as e:
        return {'success': False, 'error': f'ultralytics not installed: {e}'}

    try:
        model = YOLO(str(model_path))
        results = model.val(
            data=str(data_file),
            device=device,
            conf=conf,
            iou=iou,
            verbose=False,
        )
        metrics = results.results_dict if hasattr(results, 'results_dict') else {}
        return {
            'success': True,
            'metrics': {
                'map50': metrics.get('metrics/mAP50(B)', 0),
                'map50_95': metrics.get('metrics/mAP50-95(B)', 0),
                'precision': metrics.get('metrics/precision(B)', 0),
                'recall': metrics.get('metrics/recall(B)', 0),
                'fitness': metrics.get('fitness', 0),
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
