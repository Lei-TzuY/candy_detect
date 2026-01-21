"""
列出所有攝影機設備及詳細資訊
"""
import cv2

def get_camera_name(index):
    """嘗試獲取攝影機名稱"""
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if cap.isOpened():
        # 獲取後端名稱
        backend = cap.getBackendName()
        cap.release()
        return backend
    return None

print("=" * 70)
print("攝影機設備列表")
print("=" * 70)

found_cameras = []

for i in range(10):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    
    if cap.isOpened():
        ret, frame = cap.read()
        
        if ret:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            
            # 測試是否支援 1920x1080
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            ret2, frame2 = cap.read()
            
            if ret2:
                actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                supports_1080p = (actual_w == 1920 and actual_h == 1080)
            else:
                supports_1080p = False
            
            # 測試是否支援 4K (BRIO 支援)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
            ret3, frame3 = cap.read()
            
            if ret3:
                actual_w_4k = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h_4k = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                supports_4k = (actual_w_4k == 3840 and actual_h_4k == 2160)
            else:
                supports_4k = False
            
            info = {
                'index': i,
                'default_res': f"{width}x{height}",
                'fps': fps,
                'supports_1080p': supports_1080p,
                'supports_4k': supports_4k
            }
            
            found_cameras.append(info)
            
            print(f"\n攝影機 {i}:")
            print(f"  預設解析度: {width}x{height}")
            print(f"  FPS: {fps}")
            print(f"  支援 1920x1080: {'✓' if supports_1080p else '✗'}")
            print(f"  支援 4K (3840x2160): {'✓ (可能是 BRIO)' if supports_4k else '✗'}")
            
        cap.release()

print("\n" + "=" * 70)
print("總結")
print("=" * 70)

brio_candidates = [c for c in found_cameras if c['supports_4k']]

if len(brio_candidates) >= 2:
    print(f"\n找到 {len(brio_candidates)} 個支援 4K 的攝影機 (可能是 BRIO):")
    for cam in brio_candidates:
        print(f"  - 攝影機 {cam['index']}: {cam['default_res']}, 4K: ✓")
    
    print("\n建議配置:")
    print(f"  Camera1: camera_index = {brio_candidates[0]['index']}")
    print(f"  Camera2: camera_index = {brio_candidates[1]['index']}")
    
elif len(brio_candidates) == 1:
    print(f"\n只找到 1 個支援 4K 的攝影機: 索引 {brio_candidates[0]['index']}")
else:
    print("\n未找到支援 4K 的攝影機")
    print("支援 1080p 的攝影機:")
    for cam in found_cameras:
        if cam['supports_1080p']:
            print(f"  - 攝影機 {cam['index']}: {cam['default_res']}")

print("\n" + "=" * 70)
