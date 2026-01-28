"""
Jetson TX2 糖果瑕疵检测推理脚本
优化用于边缘设备的实时检测
模型: YOLOv8n (召回率 0.967 - 最适合食品安全)
"""
from ultralytics import YOLO
import cv2
import time
import argparse
from pathlib import Path
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('candy_detector.log'),
        logging.StreamHandler()
    ]
)

class CandyDefectDetector:
    def __init__(self, model_path, conf_threshold=0.3, camera_id=0):
        """
        初始化糖果瑕疵检测器
        
        Args:
            model_path: 模型路径 (.pt, .onnx, .engine)
            conf_threshold: 置信度阈值（降低以提高召回率）
            camera_id: 摄像头 ID 或视频路径
        """
        self.conf_threshold = conf_threshold
        self.camera_id = camera_id
        
        # 加载模型
        logging.info(f"加载模型: {model_path}")
        self.model = YOLO(model_path)
        
        # 性能统计
        self.fps_buffer = []
        self.defect_count = 0
        self.total_frames = 0
        
        # 类别名称
        self.class_names = {0: 'abnormal', 1: 'normal'}
        
    def setup_camera(self):
        """初始化摄像头"""
        logging.info(f"初始化摄像头: {self.camera_id}")
        
        # 尝试使用 GStreamer（Jetson 优化）
        if isinstance(self.camera_id, int):
            # CSI 摄像头的 GStreamer pipeline
            gst_pipeline = (
                f"nvarguscamerasrc sensor-id={self.camera_id} ! "
                "video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! "
                "nvvidconv ! "
                "video/x-raw, width=640, height=640, format=BGRx ! "
                "videoconvert ! "
                "video/x-raw, format=BGR ! "
                "appsink"
            )
            
            cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
            
            if not cap.isOpened():
                logging.warning("GStreamer 失败，使用默认方式")
                cap = cv2.VideoCapture(self.camera_id)
        else:
            cap = cv2.VideoCapture(self.camera_id)
        
        if not cap.isOpened():
            raise RuntimeError(f"无法打开摄像头: {self.camera_id}")
        
        # 设置分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
        
        return cap
    
    def detect_frame(self, frame):
        """
        对单帧进行检测
        
        Returns:
            results: 检测结果
            inference_time: 推理时间 (ms)
        """
        start_time = time.time()
        
        results = self.model.predict(
            frame,
            conf=self.conf_threshold,
            iou=0.5,
            verbose=False,
            device=0  # 使用 GPU
        )
        
        inference_time = (time.time() - start_time) * 1000
        return results[0], inference_time
    
    def draw_results(self, frame, results, inference_time):
        """绘制检测结果"""
        # 使用 YOLO 内置的绘制
        annotated = results.plot()
        
        # 计算 FPS
        fps = 1000 / inference_time if inference_time > 0 else 0
        self.fps_buffer.append(fps)
        if len(self.fps_buffer) > 30:
            self.fps_buffer.pop(0)
        avg_fps = sum(self.fps_buffer) / len(self.fps_buffer)
        
        # 检测到的物体数量
        num_detections = len(results.boxes)
        num_defects = sum(1 for box in results.boxes if int(box.cls[0]) == 0)
        
        # 绘制信息面板
        info_y = 30
        cv2.putText(annotated, f'FPS: {avg_fps:.1f}', (10, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        info_y += 35
        cv2.putText(annotated, f'Inference: {inference_time:.1f}ms', (10, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        info_y += 35
        cv2.putText(annotated, f'Detections: {num_detections}', (10, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # 瑕疵警报
        if num_defects > 0:
            self.defect_count += num_defects
            cv2.putText(annotated, f'DEFECT ALERT: {num_defects}', (10, 140),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            logging.warning(f'检测到瑕疵品: {num_defects} 个')
        
        return annotated
    
    def run(self, display=True, save_video=False):
        """
        运行检测循环
        
        Args:
            display: 是否显示窗口
            save_video: 是否保存视频
        """
        cap = self.setup_camera()
        
        # 视频录制
        if save_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            out = cv2.VideoWriter(f'candy_detection_{timestamp}.mp4', 
                                  fourcc, 20.0, (640, 640))
        
        logging.info("🚀 开始检测...")
        logging.info(f"📊 配置: 置信度阈值 = {self.conf_threshold}")
        logging.info(f"🎯 模型召回率: 0.967 (最适合食品安全)")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logging.error("无法读取摄像头画面")
                    break
                
                self.total_frames += 1
                
                # 检测
                results, inference_time = self.detect_frame(frame)
                
                # 绘制结果
                annotated = self.draw_results(frame, results, inference_time)
                
                # 保存视频
                if save_video:
                    out.write(annotated)
                
                # 显示
                if display:
                    cv2.imshow('Candy Defect Detection - YOLOv8n', annotated)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logging.info("用户退出")
                        break
                    elif key == ord('s'):
                        # 保存截图
                        screenshot_path = f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
                        cv2.imwrite(screenshot_path, annotated)
                        logging.info(f"截图已保存: {screenshot_path}")
        
        except KeyboardInterrupt:
            logging.info("检测被中断")
        
        finally:
            # 清理
            cap.release()
            if save_video:
                out.release()
            if display:
                cv2.destroyAllWindows()
            
            # 统计信息
            logging.info("\n" + "=" * 50)
            logging.info("检测统计:")
            logging.info(f"  总帧数: {self.total_frames}")
            logging.info(f"  检测到的瑕疵品: {self.defect_count}")
            if self.fps_buffer:
                logging.info(f"  平均 FPS: {sum(self.fps_buffer)/len(self.fps_buffer):.2f}")
            logging.info("=" * 50)

def main():
    parser = argparse.ArgumentParser(description='Jetson TX2 糖果瑕疵检测')
    parser.add_argument('--model', type=str, default='yolov8n_candy_fp16.engine',
                        help='模型路径 (.pt, .onnx, .engine)')
    parser.add_argument('--conf', type=float, default=0.3,
                        help='置信度阈值 (默认 0.3 以提高召回率)')
    parser.add_argument('--camera', type=int, default=0,
                        help='摄像头 ID')
    parser.add_argument('--no-display', action='store_true',
                        help='不显示窗口（无头模式）')
    parser.add_argument('--save-video', action='store_true',
                        help='保存检测视频')
    
    args = parser.parse_args()
    
    # 检查模型文件
    if not Path(args.model).exists():
        logging.error(f"模型文件不存在: {args.model}")
        logging.info("\n请确保:")
        logging.info("1. 已从训练机器导出模型")
        logging.info("2. 已传输到 Jetson TX2")
        logging.info("3. 模型路径正确")
        return
    
    # 启动检测器
    detector = CandyDefectDetector(
        model_path=args.model,
        conf_threshold=args.conf,
        camera_id=args.camera
    )
    
    detector.run(
        display=not args.no_display,
        save_video=args.save_video
    )

if __name__ == '__main__':
    main()
