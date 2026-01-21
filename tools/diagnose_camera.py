"""
攝影機診斷工具
檢查攝影機是否正確連接並可用
"""

import cv2
import sys

def test_camera(index):
    """測試指定索引的攝影機"""
    print(f"\n正在測試攝影機 {index}...")
    
    try:
        # 使用 DirectShow（Windows 專用）
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            print(f"❌ 無法開啟攝影機 {index}")
            return False
        
        print(f"✓ 攝影機 {index} 已開啟")
        
        # 嘗試讀取一幀
        ret, frame = cap.read()
        
        if not ret:
            print(f"❌ 無法從攝影機 {index} 讀取畫面")
            cap.release()
            return False
        
        print(f"✓ 成功讀取畫面")
        print(f"  解析度: {frame.shape[1]}x{frame.shape[0]}")
        
        # 取得攝影機屬性
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        auto_focus = int(cap.get(cv2.CAP_PROP_AUTOFOCUS))
        focus = int(cap.get(cv2.CAP_PROP_FOCUS))
        exposure = int(cap.get(cv2.CAP_PROP_EXPOSURE))
        
        print(f"  設定解析度: {width}x{height}")
        print(f"  FPS: {fps}")
        print(f"  自動對焦: {auto_focus}")
        print(f"  焦距值: {focus}")
        print(f"  曝光值: {exposure}")
        
        cap.release()
        print(f"✓ 攝影機 {index} 測試完成")
        return True
        
    except Exception as e:
        print(f"❌ 攝影機 {index} 測試失敗: {e}")
        return False

def main():
    print("=" * 60)
    print("攝影機診斷工具")
    print("=" * 60)
    
    # 檢查 OpenCV 版本
    print(f"\nOpenCV 版本: {cv2.__version__}")
    
    # 測試攝影機 0-3
    available_cameras = []
    for i in range(4):
        if test_camera(i):
            available_cameras.append(i)
    
    print("\n" + "=" * 60)
    print("診斷結果")
    print("=" * 60)
    
    if available_cameras:
        print(f"\n✓ 找到 {len(available_cameras)} 個可用的攝影機:")
        for idx in available_cameras:
            print(f"  - 攝影機 {idx}")
    else:
        print("\n❌ 沒有找到可用的攝影機")
        print("\n可能的原因：")
        print("  1. 攝影機未連接")
        print("  2. 攝影機驅動程式未安裝")
        print("  3. 攝影機被其他程式佔用")
        print("  4. 需要管理員權限")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
