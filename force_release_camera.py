"""
強制釋放攝影機資源工具
如果攝影機被占用，強制關閉占用進程並重新打開
"""
import cv2
import psutil
import time
import os
import sys

def find_camera_processes():
    """找出可能占用攝影機的進程"""
    camera_processes = []
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pinfo = proc.info
            pid = pinfo['pid']
            name = pinfo['name'].lower()
            
            # 跳過當前進程
            if pid == current_pid:
                continue
            
            # 檢查是否為可能使用攝影機的進程
            camera_keywords = [
                'python', 'opencv', 'camera', 'webcam', 'video',
                'streamlabs', 'obs', 'zoom', 'teams', 'skype',
                'chrome', 'firefox', 'edge'
            ]
            
            if any(keyword in name for keyword in camera_keywords):
                camera_processes.append({
                    'pid': pid,
                    'name': pinfo['name'],
                    'cmdline': ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return camera_processes

def kill_process(pid, name):
    """強制終止進程"""
    try:
        proc = psutil.Process(pid)
        proc.kill()
        print(f"  ✅ 已終止進程: {name} (PID: {pid})")
        return True
    except psutil.NoSuchProcess:
        print(f"  ⚠️ 進程已不存在: {pid}")
        return False
    except psutil.AccessDenied:
        print(f"  ❌ 權限不足，無法終止: {name} (PID: {pid})")
        return False
    except Exception as e:
        print(f"  ❌ 終止失敗: {e}")
        return False

def force_release_camera(index):
    """強制釋放攝影機"""
    print(f"\n{'='*60}")
    print(f"強制釋放攝影機 {index}")
    print('='*60)
    
    # 1. 嘗試直接打開
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if cap.isOpened():
        print("✅ 攝影機可以正常打開，無需強制釋放")
        cap.release()
        return True
    cap.release()
    
    print("❌ 攝影機被占用，開始強制釋放...")
    
    # 2. 找出占用進程
    print("\n正在掃描占用進程...")
    processes = find_camera_processes()
    
    if not processes:
        print("  未找到明顯占用攝影機的進程")
        print("  可能是驅動問題或攝影機硬體故障")
        return False
    
    print(f"\n找到 {len(processes)} 個可能占用攝影機的進程:")
    for i, proc in enumerate(processes, 1):
        print(f"\n{i}. {proc['name']} (PID: {proc['pid']})")
        if proc['cmdline']:
            print(f"   命令: {proc['cmdline'][:100]}...")
    
    # 3. 詢問是否終止
    print(f"\n{'='*60}")
    choice = input("是否終止所有這些進程？(y/n): ").strip().lower()
    
    if choice != 'y':
        print("取消操作")
        return False
    
    # 4. 終止進程
    print(f"\n正在終止 {len(processes)} 個進程...")
    killed = 0
    for proc in processes:
        if kill_process(proc['pid'], proc['name']):
            killed += 1
    
    print(f"\n成功終止 {killed}/{len(processes)} 個進程")
    
    # 5. 等待系統釋放資源
    print("\n等待系統釋放資源 (3秒)...")
    time.sleep(3)
    
    # 6. 重新嘗試打開
    print("\n重新嘗試打開攝影機...")
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ 成功！攝影機 {index} 已可用")
            print(f"   解析度: {frame.shape[1]}x{frame.shape[0]}")
            cap.release()
            return True
        else:
            print(f"⚠️ 攝影機已打開但無法讀取畫面")
            cap.release()
            return False
    else:
        print(f"❌ 仍然無法打開攝影機 {index}")
        print("可能需要:")
        print("  1. 重新插拔 USB 線")
        print("  2. 重啟電腦")
        print("  3. 檢查攝影機驅動")
        cap.release()
        return False

def force_release_all_cameras():
    """強制釋放所有攝影機"""
    print("\n" + "="*60)
    print("強制釋放所有攝影機資源")
    print("="*60)
    
    print("\n⚠️ 警告：此操作會終止所有可能使用攝影機的進程！")
    print("這包括:")
    print("  - 其他 Python 腳本")
    print("  - 視訊會議軟體 (Zoom, Teams, Skype)")
    print("  - 瀏覽器（如果正在使用攝影機）")
    print("  - OBS, StreamLabs 等直播軟體")
    
    choice = input("\n確定要繼續嗎？(yes/no): ").strip().lower()
    if choice != 'yes':
        print("取消操作")
        return False
    
    # 找出所有占用進程
    print("\n正在掃描所有占用進程...")
    processes = find_camera_processes()
    
    if not processes:
        print("✅ 未找到占用進程，攝影機應該可用")
        return True
    
    print(f"\n找到 {len(processes)} 個進程:")
    for proc in processes:
        print(f"  - {proc['name']} (PID: {proc['pid']})")
    
    # 終止所有進程
    print(f"\n正在終止所有進程...")
    killed = 0
    for proc in processes:
        if kill_process(proc['pid'], proc['name']):
            killed += 1
            time.sleep(0.1)  # 短暫延遲
    
    print(f"\n成功終止 {killed}/{len(processes)} 個進程")
    
    # 等待系統釋放資源
    print("\n等待系統釋放資源 (5秒)...")
    time.sleep(5)
    
    # 測試所有攝影機
    print("\n正在測試攝影機...")
    available = []
    for i in range(3):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                print(f"  ✅ 攝影機 {i} 可用")
                available.append(i)
            else:
                print(f"  ⚠️ 攝影機 {i} 打開但無法讀取")
        cap.release()
        time.sleep(0.5)
    
    if available:
        print(f"\n✅ 成功釋放！可用攝影機: {available}")
        return True
    else:
        print("\n❌ 所有攝影機仍不可用")
        print("建議:")
        print("  1. 重新插拔 USB 攝影機")
        print("  2. 重啟電腦")
        return False

if __name__ == "__main__":
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "攝影機強制釋放工具" + " "*15 + "║")
    print("╚" + "="*58 + "╝")
    
    print("\n選項:")
    print("  1. 強制釋放攝影機 0 (Camera 1)")
    print("  2. 強制釋放攝影機 1 (Camera 2)")
    print("  3. 強制釋放所有攝影機")
    print("  4. 退出")
    
    choice = input("\n請選擇 (1-4): ").strip()
    
    if choice == '1':
        force_release_camera(0)
    elif choice == '2':
        force_release_camera(1)
    elif choice == '3':
        force_release_all_cameras()
    elif choice == '4':
        print("退出")
        sys.exit(0)
    else:
        print("無效選擇")
    
    print(f"\n{'='*60}")
    input("按 Enter 鍵退出...")
