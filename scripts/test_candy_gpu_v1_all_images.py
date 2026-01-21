"""
使用 candy_gpu_v1 模型对 extracted_frames 中所有 1050 张图片进行检测并生成报告
"""
from ultralytics import YOLO
from pathlib import Path
import cv2
import base64
from datetime import datetime
from tqdm import tqdm

def generate_detection_report(detections_data, model_name, output_file):
    """生成 HTML 检测报告"""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 统计
    total_images = len(detections_data)
    total_detections = sum(len(d['boxes']) for d in detections_data)
    images_with_detections = sum(1 for d in detections_data if len(d['boxes']) > 0)
    
    # 类别统计
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
    <title>YOLOv8 模型检测报告 - {model_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
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
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .stat-label {{
            color: #666;
            font-size: 1.1em;
        }}
        .gallery {{
            padding: 40px;
            background: white;
        }}
        .gallery h2 {{
            font-size: 2em;
            margin-bottom: 30px;
            color: #333;
            border-left: 5px solid #667eea;
            padding-left: 20px;
        }}
        .filters {{
            margin-bottom: 30px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            padding: 12px 24px;
            border: none;
            border-radius: 25px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            background: #f0f0f0;
            color: #333;
        }}
        .filter-btn:hover {{
            background: #667eea;
            color: white;
            transform: translateY(-2px);
        }}
        .filter-btn.active {{
            background: #667eea;
            color: white;
        }}
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }}
        .image-card {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .image-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }}
        .image-card img {{
            width: 100%;
            height: 250px;
            object-fit: contain;
            background: #f5f5f5;
        }}
        .image-info {{
            padding: 15px;
            background: white;
        }}
        .image-info .filename {{
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
            font-size: 0.9em;
            word-break: break-all;
        }}
        .image-info .folder {{
            color: #999;
            font-size: 0.85em;
            margin-bottom: 10px;
        }}
        .detection-count {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .detection-count.has-defects {{
            background: #fee;
            color: #d00;
        }}
        .detection-count.no-defects {{
            background: #efe;
            color: #0a0;
        }}
        .detection-count.no-detection {{
            background: #eee;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 YOLOv8 模型检测报告</h1>
            <div class="subtitle">{model_name}</div>
            <div class="subtitle" style="margin-top:10px;">{timestamp}</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">📷 总图片数</div>
                <div class="stat-value">{total_images}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🔍 检测到物体</div>
                <div class="stat-value">{images_with_detections}</div>
                <div class="stat-label" style="font-size:0.9em;color:#999;">{images_with_detections/total_images*100:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📊 总检测数</div>
                <div class="stat-value">{total_detections}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">✅ 正常</div>
                <div class="stat-value" style="color:#0a0;">{class_counts[0]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">❌ 瑕疵</div>
                <div class="stat-value" style="color:#d00;">{class_counts[1]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🎯 平均信心度</div>
                <div class="stat-value">{avg_confidence:.1%}</div>
            </div>
        </div>
        
        <div class="gallery">
            <h2>检测结果</h2>
            <div class="filters">
                <button class="filter-btn active" onclick="filterImages('all')">全部 ({total_images})</button>
                <button class="filter-btn" onclick="filterImages('with-defects')">有瑕疵</button>
                <button class="filter-btn" onclick="filterImages('normal-only')">仅正常</button>
                <button class="filter-btn" onclick="filterImages('no-detection')">无检测</button>
            </div>
            
            <div class="image-grid" id="imageGrid">
"""
    
    # 添加所有图片
    for data in detections_data:
        has_defects = any(b['class'] == 1 for b in data['boxes'])
        has_normal = any(b['class'] == 0 for b in data['boxes'])
        no_detection = len(data['boxes']) == 0
        
        classes = []
        if has_defects:
            classes.append('with-defects')
        if has_normal and not has_defects:
            classes.append('normal-only')
        if no_detection:
            classes.append('no-detection')
        
        class_attr = ' '.join(classes)
        
        if no_detection:
            badge_class = 'no-detection'
            badge_text = '无检测'
        elif has_defects:
            badge_class = 'has-defects'
            defect_count = len([b for b in data['boxes'] if b['class'] == 1])
            badge_text = f'{defect_count} 瑕疵'
        else:
            badge_class = 'no-defects'
            badge_text = f'{len(data["boxes"])} 正常'
        
        html += f"""
                <div class="image-card" data-filter="{class_attr}">
                    <img src="data:image/jpeg;base64,{data['image_base64']}" alt="{data['filename']}">
                    <div class="image-info">
                        <div class="filename">{data['filename']}</div>
                        <div class="folder">📁 {data['folder']}</div>
                        <span class="detection-count {badge_class}">{badge_text}</span>
                    </div>
                </div>
"""
    
    html += """
            </div>
        </div>
    </div>
    
    <script>
        function filterImages(filter) {
            const cards = document.querySelectorAll('.image-card');
            const buttons = document.querySelectorAll('.filter-btn');
            
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            cards.forEach(card => {
                if (filter === 'all') {
                    card.style.display = 'block';
                } else {
                    const filters = card.getAttribute('data-filter').split(' ');
                    card.style.display = filters.includes(filter) ? 'block' : 'none';
                }
            });
        }
    </script>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 报告已生成: {output_file}")


def main():
    """主程序"""
    
    # 模型路径
    model_path = Path(r'D:\專案\candy\runs\detect\runs\detect\candy_gpu_v1\weights\best.pt')
    
    if not model_path.exists():
        print(f"❌ 找不到模型: {model_path}")
        return
    
    print(f"📥 载入模型: {model_path.name}")
    model = YOLO(str(model_path))
    
    # 获取所有图片（使用 set 去重，避免大小写重复）
    images_dir = Path(r'D:\專案\candy\datasets\extracted_frames')
    
    all_images = set()
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        all_images.update(images_dir.rglob(ext))
    
    all_images = list(all_images)
    
    if not all_images:
        print("❌ 找不到任何图片")
        return
    
    print(f"🔍 找到 {len(all_images)} 张图片")
    print(f"📊 信心阈值: 0.25")
    print(f"\n开始检测...\n")
    
    detections_data = []
    
    # 使用 tqdm 显示进度
    for img_path in tqdm(all_images, desc="处理中", unit="张"):
        # 预测
        results = model.predict(
            source=str(img_path),
            conf=0.25,
            iou=0.45,
            verbose=False,
        )
        
        # 读取图片并转 base64
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        
        # 在图片上绘制检测框
        result = results[0]
        boxes = result.boxes
        
        for box in boxes:
            # 获取坐标
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            
            # 绘制框
            color = (0, 255, 0) if cls == 0 else (0, 0, 255)  # BGR
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            
            # 标签
            label = '正常' if cls == 0 else '瑕疵'
            label_text = f'{label} {conf:.0%}'
            
            # 标签背景
            (label_w, label_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(img, (int(x1), int(y1) - label_h - 10), (int(x1) + label_w, int(y1)), color, -1)
            cv2.putText(img, label_text, (int(x1), int(y1) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # 转 base64
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # 收集检测结果
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
    
    # 生成报告
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_name = 'candy_gpu_v1'
    report_filename = f'yolov8_test_{model_name}_{timestamp}.html'
    report_path = reports_dir / report_filename
    
    print(f"\n📝 生成报告...")
    generate_detection_report(detections_data, model_name, report_path)
    
    # 统计
    total_detections = sum(len(d['boxes']) for d in detections_data)
    images_with_detections = sum(1 for d in detections_data if len(d['boxes']) > 0)
    
    print(f"\n📈 检测统计:")
    print(f"   总图片数: {len(detections_data)}")
    print(f"   有检测结果: {images_with_detections} ({images_with_detections/len(detections_data)*100:.1f}%)")
    print(f"   总检测数: {total_detections}")
    print(f"   平均每张: {total_detections/len(detections_data):.2f} 个")
    
    print(f"\n✅ 完成！")
    print(f"   报告: {report_path}")
    
    return report_path


if __name__ == '__main__':
    main()
