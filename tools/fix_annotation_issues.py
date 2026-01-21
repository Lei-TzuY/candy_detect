"""
修正标注问题
1. 删除边界框过大的照片
2. 删除长宽比异常的照片
3. 修正超出边界的标注（clip到边界内）
"""
import os
import json
import shutil
from pathlib import Path

def fix_annotations(dataset_dir, report_file='annotation_quality_report.json', backup=True):
    """修正标注问题"""
    
    # 读取报告
    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    issues = report['issues']
    
    dataset_path = Path(dataset_dir)
    images_dir = dataset_path / 'images'
    labels_dir = dataset_path / 'labels'
    
    print("=" * 70)
    print("🔧 修正标注问题")
    print("=" * 70)
    print(f"\n📁 数据集: {dataset_dir}")
    
    # 备份
    if backup:
        backup_dir = Path(f"{dataset_dir}_backup_{report['stats']['total_images']}")
        if not backup_dir.exists():
            print(f"\n💾 创建备份: {backup_dir}")
            shutil.copytree(dataset_dir, backup_dir)
            print("   ✅ 备份完成")
    
    deleted_count = 0
    fixed_count = 0
    
    # 1. 删除边界框过大的照片
    if issues['too_large']:
        print(f"\n🗑️  删除边界框过大的照片 ({len(issues['too_large'])} 张)...")
        for item in issues['too_large']:
            img_name = item['image']
            img_path = images_dir / img_name
            label_path = labels_dir / (Path(img_name).stem + '.txt')
            
            if img_path.exists():
                img_path.unlink()
                deleted_count += 1
                print(f"   ❌ {img_name} (面积 {item['area_percent']:.1f}%)")
            
            if label_path.exists():
                label_path.unlink()
        
        print(f"   ✅ 已删除 {len(issues['too_large'])} 张")
    
    # 2. 删除长宽比异常的照片
    if issues['abnormal_aspect']:
        print(f"\n🗑️  删除长宽比异常的照片 ({len(issues['abnormal_aspect'])} 张)...")
        
        # 按图片分组
        img_set = set()
        for item in issues['abnormal_aspect']:
            img_set.add(item['image'])
        
        for img_name in img_set:
            img_path = images_dir / img_name
            label_path = labels_dir / (Path(img_name).stem + '.txt')
            
            if img_path.exists():
                img_path.unlink()
                deleted_count += 1
                print(f"   ❌ {img_name}")
            
            if label_path.exists():
                label_path.unlink()
        
        print(f"   ✅ 已删除 {len(img_set)} 张")
    
    # 3. 修正超出边界的标注（clip 到 0-1 范围）
    if issues['out_of_bounds']:
        print(f"\n🔧 修正超出边界的标注 ({len(issues['out_of_bounds'])} 个)...")
        
        # 按图片分组
        img_to_fix = {}
        for item in issues['out_of_bounds']:
            img_name = item['image']
            if img_name not in img_to_fix:
                img_to_fix[img_name] = []
            img_to_fix[img_name].append(item)
        
        for img_name in img_to_fix.keys():
            label_path = labels_dir / (Path(img_name).stem + '.txt')
            
            if not label_path.exists():
                continue
            
            # 读取所有标注
            fixed_lines = []
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        
                        # Clip 到 0-1 范围
                        x_min = max(0.0, x_center - width/2)
                        y_min = max(0.0, y_center - height/2)
                        x_max = min(1.0, x_center + width/2)
                        y_max = min(1.0, y_center + height/2)
                        
                        # 重新计算中心和宽高
                        new_x_center = (x_min + x_max) / 2
                        new_y_center = (y_min + y_max) / 2
                        new_width = x_max - x_min
                        new_height = y_max - y_min
                        
                        # 检查是否有效（宽高 > 0）
                        if new_width > 0 and new_height > 0:
                            fixed_lines.append(f"{class_id} {new_x_center:.6f} {new_y_center:.6f} {new_width:.6f} {new_height:.6f}\n")
            
            # 写回文件
            if fixed_lines:
                with open(label_path, 'w') as f:
                    f.writelines(fixed_lines)
                fixed_count += 1
        
        print(f"   ✅ 已修正 {fixed_count} 张图片的标注")
    
    # 统计结果
    remaining_images = len(list(images_dir.glob('*.jpg'))) + len(list(images_dir.glob('*.png')))
    remaining_labels = len(list(labels_dir.glob('*.txt')))
    
    print("\n" + "=" * 70)
    print("📊 处理结果")
    print("=" * 70)
    print(f"\n原始数据:")
    print(f"   图片: {report['stats']['total_images']} 张")
    print(f"   标注框: {report['stats']['total_boxes']} 个")
    
    print(f"\n删除:")
    print(f"   图片: {deleted_count} 张")
    
    print(f"\n修正:")
    print(f"   标注文件: {fixed_count} 个")
    
    print(f"\n剩余:")
    print(f"   图片: {remaining_images} 张")
    print(f"   标注: {remaining_labels} 个")
    
    print("\n💡 建议:")
    print("   1. 现在可以用模型重新标记整个数据集（补充可能遗漏的标注）")
    print("   2. 或者直接用修正后的数据集重新训练")
    
    return remaining_images, remaining_labels

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='修正标注问题')
    parser.add_argument('--dataset', type=str, 
                        default='datasets/candy_merged_20260116_154158',
                        help='数据集目录路径')
    parser.add_argument('--report', type=str,
                        default='annotation_quality_report.json',
                        help='质量检查报告文件')
    parser.add_argument('--no-backup', action='store_true',
                        help='不创建备份')
    
    args = parser.parse_args()
    
    fix_annotations(args.dataset, args.report, backup=not args.no_backup)
