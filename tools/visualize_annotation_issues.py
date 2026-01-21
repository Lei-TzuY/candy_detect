"""
可视化有问题的标注
"""
import os
import json
import cv2
import numpy as np
from pathlib import Path
import shutil

def visualize_problematic_annotations(dataset_dir, report_file='annotation_quality_report.json'):
    """可视化有问题的标注"""
    
    # 读取报告
    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    issues = report['issues']
    
    # 创建输出目录
    output_dir = Path('annotation_issues_visualization')
    output_dir.mkdir(exist_ok=True)
    
    dataset_path = Path(dataset_dir)
    images_dir = dataset_path / 'images'
    labels_dir = dataset_path / 'labels'
    
    print("=" * 70)
    print("🖼️  可视化有问题的标注")
    print("=" * 70)
    
    # 1. 处理超出边界的标注
    if issues['out_of_bounds']:
        out_dir = output_dir / '1_out_of_bounds'
        out_dir.mkdir(exist_ok=True)
        
        print(f"\n📦 处理超出边界的标注 ({len(issues['out_of_bounds'])} 个)...")
        
        # 按图片分组
        img_issues = {}
        for item in issues['out_of_bounds']:
            img_name = item['image']
            if img_name not in img_issues:
                img_issues[img_name] = []
            img_issues[img_name].append(item['box'])
        
        for idx, (img_name, boxes) in enumerate(img_issues.items()):
            if idx >= 20:  # 只处理前 20 张
                break
            
            img_path = images_dir / img_name
            if not img_path.exists():
                continue
            
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            
            h, w = img.shape[:2]
            
            # 绘制所有标注
            label_path = labels_dir / (img_path.stem + '.txt')
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
                            
                            # 检查是否超出边界
                            is_out = (x_center - box_w/2 < 0 or 
                                     y_center - box_h/2 < 0 or 
                                     x_center + box_w/2 > 1 or 
                                     y_center + box_h/2 > 1)
                            
                            color = (0, 0, 255) if is_out else (0, 255, 0)  # 红色=有问题，绿色=正常
                            thickness = 3 if is_out else 1
                            
                            cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
                            
                            # 标签
                            label = f"{'N' if class_id == 0 else 'A'}"
                            if is_out:
                                label += " OUT"
                            cv2.putText(img, label, (x1, y1-5), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # 保存
            output_path = out_dir / f"{idx+1:03d}_{img_name}"
            cv2.imwrite(str(output_path), img)
        
        print(f"   ✅ 已保存 {min(len(img_issues), 20)} 张图片到 {out_dir}")
    
    # 2. 处理过大的边界框
    if issues['too_large']:
        large_dir = output_dir / '2_too_large'
        large_dir.mkdir(exist_ok=True)
        
        print(f"\n📦 处理过大的边界框 ({len(issues['too_large'])} 个)...")
        
        for idx, item in enumerate(issues['too_large'][:10]):
            img_name = item['image']
            img_path = images_dir / img_name
            
            if not img_path.exists():
                continue
            
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            
            h, w = img.shape[:2]
            box = item['box']
            
            # 绘制
            x1 = int((box['x_center'] - box['width']/2) * w)
            y1 = int((box['y_center'] - box['height']/2) * h)
            x2 = int((box['x_center'] + box['width']/2) * w)
            y2 = int((box['y_center'] + box['height']/2) * h)
            
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            label = f"Area: {item['area_percent']:.1f}%"
            cv2.putText(img, label, (x1, y1-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            output_path = large_dir / f"{idx+1:03d}_{img_name}"
            cv2.imwrite(str(output_path), img)
        
        print(f"   ✅ 已保存 {min(len(issues['too_large']), 10)} 张图片到 {large_dir}")
    
    # 3. 处理长宽比异常
    if issues['abnormal_aspect']:
        aspect_dir = output_dir / '3_abnormal_aspect'
        aspect_dir.mkdir(exist_ok=True)
        
        print(f"\n📦 处理长宽比异常 ({len(issues['abnormal_aspect'])} 个)...")
        
        for idx, item in enumerate(issues['abnormal_aspect'][:10]):
            img_name = item['image']
            img_path = images_dir / img_name
            
            if not img_path.exists():
                continue
            
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            
            h, w = img.shape[:2]
            box = item['box']
            
            x1 = int((box['x_center'] - box['width']/2) * w)
            y1 = int((box['y_center'] - box['height']/2) * h)
            x2 = int((box['x_center'] + box['width']/2) * w)
            y2 = int((box['y_center'] + box['height']/2) * h)
            
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            label = f"Ratio: {item['aspect_ratio']:.2f}"
            cv2.putText(img, label, (x1, y1-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            
            output_path = aspect_dir / f"{idx+1:03d}_{img_name}"
            cv2.imwrite(str(output_path), img)
        
        print(f"   ✅ 已保存 {min(len(issues['abnormal_aspect']), 10)} 张图片到 {aspect_dir}")
    
    # 4. 处理标注过多的图片
    if issues['too_many_boxes']:
        many_dir = output_dir / '4_too_many_boxes'
        many_dir.mkdir(exist_ok=True)
        
        print(f"\n📦 处理标注过多的图片 ({len(issues['too_many_boxes'])} 张)...")
        
        for idx, item in enumerate(sorted(issues['too_many_boxes'], 
                                         key=lambda x: x['count'], reverse=True)[:10]):
            img_name = item['image']
            img_path = images_dir / img_name
            
            if not img_path.exists():
                continue
            
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            
            h, w = img.shape[:2]
            
            # 绘制所有标注
            label_path = labels_dir / (img_path.stem + '.txt')
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
                            
                            x1 = int((x_center - box_w/2) * w)
                            y1 = int((y_center - box_h/2) * h)
                            x2 = int((x_center + box_w/2) * w)
                            y2 = int((y_center + box_h/2) * h)
                            
                            color = (0, 255, 0) if class_id == 0 else (0, 255, 255)
                            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            # 添加计数
            cv2.putText(img, f"Total: {item['count']} boxes", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            output_path = many_dir / f"{idx+1:03d}_{img_name}"
            cv2.imwrite(str(output_path), img)
        
        print(f"   ✅ 已保存 {min(len(issues['too_many_boxes']), 10)} 张图片到 {many_dir}")
    
    # 创建 HTML 索引
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>标注问题可视化</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .section { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .section h2 { color: #d32f2f; margin-top: 0; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .item { border: 1px solid #ddd; padding: 10px; background: #fafafa; }
        .item img { width: 100%; height: auto; }
        .item p { margin: 5px 0; font-size: 14px; color: #666; }
        .stats { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .stats p { margin: 5px 0; }
    </style>
</head>
<body>
    <h1>🔍 标注问题可视化</h1>
    <div class="stats">
        <p><strong>数据集:</strong> """ + dataset_dir + """</p>
        <p><strong>总图片:</strong> """ + str(report['stats']['total_images']) + """</p>
        <p><strong>总标注框:</strong> """ + str(report['stats']['total_boxes']) + """</p>
        <p><strong>有问题的图片:</strong> """ + str(report['stats']['images_with_issues']) + """</p>
    </div>
"""
    
    if issues['out_of_bounds']:
        html_content += """
    <div class="section">
        <h2>❌ 边界框超出范围 (""" + str(len(issues['out_of_bounds'])) + """ 个)</h2>
        <p>这些标注的边界框超出了图片范围，需要修正！</p>
        <div class="gallery">
"""
        for idx, img_file in enumerate(sorted((output_dir / '1_out_of_bounds').glob('*.jpg'))[:20]):
            html_content += f"""
            <div class="item">
                <img src="1_out_of_bounds/{img_file.name}" alt="{img_file.name}">
                <p>{img_file.name}</p>
            </div>
"""
        html_content += """
        </div>
    </div>
"""
    
    if issues['too_large']:
        html_content += """
    <div class="section">
        <h2>⚠️  边界框过大 (""" + str(len(issues['too_large'])) + """ 个)</h2>
        <p>这些边界框占据了图片的大部分面积，可能是误标。</p>
        <div class="gallery">
"""
        for idx, img_file in enumerate(sorted((output_dir / '2_too_large').glob('*.jpg'))[:10]):
            html_content += f"""
            <div class="item">
                <img src="2_too_large/{img_file.name}" alt="{img_file.name}">
                <p>{img_file.name}</p>
            </div>
"""
        html_content += """
        </div>
    </div>
"""
    
    if issues['abnormal_aspect']:
        html_content += """
    <div class="section">
        <h2>⚠️  长宽比异常 (""" + str(len(issues['abnormal_aspect'])) + """ 个)</h2>
        <p>这些边界框的长宽比异常（太宽或太窄）。</p>
        <div class="gallery">
"""
        for idx, img_file in enumerate(sorted((output_dir / '3_abnormal_aspect').glob('*.jpg'))[:10]):
            html_content += f"""
            <div class="item">
                <img src="3_abnormal_aspect/{img_file.name}" alt="{img_file.name}">
                <p>{img_file.name}</p>
            </div>
"""
        html_content += """
        </div>
    </div>
"""
    
    if issues['too_many_boxes']:
        html_content += """
    <div class="section">
        <h2>⚠️  标注框过多 (""" + str(len(issues['too_many_boxes'])) + """ 张)</h2>
        <p>这些图片有超过 5 个标注框，可能是重复标注。</p>
        <div class="gallery">
"""
        for idx, img_file in enumerate(sorted((output_dir / '4_too_many_boxes').glob('*.jpg'))[:10]):
            html_content += f"""
            <div class="item">
                <img src="4_too_many_boxes/{img_file.name}" alt="{img_file.name}">
                <p>{img_file.name}</p>
            </div>
"""
        html_content += """
        </div>
    </div>
"""
    
    html_content += """
</body>
</html>
"""
    
    # 保存 HTML
    html_path = output_dir / 'index.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n{'=' * 70}")
    print(f"✅ 可视化完成！")
    print(f"📂 输出目录: {output_dir}")
    print(f"🌐 查看报告: {html_path}")
    print(f"{'=' * 70}")
    
    return output_dir

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='可视化有问题的标注')
    parser.add_argument('--dataset', type=str, 
                        default='datasets/candy_merged_20260116_154158',
                        help='数据集目录路径')
    parser.add_argument('--report', type=str,
                        default='annotation_quality_report.json',
                        help='质量检查报告文件')
    
    args = parser.parse_args()
    
    output_dir = visualize_problematic_annotations(args.dataset, args.report)
    
    # 自动打开浏览器
    import webbrowser
    import time
    time.sleep(1)
    webbrowser.open(str(output_dir / 'index.html'))
