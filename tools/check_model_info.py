"""
检查 YOLOv8 模型信息
"""
from ultralytics import YOLO

model_path = r"d:\專案\candy\之前訓練的 yolov8\runs\detect\train2\weights\best.pt"

print(f"加载模型: {model_path}\n")
model = YOLO(model_path)

print("=" * 60)
print("模型信息")
print("=" * 60)
print(f"类别名称: {model.names}")
print(f"类别数量: {len(model.names)}")
print(f"\n详细类别:")
for idx, name in model.names.items():
    print(f"  {idx}: {name}")
