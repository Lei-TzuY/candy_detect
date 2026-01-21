"""
數據模型模塊

定義項目中使用的所有數據結構和模型類別。
"""

from dataclasses import dataclass, field
import cv2


@dataclass
class TrackState:
    """
    物體追蹤狀態

    屬性:
        center: 當前中心點坐標 (x, y)
        prev_center: 前一幀中心點坐標
        seen_abnormal: 是否檢測到異常
        counted: 是否已計算
        triggered: 是否已觸發繼電器
        missed_frames: 連續遺漏的幀數
        last_class: 最後檢測到的類別
        age: 物體被追蹤的總幀數
    """

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
    """
    攝影機上下文 - 存儲單個攝影機的所有狀態和配置

    屬性:
        name: 攝影機名稱
        index: 攝影機索引
        frame_width: 幀寬度
        frame_height: 幀高度
        relay_url: 繼電器 API URL
        line_x1: 偵測線起點 X 坐標
        line_x2: 偵測線終點 X 坐標
        cap: OpenCV 攝影機物件
        tracking_objects: 追蹤物體字典 {track_id: TrackState}
        track_id: 下一個追蹤 ID
        total_num: 通過的糖果總數
        normal_num: 正常糖果數
        abnormal_num: 異常糖果數
        focus_min: 焦距最小值
        focus_max: 焦距最大值
        relay_delay_ms: 繼電器延遲時間（毫秒）
        frame_index: 當前幀索引
        use_roi: 是否使用 ROI
        roi_processor: ROI 處理器
        kalman_trackers: 卡爾曼追蹤器字典
        use_kalman: 是否使用卡爾曼濾波
        adaptive_tracker: 自適應追蹤器
        use_adaptive: 是否使用自適應追蹤
    """

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
    relay_delay_ms: int = 0
    frame_index: int = 0
    
    # 優化相關字段
    use_roi: bool = False
    roi_processor: object = None
    kalman_trackers: dict = field(default_factory=dict)
    use_kalman: bool = False
    adaptive_tracker: object = None
    use_adaptive: bool = False
    relay_paused: bool = False
    
    # 畫面緩存（供錄影預覽等功能使用）
    latest_frame: object = None  # 最新的原始畫面
    latest_processed_frame: object = None  # 最新的處理後畫面

    def release(self) -> None:
        """釋放攝影機資源"""
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def get_stats(self) -> dict:
        """
        取得攝影機的統計數據

        Returns:
            包含統計數據的字典
        """
        return {
            "total": self.total_num,
            "normal": self.normal_num,
            "abnormal": self.abnormal_num,
            "tracking": len(self.tracking_objects),
        }
