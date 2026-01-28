
import cv2

def list_ports():
    """
    Test the ports and returns a tuple with the available ports and the ones that are working.
    """
    is_working = True
    dev_port = 0
    working_ports = []
    available_ports = []
    
    print("正在掃描可用攝影機... (這可能需要幾秒鐘)")
    
    # Check ports 0-9
    for dev_port in range(10):
        try:
            camera = cv2.VideoCapture(dev_port, cv2.CAP_DSHOW)
            if not camera.isOpened():
                is_working = False
            else:
                is_reading, img = camera.read()
                w = camera.get(3)
                h = camera.get(4)
                if is_reading:
                    print(f"✅ 找到攝影機 index {dev_port}: 解析度 {int(w)}x{int(h)}")
                    working_ports.append(dev_port)
                else:
                    print(f"⚠️  找到攝影機 index {dev_port}: 但無法讀取畫面")
                    available_ports.append(dev_port)
                camera.release()
        except Exception as e:
            pass
            
    return working_ports, available_ports

if __name__ == '__main__':
    working, available = list_ports()
    print("\n" + "="*40)
    print("掃描結果:")
    if not working:
        print("❌ 未找到可用的攝影機！")
    else:
        print(f"📸 可用攝影機 ID: {working}")
        print("\n請修改 config.ini 中的 [Camera1] 或 [Camera2] 的 camera_index 為上述 ID")
    print("="*40)
