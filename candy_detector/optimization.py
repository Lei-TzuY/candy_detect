"""
偵測和追蹤優化模塊

實現高級特徵，包括：
1. 多尺度檢測 - 同時檢測不同尺寸的物體
2. ROI (感興趣區域) 處理 - 優化偵測範圍
3. 自適應追蹤 - 動態調整追蹤策略
4. 卡爾曼濾波 - 平滑物體軌跡
5. 優化的NMS - 降低誤檢
"""

import numpy as np
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import cv2


# ============================================================================
# 卡爾曼濾波追蹤器
# ============================================================================

@dataclass
class KalmanState:
    """卡爾曼濾波器狀態"""
    x: float  # x座標
    y: float  # y座標
    vx: float = 0.0  # x方向速度
    vy: float = 0.0  # y方向速度
    age: int = 0  # 追蹤年齡
    hits: int = 0  # 匹配次數


class KalmanTracker:
    """卡爾曼濾波追蹤器 - 改善物體軌跡平滑度"""
    
    def __init__(self, initial_pos: Tuple[int, int], process_noise: float = 0.1, measure_noise: float = 0.5):
        """
        初始化卡爾曼追蹤器
        
        Args:
            initial_pos: (x, y) 初始位置
            process_noise: 過程噪聲 - 越大越相信新測量值
            measure_noise: 測量噪聲 - 越大越相信預測值
        """
        self.state = KalmanState(x=float(initial_pos[0]), y=float(initial_pos[1]))
        self.process_noise = process_noise
        self.measure_noise = measure_noise
        self.P = np.array([[100.0, 0.0, 0.0, 0.0],  # 位置不確定度
                          [0.0, 100.0, 0.0, 0.0],
                          [0.0, 0.0, 10.0, 0.0],    # 速度不確定度
                          [0.0, 0.0, 0.0, 10.0]])
        self.Q = np.eye(4) * process_noise  # 過程噪聲協方差矩陣
        self.R = np.eye(2) * measure_noise  # 測量噪聲協方差矩陣
    
    def predict(self, dt: float = 1.0) -> Tuple[float, float]:
        """
        預測下一幀物體位置
        
        Args:
            dt: 時間步長
            
        Returns:
            (predicted_x, predicted_y)
        """
        # 使用常速度模型
        self.state.x += self.state.vx * dt
        self.state.y += self.state.vy * dt
        
        # 更新不確定度矩陣
        self.P[0, 0] += self.process_noise
        self.P[1, 1] += self.process_noise
        
        self.state.age += 1
        return self.state.x, self.state.y
    
    def update(self, measurement: Tuple[float, float]) -> Tuple[float, float]:
        """
        使用測量值更新狀態
        
        Args:
            measurement: (x, y) 測量的物體位置
            
        Returns:
            (updated_x, updated_y)
        """
        # 簡化的卡爾曼增益計算
        gain = self.P[0, 0] / (self.P[0, 0] + self.measure_noise)
        
        self.state.x += gain * (measurement[0] - self.state.x)
        self.state.y += gain * (measurement[1] - self.state.y)
        
        # 估計速度
        self.state.vx = (self.state.x - measurement[0]) * 0.5
        self.state.vy = (self.state.y - measurement[1]) * 0.5
        
        # 更新不確定度
        self.P *= (1 - gain)
        self.state.hits += 1
        
        return self.state.x, self.state.y
    
    def get_position(self) -> Tuple[int, int]:
        """取得當前位置"""
        return int(self.state.x), int(self.state.y)
    
    def get_velocity(self) -> Tuple[float, float]:
        """取得速度"""
        return self.state.vx, self.state.vy


# ============================================================================
# 多尺度檢測器
# ============================================================================

class MultiScaleDetector:
    """多尺度檢測 - 增強對不同尺寸物體的檢測"""
    
    def __init__(self, scales: List[float] = None):
        """
        初始化多尺度檢測器
        
        Args:
            scales: 縮放因子列表，例如 [0.5, 0.75, 1.0, 1.25]
        """
        self.scales = scales or [0.75, 1.0, 1.25]
    
    def detect_multi_scale(self, frame: np.ndarray, model, conf_threshold: float, nms_threshold: float) -> List[Dict]:
        """
        在多個尺度上進行檢測
        
        Args:
            frame: 輸入影像
            model: YOLO 模型
            conf_threshold: 信心度閾值
            nms_threshold: NMS 閾值
            
        Returns:
            合併後的檢測結果列表
        """
        all_detections = []
        frame_h, frame_w = frame.shape[:2]
        
        for scale in self.scales:
            # 縮放影像
            scaled_w = int(frame_w * scale)
            scaled_h = int(frame_h * scale)
            scaled_frame = cv2.resize(frame, (scaled_w, scaled_h))
            
            # 執行檢測
            gray_frame = cv2.cvtColor(scaled_frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else scaled_frame
            classes, scores, boxes = model.detect(gray_frame, conf_threshold, nms_threshold)
            
            # 縮放回原始尺寸
            for classid, score, (x, y, w, h) in zip(classes, scores, boxes):
                x_orig = int(x / scale)
                y_orig = int(y / scale)
                w_orig = int(w / scale)
                h_orig = int(h / scale)
                cx = x_orig + w_orig // 2
                cy = y_orig + h_orig // 2
                
                all_detections.append({
                    'classid': int(classid),
                    'score': float(score),
                    'bbox': (x_orig, y_orig, w_orig, h_orig),
                    'center': (cx, cy),
                    'scale': scale
                })
        
        # 使用軟NMS合併多尺度結果
        return self._soft_nms(all_detections, nms_threshold)
    
    @staticmethod
    def _soft_nms(detections: List[Dict], nms_threshold: float) -> List[Dict]:
        """
        軟NMS - 降低重複檢測，同時保留有價值的檢測
        
        Args:
            detections: 檢測結果列表
            nms_threshold: NMS 閾值
            
        Returns:
            過濾後的檢測結果
        """
        if not detections:
            return []
        
        # 按分數排序
        sorted_detections = sorted(detections, key=lambda x: x['score'], reverse=True)
        keep = []
        
        for i, det in enumerate(sorted_detections):
            keep_det = True
            det_box = det['bbox']
            det_area = det_box[2] * det_box[3]
            
            for kept_det in keep:
                kept_box = kept_det['bbox']
                kept_area = kept_box[2] * kept_box[3]
                
                # 計算 IoU
                iou = MultiScaleDetector._calculate_iou(det_box, kept_box)
                
                if iou > nms_threshold and det['classid'] == kept_det['classid']:
                    keep_det = False
                    break
            
            if keep_det:
                keep.append(det)
        
        return keep
    
    @staticmethod
    def _calculate_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        """計算兩個邊界框的 IoU (交集除以並集)"""
        x1_min, y1_min, w1, h1 = box1
        x1_max, y1_max = x1_min + w1, y1_min + h1
        
        x2_min, y2_min, w2, h2 = box2
        x2_max, y2_max = x2_min + w2, y2_min + h2
        
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
            return 0.0
        
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        union_area = w1 * h1 + w2 * h2 - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0


# ============================================================================
# ROI (感興趣區域) 處理器
# ============================================================================

class ROIProcessor:
    """感興趣區域處理 - 優化偵測範圍，提升速度"""
    
    def __init__(self, frame_w: int, frame_h: int, roi_x1: int, roi_x2: int, roi_y1: int = 0, roi_y2: int = None):
        """
        初始化 ROI 處理器
        
        Args:
            frame_w: 影像寬度
            frame_h: 影像高度
            roi_x1: ROI 左邊界
            roi_x2: ROI 右邊界
            roi_y1: ROI 上邊界
            roi_y2: ROI 下邊界
        """
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.roi_x1 = max(0, roi_x1)
        self.roi_x2 = min(frame_w, roi_x2)
        self.roi_y1 = max(0, roi_y1)
        self.roi_y2 = min(frame_h, roi_y2 or frame_h)
    
    def extract_roi(self, frame: np.ndarray) -> np.ndarray:
        """從影像中提取 ROI"""
        return frame[self.roi_y1:self.roi_y2, self.roi_x1:self.roi_x2]
    
    def convert_roi_to_frame_coords(self, roi_x: int, roi_y: int) -> Tuple[int, int]:
        """將 ROI 座標轉換為影像座標"""
        return roi_x + self.roi_x1, roi_y + self.roi_y1
    
    def convert_frame_to_roi_coords(self, frame_x: int, frame_y: int) -> Tuple[int, int]:
        """將影像座標轉換為 ROI 座標"""
        return frame_x - self.roi_x1, frame_y - self.roi_y1
    
    def is_in_roi(self, x: int, y: int) -> bool:
        """檢查座標是否在 ROI 内"""
        return self.roi_x1 <= x <= self.roi_x2 and self.roi_y1 <= y <= self.roi_y2


# ============================================================================
# 自適應追蹤參數調整器
# ============================================================================

class AdaptiveTracker:
    """自適應追蹤 - 動態調整追蹤策略"""
    
    def __init__(self, initial_distance_threshold: int = 120, max_missed_frames: int = 15):
        """
        初始化自適應追蹤器
        
        Args:
            initial_distance_threshold: 初始距離閾值
            max_missed_frames: 最大連續遺漏幀數
        """
        self.base_distance_threshold = initial_distance_threshold
        self.max_missed_frames = max_missed_frames
        self.detection_count = 0  # 偵測到的物體數量
        self.false_positive_count = 0  # 誤檢次數
    
    def get_distance_threshold(self) -> int:
        """
        動態計算距離閾值
        
        誤檢較多時擴大閾值，檢測穩定時縮小閾值
        """
        if self.detection_count == 0:
            return self.base_distance_threshold
        
        false_positive_rate = self.false_positive_count / max(1, self.detection_count)
        
        if false_positive_rate > 0.3:
            # 誤檢率高，擴大閾值
            return int(self.base_distance_threshold * 1.5)
        elif false_positive_rate < 0.1:
            # 誤檢率低，縮小閾值
            return int(self.base_distance_threshold * 0.8)
        else:
            return self.base_distance_threshold
    
    def record_detection(self, is_valid: bool = True) -> None:
        """記錄偵測結果"""
        self.detection_count += 1
        if not is_valid:
            self.false_positive_count += 1
    
    def reset_stats(self) -> None:
        """重置統計數據"""
        self.detection_count = 0
        self.false_positive_count = 0


# ============================================================================
# 性能監控器
# ============================================================================

class PerformanceMonitor:
    """監控系統性能指標"""
    
    def __init__(self, window_size: int = 30):
        """
        初始化性能監控器
        
        Args:
            window_size: 移動平均窗口大小
        """
        self.frame_times = []
        self.detection_times = []
        self.tracking_times = []
        self.window_size = window_size
        self.total_frames = 0
        self.total_detections = 0
    
    def add_frame_time(self, elapsed_ms: float) -> None:
        """記錄單幀處理時間"""
        self.frame_times.append(elapsed_ms)
        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)
    
    def add_detection_time(self, elapsed_ms: float) -> None:
        """記錄檢測時間"""
        self.detection_times.append(elapsed_ms)
        if len(self.detection_times) > self.window_size:
            self.detection_times.pop(0)
        self.total_detections += 1
    
    def add_tracking_time(self, elapsed_ms: float) -> None:
        """記錄追蹤時間"""
        self.tracking_times.append(elapsed_ms)
        if len(self.tracking_times) > self.window_size:
            self.tracking_times.pop(0)
    
    def get_fps(self) -> float:
        """計算當前 FPS"""
        if not self.frame_times:
            return 0.0
        avg_time = np.mean(self.frame_times)
        return 1000.0 / avg_time if avg_time > 0 else 0.0
    
    def get_detection_ratio(self) -> float:
        """計算檢測時間占比"""
        if not self.detection_times or not self.frame_times:
            return 0.0
        return (np.mean(self.detection_times) / np.mean(self.frame_times)) * 100
    
    def get_tracking_ratio(self) -> float:
        """計算追蹤時間占比"""
        if not self.tracking_times or not self.frame_times:
            return 0.0
        return (np.mean(self.tracking_times) / np.mean(self.frame_times)) * 100
    
    def get_summary(self) -> Dict:
        """取得性能摘要"""
        return {
            'fps': self.get_fps(),
            'avg_frame_time_ms': np.mean(self.frame_times) if self.frame_times else 0,
            'detection_ratio': self.get_detection_ratio(),
            'tracking_ratio': self.get_tracking_ratio(),
            'total_frames': self.total_frames,
            'total_detections': self.total_detections,
        }
    
    def increment_frame_count(self) -> None:
        """增加幀計數"""
        self.total_frames += 1


# ============================================================================
# 動態閾值調整器
# ============================================================================

class DynamicThresholdAdjuster:
    """動態調整偵測閾值，改善檢測性能"""
    
    def __init__(self, initial_conf: float = 0.2, initial_nms: float = 0.4):
        """
        初始化動態閾值調整器
        
        Args:
            initial_conf: 初始信心度閾值
            initial_nms: 初始 NMS 閾值
        """
        self.base_conf = initial_conf
        self.base_nms = initial_nms
        self.current_conf = initial_conf
        self.current_nms = initial_nms
        self.abnormal_count = 0
        self.total_count = 0
    
    def update_with_result(self, detected_count: int, abnormal_count: int) -> None:
        """
        根據檢測結果動態調整閾值
        
        Args:
            detected_count: 本幀檢測的物體數量
            abnormal_count: 本幀檢測的異常物體數量
        """
        self.total_count += detected_count
        self.abnormal_count += abnormal_count
        
        if self.total_count < 5:
            return  # 數據太少，不調整
        
        abnormal_ratio = self.abnormal_count / self.total_count
        
        if abnormal_ratio > 0.5:
            # 異常物體過多，提高閾值以減少誤檢
            self.current_conf = min(0.5, self.current_conf + 0.02)
            self.current_nms = min(0.7, self.current_nms + 0.02)
        elif abnormal_ratio < 0.05:
            # 異常物體過少，降低閾值以增加檢測
            self.current_conf = max(0.1, self.current_conf - 0.02)
            self.current_nms = max(0.2, self.current_nms - 0.02)
    
    def get_thresholds(self) -> Tuple[float, float]:
        """取得當前的信心度和 NMS 閾值"""
        return self.current_conf, self.current_nms
    
    def reset(self) -> None:
        """重置統計"""
        self.abnormal_count = 0
        self.total_count = 0
