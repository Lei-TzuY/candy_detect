# 启动 Web 标注系统
# 这个脚本会自动启动标注系统并打开浏览器

import subprocess
import webbrowser
import time
import sys
from pathlib import Path

def start_annotation_system():
    """启动标注系统"""
    
    print("=" * 70)
    print("🚀 启动糖果标注系统")
    print("=" * 70)
    
    # 检查是否在虚拟环境中
    venv_python = Path("D:/專案/candy/.venv/Scripts/python.exe")
    
    if not venv_python.exists():
        print("\n❌ 找不到虚拟环境！")
        return
    
    print("\n🔄 启动 Flask 服务器...")
    print("📍 URL: http://localhost:5000/annotate")
    print("⏹️  按 Ctrl+C 停止服务器\n")
    
    # 启动服务器
    try:
        # 先等待一秒再打开浏览器
        time.sleep(2)
        webbrowser.open('http://localhost:5000/annotate')
        
        # 启动 Flask
        subprocess.run([
            str(venv_python),
            "src/web_app.py"
        ])
        
    except KeyboardInterrupt:
        print("\n\n✅ 服务器已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")

if __name__ == '__main__':
    start_annotation_system()
