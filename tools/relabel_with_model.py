"""
用训练好的模型重新标记整个数据集
补充可能遗漏的标注
"""
import os
from pathlib import Path
from ultralytics import YOLO
import cv2

def relabel_dataset(dataset_dir, model_path, conf_threshold=0.25, iou_threshold=0.45):
    """用模型重新标记数据集"""
    
    print("=" * 70)
    print("🤖 用模型重新标记数据集")
    print("=" * 70)
    print(f"\n📁 数据集: {dataset_dir}")
    print(f"🧠 模型: {model_path}")
    print(f"⚙️  置信度阈值: {conf_threshold}")
    print(f"⚙️  IOU 阈值: {iou_threshold}")
    
    # 加载模型
    print("\n🔄 加载模型...")
    model = YOLO(model_path)
    print("   ✅ 模型加载完成")
    
    dataset_path = Path(dataset_dir)
    images_dir = dataset_path / 'images'
    labels_dir = dataset_path / 'labels'
    
    # 获取所有图片
    image_files = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.png'))
    
    print(f"\n🖼️  找到 {len(image_files)} 张图片")
    print("\n开始标记...")
    
    relabeled_count = 0
    added_boxes = 0
    
    for idx, img_path in enumerate(image_files):
        if (idx + 1) % 100 == 0:
            print(f"   进度: {idx + 1}/{len(image_files)}")
        
        # 读取图片
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        
        h, w = img.shape[:2]
        
        # 模型推理
        results = model(img, conf=conf_threshold, iou=iou_threshold, verbose=False)
        
        if len(results) == 0 or len(results[0].boxes) == 0:
            continue
        
        # 转换为 YOLO 格式
        boxes = results[0].boxes
        
        label_lines = []
        for box in boxes:
            # 获取坐标和类别
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            class_id = int(box.cls[0].cpu().numpy())
            conf = float(box.conf[0].cpu().numpy())
            
            # 转换为 YOLO 格式（归一化的中心坐标和宽高）
            x_center = ((x1 + x2) / 2) / w
            y_center = ((y1 + y2) / 2) / h
            width = (x2 - x1) / w
            height = (y2 - y1) / h
            
            # 确保在 0-1 范围内
            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            width = max(0, min(1, width))
            height = max(0, min(1, height))
            
            label_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
        
        # 保存标注
        if label_lines:
            label_path = labels_dir / (img_path.stem + '.txt')
            with open(label_path, 'w') as f:
                f.writelines(label_lines)
            
            relabeled_count += 1
            added_boxes += len(label_lines)
    
    print(f"\n{'=' * 70}")
    print("📊 标记结果")
    print(f"{'=' * 70}")
    print(f"\n✅ 重新标记: {relabeled_count} 张图片")
    print(f"✅ 新增标注框: {added_boxes} 个")
    
    # 统计最终数据
    final_images = len(list(images_dir.glob('*.jpg'))) + len(list(images_dir.glob('*.png')))
    final_labels = len(list(labels_dir.glob('*.txt')))
    
    # 统计总标注框
    total_boxes = 0
    class_counts = {0: 0, 1: 0}
    
    for label_file in labels_dir.glob('*.txt'):
        with open(label_file, 'r') as f:
            lines = f.readlines()
            total_boxes += len(lines)
            for line in lines:
                class_id = int(line.split()[0])
                class_counts[class_id] = class_counts.get(class_id, 0) + 1
    
    print(f"\n最终统计:")
    print(f"   图片: {final_images} 张")
    print(f"   标注文件: {final_labels} 个")
    print(f"   总标注框: {total_boxes} 个")
    print(f"      - normal: {class_counts.get(0, 0)} 个 ({class_counts.get(0, 0)/total_boxes*100:.1f}%)")
    print(f"      - abnormal: {class_counts.get(1, 0)} 个 ({class_counts.get(1, 0)/total_boxes*100:.1f}%)")
    
    print(f"\n💡 下一步:")
    print(f"   现在可以用修正后的数据集重新训练 YOLOv8s")
    print(f"   python train_yolov8s_max_performance.py")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='用模型重新标记数据集')
    parser.add_argument('--dataset', type=str, 
                        default='datasets/candy_merged_20260116_154158',
                        help='数据集目录路径')
    parser.add_argument('--model', type=str,
                        default='runs/detect/runs/train/candy_detector_yolov8s_max/weights/best.pt',
                        help='模型路径')
    parser.add_argument('--conf', type=float, default=0.25,
                        help='置信度阈值')
    parser.add_argument('--iou', type=float, default=0.45,
                        help='IOU 阈值')
    
    args = parser.parse_args()
    
    relabel_dataset(args.dataset, args.model, args.conf, args.iou)
