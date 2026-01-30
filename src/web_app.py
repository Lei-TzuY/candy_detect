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
import send2trash

# 將專案根目錄加入 Python 路徑
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from candy_detector.config import ConfigManager
from candy_detector.models import CameraContext, TrackState
from candy_detector.constants import (
    PROJECT_ROOT,
    TRACK_DISTANCE_THRESHOLD_PX,
    MAX_MISSED_FRAMES,
    CLASS_NORMAL,
    CLASS_ABNORMAL,
)

# 全局進度追蹤器
progress_tracker = {}
from candy_detector.logger import get_logger, setup_logger, APP_LOG_FILE
from src.video_recorder import VideoRecorder, get_recorder, cleanup_all as cleanup_recorders
from src.run_detector import trigger_relay
import src.yolov8_trainer as trainer

# 初始化 Flask（指定模板和靜態檔案路徑）
app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, 'templates'),
    static_folder=os.path.join(PROJECT_ROOT, 'static')
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

# 禁用 Flask 的訪問日誌（減少終端輸出噪音）
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)  # 只顯示錯誤，不顯示訪問日誌

# 全域變數
camera_contexts = []
model = None
class_names = []
config_manager = None
db_path = Path(PROJECT_ROOT) / "detection_data.db"
lock = threading.Lock()
model_lock = threading.Lock()  # 模型檢測鎖，防止多線程衝突
is_running = False
current_model_path = None  # 當前使用的模型路徑
current_custom_images_path = None  # 當前自定義圖片路徑


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


def load_yolo_model(model_path=None):
    """載入 YOLO 模型"""
    global model, class_names, config_manager, current_model_path

    if config_manager is None:
        config_manager = ConfigManager()
    config = config_manager.config

    # 如果指定了模型路徑，臨時修改配置
    if model_path:
        original_weights = config.get('Paths', 'weights')
        config.set('Paths', 'weights', model_path)
        current_model_path = model_path
    else:
        current_model_path = config.get('Paths', 'weights')

    from run_detector import load_yolo_model as load_model
    model, class_names = load_model(config)
    
    # 恢復原始配置（如果有修改）
    if model_path:
        config.set('Paths', 'weights', original_weights)
    
    logger.info(f"YOLO 模型載入成功: {current_model_path}")


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
            
            # 確保焦距設定被應用（攝影機硬體可能重置為預設值）
            try:
                default_focus = config.getint(section, 'default_focus', fallback=-1)
                if default_focus >= 0:
                    cam_ctx.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                    time.sleep(0.1)  # 給硬體一點時間切換到手動模式
                    cam_ctx.cap.set(cv2.CAP_PROP_FOCUS, default_focus)
                    logger.info(f"已為 {cam_ctx.name} 重新應用焦距設定: {default_focus}")
            except Exception as e:
                logger.warning(f"應用焦距設定失敗: {e}")


def generate_frames(camera_index=0):
    """產生影像串流"""
    global camera_contexts, model, class_names, is_running

    if camera_index >= len(camera_contexts):
        return

    cam_ctx = camera_contexts[camera_index]
    config = config_manager.config
    conf_threshold = config.getfloat('Detection', 'confidence_threshold')
    nms_threshold = config.getfloat('Detection', 'nms_threshold')
    model_type = config.get('Paths', 'model_type', fallback='yolov4').lower()

    from run_detector import process_camera_frame
    start_time = time.time()

    while is_running:
        now = time.time()
        elapsed_time = now - start_time
        # 顏色順序：abnormal=紅色, normal=綠色（對應 classes.txt 的順序）
        colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 0)]

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
            model_lock=model_lock,
            model_type=model_type,
            config=config,
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

        time.sleep(0.016)  # 約 60 FPS


@app.route('/')
def index():
    """主頁"""
    return render_template('index.html')


@app.route('/recorder')
def recorder_page():
    """錄影頁面"""
    return render_template('recorder.html')


@app.route('/reports/<path:filename>')
def serve_report(filename):
    """提供報告檔案"""
    reports_dir = Path(PROJECT_ROOT) / 'reports'
    report_path = reports_dir / filename
    
    if report_path.exists() and report_path.suffix == '.html':
        return send_from_directory(reports_dir, filename)
    return "報告不存在", 404


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


@app.route('/api/stats/reset', methods=['POST'])
def reset_stats():
    """重置即時統計數據"""
    try:
        with lock:
            for cam_ctx in camera_contexts:
                cam_ctx.total_num = 0
                cam_ctx.normal_num = 0
                cam_ctx.abnormal_num = 0
                # 清除追蹤物體
                cam_ctx.tracking_objects.clear()
                cam_ctx.track_id = 1
        
        logger.info("統計數據已重置")
        return jsonify({'status': 'success', 'message': '統計數據已重置'})
    except Exception as e:
        logger.error(f"重置統計數據失敗: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/models')
def get_models():
    """獲取所有可用的模型列表（根目錄的預訓練模型和已訓練模型）"""
    try:
        models_list = []
        project_root = Path(PROJECT_ROOT)
        
        # 1. 掃描根目錄的模型文件
        # 1a. 糖果訓練模型（candy_*.pt）
        for model_path in project_root.glob('candy_*.pt'):
            if model_path.is_file():
                relative_path = model_path.relative_to(PROJECT_ROOT)
                size_mb = model_path.stat().st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(model_path.stat().st_mtime)
                
                model_name = model_path.stem
                display_name = f"{model_name} ({size_mb:.1f}MB)"
                
                models_list.append({
                    'name': display_name,
                    'raw_name': model_name,
                    'path': str(relative_path),
                    'size_mb': round(size_mb, 2),
                    'modified': modified.strftime('%Y-%m-%d %H:%M'),
                    'is_current': str(relative_path) == current_model_path,
                    'type': 'candy'  # 標記為糖果專用模型
                })
        

        
        

        

        
        # 按修改時間排序（較新的在前），當前使用的排最前面
        models_list.sort(key=lambda x: (
            -1 if x.get('is_current', False) else 0,  # 當前使用的排前面
            x['modified']  # 按修改時間排序
        ), reverse=True)
        
        return jsonify({
            'success': True,
            'models': models_list,
            'current_model': current_model_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models/switch', methods=['POST'])
def switch_model():
    """切換模型"""
    global model, class_names, current_model_path, is_running
    
    try:
        data = request.get_json()
        model_path = data.get('model_path')
        
        if not model_path:
            return jsonify({'success': False, 'error': '未指定模型路徑'}), 400
        
        # 直接檢查路徑 (支援絕對路徑與相對路徑)
        full_path = Path(model_path)
        if not full_path.exists():
            # 嘗試相對於 PROJECT_ROOT
            full_path = Path(PROJECT_ROOT) / model_path
            if not full_path.exists():
                return jsonify({'success': False, 'error': f'模型檔案不存在: {model_path}'}), 404
            model_path = str(full_path) # 使用完整路徑

        # 更新配置檔 (讓選擇持久化)
        try:
            config_manager.config.set('Paths', 'weights', str(model_path))
            # 同步更新 cfg 如果是 yolov4 (這里簡化處理，因為 switch 通常是 yolov8 pt)
            if str(model_path).endswith('.weights'):
                 # 嘗試尋找對應 cfg
                 cfg_candidate = str(Path(model_path).with_suffix('.cfg'))
                 if Path(cfg_candidate).exists():
                     config_manager.config.set('Paths', 'cfg', cfg_candidate)
            
            with open('config.ini', 'w', encoding='utf-8') as f:
                config_manager.config.write(f)
        except Exception as e:
            logger.warning(f"更新設定檔失敗 (但仍會嘗試切換模型): {e}")
        
        # 暫停檢測
        was_running = is_running
        if was_running:
            is_running = False
            time.sleep(0.5)  # 等待當前幀處理完成
        
        # 重新載入模型
        try:
            with model_lock:
                load_yolo_model(model_path)
            
            # 恢復檢測
            if was_running:
                time.sleep(0.2)
                is_running = True
            
            return jsonify({
                'success': True,
                'message': f'成功切換到模型: {model_path}',
                'current_model': current_model_path
            })
        except Exception as e:
            # 恢復檢測（即使失敗）
            if was_running:
                is_running = True
            raise e
            
    except Exception as e:
        logger.error(f"切換模型失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
            # 將 UTC 時間轉換為台北時間 (UTC+8)
            utc_time = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
            taipei_time = utc_time + timedelta(hours=8)
            
            history.append({
                'camera': row[0],
                'timestamp': taipei_time.strftime('%Y-%m-%d %H:%M:%S'),
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
            # 將 UTC 時間轉換為台北時間 (UTC+8)
            utc_time = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            taipei_time = utc_time + timedelta(hours=8)
            taipei_time_str = taipei_time.strftime('%Y-%m-%d %H:%M:%S')
            
            defect_rate = round(abnormal / total * 100, 2) if total else 0
            writer.writerow([cam, taipei_time_str, total, normal, abnormal, defect_rate])

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


@app.route('/api/cameras/<int:camera_index>/exposure', methods=['POST'])
def set_camera_exposure(camera_index):
    """設定攝影機曝光值（支援自動/手動），並可選擇儲存為預設值"""
    try:
        data = request.json or {}
        exposure = int(data.get('exposure', -7))
        auto = bool(data.get('auto', False))
        save = bool(data.get('save', False))

        if camera_index < 0 or camera_index >= len(camera_contexts):
            return jsonify({'success': False, 'error': '攝影機索引無效'}), 400

        cam_ctx = camera_contexts[camera_index]
        if cam_ctx.cap is None:
            return jsonify({'success': False, 'error': '攝影機未初始化'}), 400

        try:
            if auto:
                cam_ctx.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # 0.75 = 自動模式
                logger.info(f"{cam_ctx.name} 已設定為自動曝光")
            else:
                cam_ctx.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 0.25 = 手動模式
                cam_ctx.cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
                logger.info(f"{cam_ctx.name} 曝光值已設定為: {exposure}")
            
            # 如果 save 為 True，且為手動曝光，則儲存設定
            if save and not auto:
                section_name = f"Camera{camera_index + 1}"
                if config_manager.config.has_section(section_name):
                    config_manager.config.set(section_name, 'exposure_value', str(exposure))
                    with open('config.ini', 'w', encoding='utf-8') as f:
                        config_manager.config.write(f)
                    logger.info(f"已將 {cam_ctx.name} 的預設曝光值儲存為: {exposure}")
                else:
                    logger.warning(f"找不到設定區塊 {section_name}，無法儲存曝光值")

        except Exception as e:
            logger.warning(f"設定曝光值時相機不支援或失敗: {e}")

        return jsonify({'success': True, 'exposure': exposure, 'auto': auto, 'saved': save})
    except Exception as e:
        logger.error(f"設定曝光值失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_index>/delay', methods=['POST'])
def set_camera_delay(camera_index):
    """設定繼電器延遲時間（毫秒），並自動保存到配置文件"""
    try:
        data = request.json or {}
        delay_ms = int(data.get('delay_ms', 1600))

        if camera_index < 0 or camera_index >= len(camera_contexts):
            return jsonify({'success': False, 'error': '攝影機索引無效'}), 400

        cam_ctx = camera_contexts[camera_index]
        cam_ctx.relay_delay_ms = delay_ms
        logger.info(f"{cam_ctx.name} 延遲時間已設定為: {delay_ms}ms")
        
        # 自動保存到配置文件
        try:
            section_name = f"Camera{camera_index + 1}"
            if config_manager.config.has_section(section_name):
                config_manager.config.set(section_name, 'relay_delay_ms', str(delay_ms))
                with open('config.ini', 'w', encoding='utf-8') as f:
                    config_manager.config.write(f)
                logger.info(f"已將 {cam_ctx.name} 的噴氣延遲保存為: {delay_ms}ms")
            else:
                logger.warning(f"找不到設定區塊 {section_name}，無法保存延遲時間")
        except Exception as e:
            logger.warning(f"保存延遲時間到配置文件失敗: {e}")

        return jsonify({'success': True, 'delay_ms': delay_ms})
    except Exception as e:
        logger.error(f"設定延遲時間失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_index>/duration', methods=['POST'])
def set_camera_duration(camera_index):
    """設定繼電器持續時間（毫秒），並自動保存到配置文件"""
    try:
        data = request.json or {}
        duration_ms = int(data.get('duration_ms', 50))
        
        # 限制範圍：最小 10ms，最大 1000ms
        duration_ms = max(10, min(1000, duration_ms))

        if camera_index < 0 or camera_index >= len(camera_contexts):
            return jsonify({'success': False, 'error': '攝影機索引無效'}), 400

        cam_ctx = camera_contexts[camera_index]
        cam_ctx.relay_duration_ms = duration_ms
        logger.info(f"{cam_ctx.name} 持續時間已設定為: {duration_ms}ms")
        
        # 自動保存到配置文件
        try:
            section_name = f"Camera{camera_index + 1}"
            if config_manager.config.has_section(section_name):
                config_manager.config.set(section_name, 'relay_duration_ms', str(duration_ms))
                with open('config.ini', 'w', encoding='utf-8') as f:
                    config_manager.config.write(f)
                logger.info(f"已將 {cam_ctx.name} 的噴氣持續時間保存為: {duration_ms}ms")
            else:
                logger.warning(f"找不到設定區塊 {section_name}，無法保存持續時間")
        except Exception as e:
            logger.warning(f"保存持續時間到配置文件失敗: {e}")

        return jsonify({'success': True, 'duration_ms': duration_ms})
    except Exception as e:
        logger.error(f"設定持續時間失敗: {e}")
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
    cameras = [
        {
            'index': i, 
            'name': cam.name,
            'source_index': cam.index,  # 物理攝影機索引
            'relay_paused': getattr(cam, 'relay_paused', False),
            'is_healthy': cam.cap is not None and cam.cap.isOpened(),
            'read_fail_count': getattr(cam, 'read_fail_count', 0),
            # 添加設定值（讓前端可以顯示當前配置）
            'focus': getattr(cam, 'current_focus', 128),
            'exposure': getattr(cam, 'exposure', -7),
            'relay_delay_ms': getattr(cam, 'relay_delay_ms', 1600),
            'relay_duration_ms': getattr(cam, 'relay_duration_ms', 50)
        } 
        for i, cam in enumerate(camera_contexts)
    ]
    return jsonify(cameras)


@app.route('/api/cameras/detect')
def detect_cameras():
    """偵測可用的攝影機"""
    available = []
    in_use_indices = [cam.index for cam in camera_contexts]
    
    # 檢查索引 0-9 的攝影機
    for i in range(10):
        # 如果已經在使用中，直接添加而不嘗試開啟
        if i in in_use_indices:
            available.append({
                'index': i,
                'in_use': True,
                'name': f'Camera {i}'
            })
            continue

        try:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                # 嘗試讀取一幀確認攝影機真的可用
                ret, _ = cap.read()
                if ret:
                    available.append({
                        'index': i,
                        'in_use': False,
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
            if cam.index == camera_index:
                return jsonify({'success': False, 'error': f'攝影機 {camera_index} 已在使用中'}), 400
        
        # 確定名稱 (Camera3, Camera4, etc.)
        max_num = 0
        for cam in camera_contexts:
            if cam.name.startswith("Camera"):
                try:
                    num = int(cam.name.replace("Camera", ""))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
        new_name = f"Camera{max_num + 1}"
        
        # 開啟攝影機
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return jsonify({'success': False, 'error': f'無法開啟攝影機 {camera_index}'}), 500
        
        # 設定解析度
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # 取得實際解析度
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        from run_detector import CameraContext
        
        # 建立新的攝影機上下文
        new_cam = CameraContext(
            name=new_name,
            index=camera_index,
            frame_width=frame_width,
            frame_height=frame_height,
            relay_url=config_manager.get(new_name, 'relay_url', fallback='') if config_manager else '',
            line_x1=int(frame_width * 0.45),
            line_x2=int(frame_width * 0.55),
            cap=cap,
            relay_delay_ms=config_manager.get(new_name, 'relay_delay_ms', fallback=1600) if config_manager else 1600
        )
        
        camera_contexts.append(new_cam)
        
        logger.info(f"已新增攝影機 {new_name} (Index: {camera_index})")
        return jsonify({
            'success': True,
            'camera_index': camera_index,
            'name': new_cam.name,
            'list_index': len(camera_contexts) - 1
        })
        
    except Exception as e:
        logger.error(f"新增攝影機失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:array_index>', methods=['DELETE'])
def remove_camera(array_index):
    """移除攝影機"""
    try:
        if array_index < 0 or array_index >= len(camera_contexts):
            return jsonify({'success': False, 'error': '無效的攝影機索引'}), 400
            
        cam_ctx = camera_contexts[array_index]
        name = cam_ctx.name
        
        logger.info(f"正在移除攝影機: {name} (List Index: {array_index})")
        
        # 1. 釋放資源
        if cam_ctx.cap is not None:
            cam_ctx.cap.release()
            cam_ctx.cap = None
            
        # 2. 從列表中移除
        camera_contexts.pop(array_index)
        
        logger.info(f"已移除攝影機: {name}")
        return jsonify({'success': True, 'message': f'已移除 {name}'})
        
    except Exception as e:
        logger.error(f"移除攝影機失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_index>/reconnect', methods=['POST'])
def reconnect_camera(camera_index):
    """重新連接攝影機"""
    try:
        if camera_index < 0 or camera_index >= len(camera_contexts):
            return jsonify({'success': False, 'error': '無效的攝影機索引'}), 400
        
        cam_ctx = camera_contexts[camera_index]
        old_cap = cam_ctx.cap
        
        logger.info(f"嘗試重新連接 {cam_ctx.name}...")
        
        # 1. 釋放舊連接
        if old_cap is not None:
            old_cap.release()
            time.sleep(0.5)  # 給系統時間釋放資源
        
        # 2. 重新打開攝影機
        new_cap = cv2.VideoCapture(cam_ctx.index, cv2.CAP_DSHOW)
        
        if not new_cap.isOpened():
            logger.error(f"{cam_ctx.name} 重新連接失敗：無法打開攝影機索引 {cam_ctx.index}")
            # 嘗試恢復舊連接
            cam_ctx.cap = old_cap
            return jsonify({'success': False, 'error': '無法打開攝影機'}), 500
        
        # 3. 設定解析度
        new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_ctx.frame_width)
        new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_ctx.frame_height)
        
        # 4. 測試讀取
        ret, _ = new_cap.read()
        if not ret:
            logger.error(f"{cam_ctx.name} 重新連接失敗：無法讀取畫面")
            new_cap.release()
            cam_ctx.cap = old_cap
            return jsonify({'success': False, 'error': '無法讀取畫面'}), 500
        
        # 5. 應用曝光和焦距設定
        try:
            section_name = f"Camera{camera_index + 1}"
            exposure = config_manager.config.getint(section_name, 'exposure_value', fallback=-7)
            new_cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            new_cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
            
            default_focus = config_manager.config.getint(section_name, 'default_focus', fallback=-1)
            if default_focus >= 0:
                new_cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                time.sleep(0.1)
                new_cap.set(cv2.CAP_PROP_FOCUS, default_focus)
        except Exception as e:
            logger.warning(f"重新應用攝影機參數時發生警告: {e}")
        
        # 6. 更新 context
        cam_ctx.cap = new_cap
        cam_ctx.read_fail_count = 0
        
        logger.info(f"{cam_ctx.name} 重新連接成功")
        return jsonify({'success': True, 'message': f'{cam_ctx.name} 已重新連接'})
        
    except Exception as e:
        logger.error(f"重新連接攝影機失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_index>/source', methods=['POST'])
def switch_camera_source(camera_index):
    """切換攝影機來源（實體 Index）"""
    try:
        data = request.json or {}
        source_index = data.get('source_index')
        
        if source_index is None:
            return jsonify({'success': False, 'error': '未指定來源索引'}), 400
            
        if camera_index < 0 or camera_index >= len(camera_contexts):
            return jsonify({'success': False, 'error': '攝影機索引無效'}), 400

        cam_ctx = camera_contexts[camera_index]
        current_source = cam_ctx.index
        
        if current_source == source_index:
            return jsonify({'success': True, 'message': '來源相同，無需切換'})

        logger.info(f"正在切換 {cam_ctx.name} 來源: {current_source} -> {source_index}")
        
        # 1. 釋放舊的資源
        if cam_ctx.cap is not None:
            cam_ctx.cap.release()
            
        # 2. 開啟新的來源
        new_cap = cv2.VideoCapture(source_index, cv2.CAP_DSHOW)
        
        # 設定與舊的一樣的解析度
        new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_ctx.frame_width)
        new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_ctx.frame_height)
        
        # 檢查是否成功開啟
        if not new_cap.isOpened():
            logger.error(f"無法開啟新的攝影機來源 {source_index}")
            # 嘗試恢復舊的
            cam_ctx.cap = cv2.VideoCapture(current_source, cv2.CAP_DSHOW)
            cam_ctx.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_ctx.frame_width)
            cam_ctx.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_ctx.frame_height)
            return jsonify({'success': False, 'error': f'無法開啟攝影機 {source_index}'}), 500
            
        # 3. 更新上下文
        cam_ctx.cap = new_cap
        cam_ctx.index = source_index
        
        # 4. 更新 config.ini
        section_name = f"Camera{camera_index + 1}"
        if config_manager.config.has_section(section_name):
            config_manager.config.set(section_name, 'camera_index', str(source_index))
            try:
                with open('config.ini', 'w', encoding='utf-8') as f:
                    config_manager.config.write(f)
                logger.info(f"已更新設定檔 {section_name}.camera_index = {source_index}")
            except Exception as e:
                logger.warning(f"更新設定檔失敗: {e}")
        
        # 5. 重設曝光和焦距（新來源可能需要重新設定）
        try:
            # 嘗試應用儲存的設定或預設值
            exposure = config_manager.config.getint(section_name, 'exposure_value', fallback=-5)
            new_cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            new_cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
            
            focus = config_manager.config.getint(section_name, 'default_focus', fallback=80)
            new_cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            new_cap.set(cv2.CAP_PROP_FOCUS, focus)
        except Exception as e:
            logger.warning(f"重設相機參數失敗: {e}")

        logger.info(f"攝影機 {cam_ctx.name} 來源切換成功")
        return jsonify({
            'success': True,
            'camera_index': camera_index,
            'source_index': source_index,
            'name': cam_ctx.name
        })

    except Exception as e:
        logger.error(f"切換攝影機來源失敗: {e}")
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
    duration_ms = max(0, int(getattr(cam_ctx, 'relay_duration_ms', 50)))
    threading.Thread(
        target=trigger_relay,
        args=(cam_ctx.relay_url, delay_ms, duration_ms),
        daemon=True,
    ).start()

    return jsonify({
        'success': True,
        'camera': cam_ctx.name,
        'delay_ms': delay_ms
    })


@app.route('/api/cameras/<int:camera_index>/relay/pause', methods=['POST'])
def toggle_relay_pause(camera_index):
    """切換繼電器暫停狀態"""
    try:
        cam_ctx = camera_contexts[camera_index]
    except IndexError:
        return jsonify({'error': 'Invalid camera index'}), 404

    # 切換狀態
    current_state = getattr(cam_ctx, 'relay_paused', False)
    cam_ctx.relay_paused = not current_state
    
    logger.info(f"{cam_ctx.name} 噴氣功能已{'暫停' if cam_ctx.relay_paused else '恢復'}")

    return jsonify({
        'success': True,
        'camera': cam_ctx.name,
        'paused': cam_ctx.relay_paused
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
        mtime = pt_file.stat().st_mtime
        modified_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        models.append({
            'name': pt_file.stem,
            'type': 'yolov8',
            'weights': str(pt_file),
            'cfg': '',
            'size_mb': round(pt_file.stat().st_size / (1024 * 1024), 2),
            'modified': modified_str
        })

    # 搜尋 datasets 目錄下的 .pt 檔案 (針對使用者回報的路徑)
    datasets_dir = Path('datasets')
    if datasets_dir.exists():
        for pt_file in datasets_dir.rglob('*.pt'):
            # 避免重複添加 (如果跟根目錄重複)
            if any(m['weights'] == str(pt_file) for m in models):
                continue

            mtime = pt_file.stat().st_mtime
            modified_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            
            # 改進命名邏輯
            # 如果是 weights/best.pt 形式，使用實驗名稱 (上一層資料夾)
            if pt_file.parent.name == 'weights' and pt_file.stem in ['best', 'last']:
                exp_name = pt_file.parent.parent.name
                name = f"{exp_name} ({pt_file.stem})"
            # 如果是 runs/detect/exp/best.pt 形式
            elif pt_file.stem in ['best', 'last']:
                name = f"{pt_file.parent.name} ({pt_file.stem})"
            # 一般情況，使用 資料夾/檔名
            else:
                name = f"{pt_file.parent.name}/{pt_file.stem}"

            models.append({
                'name': name,
                'type': 'yolov8',
                'weights': str(pt_file),
                'cfg': '',
                'size_mb': round(pt_file.stat().st_size / (1024 * 1024), 2),
                'modified': modified_str
            })
    
    # 按照修改時間排序 (新的在前)
    models.sort(key=lambda x: x.get('modified', ''), reverse=True)
    
    return jsonify({
        'success': True,
        'models': models
    })


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
        recordings_dir = Path(PROJECT_ROOT) / "recordings"
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
        recordings_dir = Path(PROJECT_ROOT) / "recordings"
        file_path = recordings_dir / filename
        
        # 安全檢查：確保檔案在 recordings 目錄內
        if not file_path.resolve().parent == recordings_dir.resolve():
            return jsonify({'error': '無效的檔案路徑'}), 400
        
        if not file_path.exists():
            return jsonify({'error': '檔案不存在'}), 404
        
        # 檢查檔案是否正在被錄影器使用
        from src.video_recorder import _recorders, _lock
        with _lock:
            for camera_index, recorder in _recorders.items():
                if recorder.is_recording and recorder.current_filename:
                    # 比對檔案名稱（可能包含路徑）
                    if Path(recorder.current_filename).name == filename:
                        return jsonify({
                            'error': f'檔案正在錄影中（鏡頭 {camera_index}），請先停止錄影',
                            'in_use': True,
                            'camera_index': camera_index
                        }), 409  # 409 Conflict
        
        # 移到垃圾桶而非永久刪除
        try:
            send2trash.send2trash(str(file_path))
            logger.info(f"已將錄影檔案移到垃圾桶: {filename}")
            return jsonify({'success': True})
        except PermissionError:
            return jsonify({
                'error': '檔案正在使用中，請稍後再試或關閉正在使用該檔案的程式',
                'in_use': True
            }), 409
            
    except Exception as e:
        logger.error(f"刪除錄影檔案失敗: {e}")
        return jsonify({'error': f'刪除失敗: {str(e)}'}), 500


@app.route('/recordings/<filename>')
def serve_recording(filename):
    """提供錄影檔案下載"""
    recordings_dir = Path(PROJECT_ROOT) / "recordings"
    return send_from_directory(recordings_dir, filename, as_attachment=True)


@app.route('/api/recorder/extract_frames', methods=['POST'])
def extract_video_frames():
    """從單一影片擷取圖像"""
    try:
        data = request.json or {}
        filename = data.get('filename')
        interval = int(data.get('interval', 30))
        max_frames = int(data.get('max_frames', 100))
        
        if not filename:
            return jsonify({'error': '未指定影片檔名'}), 400
            
        video_path = Path(PROJECT_ROOT) / 'recordings' / filename
        if not video_path.exists():
            return jsonify({'error': '找不到影片檔案'}), 404
            
        output_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        
        # 引用 extract_frames 模組功能
        sys.path.insert(0, str(PROJECT_ROOT))
        from extract_frames import extract_frames
        
        # 執行擷取
        count = extract_frames(video_path, output_dir, interval, max_frames)
        
        return jsonify({
            'success': True,
            'count': count,
            'video': filename
        })
    except Exception as e:
        logger.error(f"擷取影像失敗: {e}")
        return jsonify({'error': str(e)}), 500


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
        # 安全取得 filename 和 codec，處理空 body 情況
        filename = None
        codec = None
        if request.is_json and request.get_json(silent=True):
            data = request.get_json(silent=True)
            filename = data.get('filename')
            codec = data.get('codec')
        
        result = recorder.start_recording(filename, codec=codec)
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
        
        # 強制從偵測系統奪取共享攝影機
        if camera_index < len(camera_contexts):
            cam_ctx = camera_contexts[camera_index]
            if cam_ctx.cap is not None and cam_ctx.cap.isOpened():
                recorder.set_shared_camera(cam_ctx.cap)
                logger.info(f"錄影器 {camera_index}: 已連接共享攝影機")
            else:
                logger.warning(f"錄影器 {camera_index}: 偵測系統的攝影機未開啟")
        else:
            logger.warning(f"錄影器 {camera_index}: camera_contexts 中沒有此鏡頭，嘗試獨立開啟")
        
        return Response(
            recorder.generate_preview_stream(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        logger.error(f"預覽串流失敗: {e}", exc_info=True)
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


# ==================== 標註 API ====================

@app.route('/annotate')
def annotate_page():
    """標註頁面"""
    return render_template('annotate.html')


@app.route('/api/annotate/images')
def get_annotation_images():
    """取得可標註的影像列表（支援子資料夾和自訂路徑）"""
    global current_custom_images_path
    try:
        # 檢查是否有自訂路徑參數
        custom_path = request.args.get('custom_path', None)
        
        if custom_path:
            # 使用自訂路徑
            images_dir = Path(custom_path)
            if not images_dir.exists() or not images_dir.is_dir():
                return jsonify({'error': '指定的路徑不存在或不是資料夾'}), 400
            # 保存到全局變量
            current_custom_images_path = str(images_dir)
        else:
            # 使用預設路徑
            images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
            current_custom_images_path = None
        
        labels_dir = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'labels'
        metadata_dir = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'metadata'
        
        logger.info(f"圖片目錄: {images_dir}")
        logger.info(f"目錄存在: {images_dir.exists()}")
        
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # 取得所有子資料夾
        folders = sorted([d.name for d in images_dir.iterdir() if d.is_dir()])
        logger.info(f"找到 {len(folders)} 個資料夾: {folders[:5]}")
        
        # 遞迴搜尋所有子資料夾中的影像
        image_files = list(images_dir.rglob('*.jpg')) + list(images_dir.rglob('*.png'))
        logger.info(f"找到 {len(image_files)} 個圖片檔案")
        
        images_list = []
        for img_file in sorted(image_files):
            # 使用相對路徑作為檔名
            relative_path = img_file.relative_to(images_dir)
            label_file = labels_dir / relative_path.parent / f"{img_file.stem}.txt"
            metadata_file = metadata_dir / relative_path.parent / f"{img_file.stem}.json"
            
            # 讀取標註來源
            label_source = None
            if label_file.exists() and label_file.stat().st_size > 0:
                if metadata_file.exists():
                    try:
                        import json
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            label_source = meta.get('source', 'unknown')
                    except:
                        label_source = 'unknown'
                else:
                    label_source = 'unknown'
            
            images_list.append({
                'name': str(relative_path).replace('\\', '/'),  # 統一使用 / 分隔
                'labeled': label_file.exists() and label_file.stat().st_size > 0,
                'label_source': label_source  # 'ai', 'manual', 'unknown', or None
            })
        
        return jsonify({
            'images': images_list, 
            'folders': folders,
            'custom_path': str(images_dir) if custom_path else None
        })
    except Exception as e:
        logger.error(f"取得影像列表失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/annotate/browse-folder', methods=['POST'])
def browse_folder():
    """瀏覽並選擇資料夾"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # 創建隱藏的 Tkinter 視窗
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # 開啟資料夾選擇對話框
        folder_path = filedialog.askdirectory(
            title='選擇圖片資料夾',
            initialdir=str(Path(PROJECT_ROOT) / 'datasets')
        )
        
        root.destroy()
        
        if folder_path:
            # 檢查資料夾是否包含圖片
            folder_path = Path(folder_path)
            image_count = len(list(folder_path.glob('*.jpg'))) + len(list(folder_path.glob('*.png')))
            
            return jsonify({
                'success': True,
                'path': str(folder_path),
                'image_count': image_count
            })
        else:
            return jsonify({
                'success': False,
                'message': '未選擇資料夾'
            })
            
    except Exception as e:
        logger.error(f"瀏覽資料夾失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/annotate/image/<path:filename>')
def get_annotation_image(filename):
    """取得影像檔案（支援子資料夾路徑和自訂路徑）"""
    global current_custom_images_path
    try:
        # 優先使用全局變量中的自訂路徑
        if current_custom_images_path:
            images_dir = Path(current_custom_images_path)
        else:
            # 檢查 URL 參數
            custom_path = request.args.get('custom_path', None)
            if custom_path:
                images_dir = Path(custom_path)
            else:
                # 使用預設路徑
                images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        
        # 將 URL 路徑轉換為檔案系統路徑
        image_path = images_dir / filename.replace('/', '\\')
        
        if not image_path.exists():
            return jsonify({'error': '影像不存在'}), 404
        
        from flask import send_file
        return send_file(image_path, mimetype='image/jpeg')
    except Exception as e:
        logger.error(f"取得影像失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/annotate/annotations/<path:filename>')
def get_annotations(filename):
    """取得影像的標註（支援子資料夾路徑和自訂路徑）"""
    global current_custom_images_path
    try:
        # 優先使用全局變量中的自訂路徑
        if current_custom_images_path:
            images_dir = Path(current_custom_images_path)
            labels_dir = images_dir.parent / 'labels'
            metadata_dir = images_dir.parent / 'metadata' if (images_dir.parent / 'metadata').exists() else None
        else:
            # 檢查 URL 參數
            custom_path = request.args.get('custom_path', None)
            if custom_path:
                images_dir = Path(custom_path)
                labels_dir = images_dir.parent / 'labels'
                metadata_dir = images_dir.parent / 'metadata' if (images_dir.parent / 'metadata').exists() else None
            else:
                # 使用預設路徑
                labels_dir = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'labels'
                metadata_dir = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'metadata'
        
        # 保留子資料夾結構
        filename_path = Path(filename.replace('/', '\\'))
        label_file = labels_dir / f"{filename_path.stem}.txt"
        metadata_file = metadata_dir / f"{filename_path.stem}.json" if metadata_dir else None
        
        annotations = []
        if label_file.exists():
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id, x_center, y_center, width, height = map(float, parts[:5])
                        confidence = float(parts[5]) if len(parts) >= 6 else None  # 讀取信心分數
                        
                        ann_dict = {
                            'class': int(class_id),
                            'x_center': x_center,
                            'y_center': y_center,
                            'width': width,
                            'height': height
                        }
                        if confidence is not None:
                            ann_dict['confidence'] = confidence
                        annotations.append(ann_dict)
        
        # 讀取標註來源
        label_source = 'unknown'
        if metadata_file and metadata_file.exists():
            try:
                import json
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    label_source = meta.get('source', 'unknown')
            except:
                pass
        
        return jsonify({
            'annotations': annotations,
            'label_source': label_source
        })
    except Exception as e:
        logger.error(f"取得標註失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/annotate/save', methods=['POST'])
def save_annotations():
    """儲存標註（統一儲存到 datasets/annotated/）"""
    try:
        import shutil
        import json
        from datetime import datetime
        
        data = request.json
        filename = data.get('filename')
        annotations = data.get('annotations', [])
        img_width = data.get('image_width')
        img_height = data.get('image_height')
        
        # 來源目錄
        source_images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        
        # 目標目錄（標註完成的影像）
        annotated_dir = Path(PROJECT_ROOT) / 'datasets' / 'annotated'
        
        # 保留子資料夾結構
        filename_path = Path(filename.replace('/', '\\'))
        
        # 建立目標資料夾
        target_label_dir = annotated_dir / 'labels' / filename_path.parent
        target_metadata_dir = annotated_dir / 'metadata' / filename_path.parent
        target_label_dir.mkdir(parents=True, exist_ok=True)
        target_metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # 標籤檔案路徑
        label_file = target_label_dir / f"{filename_path.stem}.txt"
        metadata_file = target_metadata_dir / f"{filename_path.stem}.json"
        
        # 轉換為 YOLO 格式並儲存標籤
        with open(label_file, 'w') as f:
            for ann in annotations:
                # 從像素座標轉換為歸一化座標
                x_center = (ann['x'] + ann['width'] / 2) / img_width
                y_center = (ann['y'] + ann['height'] / 2) / img_height
                width = ann['width'] / img_width
                height = ann['height'] / img_height
                
                f.write(f"{ann['class']} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
        
        # 保存元數據（標註來源）
        metadata = {
            'source': 'manual',  # 手動標註
            'timestamp': datetime.now().isoformat(),
            'image_path': str(filename),
            'annotation_count': len(annotations)
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已儲存標註: {filename} ({len(annotations)} 個) [手動標註] -> datasets/annotated/")
        return jsonify({
            'success': True,
            'saved_to': str(annotated_dir),
            'label_source': 'manual'
        })
    except Exception as e:
        logger.error(f"儲存標註失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/annotate/image/<path:filename>', methods=['DELETE'])
def delete_annotation_image(filename):
    """刪除影像及其標註（支援子資料夾路徑）"""
    try:
        images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        labels_dir = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'labels'
        metadata_dir = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'metadata'
        
        filename_path = Path(filename.replace('/', '\\'))
        image_path = images_dir / filename_path
        label_path = labels_dir / filename_path.parent / f"{filename_path.stem}.txt"
        metadata_path = metadata_dir / filename_path.parent / f"{filename_path.stem}.json"
        
        if image_path.exists():
            send2trash.send2trash(str(image_path))
        if label_path.exists():
            send2trash.send2trash(str(label_path))
        if metadata_path.exists():
            send2trash.send2trash(str(metadata_path))
        
        logger.info(f"已刪除 (資源回收桶): {filename}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"刪除失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/annotate/export', methods=['POST'])
def export_annotation_dataset():
    """匯出標註資料集到訓練目錄（支援子資料夾結構）"""
    try:
        import shutil
        
        # 取得要匯出的檔案列表（如果有的話）
        data = request.get_json() or {}
        files_to_export = data.get('files', None)  # None 表示匯出全部
        
        source_images = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        source_labels = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'labels'
        
        target_images = Path(PROJECT_ROOT) / 'datasets' / 'candy' / 'images' / 'train'
        target_labels = Path(PROJECT_ROOT) / 'datasets' / 'candy' / 'labels' / 'train'
        
        target_images.mkdir(parents=True, exist_ok=True)
        target_labels.mkdir(parents=True, exist_ok=True)
        
        # 如果指定了檔案列表，轉換為 set 以便快速查找
        files_set = set(files_to_export) if files_to_export else None
        
        # 遞迴搜尋所有子資料夾中的標註檔
        exported_count = 0
        for label_file in source_labels.rglob('*.txt'):
            if label_file.stat().st_size > 0:  # 有內容
                # 取得相對路徑
                relative_path = label_file.relative_to(source_labels)
                
                # 尋找對應的影像檔
                image_file = source_images / relative_path.parent / f"{label_file.stem}.jpg"
                if not image_file.exists():
                    image_file = source_images / relative_path.parent / f"{label_file.stem}.png"
                
                if image_file.exists():
                    # 取得影像檔相對於 extracted_frames 的路徑
                    image_relative_path = image_file.relative_to(source_images)
                    image_name = str(image_relative_path).replace('\\', '/')
                    
                    # 如果指定了檔案列表，檢查這個檔案是否在列表中
                    if files_set is not None and image_name not in files_set:
                        continue
                    
                    # 產生唯一檔名（包含子資料夾名稱以避免衝突）
                    unique_name = str(relative_path.parent / label_file.stem).replace('\\', '_').replace('/', '_')
                    
                    shutil.copy2(image_file, target_images / f"{unique_name}{image_file.suffix}")
                    shutil.copy2(label_file, target_labels / f"{unique_name}.txt")
                    exported_count += 1
        
        logger.info(f"匯出資料集: {exported_count} 張 (指定: {len(files_to_export) if files_to_export else '全部'})")
        return jsonify({
            'success': True,
            'exported': exported_count,
            'output_dir': str(target_images.parent.parent)
        })
    except Exception as e:
        logger.error(f"匯出失敗: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/annotate/extract_frames', methods=['POST'])
def extract_frames_from_videos():
    """從錄影檔擷取影格"""
    try:
        data = request.json or {}
        interval = int(data.get('interval', 2))
        max_frames = int(data.get('max_frames', 100))
        
        import subprocess
        import sys
        
        # 取得 Python 執行檔路徑
        python_exe = sys.executable
        extract_script = Path(PROJECT_ROOT) / 'extract_frames.py'
        
        if not extract_script.exists():
            return jsonify({'error': 'extract_frames.py 不存在'}), 404
        
        # 執行擷取影格腳本
        cmd = [
            python_exe,
            str(extract_script),
            '--batch',
            '--interval', str(interval),
            '--max-frames', str(max_frames)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        
        if result.returncode != 0:
            logger.error(f"擷取影格失敗: {result.stderr}")
            return jsonify({'error': result.stderr or '擷取失敗'}), 500
        
        # 統計擷取的影格數
        frames_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        total_frames = len(list(frames_dir.glob('*.jpg'))) + len(list(frames_dir.glob('*.png')))
        
        # 統計處理的影片數
        recordings_dir = Path(PROJECT_ROOT) / 'recordings'
        videos_processed = len(list(recordings_dir.glob('*.mp4')))
        
        logger.info(f"擷取影格完成: {total_frames} 張")
        return jsonify({
            'success': True,
            'total_frames': total_frames,
            'videos_processed': videos_processed,
            'output': result.stdout
        })
    except Exception as e:
        logger.error(f"擷取影格失敗: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def generate_auto_label_report(label_files, total_images, total_detections, folder_name, output_file='auto_label_report.html'):
    """生成自動標註 HTML 報告"""
    import base64
    from PIL import Image
    from io import BytesIO
    
    images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
    
    def draw_annotations_on_image(image_path, label_file, max_size=300):
        """在影像上繪製標註框並轉為 base64"""
        try:
            from PIL import Image, ImageDraw
            import base64
            from io import BytesIO
            
            # 開啟影像
            img = Image.open(image_path)
            img_width, img_height = img.size
            
            # 縮小影像
            img.thumbnail((max_size, max_size))
            new_width, new_height = img.size
            scale_x = new_width / img_width
            scale_y = new_height / img_height
            
            # 轉為 RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            draw = ImageDraw.Draw(img)
            
            # 讀取並繪製標註框
            confidences = []  # 收集信心分數
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id, x_center, y_center, width, height = map(float, parts[:5])
                        confidence = float(parts[5]) if len(parts) >= 6 else None  # 讀取信心分數
                        if confidence is not None:
                            confidences.append(confidence)
                        
                        # YOLO 格式轉為像素座標
                        x_center_px = x_center * img_width * scale_x
                        y_center_px = y_center * img_height * scale_y
                        width_px = width * img_width * scale_x
                        height_px = height * img_height * scale_y
                        
                        x1 = int(x_center_px - width_px / 2)
                        y1 = int(y_center_px - height_px / 2)
                        x2 = int(x_center_px + width_px / 2)
                        y2 = int(y_center_px + height_px / 2)
                        
                        # 設定顏色
                        color = '#10b981' if class_id == 0 else '#ef4444'
                        
                        # 繪製矩形框
                        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
            
            # 轉為 base64
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            avg_confidence = sum(confidences) / len(confidences) if confidences else None
            return f"data:image/jpeg;base64,{img_str}", avg_confidence
        except Exception as e:
            logger.error(f"繪製標註失敗: {e}")
            return None, None
    
    # 收集標註資訊（顯示所有標註，無數量限制）
    labeled_samples = []
    
    for label_file in label_files:
        try:
            # 找對應的影像檔（標籤在 annotated/labels，影像在 extracted_frames）
            labels_base = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'labels'
            relative_path = label_file.relative_to(labels_base)
            
            img_path = None
            for ext in ['.jpg', '.png', '.jpeg']:
                potential_path = images_dir / relative_path.parent / (label_file.stem + ext)
                if potential_path.exists():
                    img_path = potential_path
                    break
            
            if not img_path or not img_path.exists():
                continue
                
            # 讀取標註數量
            with open(label_file, 'r') as f:
                annotations = f.readlines()
            
            # 繪製標註框並轉為 base64
            img_base64, avg_confidence = draw_annotations_on_image(img_path, label_file, max_size=300)
            
            if img_base64:
                labeled_samples.append({
                    'path': str(relative_path).replace('\\', '/'),
                    'image': img_base64,
                    'count': len(annotations),
                    'confidence': avg_confidence
                })
        except Exception as e:
            logger.error(f"處理標註樣本失敗: {e}")
            continue
    
    # 生成 HTML
    html_content = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>自動標註報告</title>
    <style>
        body {{
            font-family: "Microsoft JhengHei", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-box {{
            background: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #666;
        }}
        .stat-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #4CAF50;
        }}
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }}
        .image-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 3px solid #4CAF50;
        }}
        .image-card img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 4px;
            background: #f0f0f0;
        }}
        .image-info {{
            margin-top: 10px;
        }}
        .filename {{
            font-size: 0.85em;
            color: #333;
            word-break: break-all;
            margin-bottom: 5px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.75em;
            font-weight: bold;
            background: #4CAF50;
            color: white;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 自動標註報告</h1>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-label">資料夾</div>
                <div class="stat-value" style="font-size: 1.2em;">{folder_name}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">已標註影像</div>
                <div class="stat-value">{total_images}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">偵測到物件</div>
                <div class="stat-value">{total_detections}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">平均物件/圖</div>
                <div class="stat-value">{total_detections/max(total_images, 1):.1f}</div>
            </div>
        </div>
        <p style="margin-top: 15px; color: #666;">
            ✅ 以下是自動標註的範例影像（最多顯示 {len(labeled_samples)} 張）
        </p>
    </div>
    
    <div class="image-grid">
'''
    
    for sample in labeled_samples:
        confidence_text = f"平均信心: {sample['confidence']:.2%}" if sample.get('confidence') else ""
        html_content += f'''
        <div class="image-card">
            <div class="badge">已標註</div>
            <img src="{sample['image']}" alt="Labeled Image">
            <div class="image-info">
                <div class="filename">{sample['path']}</div>
                <div style="font-size: 0.8em; color: #666;">物件數量: {sample['count']}</div>
                {f'<div style="font-size: 0.8em; color: #4CAF50; font-weight: bold;">{confidence_text}</div>' if confidence_text else ''}
            </div>
        </div>
'''
    html_content += '''
    </div>
</body>
</html>
'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"✓ 報告已生成: {output_file}")


@app.route('/api/annotate/auto_label', methods=['POST'])
def auto_label_images():
    """使用現有模型自動標註影像（支援資料夾篩選或指定圖片列表）"""
    try:
        import subprocess
        import sys
        import uuid
        import tempfile
        import json
        
        logger.info(f"請求內容類型: {request.content_type}")
        logger.info(f"請求數據: {request.get_data(as_text=True)[:200]}")
        
        data = request.json or {}
        selected_folder = data.get('folder', '')  # 選擇的資料夾
        target_images = data.get('images', None)  # 指定的圖片列表
        overwrite = data.get('overwrite', False)  # 是否覆蓋已存在的標註
        confidence_threshold = data.get('confidence_threshold', 0.25)  # 信心閾值
        model_type = data.get('model', 'yolov4')  # 模型類型: yolov4 或 yolov8
        
        logger.info(f"自動標註請求: folder={selected_folder}, target_images count={len(target_images) if target_images else 0}, overwrite={overwrite}, confidence={confidence_threshold}, model={model_type}")
        
        # 取得 Python 執行檔路徑
        python_exe = sys.executable
        auto_label_script = Path(PROJECT_ROOT) / 'auto_label.py'
        
        if not auto_label_script.exists():
            return jsonify({'error': 'auto_label.py 不存在'}), 404
        
        # 建立 task_id 並初始化進度
        task_id = str(uuid.uuid4())
        
        # 計算總圖片數
        if target_images:
            total_count = len(target_images)
        elif selected_folder:
            # 估算資料夾內的圖片數量
            images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames' / selected_folder
            if images_dir.exists():
                total_count = len(list(images_dir.glob('*.jpg'))) + len(list(images_dir.glob('*.png')))
            else:
                total_count = 100  # 預估值
        else:
            # 估算總數
            images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
            total_count = sum(1 for _ in images_dir.rglob('*.jpg')) + sum(1 for _ in images_dir.rglob('*.png'))
        
        progress_tracker[task_id] = {
            'current': 0, 
            'total': total_count, 
            'status': 'processing',
            'labeled_count': 0,
            'report_url': None,
            'total_detections': 0
        }
        
        # 準備命令參數
        cmd = [python_exe, str(auto_label_script), '--task-id', task_id]
        
        # 如果有指定圖片列表，只處理這些圖片
        temp_file_path = None
        if target_images:
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8')
            json.dump(target_images, temp_file)
            temp_file.close()
            temp_file_path = temp_file.name
            cmd.extend(['--image-list', temp_file_path])
            logger.info(f"創建臨時檔案: {temp_file_path}, 包含 {len(target_images)} 張圖片")
        elif selected_folder:
            cmd.extend(['--folder', selected_folder])
        
        # 添加覆蓋、信心閾值和模型參數
        if overwrite:
            cmd.append('--overwrite')
        cmd.extend(['--confidence', str(confidence_threshold)])
        cmd.extend(['--model', model_type])
        
        logger.info(f"執行命令: {' '.join(cmd)}")
        
        # 定義背景處理函數
        def run_auto_label_in_background():
            try:
                # 修正 Windows 編碼問題：使用 utf-8 而不是 cp950
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    cwd=str(PROJECT_ROOT),
                    encoding='utf-8',
                    errors='replace'  # 遇到無法解碼的字元時用 ? 取代
                )
                
                logger.info(f"腳本輸出 (stdout): {result.stdout[:500] if result.stdout else 'None'}")
                if result.stderr:
                    logger.info(f"腳本錯誤 (stderr): {result.stderr[:500]}")
                
                # 清理臨時檔案
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                
                if result.returncode != 0:
                    logger.error(f"自動標註失敗: {result.stderr}")
                    progress_tracker[task_id]['status'] = 'error'
                    progress_tracker[task_id]['error'] = result.stderr or '自動標註失敗'
                    return
                
                # 統計標註結果
                labels_dir = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'labels'
                
                if target_images:
                    total_images = len(target_images)
                    label_files = []
                    for img_name in target_images:
                        label_name = Path(img_name).stem + '.txt'
                        label_path = labels_dir / Path(img_name).parent / label_name
                        if label_path.exists():
                            label_files.append(label_path)
                elif selected_folder:
                    folder_labels_dir = labels_dir / selected_folder
                    if folder_labels_dir.exists():
                        total_images = len(list(folder_labels_dir.glob('*.txt')))
                        label_files = list(folder_labels_dir.glob('*.txt'))
                    else:
                        total_images = 0
                        label_files = []
                else:
                    total_images = len(list(labels_dir.rglob('*.txt')))
                    label_files = list(labels_dir.rglob('*.txt'))
                
                # 計算總偵測數
                total_detections = 0
                for label_file in label_files:
                    try:
                        with open(label_file, 'r') as f:
                            total_detections += len(f.readlines())
                    except:
                        pass
                
                # 生成 HTML 報告
                from datetime import datetime
                reports_dir = Path(PROJECT_ROOT) / 'reports'
                reports_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                folder_suffix = f"_{selected_folder}" if selected_folder else "_all"
                report_filename = f"auto_label_{timestamp}{folder_suffix}.html"
                report_path = reports_dir / report_filename
                
                generate_auto_label_report(label_files, total_images, total_detections, 
                                           selected_folder or '全部資料夾', report_path)
                
                # 標記任務完成
                progress_tracker[task_id]['status'] = 'completed'
                progress_tracker[task_id]['current'] = progress_tracker[task_id]['total']
                progress_tracker[task_id]['labeled_count'] = total_images
                progress_tracker[task_id]['total_detections'] = total_detections
                progress_tracker[task_id]['report_url'] = f'/reports/{report_filename}'
                
                logger.info(f"自動標註完成 ({selected_folder or '全部'}): {total_images} 張影像, {total_detections} 個目標")
                
            except Exception as e:
                logger.error(f"背景自動標註失敗: {e}")
                import traceback
                traceback.print_exc()
                progress_tracker[task_id]['status'] = 'error'
                progress_tracker[task_id]['error'] = str(e)
        
        # 在背景執行
        background_thread = threading.Thread(target=run_auto_label_in_background)
        background_thread.daemon = True
        background_thread.start()
        
        # 立即返回 task_id，讓前端可以開始輪詢進度
        return jsonify({
            'success': True,
            'processing': True,
            'task_id': task_id,
            'total': total_count,
            'message': '自動標註已開始，請等待完成'
        })
        
    except Exception as e:
        logger.error(f"自動標註失敗: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== 資料清洗 API ====================

@app.route('/api/annotate/detect-duplicates', methods=['POST'])
def detect_duplicates():
    """偵測重複圖片（支援資料夾篩選或指定圖片列表）"""
    try:
        data = request.json or {}
        threshold = int(data.get('threshold', 5))
        selected_folder = data.get('folder', '')  # 選擇的資料夾
        target_images = data.get('images', None)  # 指定的圖片列表
        
        images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        
        if not images_dir.exists():
            return jsonify({'error': '圖片目錄不存在'}), 404
        
        # 如果有指定圖片列表，只檢測這些圖片
        if target_images:
            # 建立臨時目錄結構來使用現有的偵測邏輯
            image_paths = [images_dir / img for img in target_images]
            # 驗證所有圖片都存在
            for img_path in image_paths:
                if not img_path.exists():
                    return jsonify({'error': f'圖片不存在: {img_path.name}'}), 404
            search_paths = image_paths
            search_description = f"{len(target_images)} 張選中圖片"
        # 如果有選擇資料夾，只檢測該資料夾
        elif selected_folder:
            search_dir = images_dir / selected_folder
            if not search_dir.exists():
                return jsonify({'error': f'資料夾不存在: {selected_folder}'}), 404
            search_paths = None
            search_description = selected_folder
        else:
            search_dir = images_dir
        if target_images:
            folder_suffix = f"_selected_{len(target_images)}"
        elif selected_folder:
            folder_suffix = f"_{selected_folder}"
        else:
            folder_suffix = "_all"
            search_description = "全部資料夾"
        
        # 使用我們建立的重複偵測邏輯
        sys.path.insert(0, str(PROJECT_ROOT))
        from remove_duplicates_with_preview import find_duplicates, generate_html_report as gen_dup_report
        
        # 如果有指定圖片列表，需要修改 find_duplicates 的調用方式
        if target_images:
            # 自訂偵測邏輯（只檢查指定圖片）
            import imagehash
            from PIL import Image
            from collections import defaultdict
            import uuid
            
            # 建立 task_id 並初始化進度
            task_id = str(uuid.uuid4())
            progress_tracker[task_id] = {
                'current': 0, 
                'total': len(image_paths), 
                'status': 'processing',
                'duplicate_count': 0
            }
            
            # 在後台線程處理
            def process_duplicates():
                try:
                    logger.info(f"開始後台處理重複圖片，task_id={task_id}, 圖片數={len(image_paths)}")
                    hashes = {}
                    for idx, img_path in enumerate(image_paths, 1):
                        try:
                            with Image.open(img_path) as img:
                                img_hash = imagehash.dhash(img)
                                hashes[img_path] = img_hash
                            progress_tracker[task_id]['current'] = idx
                        except Exception as e:
                            logger.warning(f"無法處理 {img_path}: {e}")
                            progress_tracker[task_id]['current'] = idx
                            continue
                    
                    # 找出重複的圖片
                    hash_groups = defaultdict(list)
                    for img_path, img_hash in hashes.items():
                        hash_groups[img_hash].append(img_path)
                    
                    duplicate_groups = []
                    processed = set()
                    
                    for img_hash, paths in hash_groups.items():
                        if len(paths) > 1:
                            for i, path1 in enumerate(paths):
                                if path1 in processed:
                                    continue
                                
                                duplicates = []
                                for path2 in paths[i+1:]:
                                    if path2 in processed:
                                        continue
                                    
                                    hash_diff = img_hash - hashes[path2]
                                    if hash_diff <= threshold:
                                        duplicates.append(path2)
                                        processed.add(path2)
                                
                                if duplicates:
                                    duplicate_groups.append({
                                        'original': path1,
                                        'duplicates': duplicates,
                                        'reason': f'圖片雜湊相似度 ≤ {threshold}'
                                    })
                                    processed.add(path1)
                    
                    stats = {
                        'total_files': len(hashes),
                        'unique_files': len(hashes) - sum(len(g['duplicates']) for g in duplicate_groups),
                        'total_duplicates': sum(len(g['duplicates']) for g in duplicate_groups),
                        'duplicate_groups': len(duplicate_groups),
                        'space_saved_mb': sum(sum(Path(p).stat().st_size for p in g['duplicates']) for g in duplicate_groups) / (1024 * 1024)
                    }
                    
                    progress_tracker[task_id]['duplicate_count'] = stats['total_duplicates']
                    progress_tracker[task_id]['status'] = 'completed'
                    
                    # 生成報告
                    from datetime import datetime
                    reports_dir = Path(PROJECT_ROOT) / 'reports'
                    reports_dir.mkdir(exist_ok=True)
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    folder_suffix = f"_selected_{len(image_paths)}"
                    report_filename = f"duplicate_{timestamp}{folder_suffix}.html"
                    report_path = reports_dir / report_filename
                    
                    gen_dup_report(duplicate_groups, stats, report_path, images_dir=images_dir)
                    
                    # 儲存結果到進度追蹤
                    report_url = f'/reports/{report_filename}'
                    progress_tracker[task_id]['report_url'] = report_url
                    progress_tracker[task_id]['stats'] = stats
                    logger.info(f"後台處理完成，report_url={report_url}, duplicate_count={stats['total_duplicates']}")
                except Exception as e:
                    logger.error(f"後台處理失敗: {e}")
                    import traceback
                    traceback.print_exc()
                    progress_tracker[task_id]['status'] = 'error'
                    progress_tracker[task_id]['error'] = str(e)
            
            # 啟動後台處理
            threading.Thread(target=process_duplicates, daemon=True).start()
            
            # 立即返回 task_id
            return jsonify({
                'success': True,
                'task_id': task_id,
                'processing': True,
                'message': '處理中，請稍候...'
            })
        
        # else 分支：處理整個資料夾（使用現有函數）
        duplicate_groups, stats = find_duplicates(search_dir, threshold)
        
        # 生成 HTML 報告（使用時間戳記）
        from datetime import datetime
        reports_dir = Path(PROJECT_ROOT) / 'reports'
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_suffix = f"_{selected_folder}" if selected_folder else "_all"
        report_filename = f"duplicate_{timestamp}{folder_suffix}.html"
        report_path = reports_dir / report_filename
        
        gen_dup_report(duplicate_groups, stats, report_path, images_dir=images_dir)
        
        # 轉換為 JSON 可序列化格式（保留相對路徑）
        groups_data = []
        for group in duplicate_groups:
            original_rel = group['original'].relative_to(images_dir)
            duplicates_rel = [d.relative_to(images_dir) for d in group['duplicates']]
            
            groups_data.append({
                'original': str(original_rel).replace('\\', '/'),
                'duplicates': [str(d).replace('\\', '/') for d in duplicates_rel],
                'reason': group['reason']
            })
        
        stats['folder'] = selected_folder or '全部資料夾'
        
        return jsonify({
            'success': True,
            'stats': stats,
            'groups': groups_data,
            'report_url': f'/reports/{report_filename}',
            'task_id': task_id if target_images else None
        })
    except Exception as e:
        logger.error(f"偵測重複圖片失敗: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/annotate/detect-blanks', methods=['POST'])
def detect_blank_images():
    """偵測空白圖片（支援資料夾過濾或指定圖片列表）"""
    try:
        data = request.json or {}
        std_threshold = float(data.get('std_threshold', 25))
        selected_folder = data.get('folder', '')  # 選擇的資料夾
        target_images = data.get('images', None)  # 指定的圖片列表
        
        images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        
        if not images_dir.exists():
            return jsonify({'error': '圖片目錄不存在'}), 404
        
        # 如果有指定圖片列表，只檢測這些圖片
        if target_images:
            image_paths = [images_dir / img for img in target_images]
            # 驗證所有圖片都存在
            for img_path in image_paths:
                if not img_path.exists():
                    return jsonify({'error': f'圖片不存在: {img_path.name}'}), 404
            search_paths = image_paths
            search_description = f"{len(target_images)} 張選中圖片"
        # 如果有選擇資料夾，只檢測該資料夾
        elif selected_folder:
            search_dir = images_dir / selected_folder
            if not search_dir.exists():
                return jsonify({'error': f'資料夾不存在: {selected_folder}'}), 404
            search_paths = None
            search_description = selected_folder
        else:
            search_dir = images_dir
            search_paths = None
            search_description = "全部資料夾"
        
        # 使用我們建立的空白偵測邏輯
        sys.path.insert(0, str(PROJECT_ROOT))
        from remove_blank_images import find_blank_images, generate_html_report as gen_blank_report
        if target_images:
            folder_suffix = f"_selected_{len(target_images)}"
        elif selected_folder:
            folder_suffix = f"_{selected_folder}"
        else:
            folder_suffix = ""
        # 如果有指定圖片列表
        if target_images:
            import cv2
            import numpy as np
            import uuid
            
            task_id = str(uuid.uuid4())
            progress_tracker[task_id] = {
                'current': 0, 
                'total': len(image_paths), 
                'status': 'processing',
                'blank_count': 0
            }
            
            logger.info(f"創建任務: task_id={task_id}, 圖片數={len(image_paths)}")
            
            # 在後台線程處理，立即返回 task_id
            def process_blank_images():
                try:
                    logger.info(f"[TASK {task_id}] 開始後台處理空白圖片")
                    blank_images = []
                    for idx, img_path in enumerate(image_paths, 1):
                        try:
                            # 使用 numpy 避免 Unicode 路徑問題
                            with open(str(img_path), 'rb') as f:
                                img_array = np.frombuffer(f.read(), dtype=np.uint8)
                                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                            if img is None:
                                progress_tracker[task_id]['current'] = idx
                                continue
                            
                            # 計算標準差和平均顏色
                            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                            std_dev = np.std(gray)
                            mean_val = np.mean(gray)
                            
                            # 計算平均 RGB 顏色
                            mean_color = tuple(map(int, cv2.mean(img)[:3]))  # (B, G, R)
                            mean_color = (mean_color[2], mean_color[1], mean_color[0])  # 轉換為 RGB
                            
                            if std_dev < std_threshold:
                                blank_images.append({
                                    'path': img_path,
                                    'analysis': {
                                        'std_dev': float(std_dev),
                                        'mean': float(mean_val),
                                        'mean_color': mean_color,
                                        'is_blank': True,
                                        'reason': f"標準差過低 (標準差: {std_dev:.2f})",
                                        'size_kb': img_path.stat().st_size / 1024
                                    }
                                })
                            
                            # 更新進度
                            progress_tracker[task_id]['current'] = idx
                            progress_tracker[task_id]['blank_count'] = len(blank_images)
                        except Exception as e:
                            logger.warning(f"無法處理 {img_path}: {e}")
                            progress_tracker[task_id]['current'] = idx
                            continue
                    
                    progress_tracker[task_id]['status'] = 'completed'
                    logger.info(f"[TASK {task_id}] 處理完成，找到 {len(blank_images)} 張空白圖片")
                    
                    # 生成報告
                    from datetime import datetime
                    reports_dir = Path(PROJECT_ROOT) / 'reports'
                    reports_dir.mkdir(exist_ok=True)
                    logger.info(f"[TASK {task_id}] 報告目錄: {reports_dir}")
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    folder_suffix = f"_selected_{len(image_paths)}"
                    report_filename = f"blank_images_{timestamp}{folder_suffix}.html"
                    report_path = reports_dir / report_filename
                    
                    logger.info(f"[TASK {task_id}] 開始生成報告: {report_path}")
                    gen_blank_report(blank_images, len(image_paths), report_path, images_dir=images_dir)
                    logger.info(f"[TASK {task_id}] 報告生成完成")
                    
                    # 儲存報告路徑到進度追蹤
                    report_url = f'/reports/{report_filename}'
                    progress_tracker[task_id]['report_url'] = report_url
                    progress_tracker[task_id]['blank_count'] = len(blank_images)
                    progress_tracker[task_id]['total_files'] = len(image_paths)
                    
                    # 強制刷新，確保寫入
                    import time
                    time.sleep(0.1)
                    
                    logger.info(f"[TASK {task_id}] ✅ 完成！report_url={report_url}")
                    logger.info(f"[TASK {task_id}] progress_tracker 所有鍵: {list(progress_tracker[task_id].keys())}")
                    logger.info(f"[TASK {task_id}] progress_tracker 完整內容: {progress_tracker[task_id]}")
                except Exception as e:
                    logger.error(f"[TASK {task_id}] ❌ 後台處理失敗: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    progress_tracker[task_id]['status'] = 'error'
                    progress_tracker[task_id]['error'] = str(e)
            
            # 啟動後台處理
            threading.Thread(target=process_blank_images, daemon=True).start()
            
            # 立即返回 task_id
            return jsonify({
                'success': True,
                'task_id': task_id,
                'processing': True,
                'message': '處理中，請稍候...'
            })
        
        # else 分支：使用現有函數處理
        blank_images, total_files = find_blank_images(search_dir, std_threshold)
        
        # 生成 HTML 報告（使用時間戳記）
        from datetime import datetime
        reports_dir = Path(PROJECT_ROOT) / 'reports'
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_suffix = f"_{selected_folder}" if selected_folder else "_all"
        report_filename = f"blank_images_{timestamp}{folder_suffix}.html"
        report_path = reports_dir / report_filename
        
        gen_blank_report(blank_images, total_files, report_path, images_dir=images_dir)
        
        # 轉換為 JSON 可序列化格式（保留相對路徑）
        blank_data = []
        for img_info in blank_images:
            relative_path = img_info['path'].relative_to(images_dir)
            blank_data.append({
                'filename': str(relative_path).replace('\\', '/'),
                'analysis': img_info['analysis']
            })
        
        total_size = sum(img['path'].stat().st_size for img in blank_images)
        
        return jsonify({
            'success': True,
            'total_files': total_files,
            'blank_count': len(blank_images),
            'space_saved_mb': total_size / 1024 / 1024,
            'blank_images': blank_data,
            'folder': selected_folder or '全部資料夾',
            'report_url': f'/reports/{report_filename}',
            'task_id': task_id if target_images else None
        })
    except Exception as e:
        logger.error(f"偵測空白圖片失敗: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress/<task_id>')
def get_progress(task_id):
    """獲取任務進度"""
    if task_id in progress_tracker:
        # 明確構建返回的 dict，避免 jsonify 遺失欄位
        orig_data = progress_tracker[task_id]
        progress = {
            'status': orig_data.get('status', 'processing'),
            'current': orig_data.get('current', 0),
            'total': orig_data.get('total', 0),
            'blank_count': orig_data.get('blank_count', 0),
            'total_files': orig_data.get('total_files', 0),
            'labeled_count': orig_data.get('labeled_count', 0),
            'total_detections': orig_data.get('total_detections', 0),
            'report_url': orig_data.get('report_url', '')
        }
        logger.debug(f"[GET /api/progress/{task_id}] 原始資料: {orig_data}")
        logger.debug(f"[GET /api/progress/{task_id}] 返回資料: {progress}")
        return jsonify(progress)
    else:
        logger.warning(f"API /api/progress/{task_id} - Task not found")
        return jsonify({'error': 'Task not found'}), 404

@app.route('/api/progress/<task_id>', methods=['PUT'])
def update_progress(task_id):
    """更新任務進度（供 subprocess 使用）"""
    try:
        data = request.json or {}
        if task_id not in progress_tracker:
            progress_tracker[task_id] = {}
        
        # 更新進度資訊
        for key in ['current', 'total', 'status', 'labeled_count', 'duplicate_count', 'blank_count']:
            if key in data:
                progress_tracker[task_id][key] = data[key]
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/annotate/filter-extreme-boxes', methods=['POST'])
def filter_extreme_boxes():
    """過濾極端尺寸的標記框"""
    try:
        data = request.json or {}
        min_size = int(data.get('min_size', 50))
        max_size = int(data.get('max_size', 800))
        selected_folder = data.get('folder', '')
        target_images = data.get('images', None)
        
        if min_size <= 0 or max_size <= min_size:
            return jsonify({'error': '無效的尺寸範圍'}), 400
        
        images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        labels_dir = Path(PROJECT_ROOT) / 'datasets' / 'annotated' / 'labels'
        
        if not images_dir.exists():
            return jsonify({'error': '圖片目錄不存在'}), 404
        if not labels_dir.exists():
            return jsonify({'error': '標註目錄不存在'}), 404
        
        # 決定要處理的圖片列表
        if target_images:
            # 指定圖片列表
            image_files = [images_dir / img for img in target_images]
            for img_path in image_files:
                if not img_path.exists():
                    return jsonify({'error': f'圖片不存在: {img_path.name}'}), 404
        elif selected_folder:
            # 指定資料夾
            search_dir = images_dir / selected_folder
            if not search_dir.exists():
                return jsonify({'error': f'資料夾不存在: {selected_folder}'}), 404
            image_files = list(search_dir.glob('*.jpg')) + list(search_dir.glob('*.png'))
        else:
            # 所有圖片
            image_files = list(images_dir.rglob('*.jpg')) + list(images_dir.rglob('*.png'))
        
        # 備份標籤
        from datetime import datetime
        import shutil
        backup_dir = labels_dir.parent / f"labels_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(exist_ok=True)
        
        total_files = 0
        modified_files = 0
        total_boxes = 0
        filtered_boxes = 0
        
        # 使用PIL讀取圖片尺寸
        from PIL import Image
        
        for img_path in image_files:
            # 找到對應的標籤檔案
            relative_path = img_path.relative_to(images_dir)
            label_filename = relative_path.with_suffix('.txt').name
            
            # 在labels目錄中搜索標籤檔案（可能在子目錄）
            label_files = list(labels_dir.rglob(label_filename))
            if not label_files:
                continue
            
            label_path = label_files[0]
            total_files += 1
            
            # 讀取圖片尺寸
            try:
                with Image.open(img_path) as img:
                    img_width, img_height = img.size
            except Exception as e:
                logger.warning(f"無法讀取圖片尺寸 {img_path}: {e}")
                continue
            
            # 讀取標籤
            try:
                with open(label_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception as e:
                logger.warning(f"無法讀取標籤 {label_path}: {e}")
                continue
            
            if not lines:
                continue
            
            # 備份原始標籤
            backup_label_path = backup_dir / label_path.name
            shutil.copy2(label_path, backup_label_path)
            
            # 過濾標記框
            filtered_lines = []
            for line in lines:
                total_boxes += 1
                parts = line.strip().split()
                if len(parts) < 5:
                    filtered_lines.append(line)
                    continue
                
                try:
                    class_id = int(parts[0])
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                    
                    # 計算像素尺寸
                    box_width_px = width * img_width
                    box_height_px = height * img_height
                    
                    # 檢查尺寸範圍
                    if (box_width_px < min_size or box_width_px > max_size or
                        box_height_px < min_size or box_height_px > max_size):
                        filtered_boxes += 1
                        continue
                    
                    filtered_lines.append(line)
                except ValueError:
                    filtered_lines.append(line)
                    continue
            
            # 如果有標記框被過濾，更新檔案
            if len(filtered_lines) < len(lines):
                modified_files += 1
                with open(label_path, 'w', encoding='utf-8') as f:
                    f.writelines(filtered_lines)
        
        return jsonify({
            'success': True,
            'total_files': total_files,
            'modified_files': modified_files,
            'total_boxes': total_boxes,
            'filtered_boxes': filtered_boxes,
            'backup_path': str(backup_dir.relative_to(PROJECT_ROOT))
        })
    except Exception as e:
        logger.error(f"過濾極端標記框失敗: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/annotate/delete-images', methods=['POST'])
def batch_delete_images():
    """批次刪除圖片"""
    try:
        data = request.json or {}
        filenames = data.get('filenames', [])
        
        if not filenames:
            return jsonify({'error': '未指定要刪除的檔案'}), 400
        
        images_dir = Path(PROJECT_ROOT) / 'datasets' / 'extracted_frames'
        labels_dir = Path(PROJECT_ROOT) / 'datasets' / 'auto_labels'
        
        deleted_count = 0
        errors = []
        
        for filename in filenames:
            try:
                # 刪除圖片
                image_path = images_dir / filename
                if image_path.exists():
                    send2trash.send2trash(str(image_path))
                    deleted_count += 1
                
                # 刪除對應的標註（如果存在）
                label_path = labels_dir / f"{Path(filename).stem}.txt"
                if label_path.exists():
                    send2trash.send2trash(str(label_path))
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
        
        logger.info(f"批次刪除: 成功 {deleted_count} 個，失敗 {len(errors)} 個")
        
        return jsonify({
            'success': True,
            'deleted': deleted_count,
            'errors': errors if errors else None
        })
    except Exception as e:
        logger.error(f"批次刪除失敗: {e}")
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

    # 2. 在延遲後強制結束目前進程
    def delayed_exit():
        import time
        time.sleep(1.5)  # 等待回應發送完成
        logger.info("正在關閉伺服器...")
        os._exit(0)  # 強制結束進程
    
    threading.Thread(target=delayed_exit, daemon=True).start()
    
    return jsonify({'success': True, 'message': '伺服器正在重啟...'})


@app.route('/api/system/stop_blower', methods=['POST'])
def stop_blower():
    """關閉吹氣風扇"""
    logger.info("接收到關閉吹氣指令...")

    try:
        # TODO: 在此處添加關閉吹氣的具體邏輯
        # 例如，可以通過 GPIO、序列埠或 API 請求來控制硬體
        # 以下為一個模擬範例，實際應替換為真實的控制代碼
        logger.info("模擬：正在向硬體發送關閉風扇指令...")
        # from some_hardware_library import blower
        # blower.off()
        time.sleep(1) # 模擬操作耗時
        logger.info("模擬：硬體回報風扇已關閉")

        return jsonify({'success': True, 'message': '已成功發送關閉吹氣指令。'})

    except Exception as e:
        logger.error(f"關閉吹氣失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
    
    # 啟動前輸出明確訊息
    print("=" * 60)
    print("  糖果瑕疵偵測系統 - 後端啟動中...")
    print("=" * 60)
    print()
    
    # 初始化（避免 debug 模式下重複初始化）
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        print("[1/4] 正在初始化資料庫...")
        init_database()
        print("[2/4] 正在載入 YOLO 模型...")
        load_yolo_model()
        print("[3/4] 正在初始化攝影機...")
        # 使用兩個 BRIO 攝影機
        initialize_cameras(['Camera1', 'Camera2'])
        print("[4/4] 正在啟動偵測系統...")
        start_detection()
        print()
        print("✓ 所有組件初始化完成!")
        print()

    try:
        # 啟動 Web 伺服器
        print("=" * 60)
        print("  Flask 伺服器啟動中...")
        print(f"  訪問網址: http://localhost:5000")
        print(f"  訪問網址: http://127.0.0.1:5000")
        print("=" * 60)
        print()
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    finally:
        stop_detection()


