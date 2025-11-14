import cv2
import time
import os
import ctypes
import requests
import math
import numpy as np
import threading
import argparse
import configparser
from dataclasses import dataclass, field

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DISPLAY_HEIGHT = 480
AUTO_SCREEN_MARGIN = 80
TRACK_DISTANCE_PX = 120
MAX_MISSED_FRAMES = 15


@dataclass
class TrackState:
    center: tuple[int, int]
    prev_center: tuple[int, int]
    seen_abnormal: bool = False
    counted: bool = False
    triggered: bool = False
    missed_frames: int = 0
    last_class: str = ""
    age: int = 0


@dataclass
class CameraContext:
    name: str
    index: int
    frame_width: int
    frame_height: int
    relay_url: str
    line_x1: int
    line_x2: int
    cap: cv2.VideoCapture
    tracking_objects: dict = field(default_factory=dict)
    track_id: int = 1
    total_num: int = 0
    normal_num: int = 0
    abnormal_num: int = 0
    focus_min: int = 0
    focus_max: int = 255
    frame_index: int = 0

    def release(self) -> None:
        if self.cap and self.cap.isOpened():
            self.cap.release()


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
    weights_path = os.path.join(PROJECT_ROOT, config.get('Paths', 'weights'))
    cfg_path = os.path.join(PROJECT_ROOT, config.get('Paths', 'cfg'))
    classes_path = os.path.join(PROJECT_ROOT, config.get('Paths', 'classes'))

    if not all(os.path.exists(p) for p in [weights_path, cfg_path, classes_path]):
        raise FileNotFoundError(
            "模型權重或設定檔路徑不存在，請檢查 config.ini 設定"
        )

    with open(classes_path, 'r', encoding='utf-8') as f:
        class_names = [cname.strip() for cname in f.readlines()]

    net = cv2.dnn.readNet(weights_path, cfg_path)
    model = cv2.dnn_DetectionModel(net)
    input_size = config.getint('Detection', 'input_size')
    # 灰階 YOLO 模型 -> 單通道輸入，不需 swapRB
    model.setInputParams(size=(input_size, input_size), scale=1 / 255, swapRB=False)

    print(f"YOLO 模型載入成功。類別: {class_names}")
    return model, class_names


def trigger_relay(url: str) -> None:
    """對繼電器 API 發送 POST 請求"""
    try:
        response = requests.post(url, timeout=2)
        print(f"觸發繼電器: {url}, 狀態碼: {response.status_code}")
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

    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    if not cap.isOpened():
        print(f"錯誤: 無法開啟攝影機 {cam_index} ({cam_name})")
        cap.release()
        return None

    if use_startup_af:
        initialize_focus(cap, cam_name, frames=af_frames, delay_sec=af_delay_ms / 1000.0)

    print(f"啟動攝影機 {cam_name} (索引: {cam_index})")
    return CameraContext(
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
    )


def process_camera_frame(
    cam_ctx: CameraContext,
    model,
    class_names,
    colors,
    conf_threshold: float,
    nms_threshold: float,
    elapsed_time: float,
) -> np.ndarray | None:
    cam_ctx.frame_index += 1
    ret, frame = cam_ctx.cap.read()
    if not ret:
        print(f"警告: 無法向 {cam_ctx.name} 取得畫面，略過該幀。")
        return None

    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    classes, scores, boxes = model.detect(gray_frame, conf_threshold, nms_threshold)

    detections = []
    for (classid, score, box) in zip(classes, scores, boxes):
        classid = int(classid)
        x, y, w, h = box
        cx, cy = int(x + w / 2), int(y + h / 2)
        label = class_names[classid]
        detections.append({'center': (cx, cy), 'label': label})
        color = colors[classid % len(colors)]
        text_label = f"{label}: {score:.2f}"
        cv2.rectangle(frame, box, color, 2)
        cv2.putText(
            frame,
            text_label,
            (box[0], max(20, box[1] - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )

    remaining = detections[:]
    for track in cam_ctx.tracking_objects.values():
        best_det = None
        best_dist = TRACK_DISTANCE_PX
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
        crossed = (prev_x < line_mid <= curr_x) or (prev_x > line_mid >= curr_x)
        inside_zone = cam_ctx.line_x1 <= curr_x <= cam_ctx.line_x2

        if not track.counted and (crossed or (inside_zone and track.age >= 2)):
            track.counted = True
            cam_ctx.total_num += 1
            if track.seen_abnormal:
                cam_ctx.abnormal_num += 1
                if not track.triggered:
                    track.triggered = True
                    threading.Thread(
                        target=trigger_relay,
                        args=(cam_ctx.relay_url,),
                        daemon=True,
                    ).start()
            else:
                cam_ctx.normal_num += 1

        if not (0 <= track.center[0] <= cam_ctx.frame_width and 0 <= track.center[1] <= cam_ctx.frame_height):
            track.missed_frames += 1

    for track_id in to_remove:
        cam_ctx.tracking_objects.pop(track_id, None)

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

    model, class_names = load_yolo_model(config)
    colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0)]

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
            elapsed_time = time.time() - start_time
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


