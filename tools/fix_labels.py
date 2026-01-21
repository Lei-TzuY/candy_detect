"""
修复YOLO标签文件 - 移除多余的列
"""
from pathlib import Path


def fix_labels(labels_dir):
    """修复包含6列的标签文件，只保留前5列"""
    labels_dir = Path(labels_dir)
    
    fixed_count = 0
    error_count = 0
    
    for label_file in labels_dir.glob('*.txt'):
        try:
            with open(label_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            fixed_lines = []
            needs_fix = False
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) == 6:
                    # 只保留前5列：class_id x_center y_center width height
                    fixed_line = ' '.join(parts[:5]) + '\n'
                    fixed_lines.append(fixed_line)
                    needs_fix = True
                elif len(parts) == 5:
                    fixed_lines.append(line)
                else:
                    print(f"⚠️  {label_file.name}: 异常列数 {len(parts)}")
            
            if needs_fix:
                with open(label_file, 'w', encoding='utf-8') as f:
                    f.writelines(fixed_lines)
                fixed_count += 1
        
        except Exception as e:
            print(f"❌ {label_file.name}: {e}")
            error_count += 1
    
    print(f"\n✅ 修复完成：{fixed_count} 个文件")
    if error_count > 0:
        print(f"❌ 错误：{error_count} 个文件")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="修复YOLO标签文件")
    parser.add_argument("--labels", "-l", required=True, help="标签文件夹路径")
    
    args = parser.parse_args()
    
    fix_labels(args.labels)
