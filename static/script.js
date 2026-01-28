// 全域變數
let defectRateChart = null;
let productPieChart = null;
let updateInterval = null;
let camerasPaused = false;
let pausedCameraSrcs = [];

let currentZoom = 1.0;
const ZOOM_STEP = 0.1;
const MAX_ZOOM = 1.5;
const MIN_ZOOM = 0.8;

function applyInitialZoom() {
    const savedZoom = localStorage.getItem('pageZoom');
    if (savedZoom) {
        currentZoom = parseFloat(savedZoom);
        document.body.style.zoom = currentZoom;
    }
}

function changeZoom(direction) {
    if (direction === 'increase' && currentZoom < MAX_ZOOM) {
        currentZoom += ZOOM_STEP;
    } else if (direction === 'decrease' && currentZoom > MIN_ZOOM) {
        currentZoom -= ZOOM_STEP;
    } else if (direction === 'reset') {
        currentZoom = 1.0;
    }
    // toFixed to avoid floating point inaccuracies
    currentZoom = parseFloat(currentZoom.toFixed(2));
    document.body.style.zoom = currentZoom;
    localStorage.setItem('pageZoom', currentZoom);
}


// 初始化
document.addEventListener('DOMContentLoaded', function () {
    applyInitialZoom();
    initializePage();
    startAutoUpdate();
    setupNavigation();
});

// 設置導航按鈕事件
function setupNavigation() {
    const tabDashboard = document.getElementById('tab-dashboard');
    const tabHistory = document.getElementById('tab-history');
    const tabSettings = document.getElementById('tab-settings');

    if (tabDashboard) {
        tabDashboard.addEventListener('click', function () {
            showTab('dashboard', this);
        });
    }

    if (tabHistory) {
        tabHistory.addEventListener('click', function () {
            showTab('history', this);
        });
    }

    if (tabSettings) {
        tabSettings.addEventListener('click', function () {
            showTab('settings', this);
        });
    }
}

// 初始化頁面
function initializePage() {
    loadCameras();
    loadStats();
    loadHistory();
    loadConfig();
    initializeCharts();

    // 自動偵測可用攝影機（不顯示彈窗）
    detectCameras(false);
}

// 分頁切換
function showTab(tabName, clickedBtn) {
    // 隱藏所有分頁
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // 移除所有按鈕的 active 狀態
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 顯示選中的分頁
    const targetTab = document.getElementById(tabName);
    if (targetTab) {
        targetTab.classList.add('active');
    }

    // 設置點擊的按鈕為 active
    if (clickedBtn) {
        clickedBtn.classList.add('active');
    }

    // 根據分頁載入對應數據
    if (tabName === 'history') {
        loadHistory();
    } else if (tabName === 'settings') {
        loadConfig();
    }
}

// 載入攝影機列表
// 載入攝影機列表
async function loadCameras() {
    try {
        console.log('loadCameras: Starting...');
        // 同時獲取已設置的攝影機和所有可用的物理攝影機
        const [camerasResponse, availableResponse] = await Promise.all([
            fetch('/api/cameras'),
            fetch('/api/cameras/detect')
        ]);

        const cameras = await camerasResponse.json();
        const availableInfo = await availableResponse.json();
        const availableSources = availableInfo.available || [];

        console.log('loadCameras: Fetched cameras:', cameras);
        console.log('loadCameras: Available sources:', availableSources);

        // 產生攝影機畫面
        const videoContainer = document.getElementById('videoContainer');
        if (!videoContainer) {
            console.error('loadCameras: videoContainer element not found!');
            return;
        }

        videoContainer.innerHTML = '';

        cameras.forEach(camera => {
            console.log('loadCameras: Creating card for:', camera.name);
            const videoCard = document.createElement('div');
            videoCard.className = 'video-card';

            // 構建來源選項 HTML，並預選當前使用的來源
            const currentSource = camera.source_index;  // 當前物理攝影機索引
            let sourceOptions = '<option value="">-- 切換來源 --</option>';
            availableSources.forEach(source => {
                const selected = source.index === currentSource ? 'selected' : '';
                const displayText = source.index === currentSource
                    ? `來源 ${source.index} (當前)`
                    : `來源 ${source.index}`;
                sourceOptions += `<option value="${source.index}" ${selected}>${displayText}</option>`;
            });

            videoCard.innerHTML = `
                <div class="video-header">
                    <div style="display:flex; flex-direction:column; gap:5px;">
                        <h3>${camera.name}</h3>
                        <label style="font-size:0.8em;">
                            切換來源:
                            <select class="source-select" onchange="switchCameraSource(${camera.index}, this.value)">
                                ${sourceOptions}
                            </select>
                        </label>
                    </div>
                    <div style="display:flex; gap:5px; margin-left:auto;">
                        <button class="btn-pause-single" onclick="togglePauseCamera(${camera.index})" id="btn-pause-${camera.index}">
                            ⏸️
                        </button>
                        <button class="btn-remove" onclick="removeCamera(${camera.index})" title="移除攝影機" style="background-color: #ef4444; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                            ❌
                        </button>
                    </div>
                </div>
                
                <!-- 攝影機統計數據 -->
                <div class="camera-stats" id="camera-stats-${camera.index}" style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; padding:10px; background:#f8fafc; border-radius:8px; margin-bottom:10px;">
                    <div style="text-align:center;">
                        <div style="font-size:0.8em; color:#64748b;">總偵測數</div>
                        <div style="font-size:1.5em; font-weight:bold; color:#1e293b;" id="stat-total-${camera.index}">0</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:0.8em; color:#64748b;">正常品</div>
                        <div style="font-size:1.5em; font-weight:bold; color:#10b981;" id="stat-normal-${camera.index}">0</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:0.8em; color:#64748b;">瑕疵品</div>
                        <div style="font-size:1.5em; font-weight:bold; color:#ef4444;" id="stat-abnormal-${camera.index}">0</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:0.8em; color:#64748b;">瑕疵率</div>
                        <div style="font-size:1.5em; font-weight:bold; color:#f59e0b;" id="stat-rate-${camera.index}">0%</div>
                    </div>
                </div>
                
                <img src="/video_feed/${camera.index}" alt="${camera.name}" id="camera-img-${camera.index}" data-src="/video_feed/${camera.index}">
                
                <!-- 動作按鈕 -->
                <div class="camera-actions">
                    <button class="btn-action btn-hide-boxes" onclick="hideBoxes(${camera.index})" id="btn-hide-${camera.index}">
                        🚫 關閉標記框
                    </button>
                    <button class="btn-action btn-test-spray" onclick="testSpray(${camera.index})" id="btn-spray-${camera.index}">
                        💨 測試噴氣
                    </button>
                    <button class="btn-action btn-pause-relay" onclick="toggleRelayPause(${camera.index})" id="btn-pause-relay-${camera.index}">
                        ⏸️ 暫停噴氣
                    </button>
                </div>
                
                <!-- 焦距控制滑軌 -->
                <div class="camera-control">
                    <label>
                        <span class="control-label">🎯 焦距:</span>
                        <input type="range" min="0" max="255" value="128" 
                               class="slider" id="focus-${camera.index}"
                               oninput="updateFocus(${camera.index}, this.value)">
                        <span class="control-value" id="focus-value-${camera.index}">128</span>
                    </label>
                </div>
                
                <!-- 曝光控制滑軌 -->
                <div class="camera-control">
                    <label>
                        <span class="control-label">📸 曝光 (快門):</span>
                        <input type="range" min="-13" max="-1" value="-7" 
                               class="slider" id="exposure-${camera.index}"
                               oninput="updateExposure(${camera.index}, this.value)">
                        <span class="control-value" id="exposure-value-${camera.index}">-7</span>
                    </label>
                </div>
                
                <!-- 噴氣延遲控制滑軌 -->
                <div class="camera-control">
                    <label>
                        <span class="control-label">⏱️噴氣延遲(ms):</span>
                        <input type="range" min="0" max="5000" value="1600" step="100"
                               class="slider" id="delay-${camera.index}"
                               oninput="updateDelay(${camera.index}, this.value)">
                        <span class="control-value" id="delay-value-${camera.index}">1600</span>
                    </label>
                </div>
            `;
            videoContainer.appendChild(videoCard);

            // 恢復暫停噴氣按鈕的狀態
            const relayBtn = document.getElementById(`btn-pause-relay-${camera.index}`);
            if (relayBtn && camera.relay_paused) {
                relayBtn.innerHTML = '▶️ 恢復噴氣';
                relayBtn.classList.add('btn-danger');
                relayBtn.classList.remove('btn-pause-relay');
            }
        });
        console.log('loadCameras: All camera cards added to DOM');

        // 更新歷史記錄的攝影機選單
        const cameraSelect = document.getElementById('historyCamera');
        if (cameraSelect) {
            // 清空舊選項但保留 "全部"
            cameraSelect.innerHTML = '<option value="">全部</option>';
            cameras.forEach(camera => {
                const option = document.createElement('option');
                option.value = camera.name;
                option.textContent = camera.name;
                cameraSelect.appendChild(option);
            });
        }

    } catch (error) {
        console.error('載入攝影機失敗:', error);
    }
}

// 切換攝影機來源
async function switchCameraSource(cameraIdx, sourceIdx) {
    if (sourceIdx === "") return;

    if (!confirm(`確定要將 Camera ${cameraIdx + 1} 切換到來源 ${sourceIdx} 嗎？\n這可能會導致畫面短暫中斷。`)) {
        // 重置選擇
        loadCameras();
        return;
    }

    try {
        const response = await fetch(`/api/cameras/${cameraIdx}/source`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_index: parseInt(sourceIdx) })
        });

        const result = await response.json();

        if (result.success) {
            alert(`切換成功！已切換到來源 ${sourceIdx}`);
            // 重新載入相機以更新畫面和 UI
            loadCameras();
        } else {
            alert(`切換失敗: ${result.error}`);
        }
    } catch (error) {
        console.error('切換來源失敗:', error);
        alert('切換來源時發生錯誤');
    }
}

// 移除攝影機
async function removeCamera(cameraIdx) {
    // 雖然 API 支援移除任何攝影機，但通常建議保留前兩個（如果你想要的話）
    // 這裡直接詢問確認
    if (!confirm(`確定要移除此攝影機 (Camera ${cameraIdx}) 無法復原 ?\n這將會關閉此鏡頭的畫面。`)) {
        return;
    }

    try {
        const response = await fetch(`/api/cameras/${cameraIdx}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            // 成功後重新載入
            alert('已成功移除攝影機');
            loadCameras();
        } else {
            alert(`移除失敗: ${result.error}`);
        }
    } catch (error) {
        console.error('移除攝影機失敗:', error);
        alert('移除攝影機時發生錯誤');
    }
}


// 載入即時統計
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        // 更新每個攝影機卡片內的統計數據
        stats.forEach(stat => {
            // 假設 stat.name 是 "Camera1", "Camera2" 等，提取索引
            const cameraIndex = parseInt(stat.name.replace('Camera', '')) - 1;
            
            const totalEl = document.getElementById(`stat-total-${cameraIndex}`);
            const normalEl = document.getElementById(`stat-normal-${cameraIndex}`);
            const abnormalEl = document.getElementById(`stat-abnormal-${cameraIndex}`);
            const rateEl = document.getElementById(`stat-rate-${cameraIndex}`);
            
            if (totalEl) totalEl.textContent = stat.total;
            if (normalEl) normalEl.textContent = stat.normal;
            if (abnormalEl) abnormalEl.textContent = stat.abnormal;
            if (rateEl) rateEl.textContent = `${stat.defect_rate}%`;
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
        const result = await response.json();

        // 處理分頁格式（新 API 回傳 {data: [], pagination: {}}）
        const history = result.data || result;

        if (!history || !Array.isArray(history) || history.length === 0) return;

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

// 歷史記錄分頁狀態
let historyState = {
    currentPage: 1,
    totalPages: 0,
    totalRecords: 0,
    isLoading: false
};

// 載入歷史記錄
async function loadHistory(page = 1) {
    if (historyState.isLoading) return;
    historyState.isLoading = true;

    try {
        const hours = document.getElementById('historyHours').value;
        const camera = document.getElementById('historyCamera').value;
        const perPage = 500;  // 每頁筆數

        const url = `/api/history?hours=${hours}&page=${page}&per_page=${perPage}${camera ? '&camera=' + camera : ''}`;
        const response = await fetch(url);
        const result = await response.json();

        const tbody = document.getElementById('historyTableBody');

        // 第一頁時清空表格
        if (page === 1) {
            tbody.innerHTML = '';
        }

        // 處理資料（支援新舊格式）
        const history = result.data || result;
        const pagination = result.pagination;

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

        // 更新分頁狀態
        if (pagination) {
            historyState.currentPage = pagination.page;
            historyState.totalPages = pagination.total_pages;
            historyState.totalRecords = pagination.total;
            updatePaginationUI();
        }

    } catch (error) {
        console.error('載入歷史記錄失敗:', error);
    } finally {
        historyState.isLoading = false;
    }
}

// 更新分頁 UI
function updatePaginationUI() {
    let paginationDiv = document.getElementById('historyPagination');
    if (!paginationDiv) {
        // 創建分頁容器
        const container = document.querySelector('.history-table-container');
        paginationDiv = document.createElement('div');
        paginationDiv.id = 'historyPagination';
        paginationDiv.className = 'pagination-controls';
        container.parentNode.insertBefore(paginationDiv, container.nextSibling);
    }

    const { currentPage, totalPages, totalRecords } = historyState;

    paginationDiv.innerHTML = `
        <span class="pagination-info">共 ${totalRecords} 筆記錄，第 ${currentPage} / ${totalPages} 頁</span>
        <div class="pagination-buttons">
            <button onclick="loadHistory(1)" ${currentPage <= 1 ? 'disabled' : ''}>⏮️ 首頁</button>
            <button onclick="loadHistory(${currentPage - 1})" ${currentPage <= 1 ? 'disabled' : ''}>◀️ 上一頁</button>
            <button onclick="loadHistory(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''}>下一頁 ▶️</button>
            <button onclick="loadHistory(${totalPages})" ${currentPage >= totalPages ? 'disabled' : ''}>末頁 ⏭️</button>
            <button onclick="loadAllHistory()" class="btn-load-all" ${totalRecords <= 500 ? 'disabled' : ''}>📥 載入全部</button>
        </div>
    `;
}

// 載入全部歷史記錄
async function loadAllHistory() {
    if (historyState.isLoading) return;

    if (historyState.totalRecords > 10000) {
        if (!confirm(`共有 ${historyState.totalRecords} 筆記錄，載入全部可能需要較長時間，是否繼續？`)) {
            return;
        }
    }

    historyState.isLoading = true;
    const tbody = document.getElementById('historyTableBody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">正在載入全部記錄...</td></tr>';

    try {
        const hours = document.getElementById('historyHours').value;
        const camera = document.getElementById('historyCamera').value;

        // 使用較大的 per_page 來減少請求次數
        const url = `/api/history?hours=${hours}&page=1&per_page=5000${camera ? '&camera=' + camera : ''}`;
        const response = await fetch(url);
        const result = await response.json();

        const pagination = result.pagination;
        const totalPages = pagination.total_pages;

        tbody.innerHTML = '';

        // 處理第一批資料
        appendHistoryRows(result.data);

        // 載入剩餘頁面
        for (let page = 2; page <= totalPages; page++) {
            const pageUrl = `/api/history?hours=${hours}&page=${page}&per_page=5000${camera ? '&camera=' + camera : ''}`;
            const pageResponse = await fetch(pageUrl);
            const pageResult = await pageResponse.json();
            appendHistoryRows(pageResult.data);
        }

        // 更新 UI 顯示已載入全部
        let paginationDiv = document.getElementById('historyPagination');
        if (paginationDiv) {
            paginationDiv.innerHTML = `<span class="pagination-info">已載入全部 ${historyState.totalRecords} 筆記錄</span>`;
        }

    } catch (error) {
        console.error('載入全部歷史記錄失敗:', error);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:red;">載入失敗</td></tr>';
    } finally {
        historyState.isLoading = false;
    }
}

// 附加歷史記錄列
function appendHistoryRows(history) {
    const tbody = document.getElementById('historyTableBody');
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
}

// 匯出 CSV
async function exportHistory() {
    try {
        const hours = document.getElementById('historyHours').value;
        const camera = document.getElementById('historyCamera').value;

        const url = `/api/history/export?hours=${encodeURIComponent(hours)}${camera ? `&camera=${encodeURIComponent(camera)}` : ''}`;

        const res = await fetch(url);
        if (!res.ok) {
            throw new Error(`匯出失敗 (HTTP ${res.status})`);
        }

        const blob = await res.blob();

        // 從 Content-Disposition 取得檔名
        const disposition = res.headers.get('Content-Disposition') || '';
        let filename = 'history.csv';
        const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(disposition);
        if (match) {
            filename = decodeURIComponent(match[1] || match[2]);
        }

        const link = document.createElement('a');
        const href = URL.createObjectURL(blob);
        link.href = href;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(href);
    } catch (error) {
        console.error('匯出 CSV 失敗:', error);
        alert('匯出失敗：' + (error.message || error));
    }
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

        // 載入模型列表
        loadModels();

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

// 載入模型列表
async function loadModels() {
    try {
        const [modelsResponse, currentResponse] = await Promise.all([
            fetch('/api/models'),
            fetch('/api/models/current')
        ]);

        if (!modelsResponse.ok || !currentResponse.ok) {
            throw new Error('無法載入模型資訊');
        }

        const models = await modelsResponse.json();
        const current = await currentResponse.json();
        const modelSelect = document.getElementById('modelSelect');
        const currentModelInfo = document.getElementById('currentModelInfo');

        modelSelect.innerHTML = ''; // 清空選項

        if (models.length === 0) {
            modelSelect.innerHTML = '<option value="">沒有可用的模型</option>';
        } else {
            models.forEach(model => {
                const option = document.createElement('option');
                // Store full model info in data attributes
                option.value = model.weights;
                option.dataset.cfg = model.cfg || '';
                option.dataset.type = model.type || 'yolov4';
                option.textContent = `${model.name} (${model.type}, ${model.size_mb} MB)`;
                if (model.weights === current.weights) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });
        }

        if (current.name !== 'Unknown') {
            currentModelInfo.textContent = `目前模型: ${current.name}`;
        } else {
            currentModelInfo.textContent = '未選擇模型';
        }

    } catch (error) {
        console.error('載入模型失敗:', error);
        document.getElementById('modelSelect').innerHTML = '<option value="">載入失敗</option>';
        document.getElementById('currentModelInfo').textContent = '無法載入模型資訊';
    }
}

// 切換模型
async function changeModel() {
    const modelSelect = document.getElementById('modelSelect');
    const selectedOption = modelSelect.options[modelSelect.selectedIndex];

    if (!selectedOption || !selectedOption.value) {
        alert('請選擇一個模型');
        return;
    }

    const weights = selectedOption.value;
    const cfg = selectedOption.dataset.cfg;
    const type = selectedOption.dataset.type;

    const messageDiv = document.getElementById('settingsMessage');
    messageDiv.className = 'message';
    messageDiv.textContent = '正在切換模型...';
    messageDiv.style.display = 'block';

    try {
        const response = await fetch('/api/models/change', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ weights, cfg, type })
        });

        const result = await response.json();

        if (result.success) {
            messageDiv.className = 'message success';
            messageDiv.textContent = result.message || '模型切換成功！';
            // 重新載入當前模型資訊
            loadModels();
        } else {
            messageDiv.className = 'message error';
            messageDiv.textContent = '切換失敗: ' + (result.error || '未知錯誤');
        }
    } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = '切換失敗: ' + error.message;
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

// 更新焦距（自動儲存）
async function updateFocus(cameraIndex, value) {
    const valueDisplay = document.getElementById(`focus-value-${cameraIndex}`);

    if (valueDisplay) {
        valueDisplay.textContent = value;
    }

    // 調用 API 更新焦距並自動儲存
    try {
        const response = await fetch(`/api/cameras/${cameraIndex}/focus`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ focus: parseInt(value), auto: false, save: true })
        });
        const result = await response.json();

        if (result.success) {
            console.log(`Camera ${cameraIndex} 焦距已更新並儲存: ${value}`);
        }
    } catch (error) {
        console.error(`Camera ${cameraIndex} 焦距更新失敗:`, error);
    }
}



// 更新曝光值（快門速度，自動儲存）
async function updateExposure(cameraIndex, value) {
    const valueDisplay = document.getElementById(`exposure-value-${cameraIndex}`);
    if (valueDisplay) {
        valueDisplay.textContent = value;
    }

    // 調用 API 更新曝光並自動儲存
    try {
        const response = await fetch(`/api/cameras/${cameraIndex}/exposure`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exposure: parseInt(value), auto: false, save: true })
        });
        const result = await response.json();

        if (result.success) {
            console.log(`Camera ${cameraIndex} 曝光已更新並儲存: ${value}`);
        }
    } catch (error) {
        console.error(`Camera ${cameraIndex} 曝光更新失敗:`, error);
    }
}



// 更新噴氣延遲
async function updateDelay(cameraIndex, value) {
    const valueDisplay = document.getElementById(`delay-value-${cameraIndex}`);
    if (valueDisplay) {
        valueDisplay.textContent = value;
    }

    // 調用 API 更新延遲
    try {
        await fetch(`/api/cameras/${cameraIndex}/delay`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ delay_ms: parseInt(value) })
        });
        console.log(`Camera ${cameraIndex} 延遲已更新: ${value}ms`);
    } catch (error) {
        console.error(`Camera ${cameraIndex} 延遲更新失敗:`, error);
    }
}

// 暫停/繼續所有攝影機
function togglePauseCameras() {
    const btn = document.getElementById('btn-pause-cameras');
    const imgs = document.querySelectorAll('#videoContainer img');

    if (camerasPaused) {
        imgs.forEach((img, index) => {
            const originalSrc = img.getAttribute('data-src');
            if (originalSrc) {
                img.src = originalSrc + '?t=' + Date.now();
                img.classList.remove('camera-paused');
            }
            const singleBtn = document.getElementById(`btn-pause-${index}`);
            if (singleBtn) {
                singleBtn.innerHTML = '⏸️';
                singleBtn.classList.remove('paused');
            }
        });
        btn.innerHTML = '⏸️ 暫停所有鏡頭';
        btn.classList.remove('paused');
        camerasPaused = false;
    } else {
        imgs.forEach((img, index) => {
            img.src = '';
            img.classList.add('camera-paused');
            const singleBtn = document.getElementById(`btn-pause-${index}`);
            if (singleBtn) {
                singleBtn.innerHTML = '▶️';
                singleBtn.classList.add('paused');
            }
        });
        btn.innerHTML = '▶️ 繼續所有鏡頭';
        btn.classList.add('paused');
        camerasPaused = true;
    }
}

// 暫停/繼續單一攝影機
function togglePauseCamera(cameraIndex) {
    const img = document.getElementById(`camera-img-${cameraIndex}`);
    const btn = document.getElementById(`btn-pause-${cameraIndex}`);

    if (!img || !btn) return;

    if (btn.classList.contains('paused')) {
        const originalSrc = img.getAttribute('data-src');
        if (originalSrc) {
            img.src = originalSrc + '?t=' + Date.now();
        }
        img.classList.remove('camera-paused');
        btn.innerHTML = '⏸️';
        btn.classList.remove('paused');
    } else {
        img.src = '';
        img.classList.add('camera-paused');
        btn.innerHTML = '▶️';
        btn.classList.add('paused');
    }
}

// Hide/show boxes (toggle)
async function hideBoxes(cameraIndex) {
    const btn = document.getElementById(`btn-hide-${cameraIndex}`);
    const hint = document.getElementById(`hint-${cameraIndex}`);

    if (btn) btn.disabled = true;

    try {
        const response = await fetch(`/api/cameras/${cameraIndex}/hide_boxes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const result = await response.json();

        if (result.success && btn) {
            if (result.hidden) {
                btn.classList.add('active');
                btn.innerHTML = '\u958b\u555f\u6a19\u8a18\u6846';
                if (hint) hint.textContent = '\u6a19\u8a18\u6846\u5df2\u95dc\u9589\uff08\u518d\u6b21\u9ede\u64ca\u958b\u555f\uff09';
            } else {
                btn.classList.remove('active');
                btn.innerHTML = '\u95dc\u9589\u6a19\u8a18\u6846';
                if (hint) hint.textContent = '\u6a19\u8a18\u6846\u5df2\u986f\u793a\uff08\u518d\u6b21\u9ede\u64ca\u95dc\u9589\uff09';
            }
        }
    } catch (error) {
        console.error('Toggle hide boxes failed:', error);
        if (hint) hint.textContent = 'Toggle failed: ' + error.message;
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function testSpray(cameraIndex) {
    const btn = document.getElementById(`btn-spray-${cameraIndex}`);
    const hint = document.getElementById(`hint-${cameraIndex}`);

    btn.disabled = true;
    btn.innerHTML = '💨 噴氣中...';

    try {
        const response = await fetch(`/api/cameras/${cameraIndex}/test_spray`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            if (hint) hint.textContent = `已觸發噴氣 (延遲: ${result.delay_ms}ms)`;
        } else {
            if (hint) hint.textContent = '噴氣失敗: ' + (result.error || '未知錯誤');
        }
    } catch (error) {
        console.error('測試噴氣失敗:', error);
        if (hint) hint.textContent = '噴氣失敗: ' + error.message;
    } finally {
        setTimeout(() => {
            btn.disabled = false;
            btn.innerHTML = '💨 測試噴氣';
        }, 1000);
    }
}

// 切換繼電器暫停狀態
async function toggleRelayPause(cameraIndex) {
    const btn = document.getElementById(`btn-pause-relay-${cameraIndex}`);
    if (!btn) return;

    try {
        const response = await fetch(`/api/cameras/${cameraIndex}/relay/pause`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            const isPaused = result.paused;
            if (isPaused) {
                btn.innerHTML = '▶️ 恢復噴氣';
                btn.classList.add('btn-danger');
                btn.classList.remove('btn-pause-relay');
            } else {
                btn.innerHTML = '⏸️ 暫停噴氣';
                btn.classList.add('btn-pause-relay');
                btn.classList.remove('btn-danger');
            }
        } else {
            console.error('切換暫停狀態失敗:', result.error);
            alert('切換失敗');
        }
    } catch (error) {
        console.error('API 錯誤:', error);
        alert('操作失敗');
    }
}

function restartApp() {
    if (confirm('您確定要重啟應用程式嗎？目前的連線將會中斷。')) {
        fetch('/api/system/restart', {
            method: 'POST'
        }).then(response => {
            console.log('Restart command sent.');
        }).catch(error => {
            // This error is expected as the server is shutting down
            console.error('Restart command sent, server shutting down:', error);
        });

        // 等待伺服器重啟後自動重新載入頁面
        setTimeout(() => {
            location.reload();
        }, 5000);
    }
}

// 重新偵測可用攝影機
async function detectCameras(showAlert = true) {
    const btn = document.getElementById('btn-detect-cameras');
    const select = document.getElementById('available-cameras');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '🔄 偵測中...';
    }

    try {
        const response = await fetch('/api/cameras/detect');
        const result = await response.json();

        // 更新下拉選單
        if (select) {
            select.innerHTML = '<option value="">-- 選擇攝影機 --</option>';

            if (result.available && result.available.length > 0) {
                result.available.forEach(cam => {
                    const option = document.createElement('option');
                    option.value = cam.index;
                    option.textContent = `攝影機 ${cam.index}${cam.in_use ? ' (使用中)' : ''}${cam.name ? ' - ' + cam.name : ''}`;
                    if (cam.in_use) {
                        option.disabled = true;
                    }
                    select.appendChild(option);
                });

                if (showAlert) {
                    alert(`偵測到 ${result.available.length} 個攝影機`);
                } else {
                    console.log(`自動偵測到 ${result.available.length} 個攝影機`);
                }
            } else {
                if (showAlert) {
                    alert('未偵測到可用的攝影機');
                } else {
                    console.log('未偵測到可用的攝影機');
                }
            }
        }
    } catch (error) {
        console.error('偵測攝影機失敗:', error);
        if (showAlert) {
            alert('偵測攝影機失敗: ' + error.message);
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '🔍 重新偵測鏡頭';
        }
    }
}

// 新增選擇的攝影機
async function addSelectedCamera() {
    const select = document.getElementById('available-cameras');
    const cameraIndex = select.value;

    if (!cameraIndex) {
        alert('請先選擇攝影機');
        return;
    }

    try {
        const response = await fetch('/api/cameras/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ camera_index: parseInt(cameraIndex) })
        });

        const result = await response.json();

        if (result.success) {
            alert(`已新增攝影機 ${cameraIndex}`);
            // 重新載入攝影機畫面
            loadCameras();
            // 更新下拉選單
            detectCameras();
        } else {
            alert('新增失敗: ' + (result.error || '未知錯誤'));
        }
    } catch (error) {
        console.error('新增攝影機失敗:', error);
        alert('新增攝影機失敗: ' + error.message);
    }
}

// ==================== 模型管理功能 ====================

// 載入可用模型列表
async function loadModels() {
    try {
        const response = await fetch('/api/models');
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('model-versions');
            const infoSpan = document.getElementById('model-info');

            // 清空下拉選單
            select.innerHTML = '';

            if (data.models.length === 0) {
                select.innerHTML = '<option value="">-- 無可用模型 --</option>';
                return;
            }

            // 填充模型列表，顯示名稱和時間
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.path;
                // 顯示格式：名稱 | 時間 | 大小
                option.textContent = `${model.name} | ${model.modified}`;
                option.selected = model.is_current;

                // 如果是當前使用的模型，添加標記
                if (model.is_current) {
                    option.textContent = `✅ ${option.textContent}`;
                }

                select.appendChild(option);
            });

            // 顯示當前模型信息
            const currentModel = data.models.find(m => m.is_current);
            if (currentModel && infoSpan) {
                infoSpan.textContent = `當前使用`;
                infoSpan.style.color = '#10b981';
            }
        }
    } catch (error) {
        console.error('載入模型列表失敗:', error);
    }
}

// 切換模型
async function switchModel() {
    const select = document.getElementById('model-versions');
    const modelPath = select.value;
    const infoSpan = document.getElementById('model-info');

    if (!modelPath) {
        return;
    }

    // 顯示載入中
    infoSpan.textContent = '⏳ 切換中...';
    infoSpan.style.color = '#f59e0b';
    select.disabled = true;

    try {
        const response = await fetch('/api/models/switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_path: modelPath })
        });

        const result = await response.json();

        if (result.success) {
            // 成功切換
            infoSpan.textContent = '✅ 切換成功';
            infoSpan.style.color = '#10b981';

            // 顯示通知
            const selectedOption = select.options[select.selectedIndex];
            const modelName = selectedOption.textContent.split(' (')[0];
            alert(`已成功切換到模型: ${modelName}`);

            // 重新載入模型列表以更新當前狀態
            setTimeout(() => loadModels(), 1000);
        } else {
            // 切換失敗
            infoSpan.textContent = '❌ 失敗';
            infoSpan.style.color = '#ef4444';
            alert('切換模型失敗: ' + (result.error || '未知錯誤'));

            // 恢復原選項
            loadModels();
        }
    } catch (error) {
        console.error('切換模型失敗:', error);
        infoSpan.textContent = '❌ 錯誤';
        infoSpan.style.color = '#ef4444';
        alert('切換模型失敗: ' + error.message);

        // 恢復原選項
        loadModels();
    } finally {
        select.disabled = false;
    }
}

// 在頁面初始化時載入模型列表
document.addEventListener('DOMContentLoaded', function () {
    loadModels();
});
