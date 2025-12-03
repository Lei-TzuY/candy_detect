"""
糖果瑕疵偵測系統 Web 介面
提供即時影像串流、數據儀表板、歷史記錄查詢等功能
"""

from flask import Flask, render_template, Response, jsonify, request, send_from_directory
from flask_cors import CORS
import cv2
import time
import threading
import json
import sqlite3
import io
import csv
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import subprocess
import os
import sys

# 將專案根目錄加入 Python 路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from candy_detector.config import ConfigManager
from candy_detector.models import CameraContext, TrackState
from candy_detector.constants import (
    PROJECT_ROOT,
    TRACK_DISTANCE_THRESHOLD_PX,
    MAX_MISSED_FRAMES,
    CLASS_NORMAL,
    CLASS_ABNORMAL,
)
from candy_detector.logger import get_logger, setup_logger, APP_LOG_FILE
from src.video_recorder import VideoRecorder, get_recorder, cleanup_all as cleanup_recorders
from src.run_detector import trigger_relay
import src.yolov8_trainer as trainer

# 初始化 Flask（指定模板和靜態檔案路徑）
app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / 'templates'),
    static_folder=str(PROJECT_ROOT / 'static')
)
CORS(app)

# 禁用靜態檔案快取（開發時使用）
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    """確保靜態檔案不被快取"""
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# 設置日誌
setup_logger("candy_detector", APP_LOG_FILE)
logger = get_logger("candy_detector.web")

# 全域變數
camera_contexts = []
model = None
class_names = []
config_manager = None
db_path = PROJECT_ROOT / "detection_data.db"
lock = threading.Lock()
is_running = False


def init_database():
    """初始化 SQLite 資料庫與索引"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_count INTEGER DEFAULT 0,
            normal_count INTEGER DEFAULT 0,
            abnormal_count INTEGER DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS defect_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            image_path TEXT,
            confidence REAL
        )
        """
    )

    # 建立查詢加速索引（若不存在）
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_ts ON detections(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_cam ON detections(camera_name)")
    except Exception as e:
        logger.warning(f"建立索引失敗（可忽略）: {e}")

    conn.commit()
    conn.close()
    logger.info("資料庫初始化完成（含索引）")


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


def _get_retention_days(default_days: int = 30) -> int:
    """讀取保留天數設定，若無設定則回傳預設值。
    來源：config.ini -> [Retention] max_days
    """
    try:
        cfg = config_manager.config if config_manager else ConfigManager().config
        # configparser 沒有直接 fallback 參數時，使用 get + 預設字串
        value = cfg.get('Retention', 'max_days', fallback=str(default_days))
        days = int(value)
        return max(1, days)
    except Exception:
        return default_days


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
        now = time.time()
        elapsed_time = now - start_time
        colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0)]

        # �p�G�b暫�ժ�j��?�A��?�N��ܪ���?�ߧY
        hide_boxes = False
        hide_until = getattr(cam_ctx, 'hide_boxes_until', 0)
        if hide_until:
            if hide_until < 0:
                hide_boxes = True  # -1 代表持續隱藏，直到再次切換
            else:
                hide_boxes = now < hide_until
                if not hide_boxes:
                    cam_ctx.hide_boxes_until = 0

        frame = process_camera_frame(
            cam_ctx,
            model,
            class_names,
            colors,
            conf_threshold,
            nms_threshold,
            elapsed_time,
            draw_annotations=not hide_boxes,
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


@app.route('/recorder')
def recorder_page():
    """錄影頁面"""
    return render_template('recorder.html')


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


@app.route('/healthz')
def healthz():
    """存活檢查：程序可回應即為健康"""
    try:
        # 簡單的資料庫探活（不失敗即可）
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        return jsonify({'status': 'degraded', 'error': str(e)}), 200

    return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat() + 'Z'})


@app.route('/readyz')
def readyz():
    """就緒檢查：模型載入、相機初始化且偵測迴圈啟動"""
    cams = [
        {
            'name': getattr(c, 'name', f'Camera#{i}'),
            'opened': bool(c.cap is not None and getattr(c.cap, 'isOpened', lambda: False)()),
            'total': getattr(c, 'total_num', 0),
        }
        for i, c in enumerate(camera_contexts)
    ]

    ready = (model is not None) and bool(camera_contexts) and is_running
    status = {
        'ready': ready,
        'model_loaded': model is not None,
        'cameras': cams,
        'is_running': is_running,
    }
    return (jsonify(status), 200) if ready else (jsonify(status), 503)


@app.route('/api/history')
def get_history():
    """取得歷史記錄（支援無限追溯）"""
    try:
        hours = request.args.get('hours', default=24, type=int)
        camera = request.args.get('camera', default='', type=str)
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=500, type=int)
        
        # 限制每頁最多 5000 筆
        per_page = min(per_page, 5000)
        offset = (page - 1) * per_page

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 根據時間範圍構建查詢
        if hours > 0:
            # 有時間限制
            query = (
                "SELECT camera_name, timestamp, total_count, normal_count, abnormal_count "
                "FROM detections WHERE timestamp >= datetime('now', ?)"
            )
            params = [f"-{int(hours)} hours"]
        else:
            # 全部記錄（無時間限制）
            query = (
                "SELECT camera_name, timestamp, total_count, normal_count, abnormal_count "
                "FROM detections WHERE 1=1"
            )
            params = []

        if camera:
            query += " AND camera_name = ?"
            params.append(camera)

        # 計算總筆數
        count_query = query.replace(
            "SELECT camera_name, timestamp, total_count, normal_count, abnormal_count",
            "SELECT COUNT(*)"
        )
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        # 分頁查詢
        query += f" ORDER BY timestamp DESC LIMIT {per_page} OFFSET {offset}"

        cursor.execute(query, params)
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

        return jsonify({
            'data': history,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'total_pages': (total_count + per_page - 1) // per_page if per_page > 0 else 0
            }
        })
    except Exception as e:
        logger.error(f"查詢歷史記錄失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/export')
def export_history_csv():
    """匯出歷史記錄為 CSV（支援 hours / camera 過濾；hours=0 表示全部）"""
    try:
        hours = request.args.get('hours', default=24, type=int)
        camera = request.args.get('camera', default='', type=str)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if hours > 0:
            query = (
                "SELECT camera_name, timestamp, total_count, normal_count, abnormal_count "
                "FROM detections WHERE timestamp >= datetime('now', ?)"
            )
            params = [f"-{int(hours)} hours"]
        else:
            query = (
                "SELECT camera_name, timestamp, total_count, normal_count, abnormal_count "
                "FROM detections WHERE 1=1"
            )
            params = []

        if camera:
            query += " AND camera_name = ?"
            params.append(camera)

        query += " ORDER BY timestamp DESC LIMIT 100000"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # 產生 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["camera", "timestamp", "total", "normal", "abnormal", "defect_rate(%)"])
        for cam, ts, total, normal, abnormal in rows:
            defect_rate = round(abnormal / total * 100, 2) if total else 0
            writer.writerow([cam, ts, total, normal, abnormal, defect_rate])

        csv_data = output.getvalue()
        output.close()

        filename = f"history_{hours if hours > 0 else 'all'}h"
        if camera:
            safe_cam = str(Path(camera).name)
            filename += f"_{safe_cam}"
        filename += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return Response(
            csv_data,
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"匯出歷史記錄失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/cleanup', methods=['POST'])
def cleanup_history():
    """清理早於指定天數的歷史資料。
    請求 JSON 可指定：{"days": 30, "vacuum": false}
    - 若未提供 days，則使用 config.ini 的 [Retention].max_days（預設 30）。
    - vacuum 為 true 時，清理後執行 VACUUM（可能較耗時）。
    回傳：{"success": true, "days": X, "deleted": N, "estimated_before": M}
    """
    try:
        data = request.json or {}
        days = int(data.get('days', 0))
        if days <= 0:
            days = _get_retention_days(30)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 預估刪除筆數
        cursor.execute("SELECT COUNT(*) FROM detections WHERE timestamp < datetime('now', ?)", [f"-{days} days"])
        estimated = cursor.fetchone()[0]

        cursor.execute("DELETE FROM detections WHERE timestamp < datetime('now', ?)", [f"-{days} days"])
        deleted = cursor.rowcount if cursor.rowcount is not None else estimated
        conn.commit()

        # 可選執行 VACUUM（注意：會鎖表一段時間）
        if bool(data.get('vacuum', False)):
            try:
                cursor.execute("VACUUM")
            except Exception as ve:
                logger.warning(f"執行 VACUUM 失敗（可忽略）: {ve}")

        conn.close()
        logger.info(f"歷史清理完成：早於 {days} 天，刪除 {deleted} 筆（估計 {estimated}）")
        return jsonify({
            'success': True,
            'days': days,
            'deleted': int(deleted) if deleted is not None else estimated,
            'estimated_before': int(estimated)
        })
    except Exception as e:
        logger.error(f"清理歷史資料失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_index>/focus', methods=['POST'])
def set_camera_focus(camera_index):
    """設定攝影機焦距（支援自動/手動），並可選擇儲存為預設值"""
    try:
        data = request.json or {}
        focus = int(data.get('focus', 128))
        auto = bool(data.get('auto', False))
        save = bool(data.get('save', False))

        if camera_index < 0 or camera_index >= len(camera_contexts):
            return jsonify({'success': False, 'error': '攝影機索引無效'}), 400

        cam_ctx = camera_contexts[camera_index]
        if cam_ctx.cap is None:
            return jsonify({'success': False, 'error': '攝影機未初始化'}), 400

        try:
            if auto:
                cam_ctx.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                logger.info(f"{cam_ctx.name} 已設定為自動對焦")
            else:
                cam_ctx.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                cam_ctx.cap.set(cv2.CAP_PROP_FOCUS, focus)
                logger.info(f"{cam_ctx.name} 焦距已設定為: {focus}")
            
            # 如果 save 為 True，且為手動對焦，則儲存設定
            if save and not auto:
                section_name = f"Camera{camera_index + 1}"
                if config_manager.config.has_section(section_name):
                    config_manager.config.set(section_name, 'default_focus', str(focus))
                    with open('config.ini', 'w', encoding='utf-8') as f:
                        config_manager.config.write(f)
                    logger.info(f"已將 {cam_ctx.name} 的預設焦距儲存為: {focus}")
                else:
                    logger.warning(f"找不到設定區塊 {section_name}，無法儲存焦距")

        except Exception as e:
            logger.warning(f"設定焦距時相機不支援或失敗: {e}")

        return jsonify({'success': True, 'focus': focus, 'auto': auto, 'saved': save})
    except Exception as e:
        logger.error(f"設定焦距失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_index>/delay', methods=['POST'])
def set_camera_delay(camera_index):
    """設定繼電器延遲時間（毫秒）"""
    try:
        data = request.json or {}
        delay_ms = int(data.get('delay_ms', 1600))

        if camera_index < 0 or camera_index >= len(camera_contexts):
            return jsonify({'success': False, 'error': '攝影機索引無效'}), 400

        cam_ctx = camera_contexts[camera_index]
        cam_ctx.relay_delay_ms = delay_ms
        logger.info(f"{cam_ctx.name} 延遲時間已設定為: {delay_ms}ms")

        return jsonify({'success': True, 'delay_ms': delay_ms})
    except Exception as e:
        logger.error(f"設定延遲時間失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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


@app.route('/api/cameras/detect')
def detect_cameras():
    """偵測可用的攝影機"""
    available = []
    in_use_indices = [cam.camera_index for cam in camera_contexts]
    
    # 檢查索引 0-9 的攝影機
    for i in range(10):
        try:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                # 嘗試讀取一幀確認攝影機真的可用
                ret, _ = cap.read()
                if ret:
                    available.append({
                        'index': i,
                        'in_use': i in in_use_indices,
                        'name': f'Camera {i}'
                    })
                cap.release()
        except Exception as e:
            logger.debug(f"檢查攝影機 {i} 時發生錯誤: {e}")
            continue
    
    return jsonify({
        'available': available,
        'in_use': in_use_indices
    })


@app.route('/api/cameras/add', methods=['POST'])
def add_camera():
    """動態新增攝影機"""
    try:
        data = request.json or {}
        camera_index = data.get('camera_index')
        
        if camera_index is None:
            return jsonify({'success': False, 'error': '未指定攝影機索引'}), 400
        
        # 檢查是否已存在
        for cam in camera_contexts:
            if cam.camera_index == camera_index:
                return jsonify({'success': False, 'error': f'攝影機 {camera_index} 已在使用中'}), 400
        
        # 建立新的攝影機上下文
        from run_detector import CameraContext
        
        new_cam = CameraContext(
            camera_index=camera_index,
            name=f"Camera{len(camera_contexts) + 1}",
            relay_delay_ms=config_manager.get(f'Camera{len(camera_contexts) + 1}', 'relay_delay_ms', fallback=1600) if config_manager else 1600
        )
        
        # 開啟攝影機
        new_cam.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not new_cam.cap.isOpened():
            return jsonify({'success': False, 'error': f'無法開啟攝影機 {camera_index}'}), 500
        
        # 設定解析度
        new_cam.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        new_cam.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        camera_contexts.append(new_cam)
        
        logger.info(f"已新增攝影機 {camera_index}")
        return jsonify({
            'success': True,
            'camera_index': camera_index,
            'name': new_cam.name
        })
        
    except Exception as e:
        logger.error(f"新增攝影機失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_index>/hide_boxes', methods=['POST'])
def hide_boxes(camera_index):
    """????????O????/?????????????????"""
    try:
        cam_ctx = camera_contexts[camera_index]
    except IndexError:
        return jsonify({'error': 'Invalid camera index'}), 404

    data = request.json or {}
    duration = data.get('duration')  # ????????????????????????

    now = time.time()
    hide_until = getattr(cam_ctx, 'hide_boxes_until', 0)
    currently_hidden = (hide_until < 0) or (hide_until > now)

    if currently_hidden:
        # ????????????
        new_hide_until = 0
        hidden = False
    else:
        # ??????????????????
        try:
            duration = float(duration) if duration is not None else None
        except (TypeError, ValueError):
            duration = None

        if duration is not None and duration > 0:
            new_hide_until = now + duration
        else:
            new_hide_until = -1  # ??????????
        hidden = True

    with lock:
        cam_ctx.hide_boxes_until = new_hide_until

    return jsonify({
        'success': True,
        'hidden': hidden,
        'hidden_until': cam_ctx.hide_boxes_until
    })




@app.route('/api/cameras/<int:camera_index>/test_spray', methods=['POST'])
def test_spray(camera_index):
    """手動測試觸發噴氣/繼電器"""
    try:
        cam_ctx = camera_contexts[camera_index]
    except IndexError:
        return jsonify({'error': 'Invalid camera index'}), 404

    if not cam_ctx.relay_url:
        return jsonify({'error': 'Relay URL not configured'}), 400

    delay_ms = max(0, int(getattr(cam_ctx, 'relay_delay_ms', 0)))
    threading.Thread(
        target=trigger_relay,
        args=(cam_ctx.relay_url, delay_ms),
        daemon=True,
    ).start()

    return jsonify({
        'success': True,
        'camera': cam_ctx.name,
        'delay_ms': delay_ms
    })


# ==================== 模型管理 API ====================

@app.route('/api/models')
def list_available_models():
    """列出可用的偵測模型"""
    models = []
    
    # 搜尋 YOLOv4 模型 (darknet 格式)
    yolo_dir = Path('Yolo/darknet-master/build/darknet/x64/train/backup')
    if yolo_dir.exists():
        for weights_file in yolo_dir.glob('*.weights'):
            cfg_name = weights_file.stem.replace('_final', '').replace('_last', '') + '.cfg'
            cfg_file = yolo_dir.parent / cfg_name
            if not cfg_file.exists():
                # 嘗試其他可能的 cfg 位置
                for cfg_path in yolo_dir.parent.glob('*.cfg'):
                    cfg_file = cfg_path
                    break
            
            models.append({
                'name': weights_file.stem,
                'type': 'yolov4',
                'weights': str(weights_file),
                'cfg': str(cfg_file) if cfg_file.exists() else '',
                'size_mb': round(weights_file.stat().st_size / (1024 * 1024), 2)
            })
    
    # 搜尋 YOLOv8 模型 (ultralytics 格式)
    runs_dir = Path('runs/train')
    if runs_dir.exists():
        for run_dir in runs_dir.iterdir():
            if run_dir.is_dir():
                best_pt = run_dir / 'weights' / 'best.pt'
                if best_pt.exists():
                    models.append({
                        'name': f'yolov8_{run_dir.name}',
                        'type': 'yolov8',
                        'weights': str(best_pt),
                        'cfg': '',
                        'size_mb': round(best_pt.stat().st_size / (1024 * 1024), 2)
                    })
    
    # 搜尋根目錄的 .pt 檔案
    for pt_file in Path('.').glob('*.pt'):
        models.append({
            'name': pt_file.stem,
            'type': 'yolov8',
            'weights': str(pt_file),
            'cfg': '',
            'size_mb': round(pt_file.stat().st_size / (1024 * 1024), 2)
        })
    
    return jsonify(models)


@app.route('/api/models/current')
def get_current_model():
    """取得目前使用的模型資訊"""
    config = config_manager.config
    weights = config.get('Paths', 'weights', fallback='')
    cfg = config.get('Paths', 'cfg', fallback='')
    
    return jsonify({
        'weights': weights,
        'cfg': cfg,
        'name': Path(weights).stem if weights else 'Unknown'
    })


@app.route('/api/models/change', methods=['POST'])
def change_model():
    """切換偵測模型"""
    global model, class_names
    
    try:
        data = request.json or {}
        weights = data.get('weights', '')
        cfg = data.get('cfg', '')
        model_type = data.get('type', 'yolov4')
        
        if not weights or not Path(weights).exists():
            return jsonify({'success': False, 'error': '模型檔案不存在'}), 400
        
        # 更新配置檔
        config_manager.config.set('Paths', 'weights', weights)
        if cfg:
            config_manager.config.set('Paths', 'cfg', cfg)
        
        # 儲存配置
        with open('config.ini', 'w', encoding='utf-8') as f:
            config_manager.config.write(f)
        
        # 重新載入模型
        if model_type == 'yolov8':
            # YOLOv8 模型
            try:
                from ultralytics import YOLO
                model = YOLO(weights)
                class_names = model.names if hasattr(model, 'names') else ['normal', 'abnormal']
                logger.info(f"已切換到 YOLOv8 模型: {weights}")
            except ImportError:
                return jsonify({'success': False, 'error': '未安裝 ultralytics，無法載入 YOLOv8 模型'}), 400
        else:
            # YOLOv4 模型 (darknet)
            from run_detector import load_yolo_model as load_model
            model, class_names = load_model(config_manager.config)
            logger.info(f"已切換到 YOLOv4 模型: {weights}")
        
        return jsonify({
            'success': True,
            'message': f'已切換到模型: {Path(weights).stem}',
            'model_type': model_type
        })
        
    except Exception as e:
        logger.error(f"切換模型失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 錄影功能 API ====================

@app.route('/api/recorder/recordings')
def list_recordings():
    """列出所有錄影檔案"""
    try:
        recordings_dir = PROJECT_ROOT / "recordings"
        recordings_dir.mkdir(exist_ok=True)
        
        recordings = []
        for f in sorted(recordings_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            size_mb = stat.st_size / (1024 * 1024)
            date = time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
            recordings.append({
                'name': f.name,
                'size': f"{size_mb:.1f} MB",
                'date': date
            })
        
        # 也檢查 avi 格式
        for f in sorted(recordings_dir.glob("*.avi"), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            size_mb = stat.st_size / (1024 * 1024)
            date = time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
            recordings.append({
                'name': f.name,
                'size': f"{size_mb:.1f} MB",
                'date': date
            })
        
        return jsonify({'recordings': recordings})
    except Exception as e:
        logger.error(f"列出錄影檔案失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recorder/recordings/<filename>', methods=['DELETE'])
def delete_recording(filename):
    """刪除錄影檔案"""
    try:
        recordings_dir = PROJECT_ROOT / "recordings"
        file_path = recordings_dir / filename
        
        # 安全檢查：確保檔案在 recordings 目錄內
        if not file_path.resolve().parent == recordings_dir.resolve():
            return jsonify({'error': '無效的檔案路徑'}), 400
        
        if file_path.exists():
            file_path.unlink()
            return jsonify({'success': True})
        else:
            return jsonify({'error': '檔案不存在'}), 404
    except Exception as e:
        logger.error(f"刪除錄影檔案失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/recordings/<filename>')
def serve_recording(filename):
    """提供錄影檔案下載"""
    recordings_dir = PROJECT_ROOT / "recordings"
    return send_from_directory(recordings_dir, filename, as_attachment=True)


@app.route('/api/recorder/<int:camera_index>/status')
def recorder_status(camera_index):
    """取得錄影器狀態"""
    try:
        recorder = get_recorder(camera_index)
        return jsonify(recorder.get_status())
    except Exception as e:
        logger.error(f"取得錄影狀態失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recorder/<int:camera_index>/start', methods=['POST'])
def start_recording(camera_index):
    """開始錄影"""
    try:
        recorder = get_recorder(camera_index)
        # 安全取得 filename，處理空 body 情況
        filename = None
        if request.is_json and request.get_json(silent=True):
            filename = request.get_json(silent=True).get('filename')
        result = recorder.start_recording(filename)
        return jsonify(result)
    except Exception as e:
        logger.error(f"開始錄影失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recorder/<int:camera_index>/stop', methods=['POST'])
def stop_recording_api(camera_index):
    """停止錄影"""
    try:
        recorder = get_recorder(camera_index)
        result = recorder.stop_recording()
        return jsonify(result)
    except Exception as e:
        logger.error(f"停止錄影失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recorder/<int:camera_index>/focus', methods=['GET', 'POST'])
def recorder_focus(camera_index):
    """取得或設定焦距"""
    try:
        recorder = get_recorder(camera_index)
        
        if request.method == 'GET':
            return jsonify(recorder.get_focus())
        else:
            data = request.json or {}
            focus_value = data.get('focus', 0)
            auto = data.get('auto', False)
            result = recorder.set_focus(focus_value, auto)
            return jsonify(result)
    except Exception as e:
        logger.error(f"焦距操作失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recorder/<int:camera_index>/preview')
def recorder_preview(camera_index):
    """錄影預覽串流"""
    try:
        recorder = get_recorder(camera_index)
        
        # 確保共享攝影機已連接
        if recorder.shared_cap is None and camera_index < len(camera_contexts):
            cam_ctx = camera_contexts[camera_index]
            if cam_ctx.cap is not None and cam_ctx.cap.isOpened():
                recorder.set_shared_camera(cam_ctx.cap)
                logger.info(f"錄影器 {camera_index}: 已連接共享攝影機")
        
        return Response(
            recorder.generate_preview_stream(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        logger.error(f"預覽串流失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recorder/<int:camera_index>/preview/stop', methods=['POST'])
def stop_recorder_preview(camera_index):
    """停止預覽"""
    try:
        recorder = get_recorder(camera_index)
        recorder.stop_preview()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== YOLOv8 訓練 API ====================

@app.route('/trainer')
def trainer_page():
    """訓練介面頁面"""
    return render_template('trainer.html')


@app.route('/api/training/status')
def training_status():
    """取得訓練狀態"""
    return jsonify(trainer.get_training_status())


@app.route('/api/training/start', methods=['POST'])
def start_training():
    """開始訓練"""
    try:
        config = request.json or {}
        result = trainer.start_training(config)
        return jsonify(result)
    except Exception as e:
        logger.error(f"開始訓練失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/stop', methods=['POST'])
def stop_training():
    """停止訓練"""
    try:
        result = trainer.stop_training()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/prepare-dataset', methods=['POST'])
def prepare_dataset():
    """準備資料集"""
    try:
        data = request.json or {}
        data_dir = data.get('data_dir', '訓練集資料')
        output_dir = data.get('output_dir', 'datasets/candy')
        train_ratio = data.get('train_ratio', 0.8)
        
        stats = trainer.prepare_dataset(data_dir, output_dir, train_ratio)
        
        return jsonify({
            'success': True,
            'stats': stats,
            'data_yaml': str(Path(output_dir) / 'data.yaml')
        })
    except Exception as e:
        logger.error(f"準備資料集失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/models')
def list_trained_models():
    """列出已訓練的模型"""
    try:
        models = trainer.list_models()
        return jsonify(models)
    except Exception as e:
        return jsonify([]), 500


@app.route('/api/training/devices')
def list_devices():
    """列出可用裝置"""
    try:
        devices = trainer.get_available_devices()
        return jsonify(devices)
    except Exception as e:
        return jsonify([{'id': 'cpu', 'name': 'CPU'}])




@app.route('/api/training/evaluate', methods=['POST'])
def evaluate_model_api():
    try:
        data = request.json or {}
        model_path = data.get('model_path', '').strip()
        data_yaml = data.get('data_yaml', '').strip()
        device = data.get('device', 'cpu')
        try:
            conf = float(data.get('conf', 0.25))
        except Exception:
            conf = 0.25
        try:
            iou = float(data.get('iou', 0.6))
        except Exception:
            iou = 0.6

        if not model_path or not data_yaml:
            return jsonify({'success': False, 'error': 'model_path and data_yaml are required'}), 400

        result = trainer.evaluate_model(model_path, data_yaml, device, conf, iou)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"evaluate model failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/training/test-model', methods=['POST'])
def test_model_endpoint():
    """?????????????"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image uploaded'}), 400
        model_path = request.form.get('model_path', '').strip()
        if not model_path:
            return jsonify({'success': False, 'error': 'Model path is required'}), 400
        try:
            conf = float(request.form.get('conf', 0.25))
        except Exception:
            conf = 0.25

        upload_dir = Path('static') / 'test_uploads'
        upload_dir.mkdir(parents=True, exist_ok=True)
        image_file = request.files['image']
        filename = f"upload_{int(time.time() * 1000)}_{Path(image_file.filename).name}"
        saved_path = upload_dir / filename
        image_file.save(saved_path)

        result = trainer.test_model(model_path, saved_path, conf)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"??????: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/training/open-folder', methods=['POST'])
def open_training_folder():
    """開啟訓練資料夾"""
    try:
        import subprocess
        data = request.json or {}
        path = data.get('path', '')
        if path and Path(path).exists():
            subprocess.Popen(f'explorer "{path}"', shell=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recorder/<int:camera_index>/resolution', methods=['POST'])
def set_recorder_resolution(camera_index):
    """設定錄影解析度"""
    try:
        data = request.json or {}
        width = data.get('width', 1920)
        height = data.get('height', 1080)
        
        recorder = get_recorder(camera_index)
        result = recorder.set_resolution(width, height)
        
        if result['success']:
            logger.info(f"錄影機 {camera_index} 解析度設為: {result.get('actual_width')}x{result.get('actual_height')}")
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"設定解析度失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recorder/<int:camera_index>/fps', methods=['POST'])
def set_recorder_fps(camera_index):
    """設定錄影幀率"""
    try:
        data = request.json or {}
        fps = data.get('fps', 30)
        
        recorder = get_recorder(camera_index)
        result = recorder.set_fps(fps)
        
        if result['success']:
            logger.info(f"錄影機 {camera_index} 幀率設為: {result.get('actual_fps')}")
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"設定幀率失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system/restart', methods=['POST'])
def restart_system():
    """接收重啟指令，執行 start_web_app.bat 並關閉目前程序"""
    logger.info("接收到應用程式重啟指令...")

    # 1. 先啟動重啟腳本
    try:
        bat_path = os.path.join(PROJECT_ROOT, "start_web_app.bat")
        # 使用 'start' 'cmd' 和 '/c' 來確保在新視窗中獨立運行
        subprocess.Popen(
            f'start cmd /c "{bat_path}"',
            shell=True,
            cwd=PROJECT_ROOT
        )
        logger.info(f"已觸發重啟腳本: {bat_path}")
    except Exception as e:
        logger.error(f"啟動重啟腳本失敗: {e}")
        return jsonify({'success': False, 'error': f'無法啟動腳本: {e}'}), 500

    # 2. 準備關閉當前進程
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        logger.warning("非 Werkzeug 環境，無法正常關閉。請手動重啟。")
        # 在這種情況下，只返回錯誤，不自動關閉
        return jsonify({'success': False, 'error': '伺服器非 Werkzeug 環境，無法自動重啟。'}), 500
    
    # 3. 在一個延遲線程中執行關閉，以確保響應可以發送出去
    threading.Timer(1.0, shutdown_func).start()
    
    return jsonify({'success': True, 'message': '伺服器正在重啟...'})


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
    cleanup_recorders()  # 清理錄影器
    logger.info("偵測系統已停止")


if __name__ == '__main__':
    import os
    
    # 初始化（避免 debug 模式下重複初始化）
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        init_database()
        load_yolo_model()
        initialize_cameras(['Camera1', 'Camera2'])
        start_detection()

    try:
        # 啟動 Web 伺服器
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    finally:
        stop_detection()


