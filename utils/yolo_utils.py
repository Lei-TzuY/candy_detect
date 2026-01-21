"""
YOLO 格式標註處理工具
提供統一的標註載入、轉換、視覺化功能
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional


def load_yolo_annotations(label_file: Path, img_width: int, img_height: int) -> List[Dict]:
    """
    載入 YOLO 格式標註並轉換為像素座標
    
    Args:
        label_file: 標註檔案路徑
        img_width: 影像寬度
        img_height: 影像高度
        
    Returns:
        List[Dict]: 標註列表，每個包含 'class_id' 和 'bbox' (x1, y1, x2, y2)
    """
    annotations = []
    
    if not label_file.exists() or label_file.stat().st_size == 0:
        return annotations
    
    try:
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
    except Exception as e:
        print(f"[WARN] 無法讀取標註檔案 {label_file}: {e}")
    
    return annotations


def bbox_to_yolo_format(bbox: Tuple[int, int, int, int], 
                        img_width: int, img_height: int) -> Tuple[float, float, float, float]:
    """
    將像素座標邊界框轉換為 YOLO 格式（正規化座標）
    
    Args:
        bbox: (x1, y1, x2, y2) 像素座標
        img_width: 影像寬度
        img_height: 影像高度
        
    Returns:
        (x_center, y_center, width, height) 正規化座標 (0-1)
    """
    x1, y1, x2, y2 = bbox
    
    x_center = (x1 + x2) / 2.0 / img_width
    y_center = (y1 + y2) / 2.0 / img_height
    width = (x2 - x1) / img_width
    height = (y2 - y1) / img_height
    
    # 確保座標在 0-1 範圍內
    x_center = max(0, min(1, x_center))
    y_center = max(0, min(1, y_center))
    width = max(0, min(1, width))
    height = max(0, min(1, height))
    
    return x_center, y_center, width, height


def draw_annotations(image: np.ndarray, 
                     annotations: List[Dict],
                     class_names: Dict[int, str] = None,
                     colors: Dict[int, Tuple[int, int, int]] = None,
                     thickness: int = 2,
                     font_scale: float = 0.5) -> np.ndarray:
    """
    在影像上繪製標註框和類別標籤
    
    Args:
        image: OpenCV 影像 (BGR)
        annotations: 標註列表
        class_names: 類別名稱字典 {class_id: name}
        colors: 顏色字典 {class_id: (B, G, R)}
        thickness: 邊框厚度
        font_scale: 字體大小
        
    Returns:
        繪製後的影像
    """
    img = image.copy()
    
    # 預設類別名稱
    if class_names is None:
        class_names = {0: 'normal', 1: 'abnormal'}
    
    # 預設顏色
    if colors is None:
        colors = {
            0: (0, 255, 0),    # 綠色 - normal
            1: (0, 0, 255)     # 紅色 - abnormal
        }
    
    for ann in annotations:
        class_id = ann['class_id']
        x1, y1, x2, y2 = ann['bbox']
        
        # 取得顏色和類別名稱
        color = colors.get(class_id, (255, 255, 0))  # 預設青色
        class_name = class_names.get(class_id, f'class_{class_id}')
        
        # 繪製邊界框
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
        
        # 繪製類別標籤
        label = f'{class_name}'
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 
                                        font_scale, thickness)
        
        # 標籤背景
        label_y = max(y1 - 10, label_size[1])
        cv2.rectangle(img, 
                     (x1, label_y - label_size[1] - 5),
                     (x1 + label_size[0], label_y + 5),
                     color, -1)
        
        # 標籤文字
        cv2.putText(img, label, 
                   (x1, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX,
                   font_scale, (255, 255, 255), thickness)
    
    return img


def validate_annotation(annotation: Dict, 
                       img_width: int, 
                       img_height: int,
                       min_area: int = 100) -> Tuple[bool, Optional[str]]:
    """
    驗證標註是否有效
    
    Args:
        annotation: 標註字典
        img_width: 影像寬度
        img_height: 影像高度
        min_area: 最小面積
        
    Returns:
        (is_valid, error_message)
    """
    x1, y1, x2, y2 = annotation['bbox']
    
    # 檢查座標範圍
    if x1 < 0 or y1 < 0 or x2 > img_width or y2 > img_height:
        return False, "座標超出影像範圍"
    
    # 檢查寬高
    width = x2 - x1
    height = y2 - y1
    
    if width <= 0 or height <= 0:
        return False, "無效的寬度或高度"
    
    # 檢查面積
    area = width * height
    if area < min_area:
        return False, f"面積過小 ({area} < {min_area})"
    
    # 檢查長寬比
    aspect_ratio = width / height if height > 0 else 0
    if aspect_ratio > 10 or aspect_ratio < 0.1:
        return False, f"異常長寬比 ({aspect_ratio:.2f})"
    
    return True, None


def save_yolo_annotation(label_file: Path, 
                        annotations: List[Dict],
                        img_width: int,
                        img_height: int):
    """
    儲存標註為 YOLO 格式
    
    Args:
        label_file: 輸出標註檔案路徑
        annotations: 標註列表（像素座標）
        img_width: 影像寬度
        img_height: 影像高度
    """
    label_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(label_file, 'w', encoding='utf-8') as f:
        for ann in annotations:
            class_id = ann['class_id']
            x_center, y_center, width, height = bbox_to_yolo_format(
                ann['bbox'], img_width, img_height
            )
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
