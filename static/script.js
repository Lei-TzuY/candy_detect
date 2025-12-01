// 全域變數
let defectRateChart = null;
let productPieChart = null;
let updateInterval = null;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
    startAutoUpdate();
});

// 初始化頁面
function initializePage() {
    loadCameras();
    loadStats();
    loadHistory();
    loadConfig();
    initializeCharts();
}

// 分頁切換
function showTab(tabName) {
    // 隱藏所有分頁
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // 移除所有按鈕的 active 狀態
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 顯示選中的分頁
    document.getElementById(tabName).classList.add('active');

    // 設置按鈕為 active
    event.target.classList.add('active');

    // 根據分頁載入對應數據
    if (tabName === 'history') {
        loadHistory();
    } else if (tabName === 'settings') {
        loadConfig();
    }
}

// 載入攝影機列表
async function loadCameras() {
    try {
        const response = await fetch('/api/cameras');
        const cameras = await response.json();

        // 產生攝影機畫面
        const videoContainer = document.getElementById('videoContainer');
        videoContainer.innerHTML = '';

        cameras.forEach(camera => {
            const videoCard = document.createElement('div');
            videoCard.className = 'video-card';
            videoCard.innerHTML = `
                <h3>${camera.name}</h3>
                <img src="/video_feed/${camera.index}" alt="${camera.name}">
            `;
            videoContainer.appendChild(videoCard);
        });

        // 更新歷史記錄的攝影機選單
        const cameraSelect = document.getElementById('historyCamera');
        cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera.name;
            option.textContent = camera.name;
            cameraSelect.appendChild(option);
        });

    } catch (error) {
        console.error('載入攝影機失敗:', error);
    }
}

// 載入即時統計
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        const statsContainer = document.getElementById('statsContainer');
        statsContainer.innerHTML = '';

        stats.forEach(stat => {
            const statCard = document.createElement('div');
            statCard.className = 'stat-card';
            statCard.innerHTML = `
                <h3>${stat.name}</h3>
                <div class="stat-value">${stat.total}</div>
                <div class="stat-label">總偵測數</div>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-item-label">正常品</div>
                        <div class="stat-item-value normal">${stat.normal}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-item-label">瑕疵品</div>
                        <div class="stat-item-value abnormal">${stat.abnormal}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-item-label">瑕疵率</div>
                        <div class="stat-item-value rate">${stat.defect_rate}%</div>
                    </div>
                </div>
            `;
            statsContainer.appendChild(statCard);
        });

        // 更新圖表
        updateCharts(stats);

    } catch (error) {
        console.error('載入統計資料失敗:', error);
    }
}

// 初始化圖表
function initializeCharts() {
    // 瑕疵率趨勢圖
    const ctx1 = document.getElementById('defectRateChart').getContext('2d');
    defectRateChart = new Chart(ctx1, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '瑕疵率 (%)',
                data: [],
                borderColor: '#f44336',
                backgroundColor: 'rgba(244, 67, 54, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });

    // 產品分布圓餅圖
    const ctx2 = document.getElementById('productPieChart').getContext('2d');
    productPieChart = new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels: ['正常品', '瑕疵品'],
            datasets: [{
                data: [0, 0],
                backgroundColor: ['#4caf50', '#f44336']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// 更新圖表
function updateCharts(stats) {
    if (!stats || stats.length === 0) return;

    // 計算總計
    let totalNormal = 0;
    let totalAbnormal = 0;

    stats.forEach(stat => {
        totalNormal += stat.normal;
        totalAbnormal += stat.abnormal;
    });

    // 更新圓餅圖
    if (productPieChart) {
        productPieChart.data.datasets[0].data = [totalNormal, totalAbnormal];
        productPieChart.update();
    }

    // 更新瑕疵率趨勢圖（使用歷史資料）
    loadDefectRateTrend();
}

// 載入瑕疵率趨勢
async function loadDefectRateTrend() {
    try {
        const response = await fetch('/api/history?hours=1');
        const history = await response.json();

        if (!history || history.length === 0) return;

        // 反轉陣列以時間順序排列
        history.reverse();

        const labels = history.map(record => {
            const date = new Date(record.timestamp);
            return date.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });
        });

        const data = history.map(record => record.defect_rate);

        if (defectRateChart) {
            defectRateChart.data.labels = labels;
            defectRateChart.data.datasets[0].data = data;
            defectRateChart.update();
        }
    } catch (error) {
        console.error('載入趨勢圖失敗:', error);
    }
}

// 載入歷史記錄
async function loadHistory() {
    try {
        const hours = document.getElementById('historyHours').value;
        const camera = document.getElementById('historyCamera').value;

        const url = `/api/history?hours=${hours}${camera ? '&camera=' + camera : ''}`;
        const response = await fetch(url);
        const history = await response.json();

        const tbody = document.getElementById('historyTableBody');
        tbody.innerHTML = '';

        history.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date(record.timestamp).toLocaleString('zh-TW')}</td>
                <td>${record.camera}</td>
                <td>${record.total}</td>
                <td>${record.normal}</td>
                <td>${record.abnormal}</td>
                <td>${record.defect_rate}%</td>
            `;
            tbody.appendChild(row);
        });

    } catch (error) {
        console.error('載入歷史記錄失敗:', error);
    }
}

// 匯出 CSV
function exportHistory() {
    const table = document.getElementById('historyTable');
    let csv = [];

    // 標題行
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent);
    csv.push(headers.join(','));

    // 數據行
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const cols = Array.from(row.querySelectorAll('td')).map(td => td.textContent);
        csv.push(cols.join(','));
    });

    // 下載
    const csvContent = '\uFEFF' + csv.join('\n'); // UTF-8 BOM
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `detection_history_${Date.now()}.csv`;
    link.click();
}

// 載入設定
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();

        // 載入偵測參數
        if (config.Detection) {
            document.getElementById('confThreshold').value = config.Detection.confidence_threshold || 0.2;
            document.getElementById('nmsThreshold').value = config.Detection.nms_threshold || 0.4;
        }

        // 顯示攝影機設定
        const cameraSettings = document.getElementById('cameraSettings');
        cameraSettings.innerHTML = '';

        Object.keys(config).forEach(section => {
            if (section.startsWith('Camera')) {
                const settingsDiv = document.createElement('div');
                settingsDiv.className = 'settings-group';
                settingsDiv.innerHTML = `
                    <h3>${config[section].camera_name || section}</h3>
                    <label>
                        攝影機索引：
                        <input type="number" data-section="${section}" data-key="camera_index" value="${config[section].camera_index || 0}">
                    </label>
                    <label>
                        繼電器延遲 (ms)：
                        <input type="number" data-section="${section}" data-key="relay_delay_ms" value="${config[section].relay_delay_ms || 0}">
                    </label>
                    <label>
                        偵測線 X1：
                        <input type="number" data-section="${section}" data-key="detection_line_x1" value="${config[section].detection_line_x1 || 500}">
                    </label>
                    <label>
                        偵測線 X2：
                        <input type="number" data-section="${section}" data-key="detection_line_x2" value="${config[section].detection_line_x2 || 1100}">
                    </label>
                `;
                cameraSettings.appendChild(settingsDiv);
            }
        });

    } catch (error) {
        console.error('載入設定失敗:', error);
    }
}

// 儲存設定
async function saveSettings() {
    try {
        const newConfig = {
            Detection: {
                confidence_threshold: document.getElementById('confThreshold').value,
                nms_threshold: document.getElementById('nmsThreshold').value,
                input_size: 416
            }
        };

        // 收集攝影機設定
        document.querySelectorAll('#cameraSettings input').forEach(input => {
            const section = input.dataset.section;
            const key = input.dataset.key;

            if (!newConfig[section]) {
                newConfig[section] = {};
            }

            newConfig[section][key] = input.value;
        });

        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newConfig)
        });

        const result = await response.json();
        const messageDiv = document.getElementById('settingsMessage');

        if (result.success) {
            messageDiv.className = 'message success';
            messageDiv.textContent = '設定儲存成功！需要重新啟動系統才會生效。';
        } else {
            messageDiv.className = 'message error';
            messageDiv.textContent = '設定儲存失敗：' + (result.error || '未知錯誤');
        }

        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);

    } catch (error) {
        console.error('儲存設定失敗:', error);
        const messageDiv = document.getElementById('settingsMessage');
        messageDiv.className = 'message error';
        messageDiv.textContent = '儲存設定失敗：' + error.message;
    }
}

// 自動更新
function startAutoUpdate() {
    // 每 2 秒更新一次統計資料
    updateInterval = setInterval(() => {
        if (document.getElementById('dashboard').classList.contains('active')) {
            loadStats();
        }
    }, 2000);
}

// 停止自動更新
function stopAutoUpdate() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
}

// 頁面卸載時停止更新
window.addEventListener('beforeunload', stopAutoUpdate);
