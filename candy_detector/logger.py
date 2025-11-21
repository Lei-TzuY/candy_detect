"""
日誌系統模塊

提供統一的日誌記錄功能。
"""

import logging
import os
from datetime import datetime

from .constants import LOGS_DIR, LOG_FORMAT, LOG_DATE_FORMAT, LOG_LEVEL


def setup_logger(name: str, log_file: str | None = None) -> logging.Logger:
    """
    設置並返回日誌記錄器

    Args:
        name: 日誌記錄器名稱（通常使用模塊名）
        log_file: 日誌檔案路徑，如果為 None 則不寫入檔案

    Returns:
        配置好的日誌記錄器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # 避免重複的處理器
    if logger.handlers:
        return logger

    # 格式化器
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # 控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 檔案處理器（可選）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    取得現有的日誌記錄器或建立新的

    Args:
        name: 日誌記錄器名稱

    Returns:
        日誌記錄器
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        setup_logger(name)
    return logger


# 為應用程式建立主日誌檔案
APP_LOG_FILE = os.path.join(LOGS_DIR, f"candy_detector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
