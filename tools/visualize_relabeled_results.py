"""
可视化重新标记后的结果
"""
import os
import cv2
import numpy as np
from pathlib import Path
import random

def visualize_relabeled_results(dataset_dir, num_samples=50, output_dir='relabeled_visualization'):
    """可视化重新标记的结果"""
    
    dataset_path = Path(dataset_dir)
    images_dir = dataset_path / 'images'
    labels_dir = dataset_path / 'labels'
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print("=" * 70)
    print("🖼️  可视化重新标记结果")
    print("=" * 70)
    print(f"\n📁 数据集: {dataset_dir}")
    print(f"📂 输出目录: {output_dir}")
    
    # 获取所有图片
    image_files = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.png'))
    
    # 随机抽样
    if len(image_files) > num_samples:
        sampled_files = random.sample(image_files, num_samples)
    else:
        sampled_files = image_files
    
    print(f"\n🎲 从 {len(image_files)} 张图片中随机抽样 {len(sampled_files)} 张")
    print("\n开始可视化...")
    
    class_names = ['normal', 'abnormal']
    class_colors = [(0, 255, 0), (0, 0, 255)]  # 绿色=normal, 红色=abnormal
    
    stats = {
        'total_boxes': 0,
        'class_counts': {0: 0, 1: 0},
        'images_with_boxes': 0,
        'boxes_per_image': []
    }
    
    for idx, img_path in enumerate(sampled_files):
        if (idx + 1) % 10 == 0:
            print(f"   进度: {idx + 1}/{len(sampled_files)}")
        
        # 读取图片
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        
        h, w = img.shape[:2]
        
        # 读取标注
        label_path = labels_dir / (img_path.stem + '.txt')
        
        box_count = 0
        if label_path.exists():
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        box_w = float(parts[3])
                        box_h = float(parts[4])
                        
                        # 转换为像素坐标
                        x1 = int((x_center - box_w/2) * w)
                        y1 = int((y_center - box_h/2) * h)
                        x2 = int((x_center + box_w/2) * w)
                        y2 = int((y_center + box_h/2) * h)
                        
                        # 绘制边界框
                        color = class_colors[class_id]
                        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                        
                        # 添加标签
                        label_text = class_names[class_id]
                        label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                        
                        # 背景矩形
                        cv2.rectangle(img, (x1, y1 - label_size[1] - 5), 
                                    (x1 + label_size[0], y1), color, -1)
                        
                        # 文字
                        cv2.putText(img, label_text, (x1, y1 - 5), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        
                        box_count += 1
                        stats['total_boxes'] += 1
                        stats['class_counts'][class_id] += 1
        
        if box_count > 0:
            stats['images_with_boxes'] += 1
            stats['boxes_per_image'].append(box_count)
        
        # 添加信息文字
        info_text = f"Boxes: {box_count}"
        cv2.putText(img, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(img, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
        
        # 保存
        output_file = output_path / f"{idx+1:03d}_{img_path.name}"
        cv2.imwrite(str(output_file), img)
    
    # 生成 HTML
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>重新标记结果检查</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: #f5f5f5; 
        }
        h1 { 
            color: #2e7d32; 
            text-align: center;
        }
        .stats {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stats h2 {
            margin-top: 0;
            color: #1976d2;
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .stat-item {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #1976d2;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .legend {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin: 20px 0;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .legend-box {
            width: 20px;
            height: 20px;
            border: 2px solid;
        }
        .normal { border-color: #00ff00; background: rgba(0, 255, 0, 0.2); }
        .abnormal { border-color: #ff0000; background: rgba(255, 0, 0, 0.2); }
        .gallery { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); 
            gap: 20px;
            margin-top: 20px;
        }
        .item { 
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .item:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .item img { 
            width: 100%; 
            height: auto;
            display: block;
        }
        .item .info { 
            padding: 10px; 
            font-size: 14px; 
            color: #666;
            background: #fafafa;
        }
        .controls {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }
        .controls button {
            background: #1976d2;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 0 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .controls button:hover {
            background: #1565c0;
        }
    </style>
</head>
<body>
    <h1>🎯 重新标记结果检查</h1>
    
    <div class="stats">
        <h2>📊 统计信息</h2>
        <div class="stat-grid">
            <div class="stat-item">
                <div class="stat-value">""" + str(len(sampled_files)) + """</div>
                <div class="stat-label">抽样图片数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">""" + str(stats['images_with_boxes']) + """</div>
                <div class="stat-label">有标注的图片</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">""" + str(stats['total_boxes']) + """</div>
                <div class="stat-label">总标注框数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">""" + f"{np.mean(stats['boxes_per_image']):.1f}" if stats['boxes_per_image'] else "0" + """</div>
                <div class="stat-label">平均每张标注数</div>
            </div>
        </div>
        
        <div class="stat-grid" style="margin-top: 20px;">
            <div class="stat-item">
                <div class="stat-value" style="color: #2e7d32;">""" + str(stats['class_counts'][0]) + """</div>
                <div class="stat-label">Normal 糖果</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" style="color: #c62828;">""" + str(stats['class_counts'][1]) + """</div>
                <div class="stat-label">Abnormal 糖果</div>
            </div>
        </div>
    </div>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-box normal"></div>
            <span>Normal（正常糖果）</span>
        </div>
        <div class="legend-item">
            <div class="legend-box abnormal"></div>
            <span>Abnormal（异常糖果）</span>
        </div>
    </div>
    
    <div class="controls">
        <button onclick="window.scrollTo(0, 0)">⬆️ 回到顶部</button>
        <button onclick="filterClass('all')">全部显示</button>
        <button onclick="filterClass('normal')">只显示 Normal</button>
        <button onclick="filterClass('abnormal')">只显示 Abnormal</button>
    </div>
    
    <div class="gallery" id="gallery">
"""
    
    # 添加图片
    for idx, img_file in enumerate(sorted(output_path.glob('*.jpg')) + sorted(output_path.glob('*.png'))):
        html_content += f"""
        <div class="item" data-class="all">
            <img src="{img_file.name}" alt="{img_file.name}">
            <div class="info">{img_file.name}</div>
        </div>
"""
    
    html_content += """
    </div>
    
    <script>
        function filterClass(className) {
            // 这是简化版，实际需要根据图片内容过滤
            // 这里只是展示所有图片
            console.log('Filter:', className);
        }
    </script>
</body>
</html>
"""
    
    # 保存 HTML
    html_path = output_path / 'index.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n{'=' * 70}")
    print("✅ 可视化完成！")
    print(f"{'=' * 70}")
    print(f"\n📊 统计结果:")
    print(f"   抽样图片: {len(sampled_files)} 张")
    print(f"   有标注的图片: {stats['images_with_boxes']} 张")
    print(f"   总标注框: {stats['total_boxes']} 个")
    if stats['boxes_per_image']:
        print(f"   平均每张: {np.mean(stats['boxes_per_image']):.1f} 个")
        print(f"   最多: {max(stats['boxes_per_image'])} 个")
        print(f"   最少: {min(stats['boxes_per_image'])} 个")
    print(f"\n   Normal: {stats['class_counts'][0]} 个")
    print(f"   Abnormal: {stats['class_counts'][1]} 个")
    print(f"\n🌐 打开查看: {html_path}")
    print(f"{'=' * 70}")
    
    return html_path

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='可视化重新标记结果')
    parser.add_argument('--dataset', type=str, 
                        default='datasets/candy_merged_20260116_154158',
                        help='数据集目录路径')
    parser.add_argument('--samples', type=int, default=50,
                        help='随机抽样数量')
    parser.add_argument('--output', type=str, default='relabeled_visualization',
                        help='输出目录')
    
    args = parser.parse_args()
    
    html_path = visualize_relabeled_results(args.dataset, args.samples, args.output)
    
    # 自动打开浏览器
    import webbrowser
    import time
    time.sleep(1)
    webbrowser.open(str(html_path))
