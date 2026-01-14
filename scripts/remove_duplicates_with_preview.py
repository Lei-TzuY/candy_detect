"""
Remove duplicate images with HTML preview report.
Generates a visual report showing duplicates side-by-side before deletion.
"""
import os
import hashlib
from pathlib import Path
from PIL import Image
import imagehash
import base64
from io import BytesIO
import webbrowser
import send2trash
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 執行緒安全的進度計數器
_progress_lock = threading.Lock()
_progress_count = 0

def get_image_hash(image_path, hash_size=8):
    """Generate perceptual hash for an image."""
    try:
        with Image.open(image_path) as img:
            return str(imagehash.average_hash(img, hash_size=hash_size))
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def _hash_worker(args):
    """Worker function for parallel hash calculation."""
    img_path, hash_size = args
    img_hash = get_image_hash(img_path, hash_size)
    return (img_path, img_hash)

def image_to_base64(image_path, max_size=300):
    """Convert image to base64 for HTML embedding."""
    try:
        with Image.open(image_path) as img:
            # Resize for preview
            img.thumbnail((max_size, max_size))
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        return None

def find_duplicates(directory, similarity_threshold=5):
    """
    Find duplicate images and return detailed information (支援子資料夾).
    
    Returns:
        tuple: (duplicate_groups, stats)
        duplicate_groups: list of dicts with 'original' and 'duplicates'
        stats: dictionary with statistics
    """
    directory = Path(directory)
    
    # Dictionary to store hash -> list of file paths
    hash_dict = {}
    
    # 遞迴搜尋所有子資料夾中的圖片
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = []
    for ext in image_extensions:
        image_files.extend(directory.rglob(f'*{ext}'))
    
    image_files = sorted(image_files)
    total_files = len(image_files)
    
    print(f"Found {total_files} image files in {directory}")
    print("Calculating image hashes... (using parallel processing)")
    
    # 使用 ThreadPoolExecutor 平行計算 hash（預設 8 個執行緒）
    num_workers = min(8, max(1, total_files // 10))  # 每 10 張至少 1 個 worker
    processed = 0
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(_hash_worker, (img_path, 8)): img_path for img_path in image_files}
        
        for future in as_completed(futures):
            img_path, img_hash = future.result()
            processed += 1
            
            if processed % 200 == 0 or processed == total_files:
                print(f"Processed {processed}/{total_files} images... ({processed*100//total_files}%)")
            
            if img_hash:
                if img_hash not in hash_dict:
                    hash_dict[img_hash] = []
                hash_dict[img_hash].append(img_path)
    
    # Find exact duplicates
    duplicate_groups = []
    all_duplicates = set()
    
    print("\nFinding exact duplicates...")
    for img_hash, paths in hash_dict.items():
        if len(paths) > 1:
            duplicate_groups.append({
                'original': paths[0],
                'duplicates': paths[1:],
                'reason': 'Exact duplicate (identical hash)',
                'hash_distance': 0
            })
            all_duplicates.update(paths[1:])
    
    # Find near-duplicates
    if similarity_threshold > 0:
        print("Finding near-duplicates...")
        hashes_list = list(hash_dict.keys())
        checked_pairs = set()
        
        for i in range(len(hashes_list)):
            if i % 100 == 0 and i > 0:
                print(f"Compared {i}/{len(hashes_list)} hash groups...")
            
            for j in range(i + 1, len(hashes_list)):
                pair_key = tuple(sorted([hashes_list[i], hashes_list[j]]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                hash1 = imagehash.hex_to_hash(hashes_list[i])
                hash2 = imagehash.hex_to_hash(hashes_list[j])
                distance = hash1 - hash2
                
                if 0 < distance <= similarity_threshold:
                    # Similar images found
                    paths1 = hash_dict[hashes_list[i]]
                    paths2 = hash_dict[hashes_list[j]]
                    
                    # Use the first file from the first group as original
                    original = paths1[0]
                    duplicates = paths1[1:] + paths2
                    
                    # Remove duplicates that were already marked
                    new_duplicates = [p for p in duplicates if p not in all_duplicates]
                    
                    if new_duplicates:
                        duplicate_groups.append({
                            'original': original,
                            'duplicates': new_duplicates,
                            'reason': f'Near duplicate (difference: {distance})',
                            'hash_distance': distance
                        })
                        all_duplicates.update(new_duplicates)
    
    # Calculate statistics
    total_duplicates = len(all_duplicates)
    space_saved = sum(p.stat().st_size for p in all_duplicates)
    
    stats = {
        'total_files': len(image_files),
        'unique_files': len(image_files) - total_duplicates,
        'duplicate_groups': len(duplicate_groups),
        'total_duplicates': total_duplicates,
        'space_saved_mb': space_saved / 1024 / 1024
    }
    
    return duplicate_groups, stats

def generate_html_report(duplicate_groups, stats, output_file='duplicate_report.html', images_dir=None):
    """Generate HTML report with image previews.
    
    Args:
        duplicate_groups: 重複群組列表
        stats: 統計數據
        output_file: 輸出檔名
        images_dir: 圖片根目錄（用於計算相對路徑）
    """
    print(f"\nGenerating HTML report: {output_file}")
    
    html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>重複圖片檢測報告</title>
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
            background: #f0f7ff;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #2196F3;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #666;
        }}
        .stat-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #2196F3;
        }}
        .duplicate-group {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .group-header {{
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        .reason {{
            color: #666;
            font-size: 0.9em;
        }}
        .image-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: flex-start;
        }}
        .image-box {{
            flex: 0 0 auto;
            text-align: center;
            position: relative;
            transition: opacity 0.3s;
        }}
        .image-box.original {{
            border: 3px solid #4CAF50;
            padding: 10px;
            border-radius: 8px;
            background: #f1f8f4;
        }}
        .image-box.duplicate {{
            border: 3px solid #f44336;
            padding: 10px;
            border-radius: 8px;
            background: #fef1f0;
        }}
        .image-box img {{
            max-width: 250px;
            max-height: 250px;
            border-radius: 4px;
            display: block;
        }}
        .image-label {{
            margin-top: 8px;
            font-size: 0.85em;
            word-break: break-all;
            max-width: 250px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.75em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .badge.original {{
            background: #4CAF50;
            color: white;
        }}
        .badge.duplicate {{
            background: #f44336;
            color: white;
        }}
        .arrow {{
            font-size: 2em;
            color: #999;
            align-self: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 重複圖片檢測報告</h1>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-label">總圖片數</div>
                <div class="stat-value">{stats['total_files']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">唯一圖片</div>
                <div class="stat-value">{stats['unique_files']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">重複群組</div>
                <div class="stat-value">{stats['duplicate_groups']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">重複圖片</div>
                <div class="stat-value">{stats['total_duplicates']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">可節省空間</div>
                <div class="stat-value">{stats['space_saved_mb']:.1f} MB</div>
            </div>
        </div>
        <p style="margin-top: 15px; color: #666;">
            ✅ <strong>綠框</strong> = 將保留的原始圖片 | 
            ❌ <strong>紅框</strong> = 可刪除的重複圖片（請勾選）
        </p>
        <div style="margin-top: 15px;">
            <button id="selectAllBtn" onclick="toggleSelectAll()" style="padding: 10px 20px; margin-right: 10px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px;">☑ 全選</button>
            <button id="deleteSelectedBtn" onclick="deleteSelected()" style="padding: 10px 20px; background: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px;">🗑️ 刪除選中項</button>
            <span id="selectedCount" style="margin-left: 15px; color: #666;">已選擇: 0</span>
        </div>
    </div>
"""
    
    # Add duplicate groups (顯示所有群組)
    for idx, group in enumerate(duplicate_groups, 1):
        original = group['original']
        duplicates = group['duplicates']
        reason = group['reason']
        
        html += f"""
    <div class="duplicate-group">
        <div class="group-header">
            <h3>重複群組 #{idx}</h3>
            <div class="reason">{reason}</div>
        </div>
        <div class="image-container">
            <div class="image-box original">
                <div class="badge original">保留</div>
"""
        
        # Add original image
        img_data = image_to_base64(original)
        if img_data:
            html += f'                <img src="{img_data}" alt="Original">\n'
        html += f'                <div class="image-label">📁 {original.name}</div>\n'
        html += '            </div>\n'
        
        html += '            <div class="arrow">→</div>\n'
        
        # Add duplicate images (顯示所有重複圖片)
        for dup in duplicates:
            # 計算相對路徑
            if images_dir:
                try:
                    dup_rel_path = str(dup.relative_to(images_dir)).replace('\\', '/')
                except ValueError:
                    dup_rel_path = dup.name
            else:
                dup_rel_path = dup.name
                
            html += f"""
            <div class="image-box duplicate" data-filename="{dup_rel_path}">
                <input type="checkbox" class="img-checkbox" style="position: absolute; top: 5px; left: 5px; width: 20px; height: 20px; cursor: pointer; z-index: 10;" onchange="updateSelectedCount()">
                <div class="badge duplicate" style="margin-left: 30px;">可刪除</div>
"""
            img_data = image_to_base64(dup)
            if img_data:
                html += f'                <img src="{img_data}" alt="Duplicate">\n'
            html += f'                <div class="image-label">📁 {dup.name}</div>\n'
            html += '            </div>\n'
        
        html += '        </div>\n    </div>\n'
    
    html += """
    <script>
        let allSelected = false;
        
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
                cb.closest('.image-box').getAttribute('data-filename')
            );
            
            if (!confirm(`確定要刪除 ${filenames.length} 張圖片嗎？`)) {
                return;
            }
            
            // 調試信息
            console.log('window.opener:', window.opener);
            console.log('deleteImagesFromReport:', window.opener ? window.opener.deleteImagesFromReport : 'N/A');
            
            // 嘗試調用父窗口的刪除函數
            if (window.opener && typeof window.opener.deleteImagesFromReport === 'function') {
                window.opener.deleteImagesFromReport(filenames);
                alert('刪除請求已發送！');
                // Mark as deleted in UI
                checkboxes.forEach(cb => {
                    const box = cb.closest('.image-box');
                    box.style.opacity = '0.3';
                    box.querySelector('.badge').textContent = '已刪除';
                    box.querySelector('.badge').style.background = '#999';
                    cb.disabled = true;
                });
                updateSelectedCount();
            } else {
                // 如果無法通過 window.opener，嘗試直接 API 調用
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
                        const box = cb.closest('.image-box');
                        box.style.opacity = '0.3';
                        box.querySelector('.badge').textContent = '已刪除';
                        box.querySelector('.badge').style.background = '#999';
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

def delete_duplicates(duplicate_groups):
    """Delete duplicate files."""
    all_duplicates = []
    for group in duplicate_groups:
        all_duplicates.extend(group['duplicates'])
    
    deleted = 0
    errors = 0
    
    for dup_path in all_duplicates:
        try:
            # dup_path.unlink()
            send2trash.send2trash(str(dup_path))
            deleted += 1
        except Exception as e:
            print(f"Error deleting {dup_path}: {e}")
            errors += 1
    
    return deleted, errors

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Remove duplicate images with visual preview')
    parser.add_argument('directory', nargs='?', 
                       default='datasets/extracted_frames',
                       help='Directory containing images')
    parser.add_argument('--threshold', type=int, default=5,
                       help='Similarity threshold (0-64, default=5)')
    parser.add_argument('--report', type=str, default='duplicate_report.html',
                       help='HTML report filename')
    parser.add_argument('--delete', action='store_true',
                       help='Delete duplicates after generating report')
    parser.add_argument('--no-browser', action='store_true',
                       help='Do not open browser automatically')
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' not found!")
        exit(1)
    
    # Find duplicates
    duplicate_groups, stats = find_duplicates(args.directory, args.threshold)
    
    # Print statistics
    print(f"\n{'='*60}")
    print(f"檢測結果:")
    print(f"{'='*60}")
    print(f"總圖片數: {stats['total_files']}")
    print(f"唯一圖片: {stats['unique_files']}")
    print(f"重複群組: {stats['duplicate_groups']}")
    print(f"重複圖片: {stats['total_duplicates']}")
    print(f"可節省空間: {stats['space_saved_mb']:.2f} MB")
    
    if stats['total_duplicates'] == 0:
        print("\n✅ 沒有找到重複的圖片！")
        exit(0)
    
    # Generate HTML report
    report_path = generate_html_report(duplicate_groups, stats, args.report)
    
    # Open in browser
    if not args.no_browser:
        print(f"\n🌐 在瀏覽器中開啟報告...")
        webbrowser.open(f'file://{os.path.abspath(report_path)}')
    
    # Delete if requested
    if args.delete:
        print(f"\n{'='*60}")
        response = input(f"❓ 確認要刪除 {stats['total_duplicates']} 個重複檔案嗎? (yes/no): ")
        if response.lower() == 'yes':
            print("🗑️  正在刪除重複檔案...")
            deleted, errors = delete_duplicates(duplicate_groups)
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
