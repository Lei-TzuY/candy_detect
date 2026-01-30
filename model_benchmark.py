"""
糖果瑕疵偵測系統 - 模型效能評估與比較
評估所有 YOLO 模型並生成可視化報告
"""
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import time

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 模型配置
MODELS = {
    'YOLOv11n': 'datasets/最新資料集/yolo11n.pt',
    'YOLOv11s': 'datasets/最新資料集/yolo11s.pt',
    'YOLOv11m': 'datasets/最新資料集/yolo11m.pt',
    'YOLOv8n': 'datasets/最新資料集/yolov8n.pt',
    'YOLOv8s': 'datasets/最新資料集/yolov8s.pt',
    'YOLOv8m': 'datasets/最新資料集/yolov8m.pt',
}

# 測試配置
TEST_CONFIG = {
    'data': 'D:/專案/candy/datasets/最新資料集/data.yaml',  # 使用正確的資料集
    'imgsz': 640,
    'batch': 16,
    'device': 0,  # 0 = GPU, 'cpu' = CPU
    'conf': 0.6,  # 信心度閾值
    'iou': 0.45,  # NMS IoU 閾值
}

class ModelBenchmark:
    """模型評估類別"""
    
    def __init__(self, output_dir='reports/model_benchmark'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.results = []
        
    def benchmark_single_model(self, model_name, model_path):
        """評估單一模型"""
        print(f"\n{'='*60}")
        print(f"📊 評估模型: {model_name}")
        print(f"{'='*60}")
        
        try:
            from ultralytics import YOLO
            
            # 載入模型
            print(f"載入模型: {model_path}")
            model = YOLO(model_path)
            
            # 執行驗證
            print("執行驗證測試...")
            start_time = time.time()
            
            val_results = model.val(
                data=TEST_CONFIG['data'],
                imgsz=TEST_CONFIG['imgsz'],
                batch=TEST_CONFIG['batch'],
                device=TEST_CONFIG['device'],
                conf=TEST_CONFIG['conf'],
                iou=TEST_CONFIG['iou'],
                plots=False,
                verbose=False
            )
            
            inference_time = time.time() - start_time
            
            # 獲取模型資訊
            model_info = model.info(verbose=False)
            
            # 提取指標
            result = {
                'Model': model_name,
                'mAP50': float(val_results.box.map50),
                'mAP50-95': float(val_results.box.map),
                'Precision': float(val_results.box.mp),
                'Recall': float(val_results.box.mr),
                'F1-Score': float(2 * val_results.box.mp * val_results.box.mr / (val_results.box.mp + val_results.box.mr + 1e-6)),
                'Inference Speed (ms)': float(val_results.speed['inference']),
                'Parameters (M)': model_info[1] / 1e6 if isinstance(model_info, tuple) else 0,
                'FLOPs (G)': model_info[2] / 1e9 if isinstance(model_info, tuple) and len(model_info) > 2 else 0,
                'Model Size (MB)': Path(model_path).stat().st_size / (1024 * 1024),
                'Total Time (s)': inference_time
            }
            
            # 顯示結果
            print(f"✅ 完成評估")
            print(f"  mAP50: {result['mAP50']:.3f}")
            print(f"  mAP50-95: {result['mAP50-95']:.3f}")
            print(f"  Precision: {result['Precision']:.3f}")
            print(f"  Recall: {result['Recall']:.3f}")
            print(f"  F1-Score: {result['F1-Score']:.3f}")
            print(f"  速度: {result['Inference Speed (ms)']:.2f} ms")
            print(f"  參數量: {result['Parameters (M)']:.2f} M")
            
            self.results.append(result)
            return result
            
        except Exception as e:
            print(f"❌ 評估失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_all_benchmarks(self):
        """執行所有模型的評估"""
        print("\n" + "="*60)
        print("🚀 開始模型評估 - 糖果瑕疵偵測系統")
        print("="*60)
        
        for model_name, model_path in MODELS.items():
            if not Path(model_path).exists():
                print(f"⚠️  跳過 {model_name}: 找不到檔案 {model_path}")
                continue
            
            self.benchmark_single_model(model_name, model_path)
        
        if not self.results:
            print("\n❌ 沒有成功評估任何模型")
            return None
        
        # 轉換為 DataFrame
        df = pd.DataFrame(self.results)
        df = df.sort_values('mAP50-95', ascending=False)
        
        return df
    
    def generate_visualizations(self, df):
        """生成可視化圖表"""
        print("\n📊 生成可視化圖表...")
        
        # 設定樣式
        sns.set_style("whitegrid")
        sns.set_palette("husl")
        
        # 1. 準確度比較 (mAP)
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('YOLO 模型效能比較 - 糖果瑕疵偵測', fontsize=16, fontweight='bold')
        
        # 1.1 mAP50 vs mAP50-95
        ax1 = axes[0, 0]
        x = range(len(df))
        width = 0.35
        ax1.bar([i - width/2 for i in x], df['mAP50'], width, label='mAP50', alpha=0.8)
        ax1.bar([i + width/2 for i in x], df['mAP50-95'], width, label='mAP50-95', alpha=0.8)
        ax1.set_xlabel('模型', fontsize=12)
        ax1.set_ylabel('mAP 分數', fontsize=12)
        ax1.set_title('準確度比較 (mAP)', fontsize=14, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(df['Model'], rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 1.2 Precision vs Recall
        ax2 = axes[0, 1]
        x = range(len(df))
        ax2.bar([i - width/2 for i in x], df['Precision'], width, label='Precision', alpha=0.8, color='green')
        ax2.bar([i + width/2 for i in x], df['Recall'], width, label='Recall', alpha=0.8, color='orange')
        ax2.set_xlabel('模型', fontsize=12)
        ax2.set_ylabel('分數', fontsize=12)
        ax2.set_title('Precision vs Recall', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(df['Model'], rotation=45, ha='right')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 1.3 推論速度
        ax3 = axes[1, 0]
        bars = ax3.barh(df['Model'], df['Inference Speed (ms)'], alpha=0.8, color='skyblue')
        ax3.set_xlabel('推論時間 (ms)', fontsize=12)
        ax3.set_ylabel('模型', fontsize=12)
        ax3.set_title('推論速度比較 (越低越好)', fontsize=14, fontweight='bold')
        ax3.invert_yaxis()
        # 在條形上顯示數值
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax3.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{width:.2f}ms', ha='left', va='center', fontsize=10)
        ax3.grid(True, alpha=0.3, axis='x')
        
        # 1.4 模型大小 vs 準確度
        ax4 = axes[1, 1]
        scatter = ax4.scatter(df['Parameters (M)'], df['mAP50-95'], 
                             s=df['Model Size (MB)']*10, alpha=0.6, c=range(len(df)), cmap='viridis')
        for idx, row in df.iterrows():
            ax4.annotate(row['Model'], (row['Parameters (M)'], row['mAP50-95']),
                        xytext=(5, 5), textcoords='offset points', fontsize=9)
        ax4.set_xlabel('參數量 (M)', fontsize=12)
        ax4.set_ylabel('mAP50-95', fontsize=12)
        ax4.set_title('模型複雜度 vs 準確度', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 儲存圖表
        chart_path = self.output_dir / f'model_comparison_{self.timestamp}.png'
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        print(f"✅ 圖表已儲存: {chart_path}")
        plt.close()
        
        # 2. 綜合效能雷達圖
        self._generate_radar_chart(df)
        
        # 3. F1-Score 排名
        self._generate_f1_ranking(df)
        
        return chart_path
    
    def _generate_radar_chart(self, df):
        """生成雷達圖"""
        from math import pi
        
        # 選擇要顯示的指標（標準化到 0-1）
        metrics = ['mAP50-95', 'Precision', 'Recall', 'F1-Score']
        
        # 計算速度分數 (越快分數越高)
        max_speed = df['Inference Speed (ms)'].max()
        df['Speed Score'] = 1 - (df['Inference Speed (ms)'] / max_speed)
        metrics.append('Speed Score')
        
        fig = plt.figure(figsize=(14, 10))
        
        # 為每個模型創建一個子圖
        n_models = len(df)
        n_cols = 3
        n_rows = (n_models + n_cols - 1) // n_cols
        
        for idx, (_, row) in enumerate(df.iterrows()):
            ax = fig.add_subplot(n_rows, n_cols, idx + 1, projection='polar')
            
            values = [row[m] for m in metrics]
            values += values[:1]  # 閉合圖形
            
            angles = [n / float(len(metrics)) * 2 * pi for n in range(len(metrics))]
            angles += angles[:1]
            
            ax.plot(angles, values, 'o-', linewidth=2, label=row['Model'])
            ax.fill(angles, values, alpha=0.25)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(metrics, fontsize=8)
            ax.set_ylim(0, 1)
            ax.set_title(row['Model'], fontsize=12, fontweight='bold', pad=20)
            ax.grid(True)
        
        plt.suptitle('模型效能雷達圖', fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        radar_path = self.output_dir / f'radar_chart_{self.timestamp}.png'
        plt.savefig(radar_path, dpi=300, bbox_inches='tight')
        print(f"✅ 雷達圖已儲存: {radar_path}")
        plt.close()
    
    def _generate_f1_ranking(self, df):
        """生成 F1-Score 排名圖"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 排序
        df_sorted = df.sort_values('F1-Score', ascending=True)
        
        # 繪製水平條形圖
        colors = plt.cm.RdYlGn(df_sorted['F1-Score'])
        bars = ax.barh(df_sorted['Model'], df_sorted['F1-Score'], color=colors, alpha=0.8)
        
        # 添加數值標籤
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{width:.3f}', ha='left', va='center', fontsize=11, fontweight='bold')
        
        ax.set_xlabel('F1-Score', fontsize=12, fontweight='bold')
        ax.set_ylabel('模型', fontsize=12, fontweight='bold')
        ax.set_title('模型 F1-Score 排名', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 1.0)
        ax.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        
        f1_path = self.output_dir / f'f1_ranking_{self.timestamp}.png'
        plt.savefig(f1_path, dpi=300, bbox_inches='tight')
        print(f"✅ F1-Score 排名已儲存: {f1_path}")
        plt.close()
    
    def generate_html_report(self, df):
        """生成 HTML 報告"""
        print("\n📄 生成 HTML 報告...")
        
        # 找出最佳模型
        best_map = df.loc[df['mAP50-95'].idxmax()]
        best_speed = df.loc[df['Inference Speed (ms)'].idxmin()]
        best_f1 = df.loc[df['F1-Score'].idxmax()]
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>模型效能評估報告 - 糖果瑕疵偵測系統</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft JhengHei', 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        .content {{
            padding: 40px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .summary-card h3 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        .summary-card .model-name {{
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
            margin: 10px 0;
        }}
        .summary-card .metric {{
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            padding: 8px;
            background: white;
            border-radius: 5px;
        }}
        .metric-label {{
            color: #666;
        }}
        .metric-value {{
            font-weight: bold;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
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
            border-bottom: 1px solid #f0f0f0;
        }}
        tr:hover {{
            background-color: #f5f7fa;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .best-badge {{
            display: inline-block;
            background: #4CAF50;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            margin-left: 10px;
        }}
        .images {{
            margin: 40px 0;
        }}
        .images img {{
            width: 100%;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin: 20px 0;
        }}
        .section-title {{
            font-size: 2em;
            color: #333;
            margin: 40px 0 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .recommendation {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 20px;
            margin: 30px 0;
            border-radius: 5px;
        }}
        .recommendation h3 {{
            color: #856404;
            margin-bottom: 15px;
        }}
        .recommendation ul {{
            margin-left: 20px;
        }}
        .recommendation li {{
            margin: 8px 0;
            color: #856404;
        }}
        .footer {{
            background: #f5f7fa;
            padding: 20px;
            text-align: center;
            color: #666;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍬 模型效能評估報告</h1>
            <p>糖果瑕疵偵測系統 - YOLO 模型比較分析</p>
            <p style="font-size: 0.9em; margin-top: 10px;">生成時間: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="content">
            <h2 class="section-title">📊 最佳模型摘要</h2>
            <div class="summary">
                <div class="summary-card">
                    <h3>🏆 最高準確度</h3>
                    <div class="model-name">{best_map['Model']}</div>
                    <div class="metric">
                        <span class="metric-label">mAP50-95:</span>
                        <span class="metric-value">{best_map['mAP50-95']:.3f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">mAP50:</span>
                        <span class="metric-value">{best_map['mAP50']:.3f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Precision:</span>
                        <span class="metric-value">{best_map['Precision']:.3f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Recall:</span>
                        <span class="metric-value">{best_map['Recall']:.3f}</span>
                    </div>
                </div>
                
                <div class="summary-card">
                    <h3>⚡ 最快速度</h3>
                    <div class="model-name">{best_speed['Model']}</div>
                    <div class="metric">
                        <span class="metric-label">推論時間:</span>
                        <span class="metric-value">{best_speed['Inference Speed (ms)']:.2f} ms</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">mAP50-95:</span>
                        <span class="metric-value">{best_speed['mAP50-95']:.3f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">參數量:</span>
                        <span class="metric-value">{best_speed['Parameters (M)']:.2f} M</span>
                    </div>
                </div>
                
                <div class="summary-card">
                    <h3>⚖️ 最佳平衡 (F1-Score)</h3>
                    <div class="model-name">{best_f1['Model']}</div>
                    <div class="metric">
                        <span class="metric-label">F1-Score:</span>
                        <span class="metric-value">{best_f1['F1-Score']:.3f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">推論時間:</span>
                        <span class="metric-value">{best_f1['Inference Speed (ms)']:.2f} ms</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">mAP50-95:</span>
                        <span class="metric-value">{best_f1['mAP50-95']:.3f}</span>
                    </div>
                </div>
            </div>
            
            <h2 class="section-title">📈 詳細效能比較</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>模型</th>
                        <th>mAP50-95</th>
                        <th>mAP50</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1-Score</th>
                        <th>速度 (ms)</th>
                        <th>參數量 (M)</th>
                        <th>大小 (MB)</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # 添加表格行
        for rank, (_, row) in enumerate(df.iterrows(), 1):
            best_tags = []
            if row['Model'] == best_map['Model']:
                best_tags.append('<span class="best-badge">最高準確度</span>')
            if row['Model'] == best_speed['Model']:
                best_tags.append('<span class="best-badge">最快速度</span>')
            if row['Model'] == best_f1['Model']:
                best_tags.append('<span class="best-badge">最佳平衡</span>')
            
            html_content += f"""
                    <tr>
                        <td>{rank}</td>
                        <td><strong>{row['Model']}</strong>{''.join(best_tags)}</td>
                        <td>{row['mAP50-95']:.3f}</td>
                        <td>{row['mAP50']:.3f}</td>
                        <td>{row['Precision']:.3f}</td>
                        <td>{row['Recall']:.3f}</td>
                        <td>{row['F1-Score']:.3f}</td>
                        <td>{row['Inference Speed (ms)']:.2f}</td>
                        <td>{row['Parameters (M)']:.2f}</td>
                        <td>{row['Model Size (MB)']:.2f}</td>
                    </tr>
"""
        
        html_content += f"""
                </tbody>
            </table>
            
            <div class="recommendation">
                <h3>💡 選型建議</h3>
                <ul>
                    <li><strong>高準確度需求:</strong> 推薦使用 <strong>{best_map['Model']}</strong>，具有最高的 mAP50-95 ({best_map['mAP50-95']:.3f})，適合品質要求嚴格的場景</li>
                    <li><strong>高速度需求:</strong> 推薦使用 <strong>{best_speed['Model']}</strong>，推論時間僅 {best_speed['Inference Speed (ms)']:.2f} ms，適合高速生產線</li>
                    <li><strong>平衡型需求:</strong> 推薦使用 <strong>{best_f1['Model']}</strong>，F1-Score 最高 ({best_f1['F1-Score']:.3f})，準確度和速度兼顧</li>
                    <li><strong>資源受限環境:</strong> YOLOv8n/YOLOv11n 系列模型參數量少、速度快，適合邊緣設備部署</li>
                </ul>
            </div>
            
            <h2 class="section-title">📊 可視化圖表</h2>
            <div class="images">
                <img src="model_comparison_{self.timestamp}.png" alt="模型比較圖表">
                <img src="radar_chart_{self.timestamp}.png" alt="雷達圖">
                <img src="f1_ranking_{self.timestamp}.png" alt="F1-Score排名">
            </div>
            
            <h2 class="section-title">📝 評估說明</h2>
            <div style="background: #f5f7fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h4>指標說明:</h4>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li><strong>mAP50-95:</strong> 在 IoU 閾值 0.5-0.95 範圍內的平均精度，綜合評估模型準確度</li>
                    <li><strong>mAP50:</strong> IoU 閾值為 0.5 時的平均精度，較為寬鬆的準確度指標</li>
                    <li><strong>Precision (精確率):</strong> 預測為陽性的樣本中實際為陽性的比例</li>
                    <li><strong>Recall (召回率):</strong> 實際為陽性的樣本中被正確預測為陽性的比例</li>
                    <li><strong>F1-Score:</strong> Precision 和 Recall 的調和平均數，綜合評估模型性能</li>
                    <li><strong>推論速度:</strong> 單張影像的處理時間，越低越好</li>
                </ul>
                
                <h4 style="margin-top: 20px;">測試配置:</h4>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li>資料集: {TEST_CONFIG['data']}</li>
                    <li>影像大小: {TEST_CONFIG['imgsz']}×{TEST_CONFIG['imgsz']}</li>
                    <li>批次大小: {TEST_CONFIG['batch']}</li>
                    <li>裝置: {'GPU' if TEST_CONFIG['device'] == 0 else 'CPU'}</li>
                    <li>信心度閾值: {TEST_CONFIG['conf']}</li>
                    <li>NMS IoU 閾值: {TEST_CONFIG['iou']}</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2026 糖果瑕疵偵測系統 | 模型效能評估報告</p>
            <p style="margin-top: 5px; font-size: 0.9em;">報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        
        # 儲存 HTML
        html_path = self.output_dir / f'benchmark_report_{self.timestamp}.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML 報告已儲存: {html_path}")
        return html_path
    
    def save_results(self, df):
        """儲存結果到 CSV 和 JSON"""
        # CSV
        csv_path = self.output_dir / f'benchmark_results_{self.timestamp}.csv'
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✅ CSV 結果已儲存: {csv_path}")
        
        # JSON
        json_path = self.output_dir / f'benchmark_results_{self.timestamp}.json'
        results_dict = {
            'timestamp': self.timestamp,
            'test_config': TEST_CONFIG,
            'results': df.to_dict('records'),
            'summary': {
                'best_accuracy': df.loc[df['mAP50-95'].idxmax()].to_dict(),
                'best_speed': df.loc[df['Inference Speed (ms)'].idxmin()].to_dict(),
                'best_f1': df.loc[df['F1-Score'].idxmax()].to_dict(),
            }
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON 結果已儲存: {json_path}")
        
        return csv_path, json_path


def main():
    """主程式"""
    print("\n" + "="*60)
    print("🍬 糖果瑕疵偵測系統 - 模型效能評估")
    print("="*60 + "\n")
    
    # 檢查資料集配置檔案
    data_yaml = Path(TEST_CONFIG['data'])
    if not data_yaml.exists():
        print(f"❌ 找不到資料集配置檔案: {data_yaml}")
        print("請修改 TEST_CONFIG['data'] 指向正確的 .yaml 檔案")
        return
    
    # 創建評估器
    benchmark = ModelBenchmark()
    
    # 執行評估
    df = benchmark.run_all_benchmarks()
    
    if df is None or len(df) == 0:
        print("\n❌ 評估失敗或無可用模型")
        return
    
    # 生成可視化
    benchmark.generate_visualizations(df)
    
    # 生成 HTML 報告
    html_path = benchmark.generate_html_report(df)
    
    # 儲存結果
    benchmark.save_results(df)
    
    # 顯示摘要
    print("\n" + "="*60)
    print("📊 評估完成！摘要:")
    print("="*60)
    print(f"\n最佳準確度: {df.loc[df['mAP50-95'].idxmax()]['Model']} (mAP50-95: {df['mAP50-95'].max():.3f})")
    print(f"最快速度: {df.loc[df['Inference Speed (ms)'].idxmin()]['Model']} ({df['Inference Speed (ms)'].min():.2f} ms)")
    print(f"最佳平衡: {df.loc[df['F1-Score'].idxmax()]['Model']} (F1: {df['F1-Score'].max():.3f})")
    
    print(f"\n📄 完整報告: {html_path}")
    print(f"📊 圖表位置: {benchmark.output_dir}")
    
    # 自動開啟 HTML 報告
    try:
        import webbrowser
        webbrowser.open(html_path.as_uri())
        print("\n✅ 已在瀏覽器中開啟報告")
    except:
        print("\n⚠️  請手動開啟 HTML 報告")


if __name__ == '__main__':
    main()
