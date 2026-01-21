"""
使用传统计算机视觉方法自动标注糖果
基于颜色、轮廓检测，无需深度学习模型
"""
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import shutil


def find_candy_contours(img, min_area=500, max_area=50000):
    """
    使用轮廓检测找到糖果
    """
    # 转换为灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 高斯模糊去噪
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 使用多种阈值方法
    detections = []
    
    # 方法1: 自适应阈值
    adaptive = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # 方法2: Otsu 阈值
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 方法3: Canny 边缘检测
    edges = cv2.Canny(blurred, 50, 150)
    
    # 组合多种方法
    combined = cv2.bitwise_or(adaptive, otsu)
    combined = cv2.bitwise_or(combined, edges)
    
    # 形态学操作：闭运算填补空隙
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # 查找轮廓
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 筛选轮廓
    valid_boxes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area < area < max_area:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 过滤掉太窄或太扁的框
            aspect_ratio = w / h if h > 0 else 0
            if 0.3 < aspect_ratio < 3.0:
                valid_boxes.append((x, y, w, h, area))
    
    # 按面积排序，选择最大的几个
    valid_boxes.sort(key=lambda x: x[4], reverse=True)
    
    return valid_boxes


def find_candy_by_color(img, min_area=500):
    """
    基于颜色检测糖果
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 定义多个颜色范围（适应不同颜色的糖果）
    color_ranges = [
        # 红色 (两个范围，因为红色跨越 0 度)
        ([0, 50, 50], [10, 255, 255]),
        ([170, 50, 50], [180, 255, 255]),
        # 黄色
        ([15, 50, 50], [35, 255, 255]),
        # 绿色
        ([35, 50, 50], [85, 255, 255]),
        # 蓝色
        ([85, 50, 50], [135, 255, 255]),
        # 粉色/紫色
        ([135, 50, 50], [170, 255, 255]),
    ]
    
    # 组合所有颜色的 mask
    combined_mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for lower, upper in color_ranges:
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        combined_mask = cv2.bitwise_or(combined_mask, mask)
    
    # 形态学操作
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # 查找轮廓
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid_boxes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            if 0.3 < aspect_ratio < 3.0:
                valid_boxes.append((x, y, w, h, area))
    
    valid_boxes.sort(key=lambda x: x[4], reverse=True)
    return valid_boxes


def auto_label_traditional_cv(
    input_dir,
    output_dir=None,
    min_area=500,
    max_area=50000,
    max_detections_per_image=3,
    save_visualizations=True
):
    """
    使用传统 CV 方法自动标注
    """
    input_path = Path(input_dir)
    
    # 设置输出目录
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = input_path.parent / f"{input_path.name}_cv_labeled_{timestamp}"
    else:
        output_dir = Path(output_dir)
    
    # 创建输出目录
    labels_dir = output_dir / "labels"
    images_dir = output_dir / "images"
    vis_dir = output_dir / "visualizations" if save_visualizations else None
    
    labels_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    if vis_dir:
        vis_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取所有图片
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [f for f in input_path.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"在 {input_dir} 中找不到图片文件！")
        return
    
    print("🔍 使用传统 CV 方法进行自动标注")
    print(f"找到 {len(image_files)} 张图片")
    print(f"输出目录: {output_dir}")
    print(f"最小物体面积: {min_area} 像素")
    print(f"最大物体面积: {max_area} 像素")
    print("-" * 60)
    
    # 统计
    total_detections = 0
    images_with_detections = 0
    
    # 处理每张图片
    for img_file in tqdm(image_files, desc="处理图片"):
        img = cv2.imread(str(img_file))
        if img is None:
            print(f"无法读取: {img_file}")
            continue
        
        h, w = img.shape[:2]
        
        # 方法1: 轮廓检测
        boxes_contour = find_candy_contours(img, min_area, max_area)
        
        # 方法2: 颜色检测
        boxes_color = find_candy_by_color(img, min_area)
        
        # 合并结果（去重）
        all_boxes = boxes_contour + boxes_color
        
        # 非极大值抑制（NMS）去除重叠的框
        final_boxes = nms_boxes(all_boxes, iou_threshold=0.5)
        
        # 限制每张图片的检测数量
        final_boxes = final_boxes[:max_detections_per_image]
        
        # 转换为 YOLO 格式并保存
        detections = []
        for (x, y, box_w, box_h, _) in final_boxes:
            # YOLO 格式：中心点坐标和宽高（归一化）
            x_center = (x + box_w / 2) / w
            y_center = (y + box_h / 2) / h
            width = box_w / w
            height = box_h / h
            
            # 类别 1 = abnormal
            detections.append([1, x_center, y_center, width, height])
            
            # 可视化
            if save_visualizations:
                cv2.rectangle(img, (x, y), (x + box_w, y + box_h), (0, 0, 255), 2)
                cv2.putText(img, "abnormal", (x, y - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # 保存标注文件
        label_file = labels_dir / f"{img_file.stem}.txt"
        with open(label_file, 'w') as f:
            for det in detections:
                f.write(f"{det[0]} {det[1]:.6f} {det[2]:.6f} {det[3]:.6f} {det[4]:.6f}\n")
        
        # 复制图片
        shutil.copy2(img_file, images_dir / img_file.name)
        
        # 保存可视化
        if save_visualizations and detections:
            cv2.imwrite(str(vis_dir / img_file.name), img)
        
        # 统计
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
        f.write(f"# Traditional CV Auto-labeled - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"path: {output_dir.absolute()}\n")
        f.write("train: images\n")
        f.write("val: images\n\n")
        f.write("names:\n")
        f.write("  0: normal\n")
        f.write("  1: abnormal\n\n")
        f.write("nc: 2\n")
    
    # 生成报告
    report_file = output_dir / "labeling_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("传统 CV 方法自动标注报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"输入目录: {input_dir}\n")
        f.write(f"输出目录: {output_dir}\n\n")
        f.write(f"总图片数: {len(image_files)}\n")
        f.write(f"有检测结果的图片: {images_with_detections}\n")
        f.write(f"总检测框数: {total_detections}\n")
        f.write(f"平均每张图片: {total_detections/len(image_files):.2f}\n")
    
    # 显示结果
    print("\n" + "=" * 60)
    print("✅ 标注完成！")
    print("=" * 60)
    print(f"总图片数: {len(image_files)}")
    print(f"有检测结果的图片: {images_with_detections}")
    print(f"总检测框数: {total_detections}")
    print(f"平均每张图片: {total_detections/len(image_files):.2f}")
    print(f"\n输出目录: {output_dir}")
    print(f"报告: {report_file}")


def nms_boxes(boxes, iou_threshold=0.5):
    """
    非极大值抑制，去除重叠的框
    """
    if not boxes:
        return []
    
    boxes_array = np.array([(x, y, x+w, y+h, area) for x, y, w, h, area in boxes])
    
    x1 = boxes_array[:, 0]
    y1 = boxes_array[:, 1]
    x2 = boxes_array[:, 2]
    y2 = boxes_array[:, 3]
    areas = boxes_array[:, 4]
    
    # 按面积排序
    order = areas.argsort()[::-1]
    
    keep = []
    while len(order) > 0:
        i = order[0]
        keep.append(i)
        
        # 计算 IoU
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        
        # 保留 IoU 小于阈值的框
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    
    return [boxes[i] for i in keep]


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="传统 CV 方法自动标注")
    parser.add_argument("--input", "-i", required=True, help="输入图片文件夹")
    parser.add_argument("--output", "-o", default=None, help="输出文件夹")
    parser.add_argument("--min-area", type=int, default=500, help="最小物体面积")
    parser.add_argument("--max-area", type=int, default=50000, help="最大物体面积")
    parser.add_argument("--max-det", type=int, default=3, help="每张图片最大检测数")
    parser.add_argument("--no-vis", action="store_true", help="不保存可视化")
    
    args = parser.parse_args()
    
    auto_label_traditional_cv(
        input_dir=args.input,
        output_dir=args.output,
        min_area=args.min_area,
        max_area=args.max_area,
        max_detections_per_image=args.max_det,
        save_visualizations=not args.no_vis
    )
