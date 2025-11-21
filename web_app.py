"""
糖果瑕疵偵測系統 Web 介面
提供即時影像串流、數據儀表板、歷史記錄查詢等功能
"""

from flask import Flask, render_template, Response, jsonify, request
from flask_cors import CORS
import cv2
import time
import threading
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

from candy_detector.config import ConfigManager
from candy_detector.models import CameraContext, TrackState
from candy_detector.constants import (
    TRACK_DISTANCE_THRESHOLD_PX,
    MAX_MISSED_FRAMES,
    CLASS_NORMAL,
    CLASS_ABNORMAL,
)
from candy_detector.logger import get_logger, setup_logger, APP_LOG_FILE

# 初始化 Flask
app = Flask(__name__)
CORS(app)

# 設置日誌
setup_logger("candy_detector", APP_LOG_FILE)
logger = get_logger("candy_detector.web")

# 全域變數
camera_contexts = []
model = None
class_names = []
config_manager = None
db_path = Path(__file__).parent / "detection_data.db"
lock = threading.Lock()
is_running = False


def init_database():
    """初始化 SQLite 資料庫"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_count INTEGER DEFAULT 0,
            normal_count INTEGER DEFAULT 0,
            abnormal_count INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defect_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            image_path TEXT,
            confidence REAL
        )
    """)

    conn.commit()
    conn.close()
    logger.info("資料庫初始化完成")


def save_detection_record(camera_name, total, normal, abnormal):
    """儲存偵測記錄到資料庫"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO detections (camera_name, total_count, normal_count, abnormal_count) VALUES (?, ?, ?, ?)",
            (camera_name, total, normal, abnormal)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"儲存偵測記錄失敗: {e}")


def load_yolo_model():
    """載入 YOLO 模型"""
    global model, class_names, config_manager

    config_manager = ConfigManager()
    config = config_manager.config

    from run_detector import load_yolo_model as load_model
    model, class_names = load_model(config)
    logger.info("YOLO 模型載入成功")


def initialize_cameras(camera_sections):
    """初始化攝影機"""
    global camera_contexts

    config = config_manager.config
    from run_detector import create_camera_context

    for section in camera_sections:
        if section not in config:
            logger.warning(f"找不到攝影機設定: {section}")
            continue

        cam_ctx = create_camera_context(config, section)
        if cam_ctx:
            camera_contexts.append(cam_ctx)
            logger.info(f"攝影機 {cam_ctx.name} 初始化成功")


def generate_frames(camera_index=0):
    """產生影像串流"""
    global camera_contexts, model, class_names, is_running

    if camera_index >= len(camera_contexts):
        return

    cam_ctx = camera_contexts[camera_index]
    config = config_manager.config
    conf_threshold = config.getfloat('Detection', 'confidence_threshold')
    nms_threshold = config.getfloat('Detection', 'nms_threshold')

    from run_detector import process_camera_frame
    start_time = time.time()

    while is_running:
        elapsed_time = time.time() - start_time
        colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0)]

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
            # 每 10 秒儲存一次記錄
            if int(elapsed_time) % 10 == 0 and cam_ctx.frame_index % 300 == 0:
                save_detection_record(
                    cam_ctx.name,
                    cam_ctx.total_num,
                    cam_ctx.normal_num,
                    cam_ctx.abnormal_num
                )

            # 編碼為 JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.03)  # 約 30 FPS


@app.route('/')
def index():
    """主頁"""
    return render_template('index.html')


@app.route('/video_feed/<int:camera_index>')
def video_feed(camera_index):
    """影像串流路由"""
    return Response(
        generate_frames(camera_index),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/stats')
def get_stats():
    """取得即時統計數據"""
    with lock:
        stats = []
        for cam_ctx in camera_contexts:
            stats.append({
                'name': cam_ctx.name,
                'total': cam_ctx.total_num,
                'normal': cam_ctx.normal_num,
                'abnormal': cam_ctx.abnormal_num,
                'defect_rate': round(cam_ctx.abnormal_num / cam_ctx.total_num * 100, 2) if cam_ctx.total_num > 0 else 0
            })
        return jsonify(stats)


@app.route('/api/history')
def get_history():
    """取得歷史記錄"""
    try:
        hours = request.args.get('hours', default=24, type=int)
        camera = request.args.get('camera', default='', type=str)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
            SELECT camera_name, timestamp, total_count, normal_count, abnormal_count
            FROM detections
            WHERE timestamp >= datetime('now', '-{} hours')
        """.format(hours)

        if camera:
            query += f" AND camera_name = '{camera}'"

        query += " ORDER BY timestamp DESC LIMIT 1000"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                'camera': row[0],
                'timestamp': row[1],
                'total': row[2],
                'normal': row[3],
                'abnormal': row[4],
                'defect_rate': round(row[4] / row[2] * 100, 2) if row[2] > 0 else 0
            })

        return jsonify(history)
    except Exception as e:
        logger.error(f"查詢歷史記錄失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """設定管理"""
    if request.method == 'GET':
        config_dict = {}
        for section in config_manager.config.sections():
            config_dict[section] = dict(config_manager.config[section])
        return jsonify(config_dict)

    elif request.method == 'POST':
        try:
            new_config = request.json
            for section, values in new_config.items():
                if section not in config_manager.config:
                    config_manager.config.add_section(section)
                for key, value in values.items():
                    config_manager.config.set(section, key, str(value))

            # 儲存到檔案
            with open('config.ini', 'w', encoding='utf-8') as f:
                config_manager.config.write(f)

            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"更新設定失敗: {e}")
            return jsonify({'error': str(e)}), 500


@app.route('/api/cameras')
def get_cameras():
    """取得攝影機列表"""
    cameras = [{'index': i, 'name': cam.name} for i, cam in enumerate(camera_contexts)]
    return jsonify(cameras)


def start_detection():
    """啟動偵測系統"""
    global is_running
    is_running = True
    logger.info("偵測系統已啟動")


def stop_detection():
    """停止偵測系統"""
    global is_running, camera_contexts
    is_running = False

    for cam_ctx in camera_contexts:
        cam_ctx.release()

    camera_contexts.clear()
    logger.info("偵測系統已停止")


if __name__ == '__main__':
    # 初始化
    init_database()
    load_yolo_model()
    initialize_cameras(['Camera1', 'Camera2'])
    start_detection()

    try:
        # 啟動 Web 伺服器
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    finally:
        stop_detection()
