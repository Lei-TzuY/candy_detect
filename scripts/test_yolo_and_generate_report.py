"""
使用 YOLOv8 模型測試並生成檢測報告
類似 auto_label 的 HTML 報告格式
"""
from ultralytics import YOLO
from pathlib import Path
import cv2
import base64
from datetime import datetime
from tqdm import tqdm

def generate_detection_report(detections_data, model_name, output_file):
    """生成 HTML 檢測報告"""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 統計
    total_images = len(detections_data)
    total_detections = sum(len(d['boxes']) for d in detections_data)
    images_with_detections = sum(1 for d in detections_data if len(d['boxes']) > 0)
    
    # 類別統計
    class_counts = {0: 0, 1: 0}  # 0: 正常, 1: 瑕疵
    confidences = []
    
    for data in detections_data:
        for box in data['boxes']:
            class_counts[box['class']] = class_counts.get(box['class'], 0) + 1
            confidences.append(box['confidence'])
    
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YOLOv8 模型檢測報告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft JhengHei', 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }}
        
        .stat-label {{
            color: #6c757d;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .gallery {{
            padding: 40px;
        }}
        
        .gallery-header {{
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .gallery-header h2 {{
            color: #333;
            font-size: 2em;
            margin-bottom: 10px;
        }}
        
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
        }}
        
        .image-item {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            border: 3px solid transparent;
        }}
        
        .image-item:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }}
        
        .image-item.has-detection {{
            border-color: #10b981;
        }}
        
        .image-item.no-detection {{
            border-color: #ef4444;
        }}
        
        .image-wrapper {{
            position: relative;
            width: 100%;
            padding-top: 75%;
            background: #f0f0f0;
            overflow: hidden;
        }}
        
        .image-wrapper img {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}
        
        .image-info {{
            padding: 15px;
        }}
        
        .image-name {{
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
            word-break: break-all;
            font-size: 0.9em;
        }}
        
        .detection-count {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .detection-count.has {{
            background: #10b981;
            color: white;
        }}
        
        .detection-count.none {{
            background: #ef4444;
            color: white;
        }}
        
        .detections {{
            margin-top: 10px;
        }}
        
        .detection-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 8px;
            font-size: 0.85em;
        }}
        
        .detection-label {{
            font-weight: bold;
        }}
        
        .detection-label.normal {{
            color: #10b981;
        }}
        
        .detection-label.defect {{
            color: #ef4444;
        }}
        
        .detection-confidence {{
            background: #667eea;
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.9em;
        }}
        
        .footer {{
            background: #2d3748;
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .footer p {{
            margin: 5px 0;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 YOLOv8 模型檢測報告</h1>
            <p class="subtitle">模型: {model_name}</p>
            <p class="subtitle">生成時間: {timestamp}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">總圖片數</div>
                <div class="stat-value">{total_images}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">有檢測結果</div>
                <div class="stat-value">{images_with_detections}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">總檢測數</div>
                <div class="stat-value">{total_detections}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">平均信心度</div>
                <div class="stat-value">{avg_confidence:.1%}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🟢 正常</div>
                <div class="stat-value">{class_counts.get(0, 0)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🔴 瑕疵</div>
                <div class="stat-value">{class_counts.get(1, 0)}</div>
            </div>
        </div>
        
        <div class="gallery">
            <div class="gallery-header">
                <h2>📸 檢測結果圖庫</h2>
            </div>
            
            <div class="image-grid">
"""
    
    # 添加每張圖片
    for data in detections_data:
        has_detection = len(data['boxes']) > 0
        status_class = 'has-detection' if has_detection else 'no-detection'
        
        html += f"""
                <div class="image-item {status_class}">
                    <div class="image-wrapper">
                        <img src="data:image/jpeg;base64,{data['image_base64']}" alt="{data['filename']}">
                    </div>
                    <div class="image-info">
                        <div class="image-name">{data['filename']}</div>
                        <span class="detection-count {'has' if has_detection else 'none'}">
                            {'✅' if has_detection else '❌'} {len(data['boxes'])} 個偵測
                        </span>
"""
        
        if has_detection:
            html += '<div class="detections">'
            for box in data['boxes']:
                label = '正常' if box['class'] == 0 else '瑕疵'
                label_class = 'normal' if box['class'] == 0 else 'defect'
                html += f"""
                            <div class="detection-item">
                                <span class="detection-label {label_class}">{label}</span>
                                <span class="detection-confidence">{box['confidence']:.1%}</span>
                            </div>
"""
            html += '</div>'
        
        html += """
                    </div>
                </div>
"""
    
    html += f"""
            </div>
        </div>
        
        <div class="footer">
            <p>🍬 糖果瑕疵檢測系統</p>
            <p>YOLOv8 模型測試報告</p>
            <p>© 2026 Candy Detector</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 報告已生成: {output_file}")

def test_model_on_all_images(model_path, confidence_threshold=0.25):
    """使用模型測試所有圖片並生成報告"""
    
    model_path = Path(model_path)
    if not model_path.exists():
        print(f"❌ 找不到模型: {model_path}")
        return
    
    print(f"📥 載入模型: {model_path}")
    model = YOLO(str(model_path))
    
    # 獲取所有圖片
    images_dir = Path('datasets/extracted_frames')
    
    all_images = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
        all_images.extend(images_dir.rglob(ext))
    
    if not all_images:
        print("❌ 找不到任何圖片")
        return
    
    print(f"🔍 找到 {len(all_images)} 張圖片")
    print(f"📊 信心閾值: {confidence_threshold}")
    print(f"\n開始檢測...")
    
    detections_data = []
    
    # 使用 tqdm 顯示進度
    for img_path in tqdm(all_images, desc="處理中", unit="張"):
        # 預測
        results = model.predict(
            source=str(img_path),
            conf=confidence_threshold,
            iou=0.45,
            verbose=False,
        )
        
        # 讀取圖片並轉 base64
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        
        # 在圖片上繪製檢測框
        result = results[0]
        boxes = result.boxes
        
        for box in boxes:
            # 獲取坐標
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            
            # 繪製框
            color = (0, 255, 0) if cls == 0 else (0, 0, 255)  # BGR
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            
            # 標籤
            label = '正常' if cls == 0 else '瑕疵'
            label_text = f'{label} {conf:.0%}'
            
            # 標籤背景
            (label_w, label_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(img, (int(x1), int(y1) - label_h - 10), (int(x1) + label_w, int(y1)), color, -1)
            cv2.putText(img, label_text, (int(x1), int(y1) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # 轉 base64
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # 收集檢測結果
        boxes_data = []
        for box in boxes:
            boxes_data.append({
                'class': int(box.cls[0]),
                'confidence': float(box.conf[0]),
            })
        
        detections_data.append({
            'filename': img_path.name,
            'folder': img_path.parent.name,
            'image_base64': img_base64,
            'boxes': boxes_data,
        })
    
    # 生成報告
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_name = model_path.stem
    report_filename = f'yolov8_test_{model_name}_{timestamp}.html'
    report_path = reports_dir / report_filename
    
    print(f"\n📝 生成報告...")
    generate_detection_report(detections_data, model_name, report_path)
    
    # 統計
    total_detections = sum(len(d['boxes']) for d in detections_data)
    images_with_detections = sum(1 for d in detections_data if len(d['boxes']) > 0)
    
    print(f"\n📈 檢測統計:")
    print(f"   總圖片數: {len(detections_data)}")
    print(f"   有檢測結果: {images_with_detections} ({images_with_detections/len(detections_data)*100:.1f}%)")
    print(f"   總檢測數: {total_detections}")
    print(f"   平均每張: {total_detections/len(detections_data):.2f} 個")
    
    print(f"\n✅ 完成！")
    print(f"   報告: {report_path}")
    
    return report_path

if __name__ == '__main__':
    # 測試指定模型
    model_path = r'之前訓練的 yolov8\yolov8\yolov8n.pt'
    confidence_threshold = 0.25  # 可調整信心閾值
    
    test_model_on_all_images(model_path, confidence_threshold)
