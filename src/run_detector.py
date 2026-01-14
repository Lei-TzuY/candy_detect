"""
糖果瑕疵偵測系統主程式

使用 YOLO 進行實時瑕疵偵測，支援多攝影機、物體追蹤、
繼電器控制等功能。

使用方法:
    python run_detector.py Camera1 Camera2
    python run_detector.py Camera1
"""

import cv2
import time
import threading
import argparse
import requests
import math
import numpy as np
import os
import ctypes
import configparser
import sys
from pathlib import Path

# 將專案根目錄加入 Python 路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from candy_detector.config import ConfigManager
from candy_detector.models import CameraContext, TrackState
from candy_detector.constants import (
    PROJECT_ROOT,
    TRACK_DISTANCE_THRESHOLD_PX,
    MAX_MISSED_FRAMES,
    DEFAULT_DISPLAY_HEIGHT,
    AUTO_SCREEN_MARGIN,
    RELAY_TIMEOUT_SECONDS,
    DISPLAY_COLORS,
    CLASS_NORMAL,
    CLASS_ABNORMAL,
)
from candy_detector.logger import get_logger, setup_logger, APP_LOG_FILE
from candy_detector.optimization import (
    MultiScaleDetector,
    ROIProcessor,
    KalmanTracker,
    AdaptiveTracker,
    DynamicThresholdAdjuster,
    PerformanceMonitor,
)

# 設置日誌
setup_logger("candy_detector", APP_LOG_FILE)
logger = get_logger("candy_detector.detector")


def setup_config(config_file: str = 'config.ini') -> configparser.ConfigParser:
    """讀取設定檔並回傳 ConfigParser 物件"""
    config = configparser.ConfigParser()
    config_path = os.path.join(PROJECT_ROOT, config_file)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"設定檔 '{config_path}' 不存在")
    config.read(config_path, encoding='utf-8')
    return config


def load_yolo_model(config: configparser.ConfigParser):
    """依設定檔路徑載入 YOLO 模型"""
    weights_path = os.path.normpath(os.path.join(PROJECT_ROOT, config.get('Paths', 'weights')))
    cfg_path = os.path.normpath(os.path.join(PROJECT_ROOT, config.get('Paths', 'cfg')))
    classes_path = os.path.normpath(os.path.join(PROJECT_ROOT, config.get('Paths', 'classes')))

    if not all(os.path.exists(p) for p in [weights_path, cfg_path, classes_path]):
        raise FileNotFoundError(
            f"模型權重或設定檔路徑不存在，請檢查 config.ini 設定\n"
            f"weights: {weights_path} (exists: {os.path.exists(weights_path)})\n"
            f"cfg: {cfg_path} (exists: {os.path.exists(cfg_path)})\n"
            f"classes: {classes_path} (exists: {os.path.exists(classes_path)})"
        )

    with open(classes_path, 'r', encoding='utf-8') as f:
        class_names = [cname.strip() for cname in f.readlines()]

    # OpenCV DNN 無法處理中文路徑，將檔案複製到暫存目錄（使用固定名稱避免重複複製）
    import tempfile
    import shutil
    import atexit
    
    # 使用固定的暫存目錄名稱，如果已存在則重用
    temp_dir = os.path.join(tempfile.gettempdir(), 'candy_yolo_models')
    os.makedirs(temp_dir, exist_ok=True)
    temp_cfg = os.path.join(temp_dir, 'model.cfg')
    temp_weights = os.path.join(temp_dir, 'model.weights')
    
    # 只在檔案不存在或大小不同時才複製（避免重複複製）
    if not os.path.exists(temp_cfg) or os.path.getsize(temp_cfg) != os.path.getsize(cfg_path):
        shutil.copy2(cfg_path, temp_cfg)
        print(f"已複製模型配置到: {temp_cfg}")
    
    if not os.path.exists(temp_weights) or os.path.getsize(temp_weights) != os.path.getsize(weights_path):
        shutil.copy2(weights_path, temp_weights)
        print(f"已複製模型權重到: {temp_weights}")
    
    # 註冊程式結束時清理暫存檔案
    def cleanup_temp_models():
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"已清理暫存模型檔案: {temp_dir}")
        except:
            pass
    atexit.register(cleanup_temp_models)
    
    # 從暫存目錄載入模型
    net = cv2.dnn.readNet(temp_weights, temp_cfg)
    model = cv2.dnn_DetectionModel(net)
    input_size = config.getint('Detection', 'input_size')
    # 灰階 YOLO 模型 -> 單通道輸入，不需 swapRB
    model.setInputParams(size=(input_size, input_size), scale=1 / 255, swapRB=False)

    print(f"YOLO 模型載入成功。類別: {class_names}")
    return model, class_names


def trigger_relay(url: str, delay_ms: int = 0) -> None:
    """對繼電器 API 發送 POST 請求，可選延遲"""
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)
    
    try:
        response = requests.post(url, timeout=2)
        print(f"觸發繼電器: {url}, 狀態碼: {response.status_code}" + (f" (延遲: {delay_ms}ms)" if delay_ms > 0 else ""))
        if response.status_code != 200:
            print(f"警告: 繼電器 API 回傳異常: {response.text}")
    except requests.exceptions.RequestException as exc:
        print(f"錯誤: 無法觸發繼電器 {url} - {exc}")


def resize_for_display(frame: np.ndarray, target_height: int) -> np.ndarray:
    """將影像縮放至指定高度，保持長寬比"""
    height, width = frame.shape[:2]
    if height == 0 or width == 0:
        return frame
    scale = target_height / height
    target_width = max(1, int(width * scale))
    return cv2.resize(frame, (target_width, target_height))


def get_screen_width() -> int | None:
    """取得螢幕寬度，若無法取得則回傳 None"""
    if os.name == 'nt':
        try:
            return ctypes.windll.user32.GetSystemMetrics(0)
        except Exception:
            return None
    try:
        import tkinter as tk
    except Exception:
        return None
    try:
        root = tk.Tk()
        root.withdraw()
        width = root.winfo_screenwidth()
        root.destroy()
        return width
    except Exception:
        return None


def scale_to_fit_width(frame: np.ndarray, max_width: int) -> np.ndarray:
    """若影像寬度超過限制，依比例縮放至指定最大寬度"""
    if max_width <= 0:
        return frame
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame
    scale = max_width / width
    new_height = max(1, int(height * scale))
    return cv2.resize(frame, (max_width, new_height))


def initialize_focus(
    cap: cv2.VideoCapture,
    cam_name: str,
    frames: int = 20,
    delay_sec: float = 0.05,
) -> None:
    """啟動自動對焦一小段時間後鎖定焦距"""
    try:
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    except Exception:
        return

    for _ in range(frames):
        ok, _ = cap.read()
        if not ok:
            break
        cv2.waitKey(1)
        time.sleep(delay_sec)

    focus_value = cap.get(cv2.CAP_PROP_FOCUS)
    try:
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        if focus_value > 0:
            cap.set(cv2.CAP_PROP_FOCUS, focus_value)
    except Exception:
        return

    print(f"{cam_name}: 已鎖定焦距 ({focus_value})")


def setup_focus_trackbars(window_name: str, camera_contexts: list[CameraContext]) -> None:
    """在主視窗建立每個攝影機的焦距滑桿，供人員手動調整焦距"""
    for cam_ctx in camera_contexts:
        trackbar_name = f"{cam_ctx.name} Focus"
        try:
            current_focus = cam_ctx.cap.get(cv2.CAP_PROP_FOCUS)
        except Exception:
            current_focus = 0

        if not isinstance(current_focus, (int, float)):
            current_focus = 0

        if current_focus < cam_ctx.focus_min or current_focus > cam_ctx.focus_max:
            current_focus = cam_ctx.focus_min

        max_val = max(cam_ctx.focus_max, cam_ctx.focus_min + 1)

        def _on_change(val: int, ctx: CameraContext = cam_ctx) -> None:
            try:
                ctx.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                ctx.cap.set(cv2.CAP_PROP_FOCUS, int(val))
            except Exception:
                # 某些攝影機可能不支援手動焦距，忽略錯誤即可
                pass

        cv2.createTrackbar(
            trackbar_name,
            window_name,
            int(current_focus),
            int(max_val),
            _on_change,
        )

        # 為每個攝影機添加延遲時間滑軌（最大延遲 5000 毫秒 = 5 秒）
        delay_trackbar_name = f"{cam_ctx.name} Relay Delay (ms)"
        
        def _on_delay_change(val: int, ctx: CameraContext = cam_ctx) -> None:
            ctx.relay_delay_ms = int(val)

        cv2.createTrackbar(
            delay_trackbar_name,
            window_name,
            cam_ctx.relay_delay_ms,
            5000,
            _on_delay_change,
        )


def create_camera_context(config: configparser.ConfigParser, section: str):
    cam_config = config[section]
    cam_index = cam_config.getint('camera_index')
    cam_name = cam_config.get('camera_name')
    frame_width = cam_config.getint('frame_width')
    frame_height = cam_config.getint('frame_height')
    relay_url = cam_config.get('relay_url')
    line_x1 = cam_config.getint('detection_line_x1')
    line_x2 = cam_config.getint('detection_line_x2')
    use_startup_af = cam_config.getint('use_startup_autofocus', fallback=0)
    af_frames = cam_config.getint('autofocus_frames', fallback=20)
    af_delay_ms = cam_config.getint('autofocus_delay_ms', fallback=50)
    focus_min = cam_config.getint('focus_min', fallback=0)
    focus_max = cam_config.getint('focus_max', fallback=255)
    relay_delay_ms = cam_config.getint('relay_delay_ms', fallback=0)
    default_focus = cam_config.getint('default_focus', fallback=-1)
    
    # 優化相關參數
    use_roi = cam_config.getint('use_roi', fallback=1)
    roi_x1 = cam_config.getint('roi_x1', fallback=0)
    roi_x2 = cam_config.getint('roi_x2', fallback=frame_width)
    roi_y1 = cam_config.getint('roi_y1', fallback=0)
    roi_y2 = cam_config.getint('roi_y2', fallback=frame_height)
    kalman_process_noise = cam_config.getfloat('kalman_process_noise', fallback=0.1)
    kalman_measure_noise = cam_config.getfloat('kalman_measure_noise', fallback=0.5)

    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    if not cap.isOpened():
        print(f"錯誤: 無法開啟攝影機 {cam_index} ({cam_name})")
        cap.release()
        return None

    # 設定曝光以減少殘影（Motion Blur）
    try:
        # 關閉自動曝光
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 0.25 = 手動模式
        # 設定較短的曝光時間（值越小 = 快門越快）
        # -4 到 -13 之間，-7 通常適合快速移動物體
        exposure_value = config.getint(section, 'exposure_value', fallback=-7)
        cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
        logger.info(f"{cam_name}: 已設定曝光值為 {exposure_value} (減少殘影)")
    except Exception as e:
        logger.warning(f"{cam_name}: 設定曝光失敗（可能不支援）: {e}")

    # 設定初始焦距
    if use_startup_af:
        initialize_focus(cap, cam_name, frames=af_frames, delay_sec=af_delay_ms / 1000.0)
    elif default_focus >= 0:
        try:
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            cap.set(cv2.CAP_PROP_FOCUS, default_focus)
            logger.info(f"{cam_name}: 已將初始焦距設為預設值 {default_focus}")
        except Exception as e:
            logger.warning(f"為 {cam_name} 設定預設焦距失敗: {e}")

    # 初始化優化組件
    roi_processor = None
    if use_roi:
        roi_processor = ROIProcessor(frame_width, frame_height, roi_x1, roi_x2, roi_y1, roi_y2)
    
    # 讀取全局優化設置
    detection_config = config['Detection']
    use_kalman = detection_config.getint('use_kalman_filter', fallback=1)
    use_adaptive = detection_config.getint('use_adaptive_tracking', fallback=1)

    print(f"啟動攝影機 {cam_name} (索引: {cam_index})")
    ctx = CameraContext(
        name=cam_name,
        index=cam_index,
        frame_width=frame_width,
        frame_height=frame_height,
        relay_url=relay_url,
        line_x1=line_x1,
        line_x2=line_x2,
        cap=cap,
        focus_min=focus_min,
        focus_max=focus_max,
        relay_delay_ms=relay_delay_ms,
        use_roi=use_roi and roi_processor is not None,
        roi_processor=roi_processor,
        use_kalman=use_kalman == 1,
        use_adaptive=use_adaptive == 1,
        adaptive_tracker=AdaptiveTracker() if use_adaptive == 1 else None,
    )
    return ctx


def process_camera_frame(
    cam_ctx: CameraContext,
    model,
    class_names,
    colors,
    conf_threshold: float,
    nms_threshold: float,
    elapsed_time: float,
    draw_annotations: bool = True,
    multi_scale_detector=None,
    model_lock=None,
) -> np.ndarray | None:
    cam_ctx.frame_index += 1
    ret, frame = cam_ctx.cap.read()
    if not ret:
        print(f"警告: 無法向 {cam_ctx.name} 取得畫面，略過該幀。")
        return None

    # 提取 ROI（如果啟用）
    detection_frame = frame
    if cam_ctx.use_roi and cam_ctx.roi_processor:
        detection_frame = cam_ctx.roi_processor.extract_roi(frame)
    
    # 執行檢測
    if multi_scale_detector:
        # 使用多尺度檢測
        detections_raw = multi_scale_detector.detect_multi_scale(detection_frame, model, conf_threshold, nms_threshold)
        detections = []
        for det in detections_raw:
            classid = det['classid']
            score = det['score']
            cx, cy = det['center']
            
            # 如果使用 ROI，轉換座標
            if cam_ctx.use_roi and cam_ctx.roi_processor:
                cx, cy = cam_ctx.roi_processor.convert_roi_to_frame_coords(cx, cy)
            
            label = class_names[classid]
            detections.append({'center': (cx, cy), 'label': label, 'score': score, 'bbox': det['bbox']})
    else:
        # 標準檢測
        gray_frame = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2GRAY)
        
        # 使用鎖保護模型檢測，防止多線程衝突
        if model_lock:
            with model_lock:
                classes, scores, boxes = model.detect(gray_frame, conf_threshold, nms_threshold)
        else:
            classes, scores, boxes = model.detect(gray_frame, conf_threshold, nms_threshold)

        detections = []
        for (classid, score, box) in zip(classes, scores, boxes):
            classid = int(classid)
            x, y, w, h = box
            cx, cy = int(x + w / 2), int(y + h / 2)
            
            # 如果使用 ROI，轉換座標
            if cam_ctx.use_roi and cam_ctx.roi_processor:
                cx, cy = cam_ctx.roi_processor.convert_roi_to_frame_coords(cx, cy)
            
            label = class_names[classid]
            detections.append({'center': (cx, cy), 'label': label, 'score': score, 'bbox': box})
    
    # ??s??????
    if draw_annotations:
        for det in detections:
            cx, cy = det['center']
            label = det['label']
            score = det['score']
            classid = class_names.index(label)
            color = colors[classid % len(colors)]
            text_label = f"{label}: {score:.2f}"
            
            # ??s?????
            x, y, w, h = det['bbox']
            if cam_ctx.use_roi and cam_ctx.roi_processor:
                x, y = cam_ctx.roi_processor.convert_roi_to_frame_coords(x, y)
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                frame,
                text_label,
                (x, max(20, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )

    remaining = detections[:]
    for track in cam_ctx.tracking_objects.values():
        best_det = None
        best_dist = TRACK_DISTANCE_THRESHOLD_PX
        for det in remaining:
            distance = math.hypot(track.center[0] - det['center'][0], track.center[1] - det['center'][1])
            if distance < best_dist:
                best_dist = distance
                best_det = det

        if best_det:
            track.prev_center = track.center
            track.center = best_det['center']
            track.last_class = best_det['label']
            if best_det['label'] == 'abnormal':
                track.seen_abnormal = True
            track.missed_frames = 0
            remaining.remove(best_det)
        else:
            track.missed_frames += 1
        track.age += 1

    for det in remaining:
        new_track = TrackState(
            center=det['center'],
            prev_center=det['center'],
            seen_abnormal=(det['label'] == 'abnormal'),
            last_class=det['label'],
        )
        cam_ctx.tracking_objects[cam_ctx.track_id] = new_track
        cam_ctx.track_id += 1

    line_mid = (cam_ctx.line_x1 + cam_ctx.line_x2) // 2
    to_remove = []
    for track_id, track in cam_ctx.tracking_objects.items():
        if track.missed_frames > MAX_MISSED_FRAMES:
            to_remove.append(track_id)
            continue

        prev_x = track.prev_center[0]
        curr_x = track.center[0]
        # 檢查是否真的穿越偵測線（前一幀在線的一側，當前幀在另一側）
        crossed = (prev_x < line_mid <= curr_x) or (prev_x > line_mid >= curr_x)
        
        # 只有在真正穿越偵測線時才計數，移除靜止物體誤計數的問題
        if not track.counted and crossed:
            track.counted = True
            cam_ctx.total_num += 1
            if track.seen_abnormal:
                cam_ctx.abnormal_num += 1
                if not track.triggered:
                    track.triggered = True
                    # 檢查是否暫停噴氣
                    if not getattr(cam_ctx, 'relay_paused', False):
                        threading.Thread(
                            target=trigger_relay,
                            args=(cam_ctx.relay_url, cam_ctx.relay_delay_ms),
                            daemon=True,
                        ).start()
                    else:
                        print(f"[{cam_ctx.name}] 檢測到異常但噴氣已暫停，略過觸發")
            else:
                cam_ctx.normal_num += 1

        if not (0 <= track.center[0] <= cam_ctx.frame_width and 0 <= track.center[1] <= cam_ctx.frame_height):
            track.missed_frames += 1

    for track_id in to_remove:
        cam_ctx.tracking_objects.pop(track_id, None)

    if draw_annotations:
        for object_id, track in cam_ctx.tracking_objects.items():
            pt = track.center
            cv2.circle(frame, pt, 5, (0, 0, 255), -1)
            cv2.putText(
                frame,
                str(object_id),
                (pt[0], pt[1] - 7),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2,
            )

    cv2.line(frame, (cam_ctx.line_x1, 0), (cam_ctx.line_x1, cam_ctx.frame_height), (200, 100, 0), 2)
    cv2.line(frame, (cam_ctx.line_x2, 0), (cam_ctx.line_x2, cam_ctx.frame_height), (200, 100, 0), 2)

    cv2.putText(frame, cam_ctx.name, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 2)
    cv2.putText(frame, f'Time: {elapsed_time:.1f}s', (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 200, 0), 2)
    cv2.putText(frame, f'Total: {cam_ctx.total_num}', (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 200, 0), 2)
    cv2.putText(frame, f'Normal: {cam_ctx.normal_num}', (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 200, 0), 2)
    cv2.putText(frame, f'Abnormal: {cam_ctx.abnormal_num}', (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 200), 2)

    return frame

def main(camera_sections: list[str]) -> None:
    """主偵測流程，可同時處理多個攝影機"""
    config = setup_config()
    conf_threshold = config.getfloat('Detection', 'confidence_threshold')
    nms_threshold = config.getfloat('Detection', 'nms_threshold')
    display_height = config.getint('Display', 'target_height', fallback=DEFAULT_DISPLAY_HEIGHT)
    max_display_width = config.getint('Display', 'max_width', fallback=0)

    # 優化設置
    use_multi_scale = config.getint('Detection', 'use_multi_scale', fallback=0) == 1
    multi_scale_str = config.get('Detection', 'multi_scale_factors', fallback='0.75,1.0,1.25')
    multi_scale_factors = [float(x.strip()) for x in multi_scale_str.split(',')]
    
    model, class_names = load_yolo_model(config)
    colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0)]
    
    # 初始化多尺度檢測器
    multi_scale_detector = MultiScaleDetector(multi_scale_factors) if use_multi_scale else None
    
    # 初始化性能監控
    perf_monitor = PerformanceMonitor(window_size=30)

    camera_contexts = []
    for section in camera_sections:
        if section not in config:
            print(f"警告: config.ini 中找不到區塊 '{section}'，已略過。")
            continue
        cam_ctx = create_camera_context(config, section)
        if cam_ctx:
            camera_contexts.append(cam_ctx)

    if not camera_contexts:
        print("沒有可用攝影機，程式結束。")
        return

    window_name = 'Candy Monitor' if len(camera_contexts) > 1 else camera_contexts[0].name
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    setup_focus_trackbars(window_name, camera_contexts)
    start_time = time.time()

    try:
        while True:
            frame_start_time = time.time()
            elapsed_time = frame_start_time - start_time
            processed_frames = []
            
            for cam_ctx in camera_contexts:
                frame = process_camera_frame(
                    cam_ctx,
                    model,
                    class_names,
                    colors,
                    conf_threshold,
                    nms_threshold,
                    elapsed_time,
                    multi_scale_detector=multi_scale_detector,
                )
                if frame is not None:
                    processed_frames.append(frame)

            if not processed_frames:
                print("所有攝影機都沒有畫面可以顯示，程式結束。")
                break

            if len(processed_frames) > 1:
                resized_frames = [resize_for_display(frame, display_height) for frame in processed_frames]
                composite_frame = np.hstack(resized_frames)
            else:
                composite_frame = resize_for_display(processed_frames[0], display_height)

            effective_max_width = max_display_width
            if effective_max_width <= 0:
                screen_width = get_screen_width()
                if screen_width:
                    effective_max_width = max(0, screen_width - AUTO_SCREEN_MARGIN)
            if effective_max_width and effective_max_width > 0:
                composite_frame = scale_to_fit_width(composite_frame, int(effective_max_width))

            cv2.imshow(window_name, composite_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        for cam_ctx in camera_contexts:
            cam_ctx.release()
        cv2.destroyAllWindows()
        print("所有攝影機已關閉。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO 瑕疵偵測程式 (可多攝影機)")
    parser.add_argument(
        "camera_sections",
        nargs='+',
        help="要使用的攝影機設定區塊名稱，例如: Camera1 Camera2",
    )
    args = parser.parse_args()

    main(args.camera_sections)


