"""
生成圖像標記的完整可視化報告
包含統計數據、可視化圖片和HTML報告
"""
import cv2
from pathlib import Path
from PIL import Image
import numpy as np
from tqdm import tqdm
import json
from datetime import datetime
import shutil


def load_yolo_annotations(label_file, img_width, img_height):
    """加载YOLO格式标注并转换为像素坐标"""
    annotations = []
    
    if not label_file.exists():
        return annotations
    
    with open(label_file, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                class_id = int(parts[0])
                x_center = float(parts[1]) * img_width
                y_center = float(parts[2]) * img_height
                width = float(parts[3]) * img_width
                height = float(parts[4]) * img_height
                
                x1 = int(x_center - width / 2)
                y1 = int(y_center - height / 2)
                x2 = int(x_center + width / 2)
                y2 = int(y_center + height / 2)
                
                annotations.append({
                    'class_id': class_id,
                    'bbox': (x1, y1, x2, y2),
                    'width': width,
                    'height': height,
                    'area': width * height
                })
    
    return annotations


def draw_annotations(image, annotations, class_names=['normal', 'abnormal']):
    """在图片上绘制标注框"""
    colors = {
        0: (0, 255, 0),    # 绿色 - normal
        1: (0, 0, 255)     # 红色 - abnormal
    }
    
    for ann in annotations:
        class_id = ann['class_id']
        x1, y1, x2, y2 = ann['bbox']
        
        color = colors.get(class_id, (255, 255, 255))
        
        # 绘制边界框
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        
        # 绘制标签
        label = class_names[class_id] if class_id < len(class_names) else f"class_{class_id}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        
        # 标签背景
        cv2.rectangle(image, 
                     (x1, y1 - label_size[1] - 10), 
                     (x1 + label_size[0] + 10, y1), 
                     color, -1)
        
        # 标签文字
        cv2.putText(image, label, 
                   (x1 + 5, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   0.6, (255, 255, 255), 2)
    
    return image


def generate_statistics(dataset_dir, class_names=['normal', 'abnormal']):
    """生成详细的统计数据"""
    dataset_dir = Path(dataset_dir)
    images_dir = dataset_dir / 'images'
    labels_dir = dataset_dir / 'labels'
    
    # 获取所有图片
    image_files = list(images_dir.glob('*.jpg')) + \
                  list(images_dir.glob('*.jpeg')) + \
                  list(images_dir.glob('*.png'))
    
    stats = {
        'dataset_name': dataset_dir.name,
        'total_images': len(image_files),
        'images_with_annotations': 0,
        'images_without_annotations': 0,
        'total_boxes': 0,
        'class_distribution': {name: 0 for name in class_names},
        'box_sizes': [],
        'boxes_per_image': [],
        'image_details': []
    }
    
    for img_file in tqdm(image_files, desc="分析标注"):
        try:
            # 读取图片尺寸
            pil_img = Image.open(img_file)
            img_width, img_height = pil_img.size
            
            # 读取标注
            label_file = labels_dir / f"{img_file.stem}.txt"
            annotations = load_yolo_annotations(label_file, img_width, img_height)
            
            num_boxes = len(annotations)
            stats['boxes_per_image'].append(num_boxes)
            
            if annotations:
                stats['images_with_annotations'] += 1
                stats['total_boxes'] += num_boxes
                
                for ann in annotations:
                    class_id = ann['class_id']
                    if class_id < len(class_names):
                        stats['class_distribution'][class_names[class_id]] += 1
                    
                    stats['box_sizes'].append(ann['area'])
                
                stats['image_details'].append({
                    'filename': img_file.name,
                    'boxes': num_boxes,
                    'has_normal': any(ann['class_id'] == 0 for ann in annotations),
                    'has_abnormal': any(ann['class_id'] == 1 for ann in annotations)
                })
            else:
                stats['images_without_annotations'] += 1
                stats['image_details'].append({
                    'filename': img_file.name,
                    'boxes': 0,
                    'has_normal': False,
                    'has_abnormal': False
                })
        
        except Exception as e:
            print(f"⚠️  处理失败: {img_file.name} - {e}")
    
    # 计算统计指标
    if stats['boxes_per_image']:
        stats['avg_boxes_per_image'] = np.mean(stats['boxes_per_image'])
        stats['median_boxes_per_image'] = np.median(stats['boxes_per_image'])
        stats['max_boxes_per_image'] = max(stats['boxes_per_image'])
        stats['min_boxes_per_image'] = min(stats['boxes_per_image'])
    
    if stats['box_sizes']:
        stats['avg_box_size'] = np.mean(stats['box_sizes'])
        stats['median_box_size'] = np.median(stats['box_sizes'])
    
    return stats


def generate_visualizations(dataset_dir, output_dir, max_images=None):
    """生成可视化图片"""
    dataset_dir = Path(dataset_dir)
    output_dir = Path(output_dir)
    images_dir = dataset_dir / 'images'
    labels_dir = dataset_dir / 'labels'
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取所有图片
    image_files = list(images_dir.glob('*.jpg')) + \
                  list(images_dir.glob('*.jpeg')) + \
                  list(images_dir.glob('*.png'))
    
    if max_images:
        image_files = image_files[:max_images]
    
    vis_files = []
    
    for img_file in tqdm(image_files, desc="生成可视化"):
        try:
            # 使用PIL读取图片（支持中文路径）
            pil_img = Image.open(img_file)
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            img_height, img_width = img.shape[:2]
            
            # 读取标注
            label_file = labels_dir / f"{img_file.stem}.txt"
            annotations = load_yolo_annotations(label_file, img_width, img_height)
            
            if annotations:
                # 绘制标注
                img = draw_annotations(img, annotations)
            else:
                # 添加"无标注"水印
                cv2.putText(img, "No Annotations", 
                           (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 
                           1.0, (0, 0, 255), 2)
            
            # 保存可视化图片
            output_file = output_dir / f"{img_file.stem}_vis.jpg"
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_output = Image.fromarray(img_rgb)
            pil_output.save(output_file, 'JPEG', quality=90)
            
            vis_files.append({
                'original': img_file.name,
                'visualization': f"visualizations/{output_file.name}",
                'num_boxes': len(annotations)
            })
            
        except Exception as e:
            print(f"⚠️  处理失败: {img_file.name} - {e}")
    
    return vis_files


def generate_html_report(stats, vis_files, output_file):
    """生成HTML报告"""
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>圖像標記報告 - {stats['dataset_name']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft JhengHei', 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .timestamp {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }}
        
        .stat-label {{
            color: #666;
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
        
        .stat-subvalue {{
            color: #888;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        .class-distribution {{
            padding: 40px;
        }}
        
        .class-bars {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .class-bar {{
            background: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
            position: relative;
        }}
        
        .class-bar-fill {{
            height: 50px;
            display: flex;
            align-items: center;
            padding: 0 20px;
            color: white;
            font-weight: bold;
            transition: width 1s ease-out;
        }}
        
        .normal-bar {{
            background: linear-gradient(90deg, #4ade80, #22c55e);
        }}
        
        .abnormal-bar {{
            background: linear-gradient(90deg, #f87171, #ef4444);
        }}
        
        .gallery {{
            padding: 40px;
        }}
        
        .gallery h2 {{
            margin-bottom: 30px;
            color: #333;
            font-size: 2em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 30px;
        }}
        
        .image-card {{
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .image-card:hover {{
            transform: scale(1.05);
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
        }}
        
        .image-card img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        
        .image-info {{
            padding: 15px;
            background: #f8f9fa;
        }}
        
        .image-filename {{
            font-size: 0.85em;
            color: #666;
            word-break: break-all;
            margin-bottom: 5px;
        }}
        
        .image-boxes {{
            font-weight: bold;
            color: #667eea;
        }}
        
        footer {{
            background: #2d3748;
            color: white;
            text-align: center;
            padding: 20px;
        }}
        
        .filter-buttons {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            background: #667eea;
            color: white;
            cursor: pointer;
            transition: background 0.3s;
        }}
        
        .filter-btn:hover {{
            background: #5568d3;
        }}
        
        .filter-btn.active {{
            background: #4c51bf;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 圖像標記報告</h1>
            <div class="timestamp">生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div class="timestamp">資料集: {stats['dataset_name']}</div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">總圖片數</div>
                <div class="stat-value">{stats['total_images']}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">已標記</div>
                <div class="stat-value">{stats['images_with_annotations']}</div>
                <div class="stat-subvalue">{stats['images_with_annotations']/stats['total_images']*100:.1f}%</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">未標記</div>
                <div class="stat-value">{stats['images_without_annotations']}</div>
                <div class="stat-subvalue">{stats['images_without_annotations']/stats['total_images']*100:.1f}%</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">總標記框</div>
                <div class="stat-value">{stats['total_boxes']}</div>
                <div class="stat-subvalue">平均 {stats.get('avg_boxes_per_image', 0):.2f} 個/張</div>
            </div>
        </div>
        
        <div class="class-distribution">
            <h2>📊 類別分布</h2>
            <div class="class-bars">
"""
    
    # 添加类别分布条形图
    max_count = max(stats['class_distribution'].values()) if stats['class_distribution'] else 1
    
    for class_name, count in stats['class_distribution'].items():
        percentage = (count / stats['total_boxes'] * 100) if stats['total_boxes'] > 0 else 0
        bar_width = (count / max_count * 100) if max_count > 0 else 0
        bar_class = 'normal-bar' if class_name == 'normal' else 'abnormal-bar'
        
        html_content += f"""
                <div class="class-bar">
                    <div class="class-bar-fill {bar_class}" style="width: {bar_width}%">
                        {class_name.upper()}: {count} ({percentage:.1f}%)
                    </div>
                </div>
"""
    
    html_content += """
            </div>
        </div>
        
        <div class="gallery">
            <h2>🖼️ 可視化圖片</h2>
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="filterImages('all')">全部</button>
                <button class="filter-btn" onclick="filterImages('annotated')">已標記</button>
                <button class="filter-btn" onclick="filterImages('empty')">未標記</button>
            </div>
            <div class="image-grid" id="imageGrid">
"""
    
    # 添加可视化图片
    for vis in vis_files:
        has_boxes = vis['num_boxes'] > 0
        data_filter = 'annotated' if has_boxes else 'empty'
        
        html_content += f"""
                <div class="image-card" data-filter="{data_filter}">
                    <img src="{vis['visualization']}" alt="{vis['original']}" loading="lazy">
                    <div class="image-info">
                        <div class="image-filename">{vis['original']}</div>
                        <div class="image-boxes">{vis['num_boxes']} 個標記框</div>
                    </div>
                </div>
"""
    
    html_content += """
            </div>
        </div>
        
        <footer>
            <p>© 2026 Candy Detection System - 自動生成的報告</p>
        </footer>
    </div>
    
    <script>
        function filterImages(filter) {
            const cards = document.querySelectorAll('.image-card');
            const buttons = document.querySelectorAll('.filter-btn');
            
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            cards.forEach(card => {
                if (filter === 'all' || card.dataset.filter === filter) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""
    
    # 写入HTML文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_report(dataset_dir, output_dir=None, max_images=None):
    """生成完整的可视化报告"""
    dataset_dir = Path(dataset_dir)
    
    if output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = dataset_dir.parent / f"annotation_report_{timestamp}"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("📊 生成圖像標記報告")
    print("=" * 70)
    print(f"資料集: {dataset_dir}")
    print(f"輸出目錄: {output_dir}")
    print("-" * 70)
    
    # 1. 生成统计数据
    print("\n步驟 1/3: 分析標記數據...")
    stats = generate_statistics(dataset_dir)
    
    # 保存统计数据为JSON
    stats_file = output_dir / 'statistics.json'
    with open(stats_file, 'w', encoding='utf-8') as f:
        # 转换numpy类型为Python原生类型
        stats_copy = stats.copy()
        for key in ['avg_boxes_per_image', 'median_boxes_per_image', 
                    'avg_box_size', 'median_box_size']:
            if key in stats_copy:
                stats_copy[key] = float(stats_copy[key])
        stats_copy['boxes_per_image'] = [int(x) for x in stats_copy.get('boxes_per_image', [])]
        stats_copy['box_sizes'] = [float(x) for x in stats_copy.get('box_sizes', [])]
        
        json.dump(stats_copy, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 統計數據已保存: {stats_file}")
    
    # 2. 生成可视化图片
    print("\n步驟 2/3: 生成可視化圖片...")
    vis_dir = output_dir / 'visualizations'
    vis_files = generate_visualizations(dataset_dir, vis_dir, max_images)
    print(f"✅ 生成 {len(vis_files)} 張可視化圖片")
    
    # 3. 生成HTML报告
    print("\n步驟 3/3: 生成HTML報告...")
    html_file = output_dir / 'index.html'
    generate_html_report(stats, vis_files, html_file)
    print(f"✅ HTML報告已生成: {html_file}")
    
    # 显示摘要
    print("\n" + "=" * 70)
    print("✅ 報告生成完成！")
    print("=" * 70)
    print(f"📁 輸出目錄: {output_dir}")
    print(f"📊 統計數據: {stats_file}")
    print(f"🌐 HTML報告: {html_file}")
    print(f"🖼️  可視化圖片: {vis_dir}")
    print("-" * 70)
    print(f"總圖片數: {stats['total_images']}")
    print(f"已標記: {stats['images_with_annotations']} ({stats['images_with_annotations']/stats['total_images']*100:.1f}%)")
    print(f"總標記框: {stats['total_boxes']}")
    print(f"平均每張: {stats.get('avg_boxes_per_image', 0):.2f} 個框")
    print("\n類別分布:")
    for class_name, count in stats['class_distribution'].items():
        percentage = (count / stats['total_boxes'] * 100) if stats['total_boxes'] > 0 else 0
        print(f"  - {class_name}: {count} ({percentage:.1f}%)")
    print("=" * 70)
    
    return output_dir


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="生成圖像標記的完整可視化報告")
    parser.add_argument("--dataset", "-d", 
                       default=r"d:\專案\candy\datasets\candy_merged_20260116_154158",
                       help="數據集目錄")
    parser.add_argument("--output", "-o", help="輸出目錄（可選）")
    parser.add_argument("--max", "-m", type=int, help="最大處理圖片數（用於快速預覽）")
    parser.add_argument("--open", action="store_true", help="完成後打開HTML報告")
    
    args = parser.parse_args()
    
    output_dir = generate_report(args.dataset, args.output, args.max)
    
    if args.open:
        import subprocess
        import webbrowser
        html_file = output_dir / 'index.html'
        webbrowser.open(str(html_file))
