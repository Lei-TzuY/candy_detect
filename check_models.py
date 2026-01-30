"""
檢查模型文件的類別信息
"""
from ultralytics import YOLO
import sys
from pathlib import Path

def check_model(model_path):
    """檢查模型的類別信息"""
    try:
        print(f"\n{'='*60}")
        print(f"模型: {model_path}")
        print('='*60)
        
        model = YOLO(model_path)
        
        # 獲取類別信息
        names = model.names
        num_classes = len(names)
        
        print(f"類別數量: {num_classes}")
        print(f"類別列表: {names}")
        
        # 判斷是否為糖果模型
        if num_classes == 2 and set(names.values()) == {'normal', 'abnormal'}:
            print("✅ 這是糖果專用訓練模型")
            return True
        elif num_classes == 80:
            print("❌ 這是 COCO 預訓練模型（80類）")
            return False
        else:
            print(f"⚠️ 未知模型類型（{num_classes}類）")
            return False
            
    except Exception as e:
        print(f"❌ 載入失敗: {e}")
        return False

if __name__ == "__main__":
    # 檢查專案根目錄的所有 .pt 文件
    project_root = Path(__file__).parent
    
    pt_files = sorted(project_root.glob("*.pt"))
    
    if not pt_files:
        print("未找到 .pt 模型文件")
        sys.exit(1)
    
    print(f"\n找到 {len(pt_files)} 個模型文件")
    
    candy_models = []
    coco_models = []
    
    for pt_file in pt_files:
        is_candy = check_model(pt_file)
        if is_candy:
            candy_models.append(pt_file.name)
        else:
            coco_models.append(pt_file.name)
    
    print(f"\n{'='*60}")
    print("總結")
    print('='*60)
    print(f"\n✅ 糖果專用模型 ({len(candy_models)} 個):")
    for model in candy_models:
        print(f"   - {model}")
    
    print(f"\n❌ COCO 預訓練模型 ({len(coco_models)} 個):")
    for model in coco_models:
        print(f"   - {model}")
    
    print("\n" + "="*60)
