"""
樣本採集工具 - 可調整焦距的錄影與截圖程式

功能：
- 即時調整攝影機焦距
- 錄製影片
- 截圖保存樣本
- 顯示即時預覽

使用方法：
    python sample_recorder.py

按鍵操作：
    [Space]  - 截圖保存樣本
    [R]      - 開始/停止錄影
    [+/-]    - 調整焦距（也可使用滑桿）
    [A]      - 自動對焦
    [M]      - 手動對焦模式
    [Q/ESC]  - 退出程式
"""

import cv2
import time
import os
from datetime import datetime
from pathlib import Path


class SampleRecorder:
    def __init__(self, camera_index=0, width=1920, height=1080):
        """初始化樣本採集器"""
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None
        self.is_recording = False
        self.video_writer = None
        self.focus_value = 0
        self.auto_focus = False
        
        # 建立輸出目錄
        self.base_dir = Path(__file__).parent / "samples"
        self.images_dir = self.base_dir / "images"
        self.videos_dir = self.base_dir / "videos"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"樣本保存位置：{self.base_dir}")
        print(f"- 圖片：{self.images_dir}")
        print(f"- 影片：{self.videos_dir}")
    
    def initialize_camera(self):
        """初始化攝影機"""
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"無法開啟攝影機 {self.camera_index}")
        
        # 設定解析度
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        # 獲取焦距範圍
        try:
            self.focus_value = int(self.cap.get(cv2.CAP_PROP_FOCUS))
            print(f"當前焦距：{self.focus_value}")
        except:
            self.focus_value = 0
        
        print(f"攝影機初始化成功 ({self.width}x{self.height})")
    
    def set_focus(self, value):
        """設定焦距"""
        try:
            # 關閉自動對焦
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            self.auto_focus = False
            # 設定焦距值
            self.cap.set(cv2.CAP_PROP_FOCUS, value)
            self.focus_value = value
            print(f"焦距設定為：{value}")
        except Exception as e:
            print(f"無法設定焦距：{e}")
    
    def toggle_autofocus(self):
        """切換自動對焦"""
        try:
            self.auto_focus = not self.auto_focus
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1 if self.auto_focus else 0)
            mode = "自動對焦" if self.auto_focus else "手動對焦"
            print(f"已切換至 {mode} 模式")
        except Exception as e:
            print(f"無法切換對焦模式：{e}")
    
    def capture_image(self, frame):
        """截圖保存樣本"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = self.images_dir / f"sample_{timestamp}.jpg"
        
        cv2.imwrite(str(filename), frame)
        print(f"✓ 已保存圖片：{filename.name}")
        return str(filename)
    
    def start_recording(self, frame_size):
        """開始錄影"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.videos_dir / f"video_{timestamp}.avi"
        
        # 使用 MJPEG 編碼器（兼容性好）
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        fps = 30.0
        
        self.video_writer = cv2.VideoWriter(
            str(filename), fourcc, fps, frame_size
        )
        
        if self.video_writer.isOpened():
            self.is_recording = True
            print(f"● 開始錄影：{filename.name}")
        else:
            print("✗ 無法開始錄影")
            self.video_writer = None
    
    def stop_recording(self):
        """停止錄影"""
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        self.is_recording = False
        print("■ 停止錄影")
    
    def on_focus_trackbar(self, value):
        """焦距滑桿回調函數"""
        self.set_focus(value)
    
    def run(self):
        """運行主程式"""
        try:
            self.initialize_camera()
            
            # 創建視窗和滑桿
            window_name = "樣本採集工具 - 按 Q 退出"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            
            # 創建焦距滑桿（0-255）
            cv2.createTrackbar(
                "焦距 (Focus)", 
                window_name, 
                self.focus_value, 
                255, 
                self.on_focus_trackbar
            )
            
            # 顯示使用說明
            print("\n" + "="*60)
            print("按鍵操作說明：")
            print("  [Space]  - 截圖保存樣本")
            print("  [R]      - 開始/停止錄影")
            print("  [+/-]    - 微調焦距")
            print("  [A]      - 切換自動對焦")
            print("  [M]      - 手動對焦模式")
            print("  [Q/ESC]  - 退出程式")
            print("="*60 + "\n")
            
            frame_count = 0
            
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("無法讀取攝影機畫面")
                    break
                
                frame_count += 1
                
                # 如果正在錄影，寫入影片
                if self.is_recording and self.video_writer:
                    self.video_writer.write(frame)
                
                # 在畫面上顯示資訊
                display_frame = frame.copy()
                
                # 顯示狀態資訊
                info_y = 40
                font = cv2.FONT_HERSHEY_SIMPLEX
                
                # 對焦模式
                focus_mode = "自動對焦" if self.auto_focus else f"手動對焦 ({self.focus_value})"
                cv2.putText(display_frame, f"對焦：{focus_mode}", 
                           (20, info_y), font, 1.2, (0, 255, 0), 2)
                info_y += 45
                
                # 錄影狀態
                if self.is_recording:
                    cv2.putText(display_frame, "● 錄影中...", 
                               (20, info_y), font, 1.2, (0, 0, 255), 2)
                    # 錄影指示燈（閃爍）
                    if frame_count % 20 < 10:
                        cv2.circle(display_frame, (self.width - 50, 50), 
                                 20, (0, 0, 255), -1)
                else:
                    cv2.putText(display_frame, "○ 未錄影", 
                               (20, info_y), font, 1.2, (200, 200, 200), 2)
                info_y += 45
                
                # 幀數
                cv2.putText(display_frame, f"Frame: {frame_count}", 
                           (20, info_y), font, 0.8, (255, 255, 255), 2)
                
                # 顯示畫面
                cv2.imshow(window_name, display_frame)
                
                # 處理按鍵
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == 27:  # Q 或 ESC
                    break
                elif key == ord(' '):  # Space - 截圖
                    self.capture_image(frame)
                elif key == ord('r') or key == ord('R'):  # R - 錄影
                    if self.is_recording:
                        self.stop_recording()
                    else:
                        frame_size = (frame.shape[1], frame.shape[0])
                        self.start_recording(frame_size)
                elif key == ord('a') or key == ord('A'):  # A - 自動對焦
                    self.toggle_autofocus()
                elif key == ord('m') or key == ord('M'):  # M - 手動對焦
                    if self.auto_focus:
                        self.toggle_autofocus()
                elif key == ord('+') or key == ord('='):  # + - 增加焦距
                    new_focus = min(255, self.focus_value + 5)
                    self.set_focus(new_focus)
                    cv2.setTrackbarPos("焦距 (Focus)", window_name, new_focus)
                elif key == ord('-') or key == ord('_'):  # - - 減少焦距
                    new_focus = max(0, self.focus_value - 5)
                    self.set_focus(new_focus)
                    cv2.setTrackbarPos("焦距 (Focus)", window_name, new_focus)
        
        finally:
            # 清理資源
            if self.is_recording:
                self.stop_recording()
            
            if self.cap:
                self.cap.release()
            
            cv2.destroyAllWindows()
            print("\n程式已結束")


def main():
    """主函數"""
    print("=" * 60)
    print("  樣本採集工具 v1.0")
    print("=" * 60)
    
    # 可以修改這些參數
    CAMERA_INDEX = 0      # 攝影機索引（0=第一個，1=第二個）
    WIDTH = 1920          # 寬度
    HEIGHT = 1080         # 高度
    
    recorder = SampleRecorder(
        camera_index=CAMERA_INDEX,
        width=WIDTH,
        height=HEIGHT
    )
    
    try:
        recorder.run()
    except KeyboardInterrupt:
        print("\n使用者中斷程式")
    except Exception as e:
        print(f"\n錯誤：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
