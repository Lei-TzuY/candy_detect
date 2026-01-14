from pathlib import Path

# Append to script.js
script_path = Path(r'c:\Users\st313\Desktop\candy\static\script.js')
script_content = script_path.read_text(encoding='utf-8')

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

if "async function toggleRelayPause" not in script_content:
    with open(script_path, 'a', encoding='utf-8') as f:
        f.write(js_to_append)
    print("Appended to script.js")
else:
    print("Function already exists in script.js")

# Append to style.css
style_path = Path(r'c:\Users\st313\Desktop\candy\static\style.css')
style_content = style_path.read_text(encoding='utf-8')

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

if ".btn-pause-relay" not in style_content:
    with open(style_path, 'a', encoding='utf-8') as f:
        f.write(css_to_append)
    print("Appended to style.css")
else:
    print("Styles already exist in style.css")
