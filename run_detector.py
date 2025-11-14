import cv2
import time
import os
import requests
import math
import numpy as np
import threading
import argparse
import configparser

# 專案根目錄，用於將相對路徑轉換為絕對路徑
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def setup_config(config_file='config.ini'):
    """讀取並解析設定檔"""
    config = configparser.ConfigParser()
    config_path = os.path.join(PROJECT_ROOT, config_file)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"設定檔 '{config_path}' 不存在！")
    config.read(config_path)
    return config

def load_yolo_model(config):
    """根據設定檔載入 YOLO 模型，並將相對路徑轉換為絕對路徑"""
    # 將設定檔中的相對路徑轉換為絕對路徑
    weights_path = os.path.join(PROJECT_ROOT, config.get('Paths', 'weights'))
    cfg_path = os.path.join(PROJECT_ROOT, config.get('Paths', 'cfg'))
    classes_path = os.path.join(PROJECT_ROOT, config.get('Paths', 'classes'))

    if not all(os.path.exists(p) for p in [weights_path, cfg_path, classes_path]):
        raise FileNotFoundError(f"模型權重、設定檔或類別檔路徑無效！ Check paths: {weights_path}, {cfg_path}, {classes_path}")

    class_names = []
    with open(classes_path, 'r') as f:
        class_names = [cname.strip() for cname in f.readlines()]

    net = cv2.dnn.readNet(weights_path, cfg_path)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA_FP16)

    model = cv2.dnn_DetectionModel(net)
    input_size = config.getint('Detection', 'input_size')
    model.setInputParams(size=(input_size, input_size), scale=1/255, swapRB=True)
    
    print(f"YOLO 模型載入成功。類別: {class_names}")
    return model, class_names

def trigger_relay(url):
    """使用 requests 發送 HTTP POST 請求來觸發繼電器"""
    try:
        # 增加 timeout 避免請求卡住
        response = requests.post(url, timeout=2)
        print(f"觸發繼電器: {url}, 狀態碼: {response.status_code}")
        if response.status_code != 200:
            print(f"警告: 繼電器 API 回應異常: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"錯誤: 無法觸發繼電器 {url} - {e}")

def main(camera_section):
    """主偵測流程"""
    config = setup_config()
    
    # 讀取通用設定
    conf_threshold = config.getfloat('Detection', 'confidence_threshold')
    nms_threshold = config.getfloat('Detection', 'nms_threshold')
    
    # 讀取指定攝影機的設定
    cam_config = config[camera_section]
    cam_index = cam_config.getint('camera_index')
    cam_name = cam_config.get('camera_name')
    frame_width = cam_config.getint('frame_width')
    frame_height = cam_config.getint('frame_height')
    relay_url = cam_config.get('relay_url')
    line_x1 = cam_config.getint('detection_line_x1')
    line_x2 = cam_config.getint('detection_line_x2')

    # 載入模型
    model, class_names = load_yolo_model(config)
    colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0)]

    # 開啟攝影機
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    if not cap.isOpened():
        print(f"錯誤: 無法開啟攝影機 {cam_index}")
        return

    print(f"執行攝影機: {cam_name} (索引: {cam_index})")

    # 變數初始化
    tracking_objects = {}
    track_id = 1
    total_num, normal_num, abnormal_num = 0, 0, 0
    start_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 偵測
        classes, scores, boxes = model.detect(frame, conf_threshold, nms_threshold)

        current_centers = []
        detected_class_id = -1

        for (classid, score, box) in zip(classes, scores, boxes):
            (x, y, w, h) = box
            cx, cy = int(x + w / 2), int(y + h / 2)
            current_centers.append((cx, cy))
            detected_class_id = classid # 暫存偵測到的類別

            color = colors[int(classid) % len(colors)]
            label = f"{class_names[classid]}: {score:.2f}"
            cv2.rectangle(frame, box, color, 2)
            cv2.putText(frame, label, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # 簡易追蹤與計數邏輯
        new_objects = []
        for pt in current_centers:
            is_new = True
            for obj_id, obj_pt in tracking_objects.items():
                distance = math.hypot(pt[0] - obj_pt[0], pt[1] - obj_pt[1])
                if distance < 100: # 判斷為同一個物件
                    tracking_objects[obj_id] = pt
                    is_new = False
                    break
            if is_new and line_x1 < pt[0] < line_x2:
                new_objects.append(pt)

        for pt in new_objects:
            tracking_objects[track_id] = pt
            track_id += 1
            total_num += 1
            
            if detected_class_id != -1:
                if class_names[detected_class_id] == 'normal':
                    normal_num += 1
                elif class_names[detected_class_id] == 'abnormal':
                    abnormal_num += 1
                    # 使用多執行緒觸發噴氣，避免影像處理被卡住
                    threading.Thread(target=trigger_relay, args=(relay_url,)).start()

        # 移除畫面外的物件
        tracking_objects = {oid: pt for oid, pt in tracking_objects.items() if 0 < pt[0] < frame_width and 0 < pt[1] < frame_height}

        # 繪製畫面元件
        cv2.line(frame, (line_x1, 0), (line_x1, frame_height), (200, 100, 0), 2)
        cv2.line(frame, (line_x2, 0), (line_x2, frame_height), (200, 100, 0), 2)

        elapsed_time = time.time() - start_time
        cv2.putText(frame, f'Time: {elapsed_time:.2f}s', (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 150, 0), 2)
        cv2.putText(frame, f'Total: {total_num}', (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 150, 0), 2)
        cv2.putText(frame, f'Normal: {normal_num}', (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 150, 0), 2)
        cv2.putText(frame, f'Abnormal: {abnormal_num}', (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)

        cv2.imshow(cam_name, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"攝影機 {cam_name} 已關閉。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO 瑕疵偵測程式")
    parser.add_argument("camera_section", type=str, help="要使用的攝影機設定區塊名稱 (例如: Camera1)")
    args = parser.parse_args()
    
    main(args.camera_section)
