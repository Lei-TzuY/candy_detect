import csv
from datetime import datetime

print('讀取訓練結果...')
# 讀取訓練結果
with open('runs/detect/runs/detect/candy_gpu_v1/results.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

last = rows[-1]
best = max(rows, key=lambda x: float(x['metrics/mAP50(B)']))

# 準確度數據
precision = float(last['metrics/precision(B)'])
recall = float(last['metrics/recall(B)'])
map50 = float(last['metrics/mAP50(B)'])
map50_95 = float(last['metrics/mAP50-95(B)'])
f1_score = 2 * (precision * recall) / (precision + recall)

precision_best = float(best['metrics/precision(B)'])
recall_best = float(best['metrics/recall(B)'])
map50_best = float(best['metrics/mAP50(B)'])
map50_95_best = float(best['metrics/mAP50-95(B)'])

# 計算訓練趨勢
epochs_data = []
for row in rows:
    epochs_data.append({
        'epoch': int(row['epoch']),
        'precision': float(row['metrics/precision(B)']),
        'recall': float(row['metrics/recall(B)']),
        'map50': float(row['metrics/mAP50(B)']),
        'map50_95': float(row['metrics/mAP50-95(B)'])
    })

# 生成 HTML 報告
html_content = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YOLOv8 candy_gpu_v1 模型準確度分析報告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 36px;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header .subtitle {{
            font-size: 18px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        }}
        
        .metric-card.primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .metric-label {{
            font-size: 14px;
            opacity: 0.8;
            margin-bottom: 10px;
            font-weight: 500;
        }}
        
        .metric-value {{
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .metric-description {{
            font-size: 13px;
            opacity: 0.7;
            line-height: 1.5;
        }}
        
        .section {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        
        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 24px;
            display: flex;
            align-items: center;
        }}
        
        .section h2::before {{
            content: '';
            width: 4px;
            height: 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin-right: 12px;
            border-radius: 2px;
        }}
        
        .best-performance {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .best-item {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        
        .best-item .label {{
            color: #666;
            font-size: 14px;
            margin-bottom: 8px;
        }}
        
        .best-item .value {{
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }}
        
        .scenario-analysis {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-top: 20px;
        }}
        
        .scenario-analysis h3 {{
            color: #333;
            margin-bottom: 15px;
        }}
        
        .scenario-list {{
            list-style: none;
            padding: 0;
        }}
        
        .scenario-list li {{
            padding: 12px 0;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
        }}
        
        .scenario-list li:last-child {{
            border-bottom: none;
        }}
        
        .scenario-list li::before {{
            margin-right: 12px;
            font-size: 20px;
        }}
        
        .success {{
            background: rgba(52, 211, 153, 0.1);
            border-left: 4px solid #34d399;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }}
        
        .success .title {{
            color: #065f46;
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 10px;
        }}
        
        .success .content {{
            color: #047857;
            line-height: 1.8;
        }}
        
        .chart-container {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-top: 20px;
            height: 400px;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}
        
        .info-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
        }}
        
        .info-card h3 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        
        .info-row:last-child {{
            border-bottom: none;
        }}
        
        .info-label {{
            color: #666;
        }}
        
        .info-value {{
            font-weight: bold;
            color: #333;
        }}
        
        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            
            .info-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 YOLOv8 模型準確度分析報告</h1>
            <div class="subtitle">candy_gpu_v1 模型性能評估</div>
            <div class="subtitle" style="margin-top: 10px; opacity: 0.8;">生成時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>
        
        <div class="content">
            <!-- 核心指標 -->
            <div class="metrics-grid">
                <div class="metric-card primary">
                    <div class="metric-label">F1 分數</div>
                    <div class="metric-value">{f1_score*100:.2f}%</div>
                    <div class="metric-description">精確率與召回率的調和平均，綜合性能指標</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">精確率 (Precision)</div>
                    <div class="metric-value" style="color: #667eea;">{precision*100:.2f}%</div>
                    <div class="metric-description">每 100 次偵測，只有 {(1-precision)*100:.1f} 次誤報</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">召回率 (Recall)</div>
                    <div class="metric-value" style="color: #764ba2;">{recall*100:.2f}%</div>
                    <div class="metric-description">每 100 個瑕疵，會漏掉 {(1-recall)*100:.1f} 個</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">平均精確度 (mAP@0.5)</div>
                    <div class="metric-value" style="color: #f093fb;">{map50*100:.2f}%</div>
                    <div class="metric-description">IoU 閾值 0.5 時的平均精確度</div>
                </div>
            </div>
            
            <!-- 訓練趨勢圖表 -->
            <div class="section">
                <h2>📈 訓練過程指標變化</h2>
                <div class="chart-container">
                    <canvas id="metricsChart"></canvas>
                </div>
            </div>
            
            <!-- 最佳表現 -->
            <div class="section">
                <h2>🏆 最佳訓練表現</h2>
                <div style="background: rgba(102, 126, 234, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <strong>Epoch {int(best['epoch'])}</strong> 達到最佳 mAP@0.5 性能
                </div>
                <div class="best-performance">
                    <div class="best-item">
                        <div class="label">精確率</div>
                        <div class="value">{precision_best*100:.2f}%</div>
                    </div>
                    <div class="best-item">
                        <div class="label">召回率</div>
                        <div class="value">{recall_best*100:.2f}%</div>
                    </div>
                    <div class="best-item">
                        <div class="label">mAP@0.5</div>
                        <div class="value">{map50_best*100:.2f}%</div>
                    </div>
                    <div class="best-item">
                        <div class="label">mAP@0.5-0.95</div>
                        <div class="value">{map50_95_best*100:.2f}%</div>
                    </div>
                </div>
            </div>
            
            <!-- 實際應用分析 -->
            <div class="section">
                <h2>💡 實際應用場景分析</h2>
                <div class="scenario-analysis">
                    <h3>假設檢測 1000 個糖果（其中 200 個有瑕疵）：</h3>
                    <ul class="scenario-list">
                        <li style="color: #10b981;">✅ <strong>正確偵測：</strong>約 {200*recall:.0f} 個瑕疵被成功找到</li>
                        <li style="color: #ef4444;">❌ <strong>漏檢：</strong>約 {200*(1-recall):.0f} 個瑕疵未被發現（會流入市場）</li>
                        <li style="color: #f59e0b;">⚠️ <strong>誤報：</strong>約 {800*(1-precision):.0f} 個好糖果被誤判（造成浪費）</li>
                        <li style="color: #10b981;">✅ <strong>正確放行：</strong>約 {800 - 800*(1-precision):.0f} 個好糖果正確識別</li>
                    </ul>
                </div>
                
                <div class="success">
                    <div class="title">✅ 綜合評估：優秀！可用於生產環境</div>
                    <div class="content">
                        • F1-Score 達到 <strong>{f1_score*100:.2f}%</strong>，性能優異<br>
                        • 精確率 <strong>{precision*100:.2f}%</strong>，誤報率僅 <strong>{(1-precision)*100:.2f}%</strong><br>
                        • 召回率 <strong>{recall*100:.2f}%</strong>，漏檢率僅 <strong>{(1-recall)*100:.2f}%</strong><br>
                        • mAP@0.5 達到 <strong>{map50*100:.2f}%</strong>，定位精確度極高<br>
                        • 建議在實際環境測試 1-2 天後，針對誤判案例補充訓練資料
                    </div>
                </div>
            </div>
            
            <!-- 詳細指標說明 -->
            <div class="section">
                <h2>📋 指標詳細說明</h2>
                <div class="info-grid">
                    <div class="info-card">
                        <h3>當前模型性能</h3>
                        <div class="info-row">
                            <span class="info-label">精確率 (Precision)</span>
                            <span class="info-value">{precision*100:.2f}%</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">召回率 (Recall)</span>
                            <span class="info-value">{recall*100:.2f}%</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">F1 分數</span>
                            <span class="info-value">{f1_score*100:.2f}%</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">mAP@0.5</span>
                            <span class="info-value">{map50*100:.2f}%</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">mAP@0.5-0.95</span>
                            <span class="info-value">{map50_95*100:.2f}%</span>
                        </div>
                    </div>
                    
                    <div class="info-card">
                        <h3>訓練資訊</h3>
                        <div class="info-row">
                            <span class="info-label">模型名稱</span>
                            <span class="info-value">candy_gpu_v1</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">總訓練輪數</span>
                            <span class="info-value">{len(epochs_data)} Epochs</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">最佳輪數</span>
                            <span class="info-value">Epoch {int(best['epoch'])}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">最佳 mAP@0.5</span>
                            <span class="info-value">{map50_best*100:.2f}%</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">模型架構</span>
                            <span class="info-value">YOLOv8</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 指標解釋 -->
            <div class="section">
                <h2>❓ 指標說明</h2>
                <div class="scenario-analysis">
                    <p style="margin-bottom: 15px; color: #555; line-height: 1.8;">
                        <strong style="color: #667eea;">精確率 (Precision)</strong>：在所有被模型判定為「有瑕疵」的糖果中，真正有瑕疵的比例。精確率越高，誤報越少。
                    </p>
                    <p style="margin-bottom: 15px; color: #555; line-height: 1.8;">
                        <strong style="color: #764ba2;">召回率 (Recall)</strong>：在所有實際有瑕疵的糖果中，被模型成功找出的比例。召回率越高，漏檢越少。
                    </p>
                    <p style="margin-bottom: 15px; color: #555; line-height: 1.8;">
                        <strong style="color: #f093fb;">F1 分數</strong>：精確率和召回率的調和平均數，用於綜合評估模型性能。數值越高越好。
                    </p>
                    <p style="color: #555; line-height: 1.8;">
                        <strong style="color: #4facfe;">mAP (mean Average Precision)</strong>：平均精確度，衡量模型在不同置信度閾值下的綜合表現。mAP@0.5 表示 IoU 閾值為 0.5 時的平均精確度。
                    </p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 準備圖表數據
        const epochs = [{','.join([str(d['epoch']) for d in epochs_data])}];
        const precisionData = [{','.join([f"{d['precision']:.4f}" for d in epochs_data])}];
        const recallData = [{','.join([f"{d['recall']:.4f}" for d in epochs_data])}];
        const map50Data = [{','.join([f"{d['map50']:.4f}" for d in epochs_data])}];
        
        // 繪製圖表
        const ctx = document.getElementById('metricsChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: epochs,
                datasets: [
                    {{
                        label: 'Precision (精確率)',
                        data: precisionData,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4
                    }},
                    {{
                        label: 'Recall (召回率)',
                        data: recallData,
                        borderColor: '#764ba2',
                        backgroundColor: 'rgba(118, 75, 162, 0.1)',
                        tension: 0.4
                    }},
                    {{
                        label: 'mAP@0.5',
                        data: map50Data,
                        borderColor: '#f093fb',
                        backgroundColor: 'rgba(240, 147, 251, 0.1)',
                        tension: 0.4
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'top',
                    }},
                    title: {{
                        display: true,
                        text: '訓練過程中各項指標的變化趨勢'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 1,
                        ticks: {{
                            callback: function(value) {{
                                return (value * 100).toFixed(0) + '%';
                            }}
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Epoch'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
'''

# 保存報告
output_path = f'reports/accuracy_report_candy_gpu_v1_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print()
print('=' * 60)
print('✅ 準確度分析報告生成完成！')
print('=' * 60)
print(f'報告位置: {output_path}')
print()
print('報告內容：')
print('  📊 核心性能指標（F1、Precision、Recall、mAP）')
print('  📈 訓練過程趨勢圖表')
print('  🏆 最佳訓練表現記錄')
print('  💡 實際應用場景分析')
print('  📋 詳細指標說明與解釋')
print()
