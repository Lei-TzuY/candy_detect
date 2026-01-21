"""
可视化验证集的标注结果和模型预测对比
"""
import cv2
import numpy as np
from pathlib import Path
import yaml
from ultralytics import YOLO
import shutil
from datetime import datetime


def load_yolo_annotations(label_path, img_width, img_height):
    """加载YOLO格式标注"""
    annotations = []
    if not Path(label_path).exists():
        return annotations
    
    with open(label_path, 'r') as f:
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
                    'bbox': [x1, y1, x2, y2]
                })
    
    return annotations


def visualize_validation_set(dataset_yaml, model_path=None, output_dir=None, max_images=50):
    """可视化验证集的标注和预测结果"""
    
    # 读取数据集配置
    with open(dataset_yaml, 'r', encoding='utf-8') as f:
        dataset_config = yaml.safe_load(f)
    
    # 获取路径
    dataset_path = Path(dataset_yaml).parent
    val_images_path = dataset_path / dataset_config['val']
    
    # 类别名称
    class_names = dataset_config['names']
    colors = {
        0: (0, 255, 0),    # normal - 绿色
        1: (0, 0, 255),    # abnormal - 红色
    }
    
    # 创建输出目录
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"visualizations/validation_{timestamp}")
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 加载模型（如果提供）
    model = None
    if model_path and Path(model_path).exists():
        print(f"📦 加载模型: {model_path}")
        model = YOLO(model_path)
    
    # 获取所有验证图片
    image_files = list(val_images_path.glob('*.jpg')) + list(val_images_path.glob('*.png'))
    print(f"📊 找到 {len(image_files)} 张验证图片")
    
    # 限制数量
    if len(image_files) > max_images:
        print(f"⚠️ 限制显示前 {max_images} 张图片")
        image_files = image_files[:max_images]
    
    # 处理每张图片
    processed = 0
    for img_path in image_files:
        try:
            # 读取图片
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            
            height, width = img.shape[:2]
            
            # 创建两个副本：一个显示ground truth，一个显示预测
            img_gt = img.copy()
            img_pred = img.copy() if model else None
            
            # 1. 绘制Ground Truth标注
            label_path = val_images_path.parent / 'labels' / f"{img_path.stem}.txt"
            gt_annotations = load_yolo_annotations(label_path, width, height)
            
            for ann in gt_annotations:
                class_id = ann['class_id']
                x1, y1, x2, y2 = ann['bbox']
                color = colors.get(class_id, (255, 255, 255))
                
                # 绘制边界框
                cv2.rectangle(img_gt, (x1, y1), (x2, y2), color, 2)
                
                # 绘制标签
                label = f"GT: {class_names[class_id]}"
                (text_width, text_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )
                cv2.rectangle(
                    img_gt,
                    (x1, y1 - text_height - baseline - 5),
                    (x1 + text_width, y1),
                    color,
                    -1
                )
                cv2.putText(
                    img_gt, label, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
                )
            
            # 2. 运行模型预测（如果有模型）
            if model:
                results = model.predict(img_path, conf=0.25, verbose=False)
                
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        # 获取坐标和类别
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        conf = float(box.conf[0])
                        class_id = int(box.cls[0])
                        color = colors.get(class_id, (255, 255, 255))
                        
                        # 绘制边界框
                        cv2.rectangle(img_pred, (x1, y1), (x2, y2), color, 2)
                        
                        # 绘制标签
                        label = f"Pred: {class_names[class_id]} {conf:.2f}"
                        (text_width, text_height), baseline = cv2.getTextSize(
                            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                        )
                        cv2.rectangle(
                            img_pred,
                            (x1, y1 - text_height - baseline - 5),
                            (x1 + text_width, y1),
                            color,
                            -1
                        )
                        cv2.putText(
                            img_pred, label, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
                        )
            
            # 3. 合并显示（如果有预测结果）
            if model and img_pred is not None:
                # 创建并排对比图
                # 添加标题
                title_height = 40
                combined_height = max(img_gt.shape[0], img_pred.shape[0]) + title_height
                combined_width = img_gt.shape[1] + img_pred.shape[1]
                combined = np.ones((combined_height, combined_width, 3), dtype=np.uint8) * 255
                
                # 添加标题文字
                cv2.putText(combined, "Ground Truth", (img_gt.shape[1]//2 - 80, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                cv2.putText(combined, "Prediction", (img_gt.shape[1] + img_pred.shape[1]//2 - 80, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                
                # 放置图片
                combined[title_height:title_height+img_gt.shape[0], :img_gt.shape[1]] = img_gt
                combined[title_height:title_height+img_pred.shape[0], img_gt.shape[1]:] = img_pred
                
                # 保存对比图
                output_path = output_dir / f"{img_path.stem}_comparison.jpg"
                cv2.imwrite(str(output_path), combined)
            else:
                # 只保存ground truth
                output_path = output_dir / f"{img_path.stem}_gt.jpg"
                cv2.imwrite(str(output_path), img_gt)
            
            processed += 1
            if processed % 10 == 0:
                print(f"✅ 已处理 {processed}/{len(image_files)} 张图片")
                
        except Exception as e:
            print(f"❌ 处理 {img_path.name} 失败: {e}")
            continue
    
    print(f"\n✅ 可视化完成！")
    print(f"📁 输出目录: {output_dir.absolute()}")
    print(f"📊 共处理 {processed} 张图片")
    
    # 生成HTML索引页面
    generate_html_index(output_dir, class_names)
    
    return output_dir


def generate_html_index(output_dir, class_names):
    """生成HTML索引页面"""
    image_files = sorted(output_dir.glob('*.jpg'))
    
    html = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>验证集可视化结果</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #2d3748;
            margin-bottom: 20px;
            text-align: center;
        }
        .legend {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .legend-item {
            display: inline-block;
            margin-right: 20px;
            padding: 5px 15px;
            border-radius: 5px;
            font-weight: bold;
        }
        .normal {
            background: #48bb78;
            color: white;
        }
        .abnormal {
            background: #f56565;
            color: white;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
            gap: 20px;
        }
        .image-card {
            background: white;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .image-card:hover {
            transform: translateY(-5px);
        }
        .image-card img {
            width: 100%;
            border-radius: 5px;
        }
        .image-card .filename {
            margin-top: 10px;
            color: #718096;
            font-size: 0.9em;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍬 验证集标注可视化结果</h1>
        
        <div class="legend">
            <h3>图例说明：</h3>
            <span class="legend-item normal">Normal (正常)</span>
            <span class="legend-item abnormal">Abnormal (异常)</span>
        </div>
        
        <div class="gallery">
"""
    
    for img_file in image_files:
        html += f"""
            <div class="image-card">
                <img src="{img_file.name}" alt="{img_file.stem}">
                <div class="filename">{img_file.name}</div>
            </div>
"""
    
    html += """
        </div>
    </div>
</body>
</html>
"""
    
    index_path = output_dir / 'index.html'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"📄 HTML索引页面: {index_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='可视化验证集标注结果')
    parser.add_argument('--dataset', type=str, 
                       default='datasets/candy_merged_20260116_154158/dataset.yaml',
                       help='数据集YAML文件路径')
    parser.add_argument('--model', type=str,
                       default='runs/detect/runs/train/candy_detector3/weights/best.pt',
                       help='训练好的模型路径（可选）')
    parser.add_argument('--output', type=str, default=None,
                       help='输出目录（可选）')
    parser.add_argument('--max-images', type=int, default=50,
                       help='最多可视化多少张图片')
    
    args = parser.parse_args()
    
    output_dir = visualize_validation_set(
        args.dataset,
        args.model if Path(args.model).exists() else None,
        args.output,
        args.max_images
    )
    
    # 打开结果
    import subprocess
    subprocess.run(['explorer', str(output_dir)], shell=True)
