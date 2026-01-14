"""
對調所有 AI 標註的類別
將 class 0 (正常) 改為 class 1 (瑕疵)
將 class 1 (瑕疵) 改為 class 0 (正常)
"""
import json
from pathlib import Path

def swap_ai_label_classes():
    """對調所有 AI 標註的類別"""
    labels_dir = Path('datasets/annotated/labels')
    metadata_dir = Path('datasets/annotated/metadata')
    
    if not labels_dir.exists():
        print(f"❌ 找不到 labels 目錄: {labels_dir}")
        return
    
    # 統計
    total_files = 0
    swapped_files = 0
    total_annotations = 0
    swapped_annotations = 0
    errors = 0
    
    # 遍歷所有標註文件
    for label_file in labels_dir.rglob('*.txt'):
        # 檢查對應的 metadata 文件
        relative_path = label_file.relative_to(labels_dir)
        metadata_file = metadata_dir / relative_path.parent / f"{label_file.stem}.json"
        
        # 只處理 AI 標註的文件
        is_ai = False
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    if meta.get('source') == 'ai':
                        is_ai = True
            except:
                pass
        
        if not is_ai:
            continue
            
        total_files += 1
        
        try:
            # 讀取標註
            lines = []
            with open(label_file, 'r') as f:
                lines = f.readlines()
            
            if not lines:
                continue
            
            # 對調類別
            new_lines = []
            file_changed = False
            for line in lines:
                total_annotations += 1
                parts = line.strip().split()
                if len(parts) >= 5:  # class x y w h [confidence]
                    old_class = int(parts[0])
                    new_class = 1 - old_class  # 0->1, 1->0
                    parts[0] = str(new_class)
                    new_lines.append(' '.join(parts) + '\n')
                    if old_class != new_class:
                        swapped_annotations += 1
                        file_changed = True
                else:
                    new_lines.append(line)
            
            # 寫回文件
            if file_changed:
                with open(label_file, 'w') as f:
                    f.writelines(new_lines)
                swapped_files += 1
                
                if swapped_files % 100 == 0:
                    print(f"已處理 {swapped_files} 個文件...")
                    
        except Exception as e:
            print(f"❌ 處理失敗: {label_file} - {e}")
            errors += 1
    
    print(f"\n✅ 對調完成！")
    print(f"處理的 AI 標註文件: {total_files}")
    print(f"已修改文件: {swapped_files}")
    print(f"總標註數: {total_annotations}")
    print(f"已對調標註: {swapped_annotations}")
    print(f"錯誤: {errors}")

if __name__ == '__main__':
    swap_ai_label_classes()
