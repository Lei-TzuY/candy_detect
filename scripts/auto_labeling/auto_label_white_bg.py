"""
基于白底背景去除的自动标注
针对白色背景 + 单颗糖果的场景
"""
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import shutil
from PIL import Image


def detect_candy_by_background_subtraction(img, bg_img, threshold=30):
    """
    使用背景差分检测糖果
    
    Args:
        img: 当前图像（BGR）
        bg_img: 背景参考图像（BGR）
        threshold: 差异阈值，差异大于此值的像素视为前景
    
    Returns:
        mask: 糖果 mask (255=糖果, 0=背景)
    """
    # 转换为灰度
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_bg = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY)
    
    # 计算差异
    diff = cv2.absdiff(gray_img, gray_bg)
    
    # 二值化：差异大的区域 = 糖果
    _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    
    # 形态学操作：去除噪点，连接断开的区域
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    
    return mask


def detect_candy_by_color(img, white_threshold=230):
    """
    使用颜色检测糖果（橙色/黄色）+ 白底去除
    
    Args:
        img: BGR 图像
        white_threshold: 白色阈值，更高的值可以更好地去除浅灰色
    
    Returns:
        mask: 糖果 mask (255=糖果, 0=背景)
    """
    # 1. 先用高阈值去除白色背景
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, white_mask = cv2.threshold(gray, white_threshold, 255, cv2.THRESH_BINARY_INV)
    
    # 2. 转换到 HSV 色彩空间检测橙色/黄色糖果
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 橙色/黄色范围（糖果的颜色）
    # H: 10-35 (橙色到黄色)
    # S: 50-255 (中等到高饱和度，排除灰色)
    # V: 100-255 (亮度)
    lower_candy = np.array([10, 50, 100])
    upper_candy = np.array([35, 255, 255])
    color_mask = cv2.inRange(hsv, lower_candy, upper_candy)
    
    # 3. 结合白底去除和颜色检测
    # 只保留"非白色" AND "橙黄色"的区域
    mask = cv2.bitwise_and(white_mask, color_mask)
    
    # 4. 形态学操作：去除噪点，连接断开的区域
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    return mask


def find_candy_bbox(mask, min_area=500, img_width=None, img_height=None):
    """
    从 mask 中找到糖果的边界框
    优先选择靠近图片中心的物体（糖果应该在中心）
    
    Returns:
        list of (x, y, w, h, area) 按"中心距离 + 面积"排序
    """
    # 查找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 图片中心点
    center_x = img_width / 2 if img_width else mask.shape[1] / 2
    center_y = img_height / 2 if img_height else mask.shape[0] / 2
    
    boxes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 计算边界框中心点
            box_center_x = x + w / 2
            box_center_y = y + h / 2
            
            # 距离图片中心的距离
            distance_to_center = ((box_center_x - center_x)**2 + (box_center_y - center_y)**2)**0.5
            
            # 归一化距离（相对于图片对角线）
            max_distance = (center_x**2 + center_y**2)**0.5
            normalized_distance = distance_to_center / max_distance
            
            boxes.append((x, y, w, h, area, normalized_distance))
    
    # 按"中心距离"排序（距离越近越好），然后按面积（越大越好）
    # 优先选择靠近中心的，其次是面积大的
    boxes.sort(key=lambda b: (b[5], -b[4]))
    
    return boxes


def auto_label_white_bg(
    input_dir,
    output_dir=None,
    background_image=None,
    white_threshold=230,
    bg_diff_threshold=30,
    min_area=500,
    max_boxes=1,
    save_visualizations=True,
    save_masks=False
):
    """
    基于背景差分或颜色检测的自动标注
    
    Args:
        background_image: 背景参考图片路径（如果提供，将使用背景差分；否则使用颜色检测）
        bg_diff_threshold: 背景差分阈值
    """
    input_path = Path(input_dir)
    
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = input_path.parent / f"{input_path.name}_whitebg_{timestamp}"
    else:
        output_dir = Path(output_dir)
    
    labels_dir = output_dir / "labels"
    images_dir = output_dir / "images"
    vis_dir = output_dir / "visualizations" if save_visualizations else None
    mask_dir = output_dir / "masks" if save_masks else None
    
    labels_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    if vis_dir:
        vis_dir.mkdir(parents=True, exist_ok=True)
    if mask_dir:
        mask_dir.mkdir(parents=True, exist_ok=True)
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [f for f in input_path.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"找不到图片！")
        return
    
    # 加载背景参考图片（如果提供）
    bg_img = None
    if background_image:
        bg_path = Path(background_image)
        if bg_path.exists():
            try:
                pil_bg = Image.open(bg_path).convert('RGB')
                bg_img = cv2.cvtColor(np.array(pil_bg), cv2.COLOR_RGB2BGR)
                print(f"✅ 加载背景参考图片: {bg_path.name}")
            except Exception as e:
                print(f"⚠️  无法加载背景图片: {e}")
                print("   将使用颜色检测方法")
    
    detection_method = "背景差分" if bg_img is not None else "颜色检测"
    
    print(f"🎨 {detection_method} 自动标注")
    print(f"找到 {len(image_files)} 张图片")
    print(f"输出目录: {output_dir}")
    if bg_img is not None:
        print(f"背景差分阈值: {bg_diff_threshold}")
    else:
        print(f"白色阈值: {white_threshold}")
        print(f"糖果颜色: 橙色/黄色 (HSV: H=10-35, S=50-255)")
    print(f"最小物体面积: {min_area} 像素")
    print(f"每张图片保留: {max_boxes} 个最大物体")
    print("-" * 60)
    
    total_detections = 0
    images_with_detections = 0
    no_detection_files = []
    
    for img_file in tqdm(image_files, desc="处理图片"):
        # 读取图片 (使用 PIL 解决中文路径问题)
        try:
            pil_img = Image.open(img_file).convert('RGB')
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"⚠️  无法读取: {img_file.name} - {e}")
            continue
        
        h, w = img.shape[:2]
        
        # 检测糖果（使用背景差分或颜色检测）
        if bg_img is not None:
            # 方法1: 背景差分（最准确）
            mask = detect_candy_by_background_subtraction(img, bg_img, bg_diff_threshold)
        else:
            # 方法2: 颜色检测
            mask = detect_candy_by_color(img, white_threshold)
        
        # 查找糖果边界框（传入图片尺寸用于中心点计算）
        boxes = find_candy_bbox(mask, min_area, w, h)
        
        # 保留最大的几个（靠近中心的优先）
        selected_boxes = boxes[:max_boxes]
        
        # 转换为 YOLO 格式
        detections = []
        for box_data in selected_boxes:
            x, y, box_w, box_h, area = box_data[:5]  # 忽略 distance 字段
            # YOLO 格式：中心点坐标和宽高（归一化）
            x_center = (x + box_w / 2) / w
            y_center = (y + box_h / 2) / h
            width = box_w / w
            height = box_h / h
            
            # 类别 1 = abnormal (瑕疵)
            detections.append([1, x_center, y_center, width, height])
            
            # 可视化
            if save_visualizations:
                cv2.rectangle(img, (x, y), (x + box_w, y + box_h), (0, 0, 255), 2)
                cv2.putText(img, f"abnormal ({area} px)", (x, y - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # 记录没有检测结果的图片
        if not detections:
            no_detection_files.append(img_file.name)
        
        # 保存标注文件
        label_file = labels_dir / f"{img_file.stem}.txt"
        with open(label_file, 'w') as f:
            for det in detections:
                f.write(f"{det[0]} {det[1]:.6f} {det[2]:.6f} {det[3]:.6f} {det[4]:.6f}\n")
        
        # 复制图片
        shutil.copy2(img_file, images_dir / img_file.name)
        
        # 保存可视化 (使用 PIL 解决中文路径问题)
        if save_visualizations:
            try:
                vis_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                Image.fromarray(vis_img).save(vis_dir / img_file.name)
            except Exception as e:
                print(f"⚠️  无法保存可视化: {img_file.name} - {e}")
        
        # 保存 mask (使用 PIL 解决中文路径问题)
        if save_masks:
            try:
                Image.fromarray(mask).save(mask_dir / img_file.name)
            except Exception as e:
                print(f"⚠️  无法保存 mask: {img_file.name} - {e}")
        
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
        f.write(f"# White Background Removal - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
        f.write("白底背景去除自动标注报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"输入目录: {input_dir}\n")
        f.write(f"输出目录: {output_dir}\n\n")
        f.write(f"参数设置:\n")
        f.write(f"  白色阈值: {white_threshold}\n")
        f.write(f"  最小物体面积: {min_area} 像素\n")
        f.write(f"  每张图片最多: {max_boxes} 个检测框\n\n")
        f.write(f"处理结果:\n")
        f.write(f"  总图片数: {len(image_files)}\n")
        f.write(f"  有检测结果: {images_with_detections}\n")
        f.write(f"  无检测结果: {len(no_detection_files)}\n")
        f.write(f"  总检测框数: {total_detections}\n")
        f.write(f"  平均每张: {total_detections/len(image_files):.2f}\n\n")
        
        if no_detection_files:
            f.write(f"无检测结果的图片 ({len(no_detection_files)} 张):\n")
            for fname in no_detection_files[:20]:  # 只列出前20个
                f.write(f"  - {fname}\n")
            if len(no_detection_files) > 20:
                f.write(f"  ... 还有 {len(no_detection_files) - 20} 张\n")
    
    # 显示结果
    print("\n" + "=" * 60)
    print("✅ 标注完成！")
    print("=" * 60)
    print(f"总图片数: {len(image_files)}")
    print(f"有检测结果: {images_with_detections} ({images_with_detections/len(image_files)*100:.1f}%)")
    print(f"无检测结果: {len(no_detection_files)} ({len(no_detection_files)/len(image_files)*100:.1f}%)")
    print(f"总检测框数: {total_detections}")
    print(f"平均每张: {total_detections/len(image_files):.2f}")
    print(f"\n📁 输出目录: {output_dir}")
    print(f"📊 报告: {report_file}")
    
    if no_detection_files:
        print(f"\n⚠️  有 {len(no_detection_files)} 张图片没有检测到物体")
        print(f"   建议检查这些图片或调整参数（白色阈值、最小面积）")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="背景差分或颜色检测自动标注")
    parser.add_argument("--input", "-i", required=True, help="输入图片文件夹")
    parser.add_argument("--output", "-o", default=None, help="输出文件夹")
    parser.add_argument("--background", "-bg", default=None, 
                       help="背景参考图片路径（推荐使用！）")
    parser.add_argument("--bg-threshold", type=int, default=30,
                       help="背景差分阈值 (0-255)，默认 30")
    parser.add_argument("--threshold", "-t", type=int, default=230, 
                       help="白色阈值 (仅颜色检测时使用)，默认 230")
    parser.add_argument("--min-area", type=int, default=500, 
                       help="最小物体面积（像素），默认 500")
    parser.add_argument("--max-boxes", type=int, default=1, 
                       help="每张图片最多检测框数，默认 1")
    parser.add_argument("--no-vis", action="store_true", 
                       help="不保存可视化结果")
    parser.add_argument("--save-masks", action="store_true",
                       help="保存前景 mask")
    
    args = parser.parse_args()
    
    auto_label_white_bg(
        input_dir=args.input,
        output_dir=args.output,
        background_image=args.background,
        white_threshold=args.threshold,
        bg_diff_threshold=args.bg_threshold,
        min_area=args.min_area,
        max_boxes=args.max_boxes,
        save_visualizations=not args.no_vis,
        save_masks=args.save_masks
    )
