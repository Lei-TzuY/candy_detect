"""
批量修改標註文件的類別 ID
將所有的 class 1 改為 class 0（將"瑕疵"改為"正常"）
"""
from pathlib import Path
import json

def fix_label_class(label_file):
    """修改單個標註文件的類別"""
    try:
        # 讀取原始內容
        with open(label_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 修改類別（將 1 改為 0）
        modified_lines = []
        changed = False
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                class_id = int(parts[0])
                if class_id == 1:  # 如果是瑕疵
                    parts[0] = '0'  # 改為正常
                    changed = True
                modified_lines.append(' '.join(parts) + '\n')
            else:
                modified_lines.append(line)
        
        # 寫回文件
        if changed:
            with open(label_file, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)
            return True
        return False
    except Exception as e:
        print(f"處理 {label_file} 時出錯: {e}")
        return False

def fix_metadata(meta_file):
    """更新元數據，標記為已修正"""
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        metadata['class_fixed'] = True
        metadata['fix_note'] = '已將 class 1 (abnormal) 修正為 class 0 (normal)'
        
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        return False

def main():
    project_root = Path(__file__).parent
    labels_dir = project_root / 'datasets' / 'annotated' / 'labels'
    metadata_dir = project_root / 'datasets' / 'annotated' / 'metadata'
    
    if not labels_dir.exists():
        print(f"標註目錄不存在: {labels_dir}")
        return
    
    # 找出所有標註文件
    label_files = list(labels_dir.rglob('*.txt'))
    
    print(f"找到 {len(label_files)} 個標註文件")
    print("開始修正類別...")
    
    fixed_count = 0
    for label_file in label_files:
        if fix_label_class(label_file):
            fixed_count += 1
            
            # 同時更新對應的元數據
            relative_path = label_file.relative_to(labels_dir)
            meta_file = metadata_dir / relative_path.parent / f"{label_file.stem}.json"
            if meta_file.exists():
                fix_metadata(meta_file)
        
        # 每處理 100 個文件顯示進度
        if (fixed_count + 1) % 100 == 0:
            print(f"  已處理: {fixed_count + 1}/{len(label_files)}")
    
    print(f"\n✅ 完成！共修正 {fixed_count} 個文件")
    print(f"   未修改: {len(label_files) - fixed_count} 個文件（可能已經是正確的）")

if __name__ == '__main__':
    main()
