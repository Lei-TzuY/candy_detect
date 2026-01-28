from pathlib import Path
import re

html_path = Path(r'c:\Users\st313\Desktop\candy\templates\recorder.html')

# Read as binary
content_bytes = html_path.read_bytes()

# Decode using Latin-1 (which was the original problem source, but allows us to read it)
# We know it's not valid UTF-8
try:
    content = content_bytes.decode('utf-8')
    print("Read as UTF-8 (unexpected but good)")
except UnicodeDecodeError:
    content = content_bytes.decode('latin1')
    print("Read as Latin-1 (expected)")

# Now content is a Python string (Unicode)

# Define the buttons HTML to insert
buttons_html_0 = """
                    <button class="btn btn-warning btn-sm" onclick="testSpray(0)" id="btn-spray-0">💨 測試噴氣</button>
                    <button class="btn btn-secondary btn-sm" onclick="toggleRelayPause(0)" id="btn-pause-relay-0">⏸️ 暫停噴氣</button>"""

buttons_html_1 = """
                    <button class="btn btn-warning btn-sm" onclick="testSpray(1)" id="btn-spray-1">💨 測試噴氣</button>
                    <button class="btn btn-secondary btn-sm" onclick="toggleRelayPause(1)" id="btn-pause-relay-1">⏸️ 暫停噴氣</button>"""

status_html_0 = """
                    <div class="status-item">
                        <span class="status-label">噴氣:</span>
                        <span class="status-value" id="relay-status-0">正常</span>
                    </div>"""

status_html_1 = """
                    <div class="status-item">
                        <span class="status-label">噴氣:</span>
                        <span class="status-value" id="relay-status-1">正常</span>
                    </div>"""

# Helper to insert after a regex match
def insert_after_regex(content, pattern, insertion):
    match = re.search(pattern, content, re.DOTALL)
    if match:
        end_pos = match.end()
        return content[:end_pos] + insertion + content[end_pos:], True
    return content, False

# Insert buttons for Camera 0
# The file might have garbled characters if we decoded latin1 but it was actually something else
# But we are looking for English tags mostly
pattern_0 = r'<button[^>]*id="btn-record-0"[^>]*>.*?</button>'
content, success = insert_after_regex(content, pattern_0, buttons_html_0)
if success:
    print("Inserted buttons for Camera 0")
else:
    print("Could not find insertion point for Camera 0 buttons")

# Insert status for Camera 0
pattern_status_0 = r'<span[^>]*id="status-0"[^>]*>.*?</span>\s*</div>'
content, success = insert_after_regex(content, pattern_status_0, status_html_0)
if success:
    print("Inserted status for Camera 0")

# Insert buttons for Camera 1
pattern_1 = r'<button[^>]*id="btn-record-1"[^>]*>.*?</button>'
content, success = insert_after_regex(content, pattern_1, buttons_html_1)
if success:
    print("Inserted buttons for Camera 1")

# Insert status for Camera 1
pattern_status_1 = r'<span[^>]*id="status-1"[^>]*>.*?</span>\s*</div>'
content, success = insert_after_regex(content, pattern_status_1, status_html_1)
if success:
    print("Inserted status for Camera 1")

# Save back with UTF-8-SIG (BOM) for Flask
html_path.write_text(content, encoding='utf-8-sig')
print("Saved file with utf-8-sig encoding")
