"""
測試錄影預覽 API
"""

import requests
import time

def test_preview_api():
    """測試預覽 API"""
    print("測試錄影預覽 API...")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # 測試鏡頭 0
    for camera_index in [0, 1]:
        print(f"\n測試鏡頭 {camera_index}:")
        preview_url = f"{base_url}/api/recorder/{camera_index}/preview"
        
        try:
            # 發送請求（設定短超時）
            response = requests.get(preview_url, stream=True, timeout=5)
            
            print(f"  狀態碼: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('Content-Type')}")
            
            if response.status_code == 200:
                # 讀取前幾個 bytes 確認有資料
                chunk = next(response.iter_content(chunk_size=1024), None)
                if chunk:
                    print(f"  ✓ 成功接收影像資料 ({len(chunk)} bytes)")
                else:
                    print(f"  ❌ 沒有接收到影像資料")
            else:
                print(f"  ❌ 請求失敗")
                print(f"  回應: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"  ❌ 請求超時")
        except requests.exceptions.ConnectionError as e:
            print(f"  ❌ 連線失敗: {e}")
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_preview_api()
