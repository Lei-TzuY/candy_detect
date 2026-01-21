"""
YOLOv8 自動標註腳本 - 將所有檢測框標記為 abnormal (瑕疵)
"""
import os
from pathlib import Path
from ultralytics import YOLO
import cv2
from tqdm import tqdm
from datetime import datetime

def auto_label_abnormal(
    input_dir,
    output_dir=None,
    model_path="yolov8n.pt",
    conf_threshold=0.25,
    save_visualizations=True
):
    """
    使用 YOLOv8 對圖片進行自動標註，所有檢測框標記為 abnormal
    
    Args:
        input_dir: 輸入圖片資料夾
        output_dir: 輸出資料夾 (YOLO格式標註)
        model_path: YOLOv8 模型路徑
        conf_threshold: 信心度閾值
        save_visualizations: 是否保存可視化結果
    """
    input_path = Path(input_dir)
    
    # 設定輸出目錄
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = input_path.parent / f"{input_path.name}_labeled_{timestamp}"
    else:
        output_dir = Path(output_dir)
    
    # 創建輸出目錄結構
    labels_dir = output_dir / "labels"
    images_dir = output_dir / "images"
    vis_dir = output_dir / "visualizations" if save_visualizations else None
    
    labels_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    if vis_dir:
        vis_dir.mkdir(parents=True, exist_ok=True)
    
    # 載入 YOLOv8 模型
    print(f"載入模型: {model_path}")
    model = YOLO(model_path)
    
    # 取得所有圖片
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [f for f in input_path.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"在 {input_dir} 中找不到圖片檔案！")
        return
    
    print(f"找到 {len(image_files)} 張圖片")
    print(f"輸出目錄: {output_dir}")
    print(f"信心度閾值: {conf_threshold}")
    print("-" * 60)
    
    # 統計資訊
    total_detections = 0
    images_with_detections = 0
    
    # 處理每張圖片
    for img_file in tqdm(image_files, desc="處理圖片"):
        # 讀取圖片
        img = cv2.imread(str(img_file))
        if img is None:
            print(f"無法讀取: {img_file}")
            continue
        
        h, w = img.shape[:2]
        
        # 使用 YOLOv8 進行推理
        results = model.predict(
            source=str(img_file),
            conf=conf_threshold,
            verbose=False
        )
        
        # 處理檢測結果
        detections = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                # 獲取邊界框坐標 (xyxy 格式)
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()
                
                # 轉換為 YOLO 格式 (中心點 x, y, 寬度, 高度) - 歸一化
                x_center = ((x1 + x2) / 2) / w
                y_center = ((y1 + y2) / 2) / h
                width = (x2 - x1) / w
                height = (y2 - y1) / h
                
                # 類別 ID 為 1 (abnormal/瑕疵)
                # YOLO 格式: class_id x_center y_center width height
                detections.append([1, x_center, y_center, width, height])
                
                # 可視化 - 繪製邊界框
                if save_visualizations:
                    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), 
                                (0, 0, 255), 2)
                    label = f"abnormal {conf:.2f}"
                    cv2.putText(img, label, (int(x1), int(y1) - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # 保存標註文件 (即使沒有檢測結果也要創建空文件)
        label_file = labels_dir / f"{img_file.stem}.txt"
        with open(label_file, 'w') as f:
            for det in detections:
                f.write(f"{det[0]} {det[1]:.6f} {det[2]:.6f} {det[3]:.6f} {det[4]:.6f}\n")
        
        # 複製原始圖片到輸出目錄
        import shutil
        shutil.copy2(img_file, images_dir / img_file.name)
        
        # 保存可視化結果
        if save_visualizations:
            cv2.imwrite(str(vis_dir / img_file.name), img)
        
        # 更新統計
        if detections:
            total_detections += len(detections)
            images_with_detections += 1
    
    # 生成 classes.txt
    classes_file = output_dir / "classes.txt"
    with open(classes_file, 'w', encoding='utf-8') as f:
        f.write("normal\n")
        f.write("abnormal\n")
    
    # 生成數據集配置文件
    yaml_file = output_dir / "dataset.yaml"
    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write(f"# Auto-labeled dataset - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"path: {output_dir.absolute()}\n")
        f.write("train: images\n")
        f.write("val: images\n\n")
        f.write("names:\n")
        f.write("  0: normal\n")
        f.write("  1: abnormal\n\n")
        f.write("nc: 2\n")
    
    # 生成統計報告
    report_file = output_dir / "labeling_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("YOLOv8 自動標註報告 - abnormal (瑕疵)\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"處理時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"輸入目錄: {input_dir}\n")
        f.write(f"輸出目錄: {output_dir}\n")
        f.write(f"模型: {model_path}\n")
        f.write(f"信心度閾值: {conf_threshold}\n\n")
        f.write(f"總圖片數: {len(image_files)}\n")
        f.write(f"有檢測結果的圖片: {images_with_detections}\n")
        f.write(f"總檢測框數: {total_detections}\n")
        f.write(f"平均每張圖片檢測框數: {total_detections/len(image_files):.2f}\n\n")
        f.write("輸出檔案:\n")
        f.write(f"  - 標註檔案: {labels_dir}\n")
        f.write(f"  - 圖片檔案: {images_dir}\n")
        if save_visualizations:
            f.write(f"  - 可視化結果: {vis_dir}\n")
        f.write(f"  - 類別檔案: {classes_file}\n")
        f.write(f"  - 配置檔案: {yaml_file}\n")
    
    # 顯示結果
    print("\n" + "=" * 60)
    print("標註完成！")
    print("=" * 60)
    print(f"總圖片數: {len(image_files)}")
    print(f"有檢測結果的圖片: {images_with_detections}")
    print(f"總檢測框數: {total_detections}")
    print(f"平均每張圖片檢測框數: {total_detections/len(image_files):.2f}")
    print(f"\n輸出目錄: {output_dir}")
    print(f"標註檔案: {labels_dir}")
    if save_visualizations:
        print(f"可視化結果: {vis_dir}")
    print(f"\n報告已保存至: {report_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YOLOv8 自動標註 - abnormal (瑕疵)")
    parser.add_argument("--input", "-i", type=str, required=True,
                       help="輸入圖片資料夾路徑")
    parser.add_argument("--output", "-o", type=str, default=None,
                       help="輸出資料夾路徑 (預設: 自動生成)")
    parser.add_argument("--model", "-m", type=str, default="yolov8n.pt",
                       help="YOLOv8 模型路徑 (預設: yolov8n.pt)")
    parser.add_argument("--conf", "-c", type=float, default=0.25,
                       help="信心度閾值 (預設: 0.25)")
    parser.add_argument("--no-vis", action="store_true",
                       help="不保存可視化結果")
    
    args = parser.parse_args()
    
    auto_label_abnormal(
        input_dir=args.input,
        output_dir=args.output,
        model_path=args.model,
        conf_threshold=args.conf,
        save_visualizations=not args.no_vis
    )
