"""
性能優化工具 - 提升模型準確度和演算法效率
"""

import cv2
import numpy as np
import time
from collections import deque
from typing import Tuple, List, Optional
import threading


class ModelOptimizer:
    """模型推論優化器"""

    def __init__(self, model, input_size=416):
        self.model = model
        self.input_size = input_size
        self.warmup_done = False
        self.inference_times = deque(maxlen=100)

    def warmup_model(self, iterations=10):
        """模型預熱 - 第一次推論通常較慢，預先執行幾次"""
        if self.warmup_done:
            return

        print("正在預熱模型...")
        dummy_frame = np.zeros((self.input_size, self.input_size), dtype=np.uint8)

        for i in range(iterations):
            _ = self.model.detect(dummy_frame, 0.5, 0.4)
            print(f"預熱進度: {i+1}/{iterations}")

        self.warmup_done = True
        print("模型預熱完成！")

    def get_avg_inference_time(self):
        """取得平均推論時間"""
        if len(self.inference_times) == 0:
            return 0
        return sum(self.inference_times) / len(self.inference_times)

    def detect_optimized(self, frame, conf_threshold, nms_threshold):
        """優化的偵測函數 - 記錄推論時間"""
        start_time = time.time()
        classes, scores, boxes = self.model.detect(frame, conf_threshold, nms_threshold)
        inference_time = (time.time() - start_time) * 1000  # 轉換為毫秒

        self.inference_times.append(inference_time)

        return classes, scores, boxes, inference_time


class ImagePreprocessor:
    """影像預處理優化器 - 提升影像品質和偵測準確度"""

    @staticmethod
    def enhance_contrast(frame, clip_limit=2.0, tile_grid_size=(8, 8)):
        """使用 CLAHE 增強對比度"""
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(frame)

    @staticmethod
    def denoise(frame, h=10, template_window_size=7, search_window_size=21):
        """降噪處理"""
        return cv2.fastNlMeansDenoising(frame, None, h, template_window_size, search_window_size)

    @staticmethod
    def adaptive_threshold(frame, max_value=255, method=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                          threshold_type=cv2.THRESH_BINARY, block_size=11, C=2):
        """自適應閾值處理"""
        return cv2.adaptiveThreshold(frame, max_value, method, threshold_type, block_size, C)

    @staticmethod
    def sharpen(frame):
        """銳化處理 - 增強邊緣"""
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        return cv2.filter2D(frame, -1, kernel)

    @staticmethod
    def auto_brightness(frame, target_mean=128):
        """自動亮度調整"""
        current_mean = np.mean(frame)
        alpha = target_mean / current_mean
        return np.clip(frame * alpha, 0, 255).astype(np.uint8)

    @staticmethod
    def preprocess_frame(frame, enhance_contrast=True, denoise_image=False,
                        sharpen_image=False, auto_brightness_adjust=False):
        """綜合預處理流程"""
        processed = frame.copy()

        # 自動亮度調整
        if auto_brightness_adjust:
            processed = ImagePreprocessor.auto_brightness(processed)

        # 降噪
        if denoise_image:
            processed = ImagePreprocessor.denoise(processed)

        # 增強對比度
        if enhance_contrast:
            processed = ImagePreprocessor.enhance_contrast(processed)

        # 銳化
        if sharpen_image:
            processed = ImagePreprocessor.sharpen(processed)

        return processed


class DeepSORTTracker:
    """改進的物體追蹤器 - 使用卡爾曼濾波預測"""

    def __init__(self, max_age=30, min_hits=3, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks = []
        self.track_id_counter = 1

    def update(self, detections):
        """更新追蹤器"""
        # 簡化版實作，可以整合完整的 DeepSORT
        matched_tracks = []
        unmatched_detections = list(range(len(detections)))

        # 這裡可以加入更複雜的匹配算法（Hungarian算法等）

        return matched_tracks


class AdaptiveThresholdAdjuster:
    """自適應閾值調整器 - 根據偵測結果動態調整"""

    def __init__(self, initial_conf=0.2, initial_nms=0.4):
        self.conf_threshold = initial_conf
        self.nms_threshold = initial_nms
        self.detection_history = deque(maxlen=100)

    def adjust(self, num_detections, target_detections=5):
        """根據偵測數量調整閾值"""
        self.detection_history.append(num_detections)

        if len(self.detection_history) < 50:
            return

        avg_detections = sum(self.detection_history) / len(self.detection_history)

        # 如果偵測太多，提高閾值
        if avg_detections > target_detections * 1.5:
            self.conf_threshold = min(0.5, self.conf_threshold + 0.01)
        # 如果偵測太少，降低閾值
        elif avg_detections < target_detections * 0.5:
            self.conf_threshold = max(0.1, self.conf_threshold - 0.01)

    def get_thresholds(self):
        """取得當前閾值"""
        return self.conf_threshold, self.nms_threshold


class MultiThreadedFrameReader:
    """多線程影像讀取器 - 提升 FPS"""

    def __init__(self, camera_contexts):
        self.camera_contexts = camera_contexts
        self.frames = [None] * len(camera_contexts)
        self.stopped = False
        self.lock = threading.Lock()

    def start(self):
        """啟動讀取線程"""
        for idx, cam_ctx in enumerate(self.camera_contexts):
            t = threading.Thread(target=self._update, args=(idx, cam_ctx), daemon=True)
            t.start()
        return self

    def _update(self, idx, cam_ctx):
        """持續讀取影像"""
        while not self.stopped:
            ret, frame = cam_ctx.cap.read()
            if ret:
                with self.lock:
                    self.frames[idx] = frame
            time.sleep(0.001)

    def read(self, idx):
        """讀取特定攝影機的最新畫面"""
        with self.lock:
            return self.frames[idx]

    def stop(self):
        """停止讀取"""
        self.stopped = True


class PerformanceMonitor:
    """性能監控器"""

    def __init__(self):
        self.fps_history = deque(maxlen=30)
        self.inference_times = deque(maxlen=30)
        self.last_time = time.time()

    def update(self, inference_time=None):
        """更新性能指標"""
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time)
        self.fps_history.append(fps)
        self.last_time = current_time

        if inference_time is not None:
            self.inference_times.append(inference_time)

    def get_avg_fps(self):
        """取得平均 FPS"""
        if len(self.fps_history) == 0:
            return 0
        return sum(self.fps_history) / len(self.fps_history)

    def get_avg_inference_time(self):
        """取得平均推論時間"""
        if len(self.inference_times) == 0:
            return 0
        return sum(self.inference_times) / len(self.inference_times)

    def get_stats(self):
        """取得統計資訊"""
        return {
            'avg_fps': round(self.get_avg_fps(), 2),
            'avg_inference_time': round(self.get_avg_inference_time(), 2),
            'current_fps': round(self.fps_history[-1], 2) if self.fps_history else 0
        }


class ROIOptimizer:
    """ROI 區域優化器 - 只偵測感興趣區域"""

    @staticmethod
    def extract_roi(frame, roi_coords):
        """提取 ROI 區域"""
        x1, y1, x2, y2 = roi_coords
        return frame[y1:y2, x1:x2]

    @staticmethod
    def adjust_detection_coords(boxes, roi_coords):
        """將 ROI 內的座標轉換回原始影像座標"""
        x_offset, y_offset = roi_coords[0], roi_coords[1]
        adjusted_boxes = []

        for box in boxes:
            x, y, w, h = box
            adjusted_boxes.append([x + x_offset, y + y_offset, w, h])

        return adjusted_boxes


def apply_data_augmentation(image):
    """數據增強 - 用於訓練時"""
    augmented_images = []

    # 原始影像
    augmented_images.append(image)

    # 水平翻轉
    augmented_images.append(cv2.flip(image, 1))

    # 輕微旋轉
    rows, cols = image.shape[:2]
    for angle in [-5, 5]:
        M = cv2.getRotationMatrix2D((cols/2, rows/2), angle, 1)
        rotated = cv2.warpAffine(image, M, (cols, rows))
        augmented_images.append(rotated)

    # 亮度調整
    for beta in [-30, 30]:
        adjusted = cv2.convertScaleAbs(image, alpha=1.0, beta=beta)
        augmented_images.append(adjusted)

    # 添加高斯噪聲
    noise = np.random.normal(0, 10, image.shape).astype(np.uint8)
    noisy = cv2.add(image, noise)
    augmented_images.append(noisy)

    return augmented_images
