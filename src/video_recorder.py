"""
固定焦距錄影模組
支援與偵測系統共享攝影機資源
"""

import cv2
import time
import threading
from datetime import datetime
from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 全域錄影器管理
_recorders = {}
_lock = threading.Lock()


class VideoRecorder:
    """視頻錄影器 - 支援共享攝影機模式"""

    def __init__(self, camera_index=0, output_dir=None):
        self.camera_index = camera_index
        self.output_dir = Path(output_dir) if output_dir else PROJECT_ROOT / "recordings"
        self.output_dir.mkdir(exist_ok=True)

        # 共享攝影機模式
        self.shared_cap = None  # 從 camera_contexts 共享的攝影機
        self.own_cap = None     # 獨立模式下自己開啟的攝影機
        
        # 錄影狀態
        self.is_recording = False
        self.is_previewing = False
        self.writer = None
        self.current_filename = None
        self.start_time = None
        self.frame_count = 0
        
        # 焦距設定
        self.auto_focus = True
        self.focus_value = 0  # 0-255
        
        # 錄影執行緒
        self.recording_thread = None
        self.preview_thread = None
        self._stop_event = threading.Event()

    def set_shared_camera(self, cap):
        """設定共享攝影機（從 camera_contexts 傳入）"""
        self.shared_cap = cap
        # 共享模式下套用焦距設定
        if self.shared_cap is not None:
            self._apply_focus_to_cap(self.shared_cap)

    def _get_cap(self):
        """取得可用的攝影機物件"""
        if self.shared_cap is not None:
            return self.shared_cap
        return self.own_cap

    def open_own_camera(self):
        """開啟獨立攝影機（僅在無共享攝影機時使用）"""
        if self.shared_cap is not None:
            return True  # 已有共享攝影機
            
        if self.own_cap is not None:
            return True
            
        self.own_cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.own_cap.isOpened():
            self.own_cap = None
            return False
            
        # 設定解析度
        self.own_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.own_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._apply_focus_to_cap(self.own_cap)
        return True

    def close_own_camera(self):
        """關閉獨立攝影機（不影響共享攝影機）"""
        if self.own_cap is not None:
            self.own_cap.release()
            self.own_cap = None

    def _apply_focus_to_cap(self, cap):
        """套用焦距設定到攝影機"""
        if cap is None:
            return
            
        try:
            if self.auto_focus:
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            else:
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                cap.set(cv2.CAP_PROP_FOCUS, self.focus_value)
        except Exception as e:
            print(f"焦距設定失敗: {e}")

    def _create_error_frame(self, message="錯誤"):
        """建立錯誤提示畫面"""
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (40, 40, 40)  # 深灰色背景
        
        # 繪製錯誤訊息
        cv2.putText(frame, message, (100, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        cv2.putText(frame, "Camera Not Available", (120, 280), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
        return frame

    def set_focus(self, value=0, auto=False):
        """設定焦距"""
        self.auto_focus = auto
        self.focus_value = max(0, min(255, value))
        
        cap = self._get_cap()
        self._apply_focus_to_cap(cap)
        
        return {
            'success': True,
            'auto_focus': self.auto_focus,
            'focus_value': self.focus_value
        }

    def get_focus(self):
        """取得焦距設定"""
        return {
            'auto_focus': self.auto_focus,
            'focus_value': self.focus_value
        }

    def set_resolution(self, width, height):
        """設定解析度"""
        cap = self._get_cap()
        if cap is None:
            return {'success': False, 'error': '攝影機未連接'}
            
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            return {
                'success': True, 
                'width': width, 
                'height': height,
                'actual_width': actual_w,
                'actual_height': actual_h
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def set_fps(self, fps):
        """設定幀率"""
        cap = self._get_cap()
        if cap is None:
            return {'success': False, 'error': '攝影機未連接'}
            
        try:
            cap.set(cv2.CAP_PROP_FPS, fps)
            actual_fps = cap.get(cv2.CAP_PROP_FPS)
            
            return {
                'success': True, 
                'fps': fps,
                'actual_fps': actual_fps
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def start_recording(self, filename=None):
        """開始錄影"""
        if self.is_recording:
            return {'success': False, 'error': '已在錄影中'}

        cap = self._get_cap()
        if cap is None:
            # 嘗試開啟獨立攝影機
            if not self.open_own_camera():
                return {'success': False, 'error': '無法取得攝影機'}
            cap = self.own_cap

        # 產生檔名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"recording_{self.camera_index}_{timestamp}.mp4"
        
        self.current_filename = filename
        filepath = self.output_dir / filename

        # 取得影像尺寸
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 30

        # 建立寫入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(str(filepath), fourcc, fps, (width, height))
        
        if not self.writer.isOpened():
            return {'success': False, 'error': '無法建立錄影檔案'}

        self.is_recording = True
        self.start_time = time.time()
        self.frame_count = 0
        self._stop_event.clear()

        # 啟動錄影執行緒
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.recording_thread.start()

        return {
            'success': True,
            'filename': filename,
            'message': '錄影已開始'
        }

    def _recording_loop(self):
        """錄影迴圈"""
        while not self._stop_event.is_set() and self.is_recording:
            cap = self._get_cap()
            if cap is None:
                break
                
            ret, frame = cap.read()
            if ret and self.writer is not None:
                self.writer.write(frame)
                self.frame_count += 1
            
            time.sleep(0.033)  # 約 30 FPS

    def stop_recording(self):
        """停止錄影"""
        if not self.is_recording:
            return {'success': False, 'error': '未在錄影中'}

        self.is_recording = False
        self._stop_event.set()

        # 等待執行緒結束
        if self.recording_thread:
            self.recording_thread.join(timeout=2)

        # 關閉寫入器
        if self.writer:
            self.writer.release()
            self.writer = None

        duration = time.time() - self.start_time if self.start_time else 0
        result = {
            'success': True,
            'filename': self.current_filename,
            'duration': round(duration, 2),
            'frames': self.frame_count,
            'message': '錄影已停止'
        }

        self.current_filename = None
        self.start_time = None
        self.frame_count = 0

        return result

    def get_status(self):
        """取得錄影狀態"""
        duration = 0
        if self.is_recording and self.start_time:
            duration = time.time() - self.start_time

        cap = self._get_cap()
        camera_ok = cap is not None and cap.isOpened() if cap else False

        return {
            'is_recording': self.is_recording,
            'is_previewing': self.is_previewing,
            'filename': self.current_filename,
            'duration': round(duration, 2),
            'frames': self.frame_count,
            'camera_connected': camera_ok,
            'camera_index': self.camera_index,
            'shared_mode': self.shared_cap is not None,
            'focus': self.get_focus()
        }

    def generate_preview_stream(self):
        """產生預覽串流"""
        self.is_previewing = True
        
        # 先嘗試開啟攝影機
        cap = self._get_cap()
        if cap is None:
            # 嘗試開啟獨立攝影機（使用不同的攝影機索引嘗試）
            for try_index in [self.camera_index, 0, 1, 2]:
                self.camera_index = try_index
                if self.open_own_camera():
                    cap = self.own_cap
                    print(f"錄影器: 成功開啟攝影機 {try_index}")
                    break
            
            if cap is None:
                # 無法開啟攝影機，產生錯誤畫面
                while self.is_previewing:
                    error_frame = self._create_error_frame("無法開啟攝影機")
                    ret, buffer = cv2.imencode('.jpg', error_frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    time.sleep(0.5)
                return
        
        while self.is_previewing:
            cap = self._get_cap()
            if cap is None:
                time.sleep(0.1)
                continue
            
            ret, frame = cap.read()
            if ret:
                # 加入錄影狀態提示
                if self.is_recording:
                    cv2.circle(frame, (30, 30), 15, (0, 0, 255), -1)
                    duration = time.time() - self.start_time if self.start_time else 0
                    text = f"REC {int(duration)}s"
                    cv2.putText(frame, text, (55, 38), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.8, (0, 0, 255), 2)
                
                # 顯示焦距模式
                focus_text = f"AF" if self.auto_focus else f"MF:{self.focus_value}"
                cv2.putText(frame, focus_text, (10, frame.shape[0] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            time.sleep(0.033)

    def stop_preview(self):
        """停止預覽"""
        self.is_previewing = False

    def list_recordings(self):
        """列出錄影檔案"""
        recordings = []
        for f in self.output_dir.glob("*.mp4"):
            stat = f.stat()
            recordings.append({
                'filename': f.name,
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            })
        return sorted(recordings, key=lambda x: x['created'], reverse=True)

    def delete_recording(self, filename):
        """刪除錄影檔案"""
        filepath = self.output_dir / filename
        if filepath.exists():
            filepath.unlink()
            return {'success': True, 'message': f'已刪除 {filename}'}
        return {'success': False, 'error': '檔案不存在'}

    def release(self):
        """釋放資源"""
        self.stop_preview()
        if self.is_recording:
            self.stop_recording()
        self.close_own_camera()
        # 注意：不要 release shared_cap，因為那是其他地方管理的


def get_recorder(camera_index):
    """取得或建立錄影器（全域管理）"""
    with _lock:
        if camera_index not in _recorders:
            _recorders[camera_index] = VideoRecorder(camera_index)
        
        # 每次都嘗試更新共享攝影機連接
        recorder = _recorders[camera_index]
        if recorder.shared_cap is None:
            try:
                from web_app import camera_contexts
                if camera_index < len(camera_contexts):
                    cam_ctx = camera_contexts[camera_index]
                    if cam_ctx.cap is not None and cam_ctx.cap.isOpened():
                        recorder.set_shared_camera(cam_ctx.cap)
                        print(f"錄影器 {camera_index}: 已連接共享攝影機")
            except ImportError:
                pass  # web_app 尚未初始化
            except Exception as e:
                print(f"無法取得共享攝影機: {e}")
                
        return recorder


def cleanup_all():
    """清理所有錄影器"""
    with _lock:
        for recorder in _recorders.values():
            recorder.release()
        _recorders.clear()
