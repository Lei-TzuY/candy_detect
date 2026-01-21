"""
Quick start annotation interface for candy_merged_20260116_154158 dataset
"""
import subprocess
import webbrowser
import time
import urllib.parse

# Dataset path
CUSTOM_PATH = r"d:\專案\candy\datasets\candy_merged_20260116_154158\images"

print("=" * 80)
print("Starting candy merged dataset annotation interface...")
print(f"Dataset path: {CUSTOM_PATH}")
print("=" * 80)

# Start Flask app in background
print("\nStarting web server...")
flask_process = subprocess.Popen(
    ["python", "src/web_app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    encoding='utf-8',
    errors='replace'
)

# Wait for server to start
print("Waiting for server to be ready...")
time.sleep(3)

# Build URL with custom path
encoded_path = urllib.parse.quote(CUSTOM_PATH)
url = f"http://localhost:5000/annotate?custom_path={encoded_path}"

print(f"\nOpening browser: {url}")
print("=" * 80)
print("Server started!")
print("Tips:")
print("   - Click images to view/edit annotations")
print("   - Green badge = manual, Blue badge = AI")
print("   - Close this window to stop server")
print("=" * 80)

# Open browser
webbrowser.open(url)

# Show server output
try:
    for line in flask_process.stdout:
        print(line, end='')
except KeyboardInterrupt:
    print("\n\nStopping server...")
    flask_process.terminate()
    flask_process.wait()
    print("Server stopped")
