"""
标注质量检查工具
自动检测可能存在问题的标注
"""
import os
from pathlib import Path
import cv2
import numpy as np
from collections import defaultdict
import json

def load_yolo_annotation(label_path, img_width, img_height):
    """加载 YOLO 格式标注"""
    boxes = []
    if not os.path.exists(label_path):
        return boxes
    
    with open(label_path, 'r') as f:
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
    print("🔍 标注质量检查")
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
    
    image_files = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.png'))
    
    print(f"\n🖼️  总图片数: {len(image_files)}")
    print("\n正在检查...")
    
    for idx, img_path in enumerate(image_files):
        if (idx + 1) % 100 == 0:
            print(f"   进度: {idx + 1}/{len(image_files)}")
        
        stats['total_images'] += 1
        
        # 读取图片尺寸
        img = cv2.imread(str(img_path))
        if img is None:
            issues['corrupted_images'].append(str(img_path))
            continue
        
        h, w = img.shape[:2]
        
        # 读取标注
        label_path = labels_dir / (img_path.stem + '.txt')
        boxes = load_yolo_annotation(label_path, w, h)
        
        # 检查 1: 无标注图片
        if len(boxes) == 0:
            issues['no_annotations'].append(str(img_path.name))
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
                    'image': img_path.name,
                    'box': box
                })
                has_issue = True
            
            # 检查 3: 边界框过小（可能是误标）
            if box['area'] < 0.001:  # 小于 0.1%
                issues['too_small'].append({
                    'image': img_path.name,
                    'box': box,
                    'area_percent': box['area'] * 100
                })
                has_issue = True
            
            # 检查 4: 边界框过大（可能是误标）
            if box['area'] > 0.8:  # 大于 80%
                issues['too_large'].append({
                    'image': img_path.name,
                    'box': box,
                    'area_percent': box['area'] * 100
                })
                has_issue = True
            
            # 检查 5: 长宽比异常
            aspect_ratio = box['width'] / box['height'] if box['height'] > 0 else 999
            if aspect_ratio > 5 or aspect_ratio < 0.2:
                issues['abnormal_aspect'].append({
                    'image': img_path.name,
                    'box': box,
                    'aspect_ratio': aspect_ratio
                })
                has_issue = True
        
        # 检查 6: 单张图片标注过多（可能重复标注）
        if len(boxes) > 5:
            issues['too_many_boxes'].append({
                'image': img_path.name,
                'count': len(boxes)
            })
            has_issue = True
        
        if has_issue:
            stats['images_with_issues'] += 1
    
    # 输出结果
    print("\n" + "=" * 70)
    print("📊 统计结果")
    print("=" * 70)
    
    print(f"\n✅ 总图片数: {stats['total_images']}")
    print(f"✅ 总标注框数: {stats['total_boxes']}")
    print(f"⚠️  有问题的图片: {stats['images_with_issues']} ({stats['images_with_issues']/stats['total_images']*100:.1f}%)")
    
    print(f"\n📦 类别分布:")
    for class_id, count in sorted(stats['class_counts'].items()):
        class_name = 'normal' if class_id == 0 else 'abnormal'
        print(f"   {class_name} (class {class_id}): {count} 个 ({count/stats['total_boxes']*100:.1f}%)")
    
    if stats['area_stats']:
        areas = np.array(stats['area_stats'])
        print(f"\n📏 边界框面积统计:")
        print(f"   平均: {areas.mean()*100:.2f}%")
        print(f"   中位数: {np.median(areas)*100:.2f}%")
        print(f"   最小: {areas.min()*100:.2f}%")
        print(f"   最大: {areas.max()*100:.2f}%")
    
    # 问题详情
    print("\n" + "=" * 70)
    print("⚠️  发现的问题")
    print("=" * 70)
    
    total_issues = sum(len(v) for v in issues.values())
    if total_issues == 0:
        print("\n✅ 太好了！没有发现明显的标注问题！")
        return
    
    if issues['no_annotations']:
        print(f"\n❌ 无标注图片 ({len(issues['no_annotations'])} 张):")
        for img in issues['no_annotations'][:10]:
            print(f"   - {img}")
        if len(issues['no_annotations']) > 10:
            print(f"   ... 还有 {len(issues['no_annotations']) - 10} 张")
    
    if issues['out_of_bounds']:
        print(f"\n❌ 边界框超出范围 ({len(issues['out_of_bounds'])} 个):")
        for item in issues['out_of_bounds'][:5]:
            print(f"   - {item['image']}: {item['box']}")
        if len(issues['out_of_bounds']) > 5:
            print(f"   ... 还有 {len(issues['out_of_bounds']) - 5} 个")
    
    if issues['too_small']:
        print(f"\n⚠️  边界框过小 ({len(issues['too_small'])} 个):")
        for item in issues['too_small'][:5]:
            print(f"   - {item['image']}: 面积 {item['area_percent']:.3f}%")
        if len(issues['too_small']) > 5:
            print(f"   ... 还有 {len(issues['too_small']) - 5} 个")
    
    if issues['too_large']:
        print(f"\n⚠️  边界框过大 ({len(issues['too_large'])} 个):")
        for item in issues['too_large'][:5]:
            print(f"   - {item['image']}: 面积 {item['area_percent']:.1f}%")
        if len(issues['too_large']) > 5:
            print(f"   ... 还有 {len(issues['too_large']) - 5} 个")
    
    if issues['abnormal_aspect']:
        print(f"\n⚠️  长宽比异常 ({len(issues['abnormal_aspect'])} 个):")
        for item in issues['abnormal_aspect'][:5]:
            print(f"   - {item['image']}: 长宽比 {item['aspect_ratio']:.2f}")
        if len(issues['abnormal_aspect']) > 5:
            print(f"   ... 还有 {len(issues['abnormal_aspect']) - 5} 个")
    
    if issues['too_many_boxes']:
        print(f"\n⚠️  标注框过多 ({len(issues['too_many_boxes'])} 张):")
        for item in issues['too_many_boxes'][:5]:
            print(f"   - {item['image']}: {item['count']} 个标注")
        if len(issues['too_many_boxes']) > 5:
            print(f"   ... 还有 {len(issues['too_many_boxes']) - 5} 张")
    
    if issues['corrupted_images']:
        print(f"\n❌ 损坏的图片 ({len(issues['corrupted_images'])} 张):")
        for img in issues['corrupted_images'][:5]:
            print(f"   - {img}")
    
    # 保存问题列表
    output_file = 'annotation_quality_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'stats': stats,
            'issues': {k: v for k, v in issues.items()}
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 详细报告已保存: {output_file}")
    
    # 建议
    print("\n" + "=" * 70)
    print("💡 建议")
    print("=" * 70)
    
    if len(issues['no_annotations']) > 10:
        print("\n⚠️  有较多无标注图片，建议:")
        print("   1. 确认这些图片是否应该有标注")
        print("   2. 如果不需要，可以删除这些图片")
        print("   3. 如果需要，补充标注")
    
    if len(issues['out_of_bounds']) > 0:
        print("\n❌ 有边界框超出范围，这是严重问题！")
        print("   建议在标注系统中修正这些标注")
    
    if len(issues['too_small']) > 20:
        print("\n⚠️  有较多过小的边界框，可能是:")
        print("   1. 标注工具误操作")
        print("   2. 真的是很小的物体（需确认）")
    
    critical_issues = len(issues['out_of_bounds']) + len(issues['corrupted_images'])
    if critical_issues > 0:
        print(f"\n🚨 建议: 发现 {critical_issues} 个严重问题，建议修正后再训练！")
    elif total_issues > 50:
        print(f"\n⚠️  建议: 发现 {total_issues} 个潜在问题，建议抽查部分后再训练。")
    else:
        print(f"\n✅ 标注质量良好，可以开始训练！")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='检查 YOLO 数据集标注质量')
    parser.add_argument('--dataset', type=str, 
                        default='datasets/candy_merged_20260116_154158',
                        help='数据集目录路径')
    
    args = parser.parse_args()
    
    check_annotations(args.dataset)
