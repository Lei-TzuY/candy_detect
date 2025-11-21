"""
配置管理模塊

負責讀取、驗證和管理 config.ini 配置檔案。
提供統一的配置訪問介面。
"""

import configparser
import os
from typing import Any
from pathlib import Path

from .constants import CONFIG_FILE, YOLO_DEFAULT_CONF_THRESHOLD, YOLO_DEFAULT_NMS_THRESHOLD


class ConfigManager:
    """配置文件管理器"""

    def __init__(self, config_path: str = CONFIG_FILE):
        """
        初始化配置管理器

        Args:
            config_path: 配置檔案路徑
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser()

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置檔案不存在: {config_path}")

        self.config.read(config_path, encoding="utf-8")

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """
        取得配置值

        Args:
            section: 配置區塊名稱
            key: 配置鍵名
            fallback: 預設值

        Returns:
            配置值
        """
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise ValueError(f"無法找到配置: [{section}]{key}")

    def getint(self, section: str, key: str, fallback: int | None = None) -> int:
        """取得整數配置值"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise ValueError(f"無法找到整數配置: [{section}]{key}")

    def getfloat(self, section: str, key: str, fallback: float | None = None) -> float:
        """取得浮點數配置值"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise ValueError(f"無法找到浮點數配置: [{section}]{key}")

    def get_camera_config(self, camera_name: str) -> dict:
        """
        取得指定攝影機的完整配置

        Args:
            camera_name: 攝影機配置區塊名稱 (例如: 'Camera1')

        Returns:
            包含攝影機配置的字典
        """
        if not self.config.has_section(camera_name):
            raise ValueError(f"配置中找不到攝影機區塊: {camera_name}")

        return {
            "camera_index": self.getint(camera_name, "camera_index"),
            "camera_name": self.get(camera_name, "camera_name"),
            "frame_width": self.getint(camera_name, "frame_width"),
            "frame_height": self.getint(camera_name, "frame_height"),
            "relay_url": self.get(camera_name, "relay_url"),
            "detection_line_x1": self.getint(camera_name, "detection_line_x1"),
            "detection_line_x2": self.getint(camera_name, "detection_line_x2"),
            "use_startup_autofocus": self.getint(camera_name, "use_startup_autofocus", fallback=0),
            "autofocus_frames": self.getint(camera_name, "autofocus_frames", fallback=20),
            "autofocus_delay_ms": self.getint(camera_name, "autofocus_delay_ms", fallback=50),
            "focus_min": self.getint(camera_name, "focus_min", fallback=0),
            "focus_max": self.getint(camera_name, "focus_max", fallback=255),
            "relay_delay_ms": self.getint(camera_name, "relay_delay_ms", fallback=0),
        }

    def get_detection_config(self) -> dict:
        """取得偵測配置"""
        return {
            "confidence_threshold": self.getfloat("Detection", "confidence_threshold", fallback=YOLO_DEFAULT_CONF_THRESHOLD),
            "nms_threshold": self.getfloat("Detection", "nms_threshold", fallback=YOLO_DEFAULT_NMS_THRESHOLD),
            "input_size": self.getint("Detection", "input_size", fallback=416),
        }

    def get_paths_config(self) -> dict:
        """取得模型路徑配置"""
        return {
            "weights": self.get("Paths", "weights"),
            "cfg": self.get("Paths", "cfg"),
            "classes": self.get("Paths", "classes"),
        }

    def get_display_config(self) -> dict:
        """取得顯示配置"""
        return {
            "target_height": self.getint("Display", "target_height", fallback=480),
            "max_width": self.getint("Display", "max_width", fallback=0),
        }
