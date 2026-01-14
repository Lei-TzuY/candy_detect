"""
偵測並移除空白圖片（純白色或灰色）
Detect and remove blank images (pure white or gray)
"""
import os
from pathlib import Path
from PIL import Image
import numpy as np
import webbrowser
import base64
from io import BytesIO
import send2trash
from concurrent.futures import ThreadPoolExecutor, as_completed

def analyze_image_content(image_path):
    """
    分析圖片內容，判斷是否為空白/純色圖片
    
    Returns:
        dict: {
            'is_blank': bool,
            'mean_color': tuple (R, G, B),
            'std_dev': float,  # 標準差，越小代表越單調
            'reason': str
        }
    """
    try:
        with Image.open(image_path) as img:
            # 轉換為 RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 轉為 numpy array
            img_array = np.array(img)
            
            # 計算平均顏色（轉換為 Python int 避免 JSON 序列化問題）
            mean_color = tuple(int(x) for x in img_array.mean(axis=(0, 1)))
            
            # 計算標準差（衡量顏色變化程度）
            std_dev = float(img_array.std())
            
            # 判斷標準（可調整）
            is_blank = False
            reason = ""
            
            # 標準差很小 = 顏色很單一
            if std_dev < 5:  # 幾乎完全沒有變化
                is_blank = True
                reason = f"純色圖片 (標準差: {std_dev:.2f})"
            elif std_dev < 25:  # 變化很小（放寬閾值）
                # 檢查是否為白色或灰色系
                r, g, b = mean_color
                # RGB 值都很接近且都很高 = 白色/淺灰
                # RGB 值都很接近 = 灰色
                color_diff = max(abs(r - g), abs(g - b), abs(r - b))
                
                if color_diff < 20:  # 顏色很接近 = 單色系
                    if r > 200:  # 淺色（白色/淺灰）
                        is_blank = True
                        reason = f"接近純白/淺灰 (平均色: RGB{mean_color}, 標準差: {std_dev:.2f})"
                    elif r > 150:  # 中淺灰
                        is_blank = True
                        reason = f"接近淺灰 (平均色: RGB{mean_color}, 標準差: {std_dev:.2f})"
                    elif r > 80:  # 中灰
                        is_blank = True
                        reason = f"接近中灰 (平均色: RGB{mean_color}, 標準差: {std_dev:.2f})"
                    elif r < 50:  # 深灰/黑
                        is_blank = True
                        reason = f"接近純黑/深灰 (平均色: RGB{mean_color}, 標準差: {std_dev:.2f})"

            
            return {
                'is_blank': is_blank,
                'mean_color': mean_color,
                'std_dev': std_dev,
                'reason': reason if is_blank else "正常圖片"
            }
    
    except Exception as e:
        print(f"Error analyzing {image_path}: {e}")
        return None

def image_to_base64(image_path, max_size=200):
    """Convert image to base64 for HTML embedding."""
    try:
        with Image.open(image_path) as img:
            img.thumbnail((max_size, max_size))
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        return None

def _analyze_worker(img_path):
    """Worker function for parallel image analysis."""
    analysis = analyze_image_content(img_path)
    if analysis and analysis['is_blank']:
        return {'path': img_path, 'analysis': analysis}
    return None

def find_blank_images(directory, std_threshold=15, min_brightness=100):
    """
    尋找空白圖片（支援子資料夾）- 使用平行處理加速
    
    Args:
        directory: 圖片目錄
        std_threshold: 標準差閾值（越小越嚴格）
        min_brightness: 最小亮度（0-255，用於判斷灰/白色）
    
    Returns:
        list: 空白圖片列表
    """
    directory = Path(directory)
    
    # 遞迴搜尋所有子資料夾中的圖片
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = []
    for ext in image_extensions:
        image_files.extend(directory.rglob(f'*{ext}'))
    
    image_files = sorted(image_files)
    total_files = len(image_files)
    
    print(f"找到 {total_files} 個圖片檔案")
    print("分析圖片內容... (使用平行處理)")
    
    blank_images = []
    processed = 0
    
    # 使用 ThreadPoolExecutor 平行處理（預設 8 個執行緒）
    num_workers = min(8, max(1, total_files // 10))
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(_analyze_worker, img_path): img_path for img_path in image_files}
        
        for future in as_completed(futures):
            result = future.result()
            processed += 1
            
            if processed % 200 == 0 or processed == total_files:
                print(f"已處理 {processed}/{total_files} 張圖片... ({processed*100//total_files}%)")
            
            if result is not None:
                blank_images.append(result)
    
    return blank_images, total_files

def generate_html_report(blank_images, total_files, output_file='blank_images_report.html', images_dir=None):
    """生成 HTML 報告
    
    Args:
        blank_images: 空白圖片列表
        total_files: 總圖片數
        output_file: 輸出檔名
        images_dir: 圖片根目錄（用於計算相對路徑）
    """
    print(f"\n生成 HTML 報告: {output_file}")
    
    blank_count = len(blank_images)
    total_size = sum(img['path'].stat().st_size for img in blank_images)
    size_mb = total_size / 1024 / 1024
    
    html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>空白圖片檢測報告</title>
    <style>
        body {{
            font-family: "Microsoft JhengHei", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-box {{
            background: #fff3e0;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #ff9800;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #666;
        }}
        .stat-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #ff9800;
        }}
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }}
        .image-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 3px solid #f44336;
            position: relative;
            transition: opacity 0.3s;
        }}
        .image-card img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 4px;
            background: #f0f0f0;
        }}
        .image-info {{
            margin-top: 10px;
        }}
        .filename {{
            font-size: 0.85em;
            color: #333;
            word-break: break-all;
            margin-bottom: 5px;
        }}
        .reason {{
            font-size: 0.8em;
            color: #666;
            background: #f9f9f9;
            padding: 5px;
            border-radius: 3px;
        }}
        .color-preview {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 3px;
            border: 1px solid #ddd;
            vertical-align: middle;
            margin-right: 5px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.75em;
            font-weight: bold;
            background: #f44336;
            color: white;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🗑️ 空白圖片檢測報告</h1>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-label">總圖片數</div>
                <div class="stat-value">{total_files}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">空白圖片</div>
                <div class="stat-value">{blank_count}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">佔比</div>
                <div class="stat-value">{blank_count/total_files*100:.1f}%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">可節省空間</div>
                <div class="stat-value">{size_mb:.1f} MB</div>
            </div>
        </div>
        <p style="margin-top: 15px; color: #666;">
            ⚠️ 以下 {blank_count} 張圖片被判定為空白/純色圖片，請勾選要刪除的圖片
        </p>
        <div style="margin-top: 15px;">
            <button id="selectAllBtn" onclick="toggleSelectAll()" style="padding: 10px 20px; margin-right: 10px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px;">☑ 全選</button>
            <button id="deleteSelectedBtn" onclick="deleteSelected()" style="padding: 10px 20px; background: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px;">🗑️ 刪除選中項</button>
            <span id="selectedCount" style="margin-left: 15px; color: #666;">已選擇: 0</span>
        </div>
    </div>
    
    <div class="image-grid">
"""
    
    # 顯示所有空白圖片（不限制數量）
    for img_info in blank_images:
        img_path = img_info['path']
        analysis = img_info['analysis']
        r, g, b = analysis['mean_color']
        
        # 計算相對路徑（用於刪除API）
        if images_dir:
            try:
                relative_path = str(img_path.relative_to(images_dir)).replace('\\', '/')
            except ValueError:
                relative_path = img_path.name
        else:
            relative_path = img_path.name
        
        html += f"""
        <div class="image-card" data-filename="{relative_path}">
            <input type="checkbox" class="img-checkbox" style="position: absolute; top: 10px; left: 10px; width: 20px; height: 20px; cursor: pointer; z-index: 10;" onchange="updateSelectedCount()">
            <div class="badge" style="margin-left: 30px;">可刪除</div>
"""
        
        # Add image
        img_data = image_to_base64(img_path)
        if img_data:
            html += f'            <img src="{img_data}" alt="Blank Image">\n'
        
        html += f"""
            <div class="image-info">
                <div class="filename">📁 {img_path.name}</div>
                <div class="reason">
                    <span class="color-preview" style="background-color: rgb({r},{g},{b});"></span>
                    {analysis['reason']}
                </div>
            </div>
        </div>
"""
    
    html += """
    </div>
    <script>
        let allSelected = false;
        let isDragging = false;
        let dragStartX, dragStartY;
        let selectionBox = null;
        
        // 初始化
        document.addEventListener('DOMContentLoaded', () => {
            // 創建選取框
            selectionBox = document.createElement('div');
            selectionBox.style.cssText = 'position: fixed; border: 2px dashed #2196F3; background: rgba(33, 150, 243, 0.15); display: none; pointer-events: none; z-index: 9999;';
            document.body.appendChild(selectionBox);
            
            // 點擊圖片卡片切換選取
            document.querySelector('.image-grid').addEventListener('click', (e) => {
                const card = e.target.closest('.image-card');
                if (e.target.classList.contains('img-checkbox') || e.target.closest('.img-checkbox')) return;
                if (card) { const cb = card.querySelector('.img-checkbox'); if (cb && !cb.disabled) { cb.checked = !cb.checked; updateSelectedCount(); }}
            });
            
            // 拖動選取 - 從頁面任何位置開始
            document.addEventListener('mousedown', (e) => {
                // 忽略按鈕、checkbox、以及圖片本身的點擊
                if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
                if (e.target.classList.contains('img-checkbox') || e.target.closest('.img-checkbox')) return;
                if (e.target.tagName === 'IMG') return;
                if (e.button !== 0) return; // 只響應左鍵
                
                isDragging = true; 
                dragStartX = e.clientX; 
                dragStartY = e.clientY;
                selectionBox.style.left = e.clientX + 'px'; 
                selectionBox.style.top = e.clientY + 'px';
                selectionBox.style.width = '0px'; 
                selectionBox.style.height = '0px'; 
                selectionBox.style.display = 'block'; 
                e.preventDefault();
            });
            
            document.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                const x = Math.min(dragStartX, e.clientX), y = Math.min(dragStartY, e.clientY);
                const w = Math.abs(e.clientX - dragStartX), h = Math.abs(e.clientY - dragStartY);
                selectionBox.style.left = x + 'px'; 
                selectionBox.style.top = y + 'px';
                selectionBox.style.width = w + 'px'; 
                selectionBox.style.height = h + 'px';
                
                // 高亮在選取框內的卡片
                const selRect = selectionBox.getBoundingClientRect();
                document.querySelectorAll('.image-card').forEach(card => {
                    const cardRect = card.getBoundingClientRect();
                    const overlaps = !(cardRect.right < selRect.left || cardRect.left > selRect.right || 
                                      cardRect.bottom < selRect.top || cardRect.top > selRect.bottom);
                    // 添加視覺反饋
                    if (overlaps) {
                        card.style.outline = '3px solid #2196F3';
                        card.style.outlineOffset = '2px';
                    } else {
                        card.style.outline = '';
                        card.style.outlineOffset = '';
                    }
                });
            });
            
            document.addEventListener('mouseup', (e) => { 
                if (!isDragging) return;
                
                const selRect = selectionBox.getBoundingClientRect();
                const hasArea = selRect.width > 10 && selRect.height > 10;
                
                if (hasArea) {
                    // 如果沒有按住 Ctrl，先取消所有選取
                    if (!e.ctrlKey) {
                        document.querySelectorAll('.img-checkbox').forEach(cb => cb.checked = false);
                    }
                    
                    // 選取在範圍內的卡片
                    document.querySelectorAll('.image-card').forEach(card => {
                        const cardRect = card.getBoundingClientRect();
                        const overlaps = !(cardRect.right < selRect.left || cardRect.left > selRect.right || 
                                          cardRect.bottom < selRect.top || cardRect.top > selRect.bottom);
                        const cb = card.querySelector('.img-checkbox');
                        if (overlaps && cb && !cb.disabled) cb.checked = true;
                        // 清除視覺反饋
                        card.style.outline = '';
                        card.style.outlineOffset = '';
                    });
                    updateSelectedCount();
                } else {
                    // 清除所有視覺反饋
                    document.querySelectorAll('.image-card').forEach(card => {
                        card.style.outline = '';
                        card.style.outlineOffset = '';
                    });
                }
                
                isDragging = false; 
                selectionBox.style.display = 'none';
            });
        });
        
        function updateSelectedCount() {
            const checkboxes = document.querySelectorAll('.img-checkbox:checked');
            document.getElementById('selectedCount').textContent = `已選擇: ${checkboxes.length}`;
        }
        
        function toggleSelectAll() {
            const checkboxes = document.querySelectorAll('.img-checkbox');
            allSelected = !allSelected;
            checkboxes.forEach(cb => cb.checked = allSelected);
            document.getElementById('selectAllBtn').textContent = allSelected ? '☒ 取消全選' : '☑ 全選';
            updateSelectedCount();
        }
        
        function deleteSelected() {
            const checkboxes = document.querySelectorAll('.img-checkbox:checked');
            if (checkboxes.length === 0) {
                alert('請先勾選要刪除的圖片');
                return;
            }
            
            const filenames = Array.from(checkboxes).map(cb => 
                cb.closest('.image-card').getAttribute('data-filename')
            );
            
            if (!confirm(`確定要刪除 ${filenames.length} 張圖片嗎？`)) {
                return;
            }
            
            // 方法1: 使用 BroadcastChannel (最穩定)
            if (typeof BroadcastChannel !== 'undefined') {
                try {
                    const reportChannel = new BroadcastChannel('candy_report_channel');
                    reportChannel.postMessage({
                        type: 'delete_images',
                        filenames: filenames
                    });
                    console.log('✅ 透過 BroadcastChannel 發送刪除請求');
                    alert('刪除請求已發送！');
                    
                    // Mark as deleted in UI
                    checkboxes.forEach(cb => {
                        const card = cb.closest('.image-card');
                        card.style.opacity = '0.3';
                        card.querySelector('.badge').textContent = '已刪除';
                        card.querySelector('.badge').style.background = '#999';
                        cb.disabled = true;
                    });
                    updateSelectedCount();
                    return;
                } catch (e) {
                    console.error('BroadcastChannel 失敗:', e);
                }
            }
            
            // 方法2: 嘗試 window.opener (舊版相容)
            console.log('window.opener:', window.opener);
            console.log('deleteImagesFromReport:', window.opener ? window.opener.deleteImagesFromReport : 'N/A');
            
            if (window.opener && typeof window.opener.deleteImagesFromReport === 'function') {
                window.opener.deleteImagesFromReport(filenames);
                alert('刪除請求已發送！');
                // Mark as deleted in UI
                checkboxes.forEach(cb => {
                    const card = cb.closest('.image-card');
                    card.style.opacity = '0.3';
                    card.querySelector('.badge').textContent = '已刪除';
                    card.querySelector('.badge').style.background = '#999';
                    cb.disabled = true;
                });
                updateSelectedCount();
            } else {
                // 方法3: 直接 API 調用 (最後手段)
                console.error('無法訪問 window.opener.deleteImagesFromReport');
                
                if (confirm('無法連接到主視窗。要直接刪除這些文件嗎？')) {
                    deleteViaAPI(filenames, checkboxes);
                }
            }
        }
        
        async function deleteViaAPI(filenames, checkboxes) {
            try {
                // 如果是 file:// 協議，需要使用完整 URL
                const baseUrl = window.location.protocol === 'file:' 
                    ? 'http://localhost:5000' 
                    : '';
                    
                const response = await fetch(baseUrl + '/api/annotate/delete-images', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ filenames: filenames })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    alert(`刪除完成！\\n成功刪除: ${data.deleted} 張圖片`);
                    // Mark as deleted in UI
                    checkboxes.forEach(cb => {
                        const card = cb.closest('.image-card');
                        card.style.opacity = '0.3';
                        card.querySelector('.badge').textContent = '已刪除';
                        card.querySelector('.badge').style.background = '#999';
                        cb.disabled = true;
                    });
                    updateSelectedCount();
                } else {
                    alert('刪除失敗: ' + (data.error || '未知錯誤'));
                }
            } catch (error) {
                console.error('刪除錯誤:', error);
                alert('刪除失敗: ' + error.message);
            }
        }
    </script>
</body>
</html>
"""
    
    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 報告已生成: {output_file}")
    return output_file

def delete_blank_images(blank_images):
    """刪除空白圖片"""
    deleted = 0
    errors = 0
    
    for img_info in blank_images:
        try:
            # img_info['path'].unlink()
            send2trash.send2trash(str(img_info['path']))
            deleted += 1
        except Exception as e:
            print(f"Error deleting {img_info['path']}: {e}")
            errors += 1
    
    return deleted, errors

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='偵測並移除空白/純色圖片')
    parser.add_argument('directory', nargs='?', 
                       default='datasets/extracted_frames',
                       help='圖片目錄')
    parser.add_argument('--std-threshold', type=float, default=15,
                       help='標準差閾值 (0-50, 越小越嚴格, 預設=15)')
    parser.add_argument('--report', type=str, default='blank_images_report.html',
                       help='HTML 報告檔名')
    parser.add_argument('--delete', action='store_true',
                       help='刪除空白圖片')
    parser.add_argument('--no-browser', action='store_true',
                       help='不自動開啟瀏覽器')
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.exists(args.directory):
        print(f"錯誤: 找不到目錄 '{args.directory}'")
        exit(1)
    
    # Find blank images
    blank_images, total_files = find_blank_images(args.directory, args.std_threshold)
    
    # Print statistics
    print(f"\n{'='*60}")
    print(f"檢測結果:")
    print(f"{'='*60}")
    print(f"總圖片數: {total_files}")
    print(f"空白圖片: {len(blank_images)}")
    print(f"佔比: {len(blank_images)/total_files*100:.1f}%")
    
    if len(blank_images) == 0:
        print("\n✅ 沒有找到空白圖片！")
        exit(0)
    
    total_size = sum(img['path'].stat().st_size for img in blank_images)
    print(f"可節省空間: {total_size / 1024 / 1024:.2f} MB")
    
    # Generate HTML report
    report_path = generate_html_report(blank_images, total_files, args.report)
    
    # Open in browser
    if not args.no_browser:
        print(f"\n🌐 在瀏覽器中開啟報告...")
        webbrowser.open(f'file://{os.path.abspath(report_path)}')
    
    # Delete if requested
    if args.delete:
        print(f"\n{'='*60}")
        response = input(f"❓ 確認要刪除 {len(blank_images)} 個空白圖片嗎? (yes/no): ")
        if response.lower() == 'yes':
            print("🗑️  正在刪除空白圖片...")
            deleted, errors = delete_blank_images(blank_images)
            print(f"✅ 成功刪除 {deleted} 個檔案")
            if errors > 0:
                print(f"⚠️  {errors} 個檔案刪除失敗")
        else:
            print("❌ 取消刪除")
    else:
        print(f"\n{'='*60}")
        print("ℹ️  這是預覽模式，沒有刪除任何檔案")
        print("   如果確認要刪除，請執行:")
        print(f"   python {os.path.basename(__file__)} --delete")