"""
检查所有训练数据并生成可视化汇总
"""
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
from collections import defaultdict
from datetime import datetime


def load_yolo_annotations(label_file, img_width, img_height):
    """加载 YOLO 格式标注"""
    annotations = []
    if label_file.exists():
        with open(label_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 5:
                    class_id, x_center, y_center, width, height = map(float, parts)
                    
                    # 转换为像素坐标
                    x_center *= img_width
                    y_center *= img_height
                    width *= img_width
                    height *= img_height
                    
                    x1 = int(x_center - width / 2)
                    y1 = int(y_center - height / 2)
                    x2 = int(x_center + width / 2)
                    y2 = int(y_center + height / 2)
                    
                    annotations.append({
                        'class_id': int(class_id),
                        'bbox': (x1, y1, x2, y2)
                    })
    return annotations


def draw_annotations_on_image(img_path, annotations, class_names):
    """在图片上绘制标注"""
    try:
        pil_img = Image.open(img_path).convert('RGB')
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        for ann in annotations:
            x1, y1, x2, y2 = ann['bbox']
            class_id = ann['class_id']
            class_name = class_names.get(class_id, f'Class {class_id}')
            
            # 绘制边界框
            color = (0, 255, 0) if class_id == 0 else (0, 0, 255)  # normal=绿色, abnormal=红色
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签
            label = f"{class_name}"
            cv2.putText(img, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return img
    except Exception as e:
        print(f"⚠️  无法处理图片 {img_path.name}: {e}")
        return None


def check_training_data(project_root):
    """检查所有训练数据"""
    project_root = Path(project_root)
    images_dir = project_root / 'datasets' / 'extracted_frames'
    labels_dir = project_root / 'datasets' / 'annotated' / 'labels'
    output_dir = project_root / 'reports' / f'training_data_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    
    output_dir.mkdir(parents=True, exist_ok=True)
    vis_dir = output_dir / 'visualizations'
    vis_dir.mkdir(exist_ok=True)
    
    class_names = {0: 'normal', 1: 'abnormal'}
    
    print("🔍 扫描训练数据...")
    print(f"图片目录: {images_dir}")
    print(f"标签目录: {labels_dir}")
    print("-" * 60)
    
    # 统计信息
    stats = {
        'total_images': 0,
        'labeled_images': 0,
        'unlabeled_images': 0,
        'total_annotations': 0,
        'class_distribution': defaultdict(int),
        'folders': defaultdict(lambda: {'total': 0, 'labeled': 0, 'annotations': 0})
    }
    
    labeled_images = []
    unlabeled_images = []
    
    # 扫描所有图片
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    for img_file in images_dir.rglob('*'):
        if img_file.suffix.lower() in image_extensions:
            stats['total_images'] += 1
            
            # 获取相对路径
            rel_path = img_file.relative_to(images_dir)
            folder_name = rel_path.parts[0] if len(rel_path.parts) > 1 else 'root'
            
            # 对应的标签文件
            label_file = labels_dir / rel_path.parent / f"{img_file.stem}.txt"
            
            stats['folders'][folder_name]['total'] += 1
            
            if label_file.exists() and label_file.stat().st_size > 0:
                # 有标注
                stats['labeled_images'] += 1
                stats['folders'][folder_name]['labeled'] += 1
                
                # 读取标注
                try:
                    pil_img = Image.open(img_file)
                    w, h = pil_img.size
                    annotations = load_yolo_annotations(label_file, w, h)
                    
                    stats['total_annotations'] += len(annotations)
                    stats['folders'][folder_name]['annotations'] += len(annotations)
                    
                    for ann in annotations:
                        stats['class_distribution'][ann['class_id']] += 1
                    
                    labeled_images.append({
                        'path': img_file,
                        'rel_path': rel_path,
                        'folder': folder_name,
                        'annotations': annotations,
                        'width': w,
                        'height': h
                    })
                except Exception as e:
                    print(f"⚠️  读取标注失败: {rel_path} - {e}")
            else:
                # 无标注
                stats['unlabeled_images'] += 1
                unlabeled_images.append({
                    'path': img_file,
                    'rel_path': rel_path,
                    'folder': folder_name
                })
    
    # 显示统计
    print("\n" + "=" * 60)
    print("📊 训练数据统计")
    print("=" * 60)
    print(f"总图片数: {stats['total_images']}")
    print(f"已标注: {stats['labeled_images']} ({stats['labeled_images']/stats['total_images']*100:.1f}%)")
    print(f"未标注: {stats['unlabeled_images']} ({stats['unlabeled_images']/stats['total_images']*100:.1f}%)")
    print(f"总标注数: {stats['total_annotations']}")
    print(f"平均每张: {stats['total_annotations']/max(stats['labeled_images'], 1):.2f}")
    
    print("\n类别分布:")
    for class_id, count in sorted(stats['class_distribution'].items()):
        class_name = class_names.get(class_id, f'Class {class_id}')
        percentage = count / stats['total_annotations'] * 100 if stats['total_annotations'] > 0 else 0
        print(f"  {class_name}: {count} ({percentage:.1f}%)")
    
    print("\n文件夹统计:")
    for folder_name, folder_stats in sorted(stats['folders'].items()):
        labeled_pct = folder_stats['labeled'] / folder_stats['total'] * 100 if folder_stats['total'] > 0 else 0
        print(f"  {folder_name}:")
        print(f"    图片: {folder_stats['total']}")
        print(f"    已标注: {folder_stats['labeled']} ({labeled_pct:.1f}%)")
        print(f"    标注数: {folder_stats['annotations']}")
    
    # 生成可视化样本（每个文件夹随机选10张）
    print("\n" + "=" * 60)
    print("🎨 生成可视化样本...")
    print("=" * 60)
    
    from random import sample
    
    for folder_name in stats['folders'].keys():
        folder_labeled = [img for img in labeled_images if img['folder'] == folder_name]
        
        if folder_labeled:
            # 每个文件夹最多10张
            samples = sample(folder_labeled, min(10, len(folder_labeled)))
            
            folder_vis_dir = vis_dir / folder_name
            folder_vis_dir.mkdir(exist_ok=True)
            
            for img_data in samples:
                vis_img = draw_annotations_on_image(
                    img_data['path'],
                    img_data['annotations'],
                    class_names
                )
                
                if vis_img is not None:
                    output_path = folder_vis_dir / img_data['path'].name
                    vis_img_rgb = cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB)
                    Image.fromarray(vis_img_rgb).save(output_path)
            
            print(f"  {folder_name}: {len(samples)} 张样本")
    
    # 生成 HTML 报告
    html_report = output_dir / 'training_data_report.html'
    
    with open(html_report, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>训练数据汇总报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        .stat-card h3 {{ margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; }}
        .stat-card .value {{ font-size: 32px; font-weight: bold; }}
        .class-dist {{ background: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .class-item {{ display: flex; justify-content: space-between; padding: 10px; margin: 5px 0; background: white; border-radius: 5px; }}
        .folder-stats {{ margin: 20px 0; }}
        .folder-item {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #3498db; border-radius: 5px; }}
        .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
        .gallery img {{ width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.2s; }}
        .gallery img:hover {{ transform: scale(1.05); }}
        .timestamp {{ color: #7f8c8d; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 训练数据汇总报告</h1>
        <p class="timestamp">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📊 总体统计</h2>
        <div class="stats">
            <div class="stat-card">
                <h3>总图片数</h3>
                <div class="value">{stats['total_images']}</div>
            </div>
            <div class="stat-card">
                <h3>已标注</h3>
                <div class="value">{stats['labeled_images']}</div>
                <small>{stats['labeled_images']/max(stats['total_images'], 1)*100:.1f}%</small>
            </div>
            <div class="stat-card">
                <h3>未标注</h3>
                <div class="value">{stats['unlabeled_images']}</div>
                <small>{stats['unlabeled_images']/max(stats['total_images'], 1)*100:.1f}%</small>
            </div>
            <div class="stat-card">
                <h3>总标注数</h3>
                <div class="value">{stats['total_annotations']}</div>
                <small>平均每张: {stats['total_annotations']/max(stats['labeled_images'], 1):.2f}</small>
            </div>
        </div>
        
        <h2>🏷️ 类别分布</h2>
        <div class="class-dist">
""")
        
        for class_id, count in sorted(stats['class_distribution'].items()):
            class_name = class_names.get(class_id, f'Class {class_id}')
            percentage = count / stats['total_annotations'] * 100 if stats['total_annotations'] > 0 else 0
            color = '#27ae60' if class_id == 0 else '#e74c3c'
            f.write(f"""
            <div class="class-item">
                <span><strong style="color: {color}">{class_name}</strong></span>
                <span>{count} 个 ({percentage:.1f}%)</span>
            </div>
""")
        
        f.write("""
        </div>
        
        <h2>📁 文件夹统计</h2>
        <div class="folder-stats">
""")
        
        for folder_name, folder_stats in sorted(stats['folders'].items()):
            labeled_pct = folder_stats['labeled'] / folder_stats['total'] * 100 if folder_stats['total'] > 0 else 0
            f.write(f"""
            <div class="folder-item">
                <h3>{folder_name}</h3>
                <p>图片: {folder_stats['total']} | 已标注: {folder_stats['labeled']} ({labeled_pct:.1f}%) | 标注数: {folder_stats['annotations']}</p>
            </div>
""")
        
        f.write("""
        </div>
        
        <h2>🎨 可视化样本</h2>
""")
        
        for folder_name in stats['folders'].keys():
            folder_vis_dir = vis_dir / folder_name
            if folder_vis_dir.exists():
                f.write(f"""
        <h3>{folder_name}</h3>
        <div class="gallery">
""")
                for img_file in sorted(folder_vis_dir.glob('*')):
                    rel_path = img_file.relative_to(output_dir)
                    f.write(f'            <img src="{rel_path.as_posix()}" alt="{img_file.name}">\n')
                
                f.write("""
        </div>
""")
        
        f.write("""
    </div>
</body>
</html>
""")
    
    print("\n" + "=" * 60)
    print("✅ 报告生成完成！")
    print("=" * 60)
    print(f"📄 HTML 报告: {html_report}")
    print(f"📁 可视化样本: {vis_dir}")
    print(f"📊 输出目录: {output_dir}")
    
    # 保存 JSON 统计
    json_stats = output_dir / 'statistics.json'
    with open(json_stats, 'w', encoding='utf-8') as f:
        json.dump({
            'total_images': stats['total_images'],
            'labeled_images': stats['labeled_images'],
            'unlabeled_images': stats['unlabeled_images'],
            'total_annotations': stats['total_annotations'],
            'class_distribution': dict(stats['class_distribution']),
            'folders': {k: dict(v) for k, v in stats['folders'].items()},
            'generated_at': datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    return html_report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="检查训练数据并生成可视化汇总")
    parser.add_argument("--root", "-r", default=".", help="项目根目录")
    
    args = parser.parse_args()
    
    html_report = check_training_data(args.root)
    
    # 打开报告
    import webbrowser
    webbrowser.open(html_report.as_uri())
