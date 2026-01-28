"""
删除过大或过小的标记框

只删除标记框，不删除图片。如果删除后图片没有任何标记框，会保留空的标注文件。
"""
import os
from pathlib import Path
import shutil
from datetime import datetime

# 配置
DATASET_DIR = Path(r"d:\專案\candy\datasets\最新資料")
IMAGES_DIR = DATASET_DIR / "images"
LABELS_DIR = DATASET_DIR / "labels"

# 尺寸阈值（相对于图片尺寸的比例）- 更严格的设置
MIN_BOX_SIZE = 0.0025  # 最小面积比例 (0.25%)
MAX_BOX_SIZE = 0.85    # 最大面积比例 (85%)

# 绝对尺寸阈值（归一化坐标）- 更严格的设置
MIN_WIDTH = 0.01    # 最小宽度 (1%)
MIN_HEIGHT = 0.01   # 最小高度 (1%)
MAX_WIDTH = 0.90    # 最大宽度 (90%)
MAX_HEIGHT = 0.90   # 最大高度 (90%)

def check_box_size(width, height):
    """检查标记框尺寸是否异常"""
    area = width * height
    
    # 检查面积
    if area < MIN_BOX_SIZE:
        return False, 'too_small', area
    if area > MAX_BOX_SIZE:
        return False, 'too_large', area
    
    # 检查宽高
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        return False, 'dimension_too_small', area
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        return False, 'dimension_too_large', area
    
    return True, 'normal', area

def remove_abnormal_size_boxes(labels_dir, backup_dir):
    """删除过大或过小的标记框"""
    stats = {
        'total_files': 0,
        'modified_files': 0,
        'total_boxes': 0,
        'removed_boxes': 0,
        'details': []
    }
    
    # 遍历所有标注文件
    label_files = list(labels_dir.glob("*.txt"))
    
    for label_file in label_files:
        stats['total_files'] += 1
        
        # 读取标注
        with open(label_file, 'r') as f:
            lines = f.readlines()
        
        if not lines:
            continue
        
        # 备份原文件
        backup_file = backup_dir / label_file.name
        shutil.copy2(label_file, backup_file)
        
        # 过滤标记框
        new_lines = []
        removed_count = 0
        
        for line in lines:
            stats['total_boxes'] += 1
            parts = line.strip().split()
            
            if len(parts) >= 5:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                
                is_normal, reason, area = check_box_size(width, height)
                
                if is_normal:
                    new_lines.append(line)
                else:
                    removed_count += 1
                    stats['removed_boxes'] += 1
                    stats['details'].append({
                        'file': label_file.name,
                        'class': class_id,
                        'width': width,
                        'height': height,
                        'area': area,
                        'reason': reason
                    })
            else:
                # 格式错误的行，保留
                new_lines.append(line)
        
        # 如果有标记框被删除，更新文件
        if removed_count > 0:
            stats['modified_files'] += 1
            with open(label_file, 'w') as f:
                f.writelines(new_lines)
            
            print(f"✓ {label_file.name}: 删除 {removed_count} 个异常框，保留 {len(new_lines)} 个")
    
    return stats

def generate_report(stats, backup_dir):
    """生成删除报告"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = DATASET_DIR / f"remove_abnormal_size_boxes_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("删除过大/过小标记框报告\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"数据集目录: {DATASET_DIR}\n")
        f.write(f"备份目录: {backup_dir}\n")
        f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"阈值设置:\n")
        f.write(f"  最小面积比例: {MIN_BOX_SIZE*100:.2f}% (面积 < {MIN_BOX_SIZE} 视为太小)\n")
        f.write(f"  最大面积比例: {MAX_BOX_SIZE*100:.2f}% (面积 > {MAX_BOX_SIZE} 视为太大)\n")
        f.write(f"  最小宽度: {MIN_WIDTH} (宽度 < {MIN_WIDTH} 视为太窄)\n")
        f.write(f"  最小高度: {MIN_HEIGHT} (高度 < {MIN_HEIGHT} 视为太矮)\n")
        f.write(f"  最大宽度: {MAX_WIDTH} (宽度 > {MAX_WIDTH} 视为太宽)\n")
        f.write(f"  最大高度: {MAX_HEIGHT} (高度 > {MAX_HEIGHT} 视为太高)\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("统计摘要\n")
        f.write("=" * 80 + "\n")
        f.write(f"总标注文件数: {stats['total_files']}\n")
        f.write(f"修改的文件数: {stats['modified_files']}\n")
        f.write(f"总标记框数: {stats['total_boxes']}\n")
        f.write(f"删除的标记框数: {stats['removed_boxes']}\n")
        f.write(f"删除比例: {stats['removed_boxes']/stats['total_boxes']*100:.2f}%\n\n")
        
        if stats['details']:
            # 统计原因分布
            reason_counts = {}
            for detail in stats['details']:
                reason = detail['reason']
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            f.write("删除原因分布:\n")
            reason_names = {
                'too_small': '面积过小',
                'too_large': '面积过大',
                'dimension_too_small': '宽/高过小',
                'dimension_too_large': '宽/高过大'
            }
            for reason, count in sorted(reason_counts.items()):
                f.write(f"  {reason_names.get(reason, reason)}: {count} 个\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("删除详情\n")
            f.write("=" * 80 + "\n\n")
            
            # 按文件分组
            files_dict = {}
            for detail in stats['details']:
                file = detail['file']
                if file not in files_dict:
                    files_dict[file] = []
                files_dict[file].append(detail)
            
            for file, boxes in sorted(files_dict.items()):
                f.write(f"\n{file}: 删除 {len(boxes)} 个异常框\n")
                for box in boxes:
                    reason_text = reason_names.get(box['reason'], box['reason'])
                    f.write(f"  - Class {box['class']}: "
                           f"宽={box['width']:.6f}, 高={box['height']:.6f}, "
                           f"面积={box['area']:.6f} ({reason_text})\n")
    
    return report_file

def main():
    print("=" * 80)
    print("删除过大/过小的标记框")
    print("=" * 80)
    print(f"数据集目录: {DATASET_DIR}")
    print(f"图片目录: {IMAGES_DIR}")
    print(f"标注目录: {LABELS_DIR}")
    print()
    
    # 检查目录
    if not IMAGES_DIR.exists():
        print(f"❌ 错误: 图片目录不存在: {IMAGES_DIR}")
        return
    
    if not LABELS_DIR.exists():
        print(f"❌ 错误: 标注目录不存在: {LABELS_DIR}")
        return
    
    # 创建备份目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = DATASET_DIR / f"labels_backup_{timestamp}"
    backup_dir.mkdir(exist_ok=True)
    print(f"备份目录: {backup_dir}")
    print()
    
    # 确认
    print(f"阈值设置:")
    print(f"  最小面积比例: {MIN_BOX_SIZE*100:.2f}% (太小)")
    print(f"  最大面积比例: {MAX_BOX_SIZE*100:.2f}% (太大)")
    print(f"  最小尺寸: 宽 {MIN_WIDTH}, 高 {MIN_HEIGHT}")
    print(f"  最大尺寸: 宽 {MAX_WIDTH}, 高 {MAX_HEIGHT}")
    print()
    
    response = input("确认删除过大/过小的标记框? (y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    print("\n开始处理...")
    print("-" * 80)
    
    # 删除异常框
    stats = remove_abnormal_size_boxes(LABELS_DIR, backup_dir)
    
    # 生成报告
    report_file = generate_report(stats, backup_dir)
    
    print("-" * 80)
    print("\n✅ 处理完成!")
    print(f"\n统计:")
    print(f"  总标注文件: {stats['total_files']}")
    print(f"  修改的文件: {stats['modified_files']}")
    print(f"  总标记框: {stats['total_boxes']}")
    print(f"  删除的框: {stats['removed_boxes']} ({stats['removed_boxes']/stats['total_boxes']*100:.2f}%)")
    print(f"\n备份位置: {backup_dir}")
    print(f"报告位置: {report_file}")
    print("\n提示: 如需恢复，可从备份目录复制回原位置")

if __name__ == "__main__":
    main()
