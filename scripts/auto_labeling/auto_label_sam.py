"""
使用 SAM (Segment Anything Model) 进行自动标注
SAM 可以自动检测图片中的所有物体，无需预训练
"""
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import torch

def auto_label_with_sam(
    input_dir,
    output_dir=None,
    conf_threshold=0.7,
    min_area=1000,
    save_visualizations=True
):
    """
    使用 SAM 自动标注图片中的物体
    
    Args:
        input_dir: 输入图片文件夹
        output_dir: 输出文件夹
        conf_threshold: 置信度阈值
        min_area: 最小物体面积（像素）
        save_visualizations: 是否保存可视化结果
    """
    try:
        from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
    except ImportError:
        print("❌ 未安装 segment-anything 库")
        print("请运行: pip install segment-anything")
        print("或: pip install git+https://github.com/facebookresearch/segment-anything.git")
        return
    
    input_path = Path(input_dir)
    
    # 设置输出目录
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = input_path.parent / f"{input_path.name}_sam_labeled_{timestamp}"
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
    
    # 加载 SAM 模型
    print("📥 加载 SAM 模型...")
    print("   (首次运行会自动下载模型，约 2.4 GB)")
    
    # 尝试加载 SAM 模型
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"   使用设备: {device.upper()}")
    
    # 自动下载 SAM checkpoint
    sam_checkpoint = "sam_vit_h_4b8939.pth"
    if not Path(sam_checkpoint).exists():
        print("   正在下载 SAM 模型...")
        import urllib.request
        url = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
        urllib.request.urlretrieve(url, sam_checkpoint)
    
    sam = sam_model_registry["vit_h"](checkpoint=sam_checkpoint)
    sam.to(device=device)
    
    # 创建自动标注生成器
    mask_generator = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=32,
        pred_iou_thresh=conf_threshold,
        stability_score_thresh=0.9,
        crop_n_layers=1,
        crop_n_points_downscale_factor=2,
        min_mask_region_area=min_area,
    )
    
    # 获取所有图片
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [f for f in input_path.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"在 {input_dir} 中找不到图片文件！")
        return
    
    print(f"\n找到 {len(image_files)} 张图片")
    print(f"输出目录: {output_dir}")
    print("-" * 60)
    
    # 统计
    total_detections = 0
    images_with_detections = 0
    
    # 处理每张图片
    for img_file in tqdm(image_files, desc="处理图片"):
        # 读取图片
        img = cv2.imread(str(img_file))
        if img is None:
            print(f"无法读取: {img_file}")
            continue
        
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]
        
        # 使用 SAM 生成 masks
        masks = mask_generator.generate(img_rgb)
        
        # 按面积排序，选择最大的物体
        masks = sorted(masks, key=lambda x: x['area'], reverse=True)
        
        # 保存标注
        detections = []
        for mask_data in masks[:5]:  # 最多取前5个最大的物体
            mask = mask_data['segmentation']
            
            # 获取边界框
            y_indices, x_indices = np.where(mask)
            if len(x_indices) == 0 or len(y_indices) == 0:
                continue
            
            x1, x2 = x_indices.min(), x_indices.max()
            y1, y2 = y_indices.min(), y_indices.max()
            
            # 转换为 YOLO 格式
            x_center = ((x1 + x2) / 2) / w
            y_center = ((y1 + y2) / 2) / h
            width = (x2 - x1) / w
            height = (y2 - y1) / h
            
            # 类别 1 = abnormal
            detections.append([1, x_center, y_center, width, height])
            
            # 可视化
            if save_visualizations:
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(img, "abnormal", (x1, y1 - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # 保存标注文件
        label_file = labels_dir / f"{img_file.stem}.txt"
        with open(label_file, 'w') as f:
            for det in detections:
                f.write(f"{det[0]} {det[1]:.6f} {det[2]:.6f} {det[3]:.6f} {det[4]:.6f}\n")
        
        # 复制图片
        import shutil
        shutil.copy2(img_file, images_dir / img_file.name)
        
        # 保存可视化
        if save_visualizations and detections:
            cv2.imwrite(str(vis_dir / img_file.name), img)
        
        # 统计
        if detections:
            total_detections += len(detections)
            images_with_detections += 1
    
    # 生成文件
    classes_file = output_dir / "classes.txt"
    with open(classes_file, 'w', encoding='utf-8') as f:
        f.write("normal\n")
        f.write("abnormal\n")
    
    yaml_file = output_dir / "dataset.yaml"
    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write(f"# SAM Auto-labeled - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"path: {output_dir.absolute()}\n")
        f.write("train: images\n")
        f.write("val: images\n\n")
        f.write("names:\n")
        f.write("  0: normal\n")
        f.write("  1: abnormal\n\n")
        f.write("nc: 2\n")
    
    # 报告
    print("\n" + "=" * 60)
    print("SAM 标注完成！")
    print("=" * 60)
    print(f"总图片数: {len(image_files)}")
    print(f"有检测结果的图片: {images_with_detections}")
    print(f"总检测框数: {total_detections}")
    print(f"平均每张图片: {total_detections/len(image_files):.2f}")
    print(f"\n输出目录: {output_dir}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SAM 自动标注")
    parser.add_argument("--input", "-i", required=True, help="输入图片文件夹")
    parser.add_argument("--output", "-o", default=None, help="输出文件夹")
    parser.add_argument("--conf", "-c", type=float, default=0.7, help="置信度阈值")
    parser.add_argument("--min-area", type=int, default=1000, help="最小物体面积")
    parser.add_argument("--no-vis", action="store_true", help="不保存可视化")
    
    args = parser.parse_args()
    
    auto_label_with_sam(
        input_dir=args.input,
        output_dir=args.output,
        conf_threshold=args.conf,
        min_area=args.min_area,
        save_visualizations=not args.no_vis
    )
