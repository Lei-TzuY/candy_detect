"""
檢查攝影機支援的解析度
"""

import cv2

def test_resolution(cap, width, height):
    """測試指定解析度是否支援"""
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    return actual_width == width and actual_height == height

def check_camera_resolutions(camera_index):
    """檢查攝影機支援的解析度"""
    print(f"\n{'='*60}")
    print(f"檢查攝影機 {camera_index} 支援的解析度")
    print(f"{'='*60}\n")
    
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print(f"❌ 無法開啟攝影機 {camera_index}")
        return
    
    # 常見解析度列表
    resolutions = [
        (640, 480, "VGA"),
        (800, 600, "SVGA"),
        (1024, 768, "XGA"),
        (1280, 720, "HD 720p"),
        (1280, 1024, "SXGA"),
        (1920, 1080, "Full HD 1080p"),
        (2560, 1440, "2K"),
        (3840, 2160, "4K"),
    ]
    
    print("測試常見解析度支援情況：\n")
    supported = []
    
    for width, height, name in resolutions:
        if test_resolution(cap, width, height):
            print(f"✓ {width}x{height} ({name})")
            supported.append((width, height, name))
        else:
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"✗ {width}x{height} ({name}) - 實際取得: {actual_width}x{actual_height}")
    
    cap.release()
    
    print(f"\n{'='*60}")
    print(f"攝影機 {camera_index} 支援 {len(supported)} 種解析度")
    print(f"{'='*60}\n")
    
    if supported:
        print("建議使用的解析度：")
        # 推薦最高支援的解析度
        best = supported[-1]
        print(f"  最佳: {best[0]}x{best[1]} ({best[2]})")
        if len(supported) > 1:
            print(f"  次佳: {supported[-2][0]}x{supported[-2][1]} ({supported[-2][2]})")

def main():
    print("\n攝影機解析度檢查工具")
    print("="*60)
    
    # 檢查攝影機 0 和 1
    for i in [0, 1]:
        check_camera_resolutions(i)
        print()

if __name__ == "__main__":
    main()
