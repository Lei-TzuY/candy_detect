#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速生成candy_gpu_v1模型测试报告
"""
import os
from pathlib import Path
from collections import defaultdict

# 扫描检测结果
results_dir = Path("runs/detect/runs/detect/candy_gpu_v1_quick_test")
labels_dir = results_dir / "labels"

if not labels_dir.exists():
    print(f"❌ 标签目录不存在: {labels_dir}")
    exit(1)

# 统计
stats = defaultdict(int)
class_counts = defaultdict(int)

label_files = list(labels_dir.glob("*.txt"))
print(f"📊 找到 {len(label_files)} 个检测结果文件\n")

for label_file in label_files:
    stats['total_images'] += 1
    
    with open(label_file, 'r') as f:
        lines = f.readlines()
    
    if not lines:
        stats['no_detection'] += 1
        continue
    
    has_normal = False
    has_abnormal = False
    
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 5:
            class_id = int(parts[0])
            confidence = float(parts[5]) if len(parts) > 5 else 0.0
            
            if class_id == 0:
                has_normal = True
                class_counts['normal'] += 1
            elif class_id == 1:
                has_abnormal = True
                class_counts['abnormal'] += 1
    
    if has_normal and has_abnormal:
        stats['both'] += 1
    elif has_normal:
        stats['normal_only'] += 1
    elif has_abnormal:
        stats['abnormal_only'] += 1

# 打印报告
print("=" * 60)
print("🎯 candy_gpu_v1 模型检测统计报告")
print("=" * 60)
print(f"\n📁 测试集: old dataset/train")
print(f"📊 总图片数: {stats['total_images']}")
print(f"\n🔍 检测结果分布:")
print(f"  ✅ 只检测到normal: {stats['normal_only']} 张")
print(f"  ⚠️  只检测到abnormal: {stats['abnormal_only']} 张")
print(f"  🔄 同时检测到两者: {stats['both']} 张")
print(f"  ❌ 未检测到任何物体: {stats['no_detection']} 张")
print(f"\n📦 类别统计:")
print(f"  normal 检测框总数: {class_counts['normal']}")
print(f"  abnormal 检测框总数: {class_counts['abnormal']}")
print(f"\n💡 检测率: {((stats['total_images'] - stats['no_detection']) / stats['total_images'] * 100):.1f}%")
print("=" * 60)

# 生成简单HTML报告
html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>candy_gpu_v1 检测报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card.green {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .stat-card.orange {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .stat-card.blue {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .details {{
            margin: 30px 0;
        }}
        .detail-row {{
            display: flex;
            justify-content: space-between;
            padding: 15px;
            border-bottom: 1px solid #eee;
        }}
        .detail-row:hover {{
            background: #f8f9fa;
        }}
        .detail-label {{
            font-weight: 500;
            color: #555;
        }}
        .detail-value {{
            color: #2c3e50;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #777;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 candy_gpu_v1 模型检测报告</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">总图片数</div>
                <div class="stat-value">{stats['total_images']}</div>
            </div>
            <div class="stat-card green">
                <div class="stat-label">只检测到Normal</div>
                <div class="stat-value">{stats['normal_only']}</div>
            </div>
            <div class="stat-card orange">
                <div class="stat-label">只检测到Abnormal</div>
                <div class="stat-value">{stats['abnormal_only']}</div>
            </div>
            <div class="stat-card blue">
                <div class="stat-label">同时检测到两者</div>
                <div class="stat-value">{stats['both']}</div>
            </div>
        </div>
        
        <div class="details">
            <h2>📊 详细统计</h2>
            <div class="detail-row">
                <span class="detail-label">测试集</span>
                <span class="detail-value">old dataset/train</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">模型</span>
                <span class="detail-value">candy_gpu_v1 (best.pt)</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">未检测到物体</span>
                <span class="detail-value">{stats['no_detection']} 张</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">检测率</span>
                <span class="detail-value">{((stats['total_images'] - stats['no_detection']) / stats['total_images'] * 100):.1f}%</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Normal 检测框总数</span>
                <span class="detail-value">{class_counts['normal']}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Abnormal 检测框总数</span>
                <span class="detail-value">{class_counts['abnormal']}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">平均每张图片检测框数</span>
                <span class="detail-value">{((class_counts['normal'] + class_counts['abnormal']) / stats['total_images']):.2f}</span>
            </div>
        </div>
        
        <div class="footer">
            <p>📁 详细检测结果图片位于: runs/detect/runs/detect/candy_gpu_v1_quick_test/</p>
            <p>生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

# 保存HTML报告
report_path = Path("reports") / f"candy_gpu_v1_quick_report_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
report_path.parent.mkdir(exist_ok=True)

with open(report_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ HTML报告已生成: {report_path}")
print(f"   使用浏览器打开查看完整报告")
