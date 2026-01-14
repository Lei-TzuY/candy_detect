from pathlib import Path
import shutil
import os
import time

def atomic_append(file_path, append_content, check_string):
    path = Path(file_path)
    try:
        content = path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return False

    if check_string in content:
        print(f"Content already exists in {path.name}")
        return True

    new_content = content + "\n" + append_content
    temp_path = path.with_name(path.name + '.tmp')
    
    try:
        temp_path.write_text(new_content, encoding='utf-8')
        # Try to replace
        try:
            os.replace(temp_path, path)
            print(f"Successfully updated {path.name}")
            return True
        except PermissionError:
            print(f"Permission denied replacing {path.name}. Trying shutil.move...")
            try:
                shutil.move(str(temp_path), str(path))
                print(f"Successfully moved to {path.name}")
                return True
            except Exception as e:
                print(f"Failed to move: {e}")
                return False
    except Exception as e:
        print(f"Error writing temp file: {e}")
        return False
    finally:
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except:
                pass

# Script.js content
js_to_append = """
// 切換繼電器暫停狀態
async function toggleRelayPause(cameraIndex) {
    const btn = document.getElementById(`btn-pause-relay-${cameraIndex}`);
    if (!btn) return;

    try {
        const response = await fetch(`/api/cameras/${cameraIndex}/relay/pause`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            const isPaused = result.paused;
            if (isPaused) {
                btn.innerHTML = '▶️ 恢復噴氣';
                btn.classList.add('btn-danger');
                btn.classList.remove('btn-pause-relay');
            } else {
                btn.innerHTML = '⏸️ 暫停噴氣';
                btn.classList.add('btn-pause-relay');
                btn.classList.remove('btn-danger');
            }
        } else {
            console.error('切換暫停狀態失敗:', result.error);
            alert('切換失敗');
        }
    } catch (error) {
        console.error('API 錯誤:', error);
        alert('操作失敗');
    }
}
"""

# Style.css content
css_to_append = """
/* Pause Relay Button Styles */
.btn-pause-relay {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    color: white;
}

.btn-pause-relay:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
}

.btn-danger {
    background: linear-gradient(135deg, #ef4444, #dc2626) !important;
    color: white;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
}

.btn-secondary {
    background: linear-gradient(135deg, #6b7280, #4b5563) !important;
    color: white;
}
"""

atomic_append(r'c:\Users\st313\Desktop\candy\static\script.js', js_to_append, "async function toggleRelayPause")
atomic_append(r'c:\Users\st313\Desktop\candy\static\style.css', css_to_append, ".btn-pause-relay")
