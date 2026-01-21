"""
合并所有训练数据到统一文件夹
"""
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json


def merge_training_data(project_root, output_name='candy_merged'):
    """
    合并所有训练数据到统一文件夹
    """
    project_root = Path(project_root)
    
    # 源目录
    images_root = project_root / 'datasets' / 'extracted_frames'
    labels_root = project_root / 'datasets' / 'annotated' / 'labels'
    
    # 目标目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / 'datasets' / f'{output_name}_{timestamp}'
    
    merged_images = output_dir / 'images'
    merged_labels = output_dir / 'labels'
    
    merged_images.mkdir(parents=True, exist_ok=True)
    merged_labels.mkdir(parents=True, exist_ok=True)
    
    print("🔄 合并训练数据")
    print(f"源图片目录: {images_root}")
    print(f"源标签目录: {labels_root}")
    print(f"目标目录: {output_dir}")
    print("-" * 60)
    
    # 统计信息
    stats = {
        'total_images': 0,
        'total_labels': 0,
        'folders': defaultdict(lambda: {'images': 0, 'labels': 0}),
        'skipped': []
    }
    
    file_counter = 0
    
    # 扫描所有子文件夹
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    
    for img_file in images_root.rglob('*'):
        if img_file.suffix.lower() in image_extensions:
            # 获取相对路径
            rel_path = img_file.relative_to(images_root)
            folder_name = rel_path.parts[0] if len(rel_path.parts) > 1 else 'root'
            
            # 对应的标签文件
            label_file = labels_root / rel_path.parent / f"{img_file.stem}.txt"
            
            # 只复制有标注的图片
            if label_file.exists() and label_file.stat().st_size > 0:
                # 生成新文件名（避免冲突）
                new_name = f"{folder_name}_{img_file.stem}{img_file.suffix}"
                
                # 如果文件名还是冲突，添加计数器
                target_img = merged_images / new_name
                target_label = merged_labels / f"{Path(new_name).stem}.txt"
                
                if target_img.exists():
                    file_counter += 1
                    new_name = f"{folder_name}_{img_file.stem}_{file_counter:04d}{img_file.suffix}"
                    target_img = merged_images / new_name
                    target_label = merged_labels / f"{Path(new_name).stem}.txt"
                
                try:
                    # 复制图片和标签
                    shutil.copy2(img_file, target_img)
                    shutil.copy2(label_file, target_label)
                    
                    stats['total_images'] += 1
                    stats['total_labels'] += 1
                    stats['folders'][folder_name]['images'] += 1
                    stats['folders'][folder_name]['labels'] += 1
                    
                except Exception as e:
                    print(f"⚠️  复制失败: {rel_path} - {e}")
                    stats['skipped'].append(str(rel_path))
    
    # 生成类别文件
    classes_file = output_dir / 'classes.txt'
    with open(classes_file, 'w', encoding='utf-8') as f:
        f.write("normal\n")
        f.write("abnormal\n")
    
    # 生成数据集配置
    yaml_file = output_dir / 'dataset.yaml'
    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write(f"# Merged Training Data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"path: {output_dir.absolute()}\n")
        f.write("train: images  # 所有数据在同一文件夹\n")
        f.write("val: images    # 训练时可以设置验证集比例\n\n")
        f.write("names:\n")
        f.write("  0: normal\n")
        f.write("  1: abnormal\n\n")
        f.write("nc: 2\n")
    
    # 生成统计报告
    report_file = output_dir / 'merge_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("训练数据合并报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"合并时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"输出目录: {output_dir}\n\n")
        f.write(f"总图片数: {stats['total_images']}\n")
        f.write(f"总标签数: {stats['total_labels']}\n\n")
        f.write("各文件夹统计:\n")
        for folder, counts in sorted(stats['folders'].items()):
            f.write(f"  {folder}:\n")
            f.write(f"    图片: {counts['images']}\n")
            f.write(f"    标签: {counts['labels']}\n")
        
        if stats['skipped']:
            f.write(f"\n跳过的文件 ({len(stats['skipped'])}):\n")
            for skipped in stats['skipped']:
                f.write(f"  - {skipped}\n")
    
    # 保存JSON统计
    json_file = output_dir / 'merge_stats.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_images': stats['total_images'],
            'total_labels': stats['total_labels'],
            'folders': dict(stats['folders']),
            'skipped_count': len(stats['skipped']),
            'merged_at': datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    # 显示结果
    print("\n" + "=" * 60)
    print("✅ 合并完成！")
    print("=" * 60)
    print(f"总图片数: {stats['total_images']}")
    print(f"总标签数: {stats['total_labels']}")
    print(f"\n各文件夹统计:")
    for folder, counts in sorted(stats['folders'].items()):
        print(f"  {folder}: {counts['images']} 张")
    
    if stats['skipped']:
        print(f"\n⚠️  跳过 {len(stats['skipped'])} 个文件")
    
    print(f"\n📁 输出目录: {output_dir}")
    print(f"📊 统计报告: {report_file}")
    print(f"📄 数据集配置: {yaml_file}")
    print(f"🏷️  类别文件: {classes_file}")
    
    return output_dir


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="合并所有训练数据")
    parser.add_argument("--root", "-r", default=".", help="项目根目录")
    parser.add_argument("--name", "-n", default="candy_merged", help="输出文件夹名称前缀")
    
    args = parser.parse_args()
    
    output_dir = merge_training_data(args.root, args.name)
    
    # 打开输出目录
    import subprocess
    subprocess.run(['explorer', str(output_dir)], shell=True)
