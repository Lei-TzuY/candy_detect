"""
为合并的训练数据生成可视化
"""
import cv2
from pathlib import Path
from PIL import Image
import numpy as np
from tqdm import tqdm


def load_yolo_annotations(label_file, img_width, img_height):
    """加载YOLO格式标注并转换为像素坐标"""
    annotations = []
    
    if not label_file.exists():
        return annotations
    
    with open(label_file, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                class_id = int(parts[0])
                x_center = float(parts[1]) * img_width
                y_center = float(parts[2]) * img_height
                width = float(parts[3]) * img_width
                height = float(parts[4]) * img_height
                
                x1 = int(x_center - width / 2)
                y1 = int(y_center - height / 2)
                x2 = int(x_center + width / 2)
                y2 = int(y_center + height / 2)
                
                annotations.append({
                    'class_id': class_id,
                    'bbox': (x1, y1, x2, y2)
                })
    
    return annotations


def draw_annotations(image, annotations, class_names=['normal', 'abnormal']):
    """在图片上绘制标注框"""
    colors = {
        0: (0, 255, 0),    # 绿色 - normal
        1: (0, 0, 255)     # 红色 - abnormal
    }
    
    for ann in annotations:
        class_id = ann['class_id']
        x1, y1, x2, y2 = ann['bbox']
        
        color = colors.get(class_id, (255, 255, 255))
        
        # 绘制边界框
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        
        # 绘制标签
        label = class_names[class_id] if class_id < len(class_names) else f"class_{class_id}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        
        # 标签背景
        cv2.rectangle(image, 
                     (x1, y1 - label_size[1] - 10), 
                     (x1 + label_size[0] + 10, y1), 
                     color, -1)
        
        # 标签文字
        cv2.putText(image, label, 
                   (x1 + 5, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   0.6, (255, 255, 255), 2)
    
    return image


def visualize_dataset(dataset_dir, max_images=None):
    """为数据集生成可视化"""
    dataset_dir = Path(dataset_dir)
    images_dir = dataset_dir / 'images'
    labels_dir = dataset_dir / 'labels'
    vis_dir = dataset_dir / 'visualizations'
    
    vis_dir.mkdir(exist_ok=True)
    
    print(f"📁 数据集目录: {dataset_dir}")
    print(f"🖼️  图片目录: {images_dir}")
    print(f"🏷️  标签目录: {labels_dir}")
    print(f"📊 输出目录: {vis_dir}")
    print("-" * 60)
    
    # 获取所有图片
    image_files = list(images_dir.glob('*.jpg')) + \
                  list(images_dir.glob('*.jpeg')) + \
                  list(images_dir.glob('*.png'))
    
    if max_images:
        image_files = image_files[:max_images]
    
    print(f"找到 {len(image_files)} 张图片")
    
    stats = {
        'total': 0,
        'with_annotations': 0,
        'without_annotations': 0,
        'total_boxes': 0
    }
    
    for img_file in tqdm(image_files, desc="生成可视化"):
        try:
            # 使用PIL读取图片（支持中文路径）
            pil_img = Image.open(img_file)
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            img_height, img_width = img.shape[:2]
            
            # 读取标注
            label_file = labels_dir / f"{img_file.stem}.txt"
            annotations = load_yolo_annotations(label_file, img_width, img_height)
            
            stats['total'] += 1
            
            if annotations:
                stats['with_annotations'] += 1
                stats['total_boxes'] += len(annotations)
                
                # 绘制标注
                img = draw_annotations(img, annotations)
            else:
                stats['without_annotations'] += 1
                
                # 添加"无标注"水印
                cv2.putText(img, "No Annotations", 
                           (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 
                           1.0, (0, 0, 255), 2)
            
            # 保存可视化图片（使用PIL支持中文路径）
            output_file = vis_dir / f"{img_file.stem}_vis.jpg"
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_output = Image.fromarray(img_rgb)
            pil_output.save(output_file, 'JPEG', quality=95)
            
        except Exception as e:
            print(f"⚠️  处理失败: {img_file.name} - {e}")
    
    # 显示统计
    print("\n" + "=" * 60)
    print("✅ 可视化完成！")
    print("=" * 60)
    print(f"总图片数: {stats['total']}")
    print(f"有标注: {stats['with_annotations']} ({stats['with_annotations']/stats['total']*100:.1f}%)")
    print(f"无标注: {stats['without_annotations']} ({stats['without_annotations']/stats['total']*100:.1f}%)")
    print(f"总标注框: {stats['total_boxes']}")
    print(f"平均每张: {stats['total_boxes']/stats['total']:.2f} 个框")
    print(f"\n📁 可视化结果: {vis_dir}")
    
    return vis_dir


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="为合并的数据集生成可视化")
    parser.add_argument("--dataset", "-d", required=True, help="数据集目录")
    parser.add_argument("--max", "-m", type=int, help="最大处理图片数（用于快速预览）")
    parser.add_argument("--open", "-o", action="store_true", help="完成后打开文件夹")
    
    args = parser.parse_args()
    
    vis_dir = visualize_dataset(args.dataset, args.max)
    
    if args.open:
        import subprocess
        subprocess.run(['explorer', str(vis_dir)], shell=True)
