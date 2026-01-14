"""
固定焦距錄影模組
支援與偵測系統共享攝影機資源
"""

import cv2
import time
import threading
import json
from datetime import datetime
from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FOCUS_CONFIG_FILE = PROJECT_ROOT / "focus_settings.json"

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
        
        # 焦距設定 - 從檔案載入
        self.auto_focus = True
        self.focus_value = 0  # 0-255
        self._load_focus_settings()
        
        # 錄影執行緒
        self.recording_thread = None
        self.preview_thread = None
        self._stop_event = threading.Event()

    def _load_focus_settings(self):
        """從檔案載入對焦設定"""
        try:
            if FOCUS_CONFIG_FILE.exists():
                with open(FOCUS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    cam_settings = settings.get(str(self.camera_index), {})
                    self.auto_focus = cam_settings.get('auto_focus', True)
                    self.focus_value = cam_settings.get('focus_value', 0)
                    print(f"攝影機 {self.camera_index}: 載入對焦設定 - auto: {self.auto_focus}, value: {self.focus_value}")
        except Exception as e:
            print(f"攝影機 {self.camera_index}: 載入對焦設定失敗: {e}")
    
    def _save_focus_settings(self):
        """儲存對焦設定到檔案"""
        try:
            # 讀取現有設定
            settings = {}
            if FOCUS_CONFIG_FILE.exists():
                with open(FOCUS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            # 更新此攝影機的設定
            settings[str(self.camera_index)] = {
                'auto_focus': self.auto_focus,
                'focus_value': self.focus_value
            }
            
            # 儲存
            with open(FOCUS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            print(f"攝影機 {self.camera_index}: 對焦設定已儲存 - auto: {self.auto_focus}, value: {self.focus_value}")
            return True
        except Exception as e:
            print(f"攝影機 {self.camera_index}: 儲存對焦設定失敗: {e}")
            return False

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
            return False
            
        try:
            if self.auto_focus:
                success = cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                print(f"攝影機 {self.camera_index}: 啟用自動對焦 - {'成功' if success else '失敗'}")
            else:
                # 先關閉自動對焦
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                time.sleep(0.15)  # 增加延遲確保設定生效
                
                # 多次嘗試設定焦距值（有些攝影機需要多次設定）
                max_attempts = 3
                for attempt in range(max_attempts):
                    success = cap.set(cv2.CAP_PROP_FOCUS, self.focus_value)
                    time.sleep(0.1)
                    
                    # 驗證設定
                    actual_focus = cap.get(cv2.CAP_PROP_FOCUS)
                    diff = abs(actual_focus - self.focus_value)
                    
                    if diff <= 5:  # 容許 5 的誤差
                        print(f"攝影機 {self.camera_index}: 手動對焦設定成功 - 目標: {self.focus_value}, 實際: {actual_focus}")
                        return True
                    elif attempt < max_attempts - 1:
                        print(f"攝影機 {self.camera_index}: 對焦值不精確 (嘗試 {attempt+1}/{max_attempts}), 目標: {self.focus_value}, 實際: {actual_focus}, 重試...")
                    else:
                        print(f"攝影機 {self.camera_index}: 對焦值設定後仍有誤差 - 目標: {self.focus_value}, 實際: {actual_focus}")
                        print(f"攝影機 {self.camera_index}: 注意：某些攝影機不支援精確的對焦控制，這是硬體限制")
                
            return True
        except Exception as e:
            print(f"攝影機 {self.camera_index}: 焦距設定失敗: {e}")
            return False

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
        self.focus_value = max(0, min(255, int(value)))
        
        cap = self._get_cap()
        if cap is None:
            return {
                'success': False,
                'error': '攝影機未連接',
                'auto_focus': self.auto_focus,
                'focus_value': self.focus_value
            }
        
        self._apply_focus_to_cap(cap)
        
        # 儲存設定到檔案
        self._save_focus_settings()
        
        return {
            'success': True,
            'auto_focus': self.auto_focus,
            'focus_value': self.focus_value,
            'message': f"對焦已設定為 {self.focus_value} (自動對焦: {'開啟' if self.auto_focus else '關閉'})",
            'saved': True
        }

    def get_focus(self):
        """取得焦距設定（返回儲存的設定值，不從攝影機讀取）"""
        # 直接返回儲存的設定值，不要從攝影機讀取
        # 因為攝影機可能未連接，或返回的值不準確
        return {
            'auto_focus': self.auto_focus,
            'focus_value': self.focus_value,
            'success': True
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

    def start_recording(self, filename=None, codec=None):
        """開始錄影"""
        if self.is_recording:
            return {'success': False, 'error': '已在錄影中'}

        cap = self._get_cap()
        if cap is None:
            # 嘗試開啟獨立攝影機
            if not self.open_own_camera():
                return {'success': False, 'error': '無法取得攝影機'}
            cap = self.own_cap
        
        # 套用儲存的對焦設定
        self._apply_focus_to_cap(cap)

        # 產生檔名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.camera_index}_{timestamp}.mp4"
        
        self.current_filename = filename
        filepath = self.output_dir / filename

        # 取得影像尺寸
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 30

        # 定義編碼器列表
        default_codecs = [
            ('avc1', 'H.264 (avc1)'),
            ('H264', 'H.264'),
            ('XVID', 'XVID'),
            ('MJPG', 'Motion JPEG'),
            ('mp4v', 'MPEG-4')
        ]
        
        # 如果指定了編碼器，將其加入列表最前方優先嘗試
        codec_list = []
        if codec:
            # 根據選擇的編碼器名稱對應到 FourCC
            if codec == 'avc1':
                codec_list.append(('avc1', 'H.264 (avc1)'))
            elif codec == 'H264':
                codec_list.append(('H264', 'H.264'))
            elif codec == 'XVID':
                codec_list.append(('XVID', 'XVID'))
            elif codec == 'MJPG':
                codec_list.append(('MJPG', 'Motion JPEG'))
            elif codec == 'mp4v':
                codec_list.append(('mp4v', 'MPEG-4'))
        
        # 加入預設列表作為備案 (排除已加入的)
        for c, name in default_codecs:
            if not codec_list or c != codec_list[0][0]:
                codec_list.append((c, name))
        
        self.writer = None
        used_codec = None
        
        for fourcc_code, codec_name in codec_list:
            try:
                fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
                test_writer = cv2.VideoWriter(str(filepath), fourcc, fps, (width, height))
                
                if test_writer.isOpened():
                    self.writer = test_writer
                    used_codec = codec_name
                    print(f"錄影器: 成功使用 {codec_name} 編碼器")
                    break
                else:
                    test_writer.release()
            except Exception as e:
                print(f"錄影器: {codec_name} 編碼器失敗: {e}")
                continue
        
        if self.writer is None or not self.writer.isOpened():
            return {
                'success': False, 
                'error': '無法建立錄影檔案 - 所有編碼器都失敗。請確認已安裝 OpenCV 和必要的編碼器。'
            }

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
        
        # 套用儲存的對焦設定
        if cap is not None:
            self._apply_focus_to_cap(cap)
        
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
                
                # 顯示資訊覆蓋層
                # 焦距模式
                focus_text = f"AF" if self.auto_focus else f"MF:{self.focus_value}"
                cv2.putText(frame, focus_text, (10, frame.shape[0] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # 解析度資訊
                res_text = f"{frame.shape[1]}x{frame.shape[0]}"
                cv2.putText(frame, res_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # 使用更高的 JPEG 品質以獲得更清晰的預覽
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
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
        """刪除錄影檔案（移到垃圾桶）"""
        import send2trash
        filepath = self.output_dir / filename
        if filepath.exists():
            send2trash.send2trash(str(filepath))
            return {'success': True, 'message': f'已將 {filename} 移到垃圾桶'}
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
