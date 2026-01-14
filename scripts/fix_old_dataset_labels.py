"""
修正舊資料集的錯誤標註
- abnormal 圖片應該標記為 class 1（瑕疵），但錯誤標記為 class 0
- 將所有標籤的 class 進行對調（0→1, 1→0）
"""
import os
import shutil
from pathlib import Path

# 路徑設定
LABELS_DIR = Path(r"d:\專案\candy\datasets\annotated\labels\old dataset\train")
BACKUP_DIR = Path(r"d:\專案\candy\datasets\annotated\labels\old dataset\train_backup")

def swap_class_labels(labels_dir, backup_dir):
    """對調標籤檔案中的 class ID (0↔1)"""
    
    # 建立備份
    if not backup_dir.exists():
        print(f"建立備份: {backup_dir}")
        shutil.copytree(labels_dir, backup_dir)
        print(f"✅ 已備份到 {backup_dir}")
    else:
        print(f"⚠️ 備份已存在: {backup_dir}")
    
    # 統計
    total_files = 0
    total_labels_changed = 0
    abnormal_count = 0
    normal_count = 0
    
    # 處理所有標籤檔案
    label_files = list(labels_dir.glob("*.txt"))
    
    for label_file in label_files:
        total_files += 1
        changed = False
        new_lines = []
        
        with open(label_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    
                    # 對調 class ID
                    new_class_id = 1 - class_id
                    parts[0] = str(new_class_id)
                    
                    new_lines.append(' '.join(parts))
                    total_labels_changed += 1
                    changed = True
        
        # 寫回檔案
        if changed:
            with open(label_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            # 統計
            if 'abnormal' in label_file.name:
                abnormal_count += 1
            elif 'normal' in label_file.name:
                normal_count += 1
    
    # 輸出報告
    print("\n" + "="*50)
    print("修正完成！")
    print("="*50)
    print(f"處理檔案數: {total_files}")
    print(f"修正標籤數: {total_labels_changed}")
    print(f"  - abnormal 檔案: {abnormal_count} (現在標記為 class 1-瑕疵)")
    print(f"  - normal 檔案: {normal_count} (現在標記為 class 0-正常)")
    print("="*50)

def verify_labels(labels_dir):
    """驗證修正後的標籤"""
    abnormal_class0 = 0
    abnormal_class1 = 0
    normal_class0 = 0
    normal_class1 = 0
    
    for label_file in labels_dir.glob("*.txt"):
        with open(label_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    
                    if 'abnormal' in label_file.name:
                        if class_id == 0:
                            abnormal_class0 += 1
                        else:
                            abnormal_class1 += 1
                    elif 'normal' in label_file.name:
                        if class_id == 0:
                            normal_class0 += 1
                        else:
                            normal_class1 += 1
    
    print("\n驗證結果:")
    print("-" * 50)
    print(f"Abnormal 檔案:")
    print(f"  Class 0 (正常): {abnormal_class0} - {'❌ 錯誤！' if abnormal_class0 > 0 else '✅'}")
    print(f"  Class 1 (瑕疵): {abnormal_class1} - {'✅ 正確！' if abnormal_class1 > 0 else '❌'}")
    print(f"\nNormal 檔案:")
    print(f"  Class 0 (正常): {normal_class0} - {'✅ 正確！' if normal_class0 > 0 else '❌'}")
    print(f"  Class 1 (瑕疵): {normal_class1} - {'❌ 錯誤！' if normal_class1 > 0 else '✅'}")
    print("-" * 50)

if __name__ == "__main__":
    print("舊資料集標籤修正工具")
    print("="*50)
    print(f"標籤目錄: {LABELS_DIR}")
    print(f"備份目錄: {BACKUP_DIR}")
    print()
    
    # 確認執行
    response = input("確定要修正標籤嗎？(y/n): ")
    if response.lower() != 'y':
        print("已取消")
        exit(0)
    
    # 執行修正
    swap_class_labels(LABELS_DIR, BACKUP_DIR)
    
    # 驗證結果
    verify_labels(LABELS_DIR)
    
    print("\n✅ 所有標籤已修正完成！")
    print(f"原始標籤已備份至: {BACKUP_DIR}")
