"""
YOLOv8 自动标注 - 只保留最大的检测框
"""
from ultralytics import YOLO
import cv2
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import shutil

def auto_label_keep_largest(
    input_dir,
    output_dir=None,
    model_path="yolov8n.pt",
    conf_threshold=0.01,
    max_boxes=1,
    save_visualizations=True
):
    """
    自动标注，只保留面积最大的几个检测框
    """
    input_path = Path(input_dir)
    
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = input_path.parent / f"{input_path.name}_largest_{timestamp}"
    else:
        output_dir = Path(output_dir)
    
    labels_dir = output_dir / "labels"
    images_dir = output_dir / "images"
    vis_dir = output_dir / "visualizations" if save_visualizations else None
    
    labels_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    if vis_dir:
        vis_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"载入模型: {model_path}")
    model = YOLO(model_path)
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [f for f in input_path.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"找不到图片！")
        return
    
    print(f"找到 {len(image_files)} 张图片")
    print(f"输出目录: {output_dir}")
    print(f"信心度阈值: {conf_threshold}")
    print(f"每张图片保留: {max_boxes} 个最大检测框")
    print("-" * 60)
    
    total_detections = 0
    images_with_detections = 0
    
    for img_file in tqdm(image_files, desc="处理图片"):
        img = cv2.imread(str(img_file))
        if img is None:
            continue
        
        h, w = img.shape[:2]
        
        # 使用 YOLOv8 推理
        results = model.predict(
            source=str(img_file),
            conf=conf_threshold,
            verbose=False
        )
        
        # 收集所有检测框并计算面积
        all_boxes = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()
                area = (x2 - x1) * (y2 - y1)
                all_boxes.append({
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                    'conf': conf, 'area': area
                })
        
        # 按面积排序，保留最大的几个
        all_boxes.sort(key=lambda x: x['area'], reverse=True)
        selected_boxes = all_boxes[:max_boxes]
        
        # 转换为 YOLO 格式
        detections = []
        for box in selected_boxes:
            x_center = ((box['x1'] + box['x2']) / 2) / w
            y_center = ((box['y1'] + box['y2']) / 2) / h
            width = (box['x2'] - box['x1']) / w
            height = (box['y2'] - box['y1']) / h
            
            # 类别 1 = abnormal
            detections.append([1, x_center, y_center, width, height])
            
            # 可视化
            if save_visualizations:
                cv2.rectangle(img, (int(box['x1']), int(box['y1'])), 
                            (int(box['x2']), int(box['y2'])), (0, 0, 255), 2)
                label = f"abnormal {box['conf']:.2f}"
                cv2.putText(img, label, (int(box['x1']), int(box['y1']) - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # 保存标注
        label_file = labels_dir / f"{img_file.stem}.txt"
        with open(label_file, 'w') as f:
            for det in detections:
                f.write(f"{det[0]} {det[1]:.6f} {det[2]:.6f} {det[3]:.6f} {det[4]:.6f}\n")
        
        shutil.copy2(img_file, images_dir / img_file.name)
        
        if save_visualizations and detections:
            cv2.imwrite(str(vis_dir / img_file.name), img)
        
        if detections:
            total_detections += len(detections)
            images_with_detections += 1
    
    # 生成配置文件
    classes_file = output_dir / "classes.txt"
    with open(classes_file, 'w', encoding='utf-8') as f:
        f.write("normal\n")
        f.write("abnormal\n")
    
    yaml_file = output_dir / "dataset.yaml"
    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write(f"# Auto-labeled (largest boxes) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"path: {output_dir.absolute()}\n")
        f.write("train: images\n")
        f.write("val: images\n\n")
        f.write("names:\n")
        f.write("  0: normal\n")
        f.write("  1: abnormal\n\n")
        f.write("nc: 2\n")
    
    print("\n" + "=" * 60)
    print("标注完成！")
    print("=" * 60)
    print(f"总图片数: {len(image_files)}")
    print(f"有检测结果的图片: {images_with_detections}")
    print(f"总检测框数: {total_detections}")
    print(f"平均每张图片: {total_detections/len(image_files):.2f}")
    print(f"\n输出目录: {output_dir}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True)
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--model", "-m", default="yolov8n.pt")
    parser.add_argument("--conf", "-c", type=float, default=0.01)
    parser.add_argument("--max-boxes", type=int, default=1)
    parser.add_argument("--no-vis", action="store_true")
    
    args = parser.parse_args()
    
    auto_label_keep_largest(
        input_dir=args.input,
        output_dir=args.output,
        model_path=args.model,
        conf_threshold=args.conf,
        max_boxes=args.max_boxes,
        save_visualizations=not args.no_vis
    )
