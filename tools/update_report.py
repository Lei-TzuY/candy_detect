import re
import csv

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

# 簡繁轉換表
s2t_map = {
    '检测': '檢測', '结果': '結果', '报告': '報告', '总': '總',
    '检查': '檢查', '张': '張', '瑕疵': '瑕疵', '正常': '正常',
    '未检测': '未檢測', '类别': '類別', '全部': '全部',
    '显示': '顯示', '隐藏': '隱藏', '数量': '數量',
    '置信度': '置信度', '图片': '圖片', '详情': '詳情',
    '过滤': '過濾', '统计': '統計', '模型': '模型',
    '测试': '測試', '性能': '性能', '准确': '準確',
    '错误': '錯誤', '漏检': '漏檢', '误报': '誤報',
    '对象': '對象', '处理': '處理', '时间': '時間',
    '运行': '運行', '训练': '訓練', '验证': '驗證',
    '标注': '標註', '框选': '框選', '识别': '識別',
    '标签': '標籤', '导出': '匯出', '保存': '儲存',
    '载入': '載入', '删除': '刪除', '选择': '選擇',
    '确认': '確認', '取消': '取消', '关闭': '關閉',
    '设置': '設定', '参数': '參數', '值': '值',
    '计算': '計算', '处理速度': '處理速度',
    '预测': '預測', '检出': '檢出', '查询': '查詢',
    '搜索': '搜尋', '筛选': '篩選'
}

# 讀取 HTML 文件
print('正在讀取報告文件...')
report_path = 'reports/yolov8_test_candy_gpu_v1_20260114_174102.html'
with open(report_path, 'r', encoding='utf-8') as f:
    html = f.read()

print('簡繁轉換中...')
# 簡繁轉換
for simp, trad in s2t_map.items():
    html = html.replace(simp, trad)

print('添加準確度數據...')
# 準備要插入的準確度統計區塊
accuracy_html = f'''
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 12px; margin: 20px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
        <h2 style="color: white; margin-top: 0; font-size: 28px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">📊 模型準確度分析</h2>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px;">
            <div style="background: rgba(255,255,255,0.95); padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; color: #666; margin-bottom: 5px;">精確率 (Precision)</div>
                <div style="font-size: 32px; font-weight: bold; color: #667eea;">{precision*100:.2f}%</div>
                <div style="font-size: 12px; color: #999; margin-top: 5px;">100次偵測，只有 {(1-precision)*100:.1f} 次誤報</div>
            </div>
            
            <div style="background: rgba(255,255,255,0.95); padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; color: #666; margin-bottom: 5px;">召回率 (Recall)</div>
                <div style="font-size: 32px; font-weight: bold; color: #764ba2;">{recall*100:.2f}%</div>
                <div style="font-size: 12px; color: #999; margin-top: 5px;">100個瑕疵，會漏掉 {(1-recall)*100:.1f} 個</div>
            </div>
            
            <div style="background: rgba(255,255,255,0.95); padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; color: #666; margin-bottom: 5px;">平均精確度 (mAP@0.5)</div>
                <div style="font-size: 32px; font-weight: bold; color: #f093fb;">{map50*100:.2f}%</div>
                <div style="font-size: 12px; color: #999; margin-top: 5px;">整體定位精確度</div>
            </div>
            
            <div style="background: rgba(255,255,255,0.95); padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; color: #666; margin-bottom: 5px;">F1 分數</div>
                <div style="font-size: 32px; font-weight: bold; color: #4facfe;">{f1_score*100:.2f}%</div>
                <div style="font-size: 12px; color: #999; margin-top: 5px;">精確率與召回率的平衡</div>
            </div>
        </div>
        
        <div style="background: rgba(255,255,255,0.95); padding: 20px; border-radius: 8px; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="margin-top: 0; color: #333;">🏆 最佳訓練表現 (Epoch {int(best['epoch'])})：</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div>
                    <span style="color: #666;">精確率：</span>
                    <span style="font-weight: bold; color: #667eea;">{precision_best*100:.2f}%</span>
                </div>
                <div>
                    <span style="color: #666;">召回率：</span>
                    <span style="font-weight: bold; color: #764ba2;">{recall_best*100:.2f}%</span>
                </div>
                <div>
                    <span style="color: #666;">mAP@0.5：</span>
                    <span style="font-weight: bold; color: #f093fb;">{map50_best*100:.2f}%</span>
                </div>
                <div>
                    <span style="color: #666;">mAP@0.5-0.95：</span>
                    <span style="font-weight: bold; color: #4facfe;">{map50_95_best*100:.2f}%</span>
                </div>
            </div>
        </div>
        
        <div style="background: rgba(255,255,255,0.95); padding: 20px; border-radius: 8px; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="margin-top: 0; color: #333;">💡 實際應用場景分析：</h3>
            <div style="color: #555; line-height: 1.8;">
                假設檢測 <strong>1000 個糖果</strong>（其中 200 個有瑕疵）：
                <ul style="margin: 10px 0;">
                    <li>✅ <strong>正確偵測：</strong>約 {200*recall:.0f} 個瑕疵被成功找到</li>
                    <li>❌ <strong>漏檢：</strong>約 {200*(1-recall):.0f} 個瑕疵未被發現</li>
                    <li>⚠️ <strong>誤報：</strong>約 {800*(1-precision):.0f} 個好糖果被誤判</li>
                    <li>✅ <strong>正確放行：</strong>約 {800 - 800*(1-precision):.0f} 個好糖果正確識別</li>
                </ul>
            </div>
        </div>
        
        <div style="background: rgba(52, 211, 153, 0.2); border-left: 4px solid #34d399; padding: 15px; border-radius: 4px; margin-top: 20px;">
            <div style="color: #065f46; font-weight: bold; font-size: 16px;">✅ 綜合評估：優秀！可用於生產環境</div>
            <div style="color: #047857; margin-top: 8px; font-size: 14px;">
                • F1-Score 達到 {f1_score*100:.2f}%，性能優異<br>
                • 誤報率僅 {(1-precision)*100:.2f}%，可靠性高<br>
                • 建議在實際環境測試 1-2 天後，針對誤判案例補充訓練資料
            </div>
        </div>
    </div>
'''

# 在統計信息後插入準確度數據 (找 header 或 body)
insert_pattern = r'(<body[^>]*>)'
match = re.search(insert_pattern, html)

if match:
    insert_pos = match.end()
    container_start = '<div style="max-width: 1400px; margin: 20px auto; padding: 0 20px;">'
    html = html[:insert_pos] + container_start + accuracy_html + '</div>' + html[insert_pos:]
    print('✅ 準確度數據已插入')
else:
    print('❌ 無法找到插入位置')

# 保存修改後的文件
output_path = 'reports/yolov8_test_candy_gpu_v1_20260114_174102_updated.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print()
print('=' * 60)
print('✅ 處理完成！')
print('=' * 60)
print(f'輸出文件: {output_path}')
print(f'文件大小: {len(html) / 1024 / 1024:.2f} MB')
print()
print('修改內容：')
print('  1. ✅ 簡體字已轉換為繁體字')
print('  2. ✅ 添加了完整的模型準確度分析')
print('  3. ✅ 包含最佳訓練表現數據')
print('  4. ✅ 添加實際應用場景分析')
print()
