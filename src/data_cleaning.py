"""
資料清洗功能模組
提供重複圖片偵測和空白圖片偵測的 API
"""
from pathlib import Path
import sys

def find_duplicates_api(images_dir, threshold=5):
    """偵測重複圖片的 API 包裝函數"""
    try:
        # 動態導入
        from remove_duplicates_with_preview import find_duplicates
        return find_duplicates(images_dir, threshold)
    except ImportError as e:
        raise ImportError(f"無法導入重複偵測模組: {e}")

def find_blank_images_api(images_dir, std_threshold=25):
    """偵測空白圖片的 API 包裝函數"""
    try:
        from remove_blank_images import find_blank_images
        return find_blank_images(images_dir, std_threshold)
    except ImportError as e:
        raise ImportError(f"無法導入空白偵測模組: {e}")
