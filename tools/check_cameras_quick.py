import cv2
import sys

print("快速檢查攝影機...")
for i in range(4):
    print(f"\n測試攝影機 {i}:")
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            w, h = frame.shape[1], frame.shape[0]
            print(f"  ✓ 可用 - 解析度: {w}x{h}")
            
            # 測試 1920x1080
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            ret2, frame2 = cap.read()
            if ret2:
                w2, h2 = frame2.shape[1], frame2.shape[0]
                print(f"  設定 1920x1080 後實際: {w2}x{h2}")
        else:
            print(f"  ✗ 開啟成功但無法讀取")
        cap.release()
    else:
        print(f"  ✗ 無法開啟")

print("\n完成")
