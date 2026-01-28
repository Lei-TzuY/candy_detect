"""
简化的标注质量检查工具 - 支持中文路径
"""
import os
from pathlib import Path
import numpy as np
from collections import defaultdict
import json

def load_yolo_annotation(label_path):
    """加载 YOLO 格式标注"""
    boxes = []
    if not os.path.exists(label_path):
        return boxes
    
    with open(label_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                
                boxes.append({
                    'class_id': class_id,
                    'x_center': x_center,
                    'y_center': y_center,
                    'width': width,
                    'height': height,
                    'area': width * height
                })
    return boxes

def check_annotations(dataset_dir):
    """检查标注质量"""
    
    dataset_path = Path(dataset_dir)
    images_dir = dataset_path / 'images'
    labels_dir = dataset_path / 'labels'
    
    if not images_dir.exists() or not labels_dir.exists():
        print(f"❌ 目录不存在: {images_dir} 或 {labels_dir}")
        return
    
    print("=" * 70)
    print("🔍 标注质量检查（简化版 - 仅检查标注文件）")
    print("=" * 70)
    print(f"\n📁 数据集: {dataset_dir}")
    
    issues = defaultdict(list)
    stats = {
        'total_images': 0,
        'total_boxes': 0,
        'images_with_issues': 0,
        'class_counts': defaultdict(int),
        'area_stats': []
    }
    
    # 获取所有标注文件
    label_files = list(labels_dir.glob('*.txt'))
    
    print(f"\n🖼️  总标注文件数: {len(label_files)}")
    print("\n正在检查...")
    
    for idx, label_path in enumerate(label_files):
        if (idx + 1) % 100 == 0:
            print(f"   进度: {idx + 1}/{len(label_files)}")
        
        stats['total_images'] += 1
        
        # 读取标注
        boxes = load_yolo_annotation(label_path)
        
        # 检查 1: 无标注图片
        if len(boxes) == 0:
            issues['no_annotations'].append(str(label_path.name))
            continue
        
        stats['total_boxes'] += len(boxes)
        has_issue = False
        
        for box in boxes:
            stats['class_counts'][box['class_id']] += 1
            stats['area_stats'].append(box['area'])
            
            # 检查 2: 边界框超出图像范围
            x_min = box['x_center'] - box['width'] / 2
            y_min = box['y_center'] - box['height'] / 2
            x_max = box['x_center'] + box['width'] / 2
            y_max = box['y_center'] + box['height'] / 2
            
            if x_min < 0 or y_min < 0 or x_max > 1 or y_max > 1:
                issues['out_of_bounds'].append({
                    'label': label_path.name,
                    'box': box
                })
                has_issue = True
            
            # 检查 3: 边界框过小（可能是误标）
            if box['area'] < 0.001:  # 小于 0.1%
                issues['too_small'].append({
                    'label': label_path.name,
                    'box': box,
                    'area_percent': box['area'] * 100
                })
                has_issue = True
            
            # 检查 4: 边界框过大（可能是误标）
            if box['area'] > 0.8:  # 大于 80%
                issues['too_large'].append({
                    'label': label_path.name,
                    'box': box,
                    'area_percent': box['area'] * 100
                })
                has_issue = True
            
            # 检查 5: 长宽比异常
            aspect_ratio = box['width'] / box['height'] if box['height'] > 0 else 999
            if aspect_ratio > 5 or aspect_ratio < 0.2:
                issues['abnormal_aspect'].append({
                    'label': label_path.name,
                    'box': box,
                    'aspect_ratio': aspect_ratio
                })
                has_issue = True
        
        # 检查 6: 单张图片标注过多（可能重复标注）
        if len(boxes) > 5:
            issues['too_many_boxes'].append({
                'label': label_path.name,
                'count': len(boxes)
            })
            has_issue = True
        
        if has_issue:
            stats['images_with_issues'] += 1
    
    # 输出结果
    print("\n" + "=" * 70)
    print("📊 统计结果")
    print("=" * 70)
    print(f"\n✅ 总标注文件数: {stats['total_images']}")
    print(f"✅ 总标注框数: {stats['total_boxes']}")
    print(f"⚠️  有问题的文件: {stats['images_with_issues']} ({stats['images_with_issues']/stats['total_images']*100:.1f}%)")
    
    print(f"\n📦 类别分布:")
    for class_id, count in sorted(stats['class_counts'].items()):
        print(f"   类别 {class_id}: {count} 个标注框")
    
    if stats['area_stats']:
        print(f"\n📏 标注框大小统计:")
        print(f"   最小面积: {min(stats['area_stats'])*100:.3f}%")
        print(f"   最大面积: {max(stats['area_stats'])*100:.3f}%")
        print(f"   平均面积: {np.mean(stats['area_stats'])*100:.3f}%")
        print(f"   中位数面积: {np.median(stats['area_stats'])*100:.3f}%")
    
    # 输出问题详情
    print("\n" + "=" * 70)
    print("⚠️  发现的问题")
    print("=" * 70)
    
    total_issues = sum(len(v) for v in issues.values())
    
    if total_issues == 0:
        print("\n✅ 未发现问题！")
    else:
        if 'no_annotations' in issues and issues['no_annotations']:
            print(f"\n❌ 无标注的文件 ({len(issues['no_annotations'])} 个):")
            for name in issues['no_annotations'][:5]:
                print(f"   - {name}")
            if len(issues['no_annotations']) > 5:
                print(f"   ... 还有 {len(issues['no_annotations']) - 5} 个")
        
        if 'out_of_bounds' in issues and issues['out_of_bounds']:
            print(f"\n❌ 边界框超出范围 ({len(issues['out_of_bounds'])} 个):")
            for item in issues['out_of_bounds'][:5]:
                print(f"   - {item['label']}: box center=({item['box']['x_center']:.3f}, {item['box']['y_center']:.3f}), size=({item['box']['width']:.3f}, {item['box']['height']:.3f})")
            if len(issues['out_of_bounds']) > 5:
                print(f"   ... 还有 {len(issues['out_of_bounds']) - 5} 个")
        
        if 'too_small' in issues and issues['too_small']:
            print(f"\n❌ 标注框过小 ({len(issues['too_small'])} 个):")
            for item in issues['too_small'][:5]:
                print(f"   - {item['label']}: {item['area_percent']:.4f}%")
            if len(issues['too_small']) > 5:
                print(f"   ... 还有 {len(issues['too_small']) - 5} 个")
        
        if 'too_large' in issues and issues['too_large']:
            print(f"\n❌ 标注框过大 ({len(issues['too_large'])} 个):")
            for item in issues['too_large'][:5]:
                print(f"   - {item['label']}: {item['area_percent']:.2f}%")
            if len(issues['too_large']) > 5:
                print(f"   ... 还有 {len(issues['too_large']) - 5} 个")
        
        if 'abnormal_aspect' in issues and issues['abnormal_aspect']:
            print(f"\n❌ 长宽比异常 ({len(issues['abnormal_aspect'])} 个):")
            for item in issues['abnormal_aspect'][:5]:
                print(f"   - {item['label']}: 长宽比 {item['aspect_ratio']:.2f}")
            if len(issues['abnormal_aspect']) > 5:
                print(f"   ... 还有 {len(issues['abnormal_aspect']) - 5} 个")
        
        if 'too_many_boxes' in issues and issues['too_many_boxes']:
            print(f"\n❌ 标注框过多 ({len(issues['too_many_boxes'])} 个):")
            for item in issues['too_many_boxes'][:5]:
                print(f"   - {item['label']}: {item['count']} 个标注框")
            if len(issues['too_many_boxes']) > 5:
                print(f"   ... 还有 {len(issues['too_many_boxes']) - 5} 个")
    
    # 保存详细报告
    report_path = 'annotation_quality_report_simple.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'stats': {
                'total_images': stats['total_images'],
                'total_boxes': stats['total_boxes'],
                'images_with_issues': stats['images_with_issues'],
                'class_counts': dict(stats['class_counts'])
            },
            'issues': {k: len(v) for k, v in issues.items()}
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 详细报告已保存: {report_path}")
    
    # 输出建议
    print("\n" + "=" * 70)
    print("💡 建议")
    print("=" * 70)
    
    serious_issues = sum([
        len(issues.get('out_of_bounds', [])),
        len(issues.get('too_large', [])),
        len(issues.get('abnormal_aspect', []))
    ])
    
    if serious_issues == 0:
        print(f"\n✅ 标注质量良好，可以开始训练！")
    else:
        print(f"\n🚨 建议: 发现 {serious_issues} 个严重问题，建议修正后再训练！")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='检查 YOLO 数据集标注质量（简化版）')
    parser.add_argument('--dataset', type=str, 
                        default=r'datasets\最新資料',
                        help='数据集目录路径')
    
    args = parser.parse_args()
    
    check_annotations(args.dataset)
