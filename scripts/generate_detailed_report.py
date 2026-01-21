#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成详细的模型测试报告，包括TP、FP、FN统计
"""
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import base64

def load_ground_truth(labels_dir, image_files):
    """加载Ground Truth标注"""
    gt_data = {}
    for img_file in image_files:
        label_file = labels_dir / f"{img_file.stem}.txt"
        if label_file.exists():
            with open(label_file, 'r') as f:
                boxes = []
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        boxes.append({
                            'class': int(parts[0]),
                            'x_center': float(parts[1]),
                            'y_center': float(parts[2]),
                            'width': float(parts[3]),
                            'height': float(parts[4])
                        })
                gt_data[img_file.name] = boxes
        else:
            gt_data[img_file.name] = []
    return gt_data

def calculate_iou(box1, box2):
    """计算两个框的IoU"""
    # 转换为 [x1, y1, x2, y2] 格式
    box1_x1 = box1['x_center'] - box1['width'] / 2
    box1_y1 = box1['y_center'] - box1['height'] / 2
    box1_x2 = box1['x_center'] + box1['width'] / 2
    box1_y2 = box1['y_center'] + box1['height'] / 2
    
    box2_x1 = box2['x_center'] - box2['width'] / 2
    box2_y1 = box2['y_center'] - box2['height'] / 2
    box2_x2 = box2['x_center'] + box2['width'] / 2
    box2_y2 = box2['y_center'] + box2['height'] / 2
    
    # 计算交集
    x1 = max(box1_x1, box2_x1)
    y1 = max(box1_y1, box2_y1)
    x2 = min(box1_x2, box2_x2)
    y2 = min(box1_y2, box2_y2)
    
    if x2 < x1 or y2 < y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    
    # 计算并集
    box1_area = box1['width'] * box1['height']
    box2_area = box2['width'] * box2['height']
    union = box1_area + box2_area - intersection
    
    return intersection / union if union > 0 else 0.0

def analyze_predictions(images_dir, gt_labels_dir, iou_threshold=0.5):
    """分析预测结果"""
    print("📊 开始分析预测结果...\n")
    
    # 获取所有图片
    image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
    print(f"找到 {len(image_files)} 张图片")
    
    # 加载Ground Truth
    print("加载Ground Truth标注...")
    gt_data = load_ground_truth(gt_labels_dir, image_files)
    
    # 运行预测
    print("运行YOLO预测并保存结果...")
    from ultralytics import YOLO
    model = YOLO("runs/detect/runs/detect/candy_gpu_v1/weights/best.pt")
    
    # 创建输出目录
    output_dir = Path("runs/detect/candy_gpu_v1_full_detection")
    
    results_data = []
    stats = {
        'TP': 0, 'FP': 0, 'FN': 0,
        'correct_by_class': defaultdict(int),
        'total_gt_by_class': defaultdict(int),
        'total_pred_by_class': defaultdict(int)
    }
    
    class_names = {0: 'normal', 1: 'abnormal'}
    
    for i, img_file in enumerate(image_files):
        print(f"\r处理: {i+1}/{len(image_files)}", end='', flush=True)
        
        # 预测并保存
        results = model.predict(str(img_file), conf=0.25, verbose=False, save=True, 
                               project=str(output_dir.parent), name=output_dir.name)
        pred_boxes = []
        
        for r in results:
            if r.boxes is not None:
                for box in r.boxes:
                    # 转换为YOLO格式
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    img_h, img_w = r.orig_shape
                    
                    x_center = ((x1 + x2) / 2) / img_w
                    y_center = ((y1 + y2) / 2) / img_h
                    width = (x2 - x1) / img_w
                    height = (y2 - y1) / img_h
                    
                    pred_boxes.append({
                        'class': int(box.cls[0].cpu().numpy()),
                        'x_center': float(x_center),
                        'y_center': float(y_center),
                        'width': float(width),
                        'height': float(height),
                        'conf': float(box.conf[0].cpu().numpy())
                    })
        
        # 获取GT
        gt_boxes = gt_data.get(img_file.name, [])
        
        # 匹配GT和预测
        matched_gt = set()
        matched_pred = set()
        
        for i, pred in enumerate(pred_boxes):
            best_iou = 0
            best_gt_idx = -1
            
            for j, gt in enumerate(gt_boxes):
                if gt['class'] == pred['class'] and j not in matched_gt:
                    iou = calculate_iou(pred, gt)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = j
            
            if best_iou >= iou_threshold:
                # TP
                stats['TP'] += 1
                stats['correct_by_class'][pred['class']] += 1
                matched_gt.add(best_gt_idx)
                matched_pred.add(i)
            else:
                # FP
                stats['FP'] += 1
            
            stats['total_pred_by_class'][pred['class']] += 1
        
        # FN (未匹配的GT)
        for j, gt in enumerate(gt_boxes):
            if j not in matched_gt:
                stats['FN'] += 1
            stats['total_gt_by_class'][gt['class']] += 1
        
        # 记录结果
        results_data.append({
            'image': img_file.name,
            'gt_count': len(gt_boxes),
            'pred_count': len(pred_boxes),
            'tp': len(matched_pred),
            'fp': len(pred_boxes) - len(matched_pred),
            'fn': len(gt_boxes) - len(matched_gt)
        })
    
    print("\n")
    
    # 计算指标
    precision = stats['TP'] / (stats['TP'] + stats['FP']) if (stats['TP'] + stats['FP']) > 0 else 0
    recall = stats['TP'] / (stats['TP'] + stats['FN']) if (stats['TP'] + stats['FN']) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'stats': stats,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'class_names': class_names,
        'results_data': results_data,
        'output_dir': output_dir
    }

def generate_html_report(analysis, output_path, detection_results_dir=None):
    """生成HTML报告"""
    stats = analysis['stats']
    precision = analysis['precision']
    recall = analysis['recall']
    f1 = analysis['f1']
    class_names = analysis['class_names']
    results_data = analysis.get('results_data', [])
    
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>candy_gpu_v1 详细测试报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', 'Microsoft JhengHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #2c3e50;
            font-size: 36px;
            margin-bottom: 10px;
            border-bottom: 4px solid #3498db;
            padding-bottom: 15px;
        }}
        .subtitle {{
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .metric-card.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .metric-card.warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .metric-card.info {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        .metric-value {{
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-label {{
            font-size: 14px;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .section {{
            margin: 40px 0;
        }}
        .section-title {{
            font-size: 24px;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-left: 15px;
            border-left: 4px solid #3498db;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
        }}
        .confusion-matrix {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            max-width: 600px;
            margin: 20px auto;
        }}
        .cm-cell {{
            padding: 20px;
            text-align: center;
            border-radius: 8px;
            font-weight: bold;
        }}
        .cm-tp {{ background: #d4edda; color: #155724; }}
        .cm-fp {{ background: #f8d7da; color: #721c24; }}
        .cm-fn {{ background: #fff3cd; color: #856404; }}
        .cm-label {{ background: #e9ecef; color: #495057; font-weight: normal; }}        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .image-item {{
            background: white;
            border-radius: 8px;
            padding: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .image-item img {{
            width: 100%;
            height: auto;
            border-radius: 4px;
        }}
        .image-name {{
            font-size: 12px;
            color: #555;
            margin-top: 8px;
            text-align: center;
            word-break: break-all;
        }}
        .image-stats {{
            font-size: 11px;
            color: #777;
            margin-top: 5px;
            text-align: center;
        }}
        .stat-good {{ color: #28a745; font-weight: bold; }}
        .stat-bad {{ color: #dc3545; font-weight: bold; }}    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 candy_gpu_v1 完整数据集测试报告</h1>
        <div class="subtitle">
            生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
            模型: candy_gpu_v1 (best.pt) | 
            测试集: old dataset (train + val)
        </div>

        <div class="metrics">
            <div class="metric-card success">
                <div class="metric-label">Precision (精确率)</div>
                <div class="metric-value">{precision*100:.1f}%</div>
            </div>
            <div class="metric-card success">
                <div class="metric-label">Recall (召回率)</div>
                <div class="metric-value">{recall*100:.1f}%</div>
            </div>
            <div class="metric-card info">
                <div class="metric-label">F1-Score</div>
                <div class="metric-value">{f1*100:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">True Positives (TP)</div>
                <div class="metric-value">{stats['TP']}</div>
            </div>
            <div class="metric-card warning">
                <div class="metric-label">False Positives (FP)</div>
                <div class="metric-value">{stats['FP']}</div>
            </div>
            <div class="metric-card warning">
                <div class="metric-label">False Negatives (FN)</div>
                <div class="metric-value">{stats['FN']}</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📊 混淆矩阵概念</div>
            <div class="confusion-matrix">
                <div class="cm-cell cm-label"></div>
                <div class="cm-cell cm-label">预测: Positive</div>
                <div class="cm-cell cm-label">预测: Negative</div>
                
                <div class="cm-cell cm-label">实际: Positive</div>
                <div class="cm-cell cm-tp">TP<br>{stats['TP']}</div>
                <div class="cm-cell cm-fn">FN<br>{stats['FN']}</div>
                
                <div class="cm-cell cm-label">实际: Negative</div>
                <div class="cm-cell cm-fp">FP<br>{stats['FP']}</div>
                <div class="cm-cell cm-label">-</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📈 各类别统计</div>
            <table>
                <thead>
                    <tr>
                        <th>类别</th>
                        <th>Ground Truth 总数</th>
                        <th>预测总数</th>
                        <th>正确预测</th>
                        <th>准确率</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for class_id, class_name in class_names.items():
        gt_total = stats['total_gt_by_class'][class_id]
        pred_total = stats['total_pred_by_class'][class_id]
        correct = stats['correct_by_class'][class_id]
        accuracy = (correct / gt_total * 100) if gt_total > 0 else 0
        
        html += f"""
                    <tr>
                        <td><strong>{class_name}</strong></td>
                        <td>{gt_total}</td>
                        <td>{pred_total}</td>
                        <td>{correct}</td>
                        <td>{accuracy:.1f}%</td>
                    </tr>
"""
    
    html += f"""
                </tbody>
            </table>
        </div>

        <div class="section">
            <div class="section-title">📋 指标说明</div>
            <table>
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>说明</th>
                        <th>当前值</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>TP (True Positive)</strong></td>
                        <td>正确检测到的目标数量</td>
                        <td>{stats['TP']}</td>
                    </tr>
                    <tr>
                        <td><strong>FP (False Positive)</strong></td>
                        <td>误检测（检测了不存在的目标）</td>
                        <td>{stats['FP']}</td>
                    </tr>
                    <tr>
                        <td><strong>FN (False Negatives)</strong></td>
                        <td>漏检测（未检测到存在的目标）</td>
                        <td>{stats['FN']}</td>
                    </tr>
                    <tr>
                        <td><strong>Precision (精确率)</strong></td>
                        <td>检测结果中正确的比例 = TP / (TP + FP)</td>
                        <td>{precision*100:.2f}%</td>
                    </tr>
                    <tr>
                        <td><strong>Recall (召回率)</strong></td>
                        <td>实际目标中被检测到的比例 = TP / (TP + FN)</td>
                        <td>{recall*100:.2f}%</td>
                    </tr>
                    <tr>
                        <td><strong>F1-Score</strong></td>
                        <td>精确率和召回率的调和平均数 = 2 × (P × R) / (P + R)</td>
                        <td>{f1*100:.2f}%</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p><strong>candy_gpu_v1 Model Performance Report</strong></p>
            <p>IoU Threshold: 0.5 | Confidence Threshold: 0.25</p>
            <p>检测结果图片保存于: runs/detect/runs/detect/candy_gpu_v1_quick_test/</p>
        </div>
"""
    
    # 添加检测结果图片
    if detection_results_dir and detection_results_dir.exists():
        print(f"\n📸 加载检测结果图片...")
        html += """
        <div class="section">
            <div class="section-title">🖼️ 检测结果可视化 (全部 {total} 张)</div>
            <div class="image-grid">
""".replace('{total}', str(len(results_data)))
        
        for i, result in enumerate(results_data):
            img_name = result['image']
            img_path = detection_results_dir / img_name
            
            if img_path.exists():
                try:
                    with open(img_path, 'rb') as f:
                        img_data = base64.b64encode(f.read()).decode()
                    
                    # 生成统计标签
                    tp = result.get('tp', 0)
                    fp = result.get('fp', 0)
                    fn = result.get('fn', 0)
                    
                    stat_class = 'stat-good' if (fp == 0 and fn == 0) else 'stat-bad'
                    
                    html += f"""
                <div class="image-item">
                    <img src="data:image/jpeg;base64,{img_data}" alt="{img_name}">
                    <div class="image-name">{img_name}</div>
                    <div class="image-stats">
                        GT: {result['gt_count']} | Pred: {result['pred_count']} | 
                        <span class="{stat_class}">TP: {tp}, FP: {fp}, FN: {fn}</span>
                    </div>
                </div>
"""
                    if (i + 1) % 50 == 0:
                        print(f"  已加载 {i+1}/{len(results_data)} 张图片...")
                except Exception as e:
                    print(f"  跳过图片 {img_name}: {e}")
        
        html += """
            </div>
        </div>
"""
        print(f"✅ 共加载 {len(results_data)} 张检测结果图片")
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ 详细报告已生成: {output_path}")
    return output_path

if __name__ == "__main__":
    import sys
    
    # 检测所有图片（train + val）
    train_images = Path("datasets/extracted_frames/old dataset/train")
    val_images = Path("datasets/extracted_frames/old dataset/val")
    
    train_labels = Path("datasets/annotated/labels/old dataset/train")
    val_labels = Path("datasets/annotated/labels/old dataset/val")
    train_labels = Path("datasets/annotated/labels/old dataset/train")
    val_labels = Path("datasets/annotated/labels/old dataset/val")
    
    # 合并所有图片和标签
    all_results = []
    
    print("=" * 60)
    print("🎯 candy_gpu_v1 完整数据集测试")
    print("=" * 60)
    
    # 处理train集
    if train_images.exists() and train_labels.exists():
        print(f"\n📁 处理 train 集...")
        train_analysis = analyze_predictions(train_images, train_labels)
        all_results.append(('train', train_analysis))
    
    # 处理val集
    if val_images.exists() and val_labels.exists():
        print(f"\n📁 处理 val 集...")
        val_analysis = analyze_predictions(val_images, val_labels)
        all_results.append(('val', val_analysis))
    
    # 合并统计
    total_stats = {
        'TP': 0, 'FP': 0, 'FN': 0,
        'correct_by_class': defaultdict(int),
        'total_gt_by_class': defaultdict(int),
        'total_pred_by_class': defaultdict(int)
    }
    
    all_results_data = []
    class_names = {0: 'normal', 1: 'abnormal'}
    output_dirs = []
    
    for dataset_name, analysis in all_results:
        stats = analysis['stats']
        total_stats['TP'] += stats['TP']
        total_stats['FP'] += stats['FP']
        total_stats['FN'] += stats['FN']
        
        for k in stats['correct_by_class']:
            total_stats['correct_by_class'][k] += stats['correct_by_class'][k]
        for k in stats['total_gt_by_class']:
            total_stats['total_gt_by_class'][k] += stats['total_gt_by_class'][k]
        for k in stats['total_pred_by_class']:
            total_stats['total_pred_by_class'][k] += stats['total_pred_by_class'][k]
        
        all_results_data.extend(analysis['results_data'])
        output_dirs.append(analysis.get('output_dir'))
    
    # 计算总体指标
    precision = total_stats['TP'] / (total_stats['TP'] + total_stats['FP']) if (total_stats['TP'] + total_stats['FP']) > 0 else 0
    recall = total_stats['TP'] / (total_stats['TP'] + total_stats['FN']) if (total_stats['TP'] + total_stats['FN']) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    combined_analysis = {
        'stats': total_stats,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'class_names': class_names,
        'results_data': all_results_data,
        'output_dir': output_dirs[0] if output_dirs else None
    }
    
    # 生成报告
    output_path = Path(f"reports/candy_gpu_v1_full_dataset_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    output_path.parent.mkdir(exist_ok=True)
    
    report_path = generate_html_report(combined_analysis, output_path, 
                                      detection_results_dir=combined_analysis['output_dir'])
    
    # 打印详细摘要
    print("\n" + "="*60)
    print("📊 完整数据集测试摘要")
    print("="*60)
    print(f"总图片数: {len(all_results_data)}")
    print(f"Precision: {precision*100:.2f}%")
    print(f"Recall: {recall*100:.2f}%")
    print(f"F1-Score: {f1*100:.2f}%")
    print(f"TP: {total_stats['TP']}")
    print(f"FP: {total_stats['FP']}")
    print(f"FN: {total_stats['FN']}")
    
    print("\n各数据集详情:")
    for dataset_name, analysis in all_results:
        print(f"\n{dataset_name}:")
        print(f"  Precision: {analysis['precision']*100:.2f}%")
        print(f"  Recall: {analysis['recall']*100:.2f}%")
        print(f"  F1: {analysis['f1']*100:.2f}%")
    
    print("="*60)
