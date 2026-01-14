"""
恢復 AI 標註來源
將被誤改為 manual 的 AI 標註改回 ai
"""
import json
from pathlib import Path

def restore_ai_labels():
    """恢復所有被改成 manual 的 AI 標註"""
    metadata_dir = Path('datasets/annotated/metadata')
    
    if not metadata_dir.exists():
        print(f"❌ 找不到 metadata 目錄: {metadata_dir}")
        return
    
    # 統計
    total_files = 0
    restored_files = 0
    errors = 0
    
    # 遍歷所有 JSON 文件
    for json_file in metadata_dir.rglob('*.json'):
        total_files += 1
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 檢查是否是被腳本修改過的（有 modified_note 且 source 是 manual）
            if 'modified_note' in data and data.get('source') == 'manual':
                # 恢復成 ai
                data['source'] = 'ai'
                # 刪除修改記錄
                del data['modified_note']
                
                # 寫回文件
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                restored_files += 1
                if restored_files % 100 == 0:
                    print(f"已處理 {restored_files} 個文件...")
                    
        except Exception as e:
            print(f"❌ 處理失敗: {json_file} - {e}")
            errors += 1
    
    print(f"\n✅ 恢復完成！")
    print(f"總文件數: {total_files}")
    print(f"已恢復: {restored_files}")
    print(f"錯誤: {errors}")
    print(f"未修改: {total_files - restored_files - errors}")

if __name__ == '__main__':
    restore_ai_labels()
