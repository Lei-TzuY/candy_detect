// 全域變數
let currentFiles = [];
let currentIndex = -1;
let currentImage = null;
let annotations = [];
let selectedClass = 0;
let isDrawing = false;
let startX, startY, currentMouseX, currentMouseY;
let canvas, ctx;
let scale = 1;
let selectedAnnotation = -1;
let offsetX = 0, offsetY = 0;
let isPanning = false;
let panStartX = 0, panStartY = 0;
let panStartOffsetX = 0, panStartOffsetY = 0;
let selectedFiles = new Set(); // 追蹤選中的檔案索引
let showLabels = true; // 控制是否顯示標籤文字

// 框選功能變數
let isDragSelecting = false;
let dragSelectStart = { x: 0, y: 0 };
let dragSelectCurrent = { x: 0, y: 0 };
let dragSelectBox = null;

// 歷史記錄用於 undo/redo
let annotationHistory = [];
let historyIndex = -1;
let maxHistorySize = 50; // 最多保存 50 步歷史

// 初始化
document.addEventListener('DOMContentLoaded', function () {
    canvas = document.getElementById('imageCanvas');
    ctx = canvas.getContext('2d');

    setupEventListeners();
    setupResizers();
    loadFileList();
    updateSelectedStats();
});

// 設置事件監聽
function setupEventListeners() {
    // 工具按鈕
    document.getElementById('btnPrevious').addEventListener('click', () => navigateImage(-1));
    document.getElementById('btnNext').addEventListener('click', () => navigateImage(1));
    document.getElementById('btnDraw').addEventListener('click', () => setTool('draw'));
    document.getElementById('btnDelete').addEventListener('click', deleteSelectedAnnotation);
    document.getElementById('btnZoomIn').addEventListener('click', () => zoom(1.2));
    document.getElementById('btnZoomOut').addEventListener('click', () => zoom(0.8));
    document.getElementById('btnZoomFit').addEventListener('click', fitToScreen);
    document.getElementById('btnToggleLabels').addEventListener('click', toggleLabels);
    document.getElementById('btnHelp').addEventListener('click', toggleHelp);
    document.getElementById('btnSave').addEventListener('click', saveAnnotations);
    document.getElementById('btnAutoLabelCurrent').addEventListener('click', autoLabelCurrentImage);
    document.getElementById('btnExport').addEventListener('click', exportDataset);
    document.getElementById('btnDeleteImage').addEventListener('click', deleteCurrentImage);
    document.getElementById('btnAutoLabel').addEventListener('click', autoLabel);
    document.getElementById('btnDetectDuplicates').addEventListener('click', detectDuplicates);
    document.getElementById('btnDetectBlanks').addEventListener('click', detectBlanks);
    document.getElementById('btnFilterExtremeBoxes').addEventListener('click', filterExtremeBoxes);
    document.getElementById('btnSelectAll').addEventListener('click', toggleSelectAll);
    document.getElementById('btnSelectManual').addEventListener('click', selectManualLabeled);
    document.getElementById('btnSelectAuto').addEventListener('click', selectAutoLabeled);
    document.getElementById('btnBatchSwapClass').addEventListener('click', batchSwapClass);
    document.getElementById('btnBatchDelete').addEventListener('click', batchDelete);

    // 重整按鈕（如果存在）
    const btnRefresh = document.getElementById('btnRefresh');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', refreshFileList);
    }

    // 預覽所有標記框
    const btnPreviewAll = document.getElementById('btnPreviewAll');
    const btnClosePreview = document.getElementById('btnClosePreview');
    if (btnPreviewAll && btnClosePreview) {
        btnPreviewAll.addEventListener('click', showPreviewModal);
        btnClosePreview.addEventListener('click', closePreviewModal);
    }

    // 類別選擇
    document.querySelectorAll('.class-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.class-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            selectedClass = parseInt(this.dataset.class);
        });
    });

    // 篩選按鈕
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            filterFiles(this.dataset.filter);
        });
    });

    // 資料夾選擇器
    document.getElementById('folderSelector').addEventListener('change', function () {
        filterFiles();
    });

    // 畫布事件
    canvas.addEventListener('mousedown', onMouseDown);
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('mouseup', onMouseUp);
    canvas.addEventListener('wheel', onMouseWheel, { passive: false });

    // 檔案列表框選事件
    const fileList = document.getElementById('fileList');
    fileList.addEventListener('mousedown', onFileListMouseDown);
    document.addEventListener('mousemove', onFileListMouseMove);
    document.addEventListener('mouseup', onFileListMouseUp);

    // 鍵盤快捷鍵
    document.addEventListener('keydown', handleKeyPress);
}

// 載入檔案列表
async function loadFileList() {
    try {
        const response = await axios.get('/api/annotate/images');
        currentFiles = response.data.images || [];
        const folders = response.data.folders || [];

        console.log('Loaded folders:', folders);
        console.log('Folders count:', folders.length);

        // 更新資料夾選擇器
        const folderSelector = document.getElementById('folderSelector');
        const currentSelection = folderSelector.value;

        folderSelector.innerHTML = '<option value="">📁 全部資料夾</option>';
        folders.forEach(folder => {
            const option = document.createElement('option');
            option.value = folder;
            option.textContent = `📁 ${folder}`;
            folderSelector.appendChild(option);
        });

        console.log('Folder selector options count:', folderSelector.options.length);

        // 恢復之前的選擇
        if (currentSelection && folders.includes(currentSelection)) {
            folderSelector.value = currentSelection;
        }

        renderFileList();
        updateStats();
    } catch (error) {
        console.error('載入檔案列表失敗:', error);
        alert('載入檔案列表失敗');
    }
}

// 重新載入檔案列表
async function refreshFileList() {
    const btn = document.getElementById('btnRefresh');
    btn.classList.add('loading');
    btn.disabled = true;

    try {
        await loadFileList();

        // 如果當前有選中的圖片，重新載入它的標註
        if (currentIndex >= 0 && currentIndex < currentFiles.length) {
            await loadImage(currentIndex);
        }

        console.log('✅ 檔案列表已重新載入');
    } catch (error) {
        console.error('重新載入失敗:', error);
        alert('重新載入失敗');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// 取得過濾後的檔案列表
function getFilteredFiles() {
    const activeFilter = document.querySelector('.filter-btn.active').dataset.filter;
    const selectedFolder = document.getElementById('folderSelector').value;

    console.log(`Filtering: filter="${activeFilter}", folder="${selectedFolder}"`);

    return currentFiles.filter(file => {
        const matchesFilter = activeFilter === 'all' ||
            (activeFilter === 'labeled' && file.labeled) ||
            (activeFilter === 'unlabeled' && !file.labeled);

        // 資料夾篩選
        let matchesFolder = true;
        if (selectedFolder) {
            matchesFolder = file.name.startsWith(selectedFolder + '/');
        }

        return matchesFilter && matchesFolder;
    });
}

// 渲染檔案列表
function renderFileList() {
    const fileList = document.getElementById('fileList');
    const filteredFiles = getFilteredFiles();
    const selectedFolder = document.getElementById('folderSelector').value;

    fileList.innerHTML = filteredFiles.map((file, index) => {
        // 如果選了資料夾，只顯示檔名部分，讓列表更簡潔
        let displayName = file.name;
        if (selectedFolder && displayName.startsWith(selectedFolder + '/')) {
            displayName = displayName.substring(selectedFolder.length + 1);
        }

        // 找到原始索引以確保點擊正確
        const originalIndex = currentFiles.indexOf(file);

        // 標註來源標籤
        let sourceLabel = '';
        if (file.label_source === 'ai') {
            sourceLabel = '<span style="background:#2196F3;color:white;padding:2px 6px;border-radius:3px;font-size:10px;margin-left:4px;">🤖AI</span>';
        } else if (file.label_source === 'manual') {
            sourceLabel = '<span style="background:#4CAF50;color:white;padding:2px 6px;border-radius:3px;font-size:10px;margin-left:4px;">✍️手動</span>';
        } else if (file.label_source === 'unknown') {
            sourceLabel = '<span style="background:#FF9800;color:white;padding:2px 6px;border-radius:3px;font-size:10px;margin-left:4px;">❓未知</span>';
        }

        const isChecked = selectedFiles.has(originalIndex);
        const hasSelection = selectedFiles.size > 0;  // 是否有選中的檔案（選取模式）

        return `
        <div class="file-item ${file.labeled ? 'labeled' : ''} ${originalIndex === currentIndex ? 'active' : ''}" style="display: flex; align-items: center; gap: 8px;">
            <input type="checkbox" 
                   class="file-checkbox" 
                   data-index="${originalIndex}" 
                   ${isChecked ? 'checked' : ''}
                   onclick="event.stopPropagation(); toggleFileSelection(${originalIndex})"
                   style="cursor: pointer; width: 16px; height: 16px;">
            <span onclick="${hasSelection ? 'toggleFileSelection(' + originalIndex + ')' : 'loadImage(' + originalIndex + ')'}" 
                  style="flex: 1; cursor: pointer;">
                ${displayName}${sourceLabel}
            </span>
        </div>
    `}).join('');

    updateSelectAllButton();
}

// 載入影像
async function loadImage(index) {
    if (index < 0 || index >= currentFiles.length) return;

    currentIndex = index;
    const file = currentFiles[index];

    // 載入影像
    const img = new Image();
    img.onload = async function () {
        currentImage = img;

        // 使用容器尺寸設定 Canvas，避免 CSS 縮放導致座標偏移
        const wrapper = document.querySelector('.canvas-wrapper');
        const wrapperWidth = wrapper.clientWidth;
        const wrapperHeight = wrapper.clientHeight;

        // 設定 canvas 為容器大小
        canvas.width = wrapperWidth;
        canvas.height = wrapperHeight;

        // 計算縮放比例以適應容器（保持原始比例）
        const scaleX = wrapperWidth / img.width;
        const scaleY = wrapperHeight / img.height;
        scale = Math.min(scaleX, scaleY);

        // 置中圖片
        const imgWidth = img.width * scale;
        const imgHeight = img.height * scale;
        offsetX = (wrapperWidth - imgWidth) / 2;
        offsetY = (wrapperHeight - imgHeight) / 2;

        // 載入標註（在影像載入完成後）
        try {
            const response = await axios.get(`/api/annotate/annotations/${encodeURIComponent(file.name)}`);
            const yoloAnnotations = response.data.annotations || [];
            const labelSource = response.data.label_source;

            // 更新畫布信息，顯示標註來源
            let sourceText = '';
            if (labelSource === 'ai') {
                sourceText = ' | 🤖 AI標註';
            } else if (labelSource === 'manual') {
                sourceText = ' | ✍️ 手動標註';
            } else if (labelSource === 'unknown') {
                sourceText = ' | ❓ 未知來源';
            }

            // 轉換 YOLO 格式到像素座標（使用影像原始尺寸）
            annotations = yoloAnnotations.map(ann => {
                const x_center = ann.x_center * img.width;
                const y_center = ann.y_center * img.height;
                const width = ann.width * img.width;
                const height = ann.height * img.height;

                return {
                    class: ann.class,
                    x: x_center - width / 2,
                    y: y_center - height / 2,
                    width: width,
                    height: height,
                    confidence: ann.confidence  // 保留信心分數
                };
            });

            // 載入圖片後重置歷史記錄
            resetHistory();

            renderAnnotationsList();
            document.getElementById('canvasInfo').textContent = `${file.name}${sourceText} (${annotations.length} 個標註)`;
        } catch (error) {
            annotations = [];
            resetHistory();
            renderAnnotationsList();
            document.getElementById('canvasInfo').textContent = file.name;
        }

        renderCanvas();
        renderFileList();
    };
    img.src = `/api/annotate/image/${encodeURIComponent(file.name)}`;
}

// 渲染畫布
function renderCanvas() {
    if (!currentImage) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 繪製圖片（考慮縮放和偏移）
    ctx.save();
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);
    ctx.drawImage(currentImage, 0, 0);
    ctx.restore();

    // 繪製標註框（考慮縮放和偏移）
    annotations.forEach((ann, index) => {
        const color = ann.class === 0 ? '#10b981' : '#ef4444';
        const isSelected = index === selectedAnnotation;

        // 選中的標註框使用更明顯的樣式
        ctx.strokeStyle = color;
        ctx.lineWidth = isSelected ? 4 : 2;  // 加粗選中的框

        const x = ann.x * scale + offsetX;
        const y = ann.y * scale + offsetY;
        const w = ann.width * scale;
        const h = ann.height * scale;

        // 如果被選中，先繪製半透明背景
        if (isSelected) {
            ctx.fillStyle = color + '20';  // 添加透明度
            ctx.fillRect(x, y, w, h);
        }

        ctx.strokeRect(x, y, w, h);

        // 如果被選中，繪製調整點
        if (isSelected) {
            ctx.fillStyle = color;
            const handleSize = 8;
            // 四個角
            ctx.fillRect(x - handleSize / 2, y - handleSize / 2, handleSize, handleSize);
            ctx.fillRect(x + w - handleSize / 2, y - handleSize / 2, handleSize, handleSize);
            ctx.fillRect(x - handleSize / 2, y + h - handleSize / 2, handleSize, handleSize);
            ctx.fillRect(x + w - handleSize / 2, y + h - handleSize / 2, handleSize, handleSize);
            // 四個邊中點
            ctx.fillRect(x + w / 2 - handleSize / 2, y - handleSize / 2, handleSize, handleSize);
            ctx.fillRect(x + w / 2 - handleSize / 2, y + h - handleSize / 2, handleSize, handleSize);
            ctx.fillRect(x - handleSize / 2, y + h / 2 - handleSize / 2, handleSize, handleSize);
            ctx.fillRect(x + w - handleSize / 2, y + h / 2 - handleSize / 2, handleSize, handleSize);
        }

        // 標籤（根據開關決定是否顯示）
        if (showLabels) {
            const label = ann.class === 0 ? '正常' : '瑕疵';
            const labelText = ann.confidence ? `${label} ${(ann.confidence * 100).toFixed(0)}%` : label;
            const labelWidth = ann.confidence ? 90 : 60;

            ctx.fillStyle = color;
            ctx.fillRect(x, y - 20, labelWidth, 20);
            ctx.fillStyle = '#fff';
            ctx.font = '12px sans-serif';
            ctx.fillText(labelText, x + 5, y - 6);
        }
    });

    // 繪製中的框
    if (isDrawing && currentMouseX !== undefined && currentMouseY !== undefined) {
        const color = selectedClass === 0 ? '#10b981' : '#ef4444';
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);

        const x = Math.min(startX, currentMouseX) * scale + offsetX;
        const y = Math.min(startY, currentMouseY) * scale + offsetY;
        const width = Math.abs(currentMouseX - startX) * scale;
        const height = Math.abs(currentMouseY - startY) * scale;

        ctx.strokeRect(x, y, width, height);
        ctx.setLineDash([]);
    }
}

// 滑鼠事件
let resizingAnnotation = -1;
let resizeEdge = null; // 'n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'
let isDragging = false;
let dragStartX, dragStartY;

// 雙擊檢測
let lastClickTime = 0;
let lastClickedAnnotation = -1;
const DOUBLE_CLICK_DELAY = 300; // 毫秒

function getResizeEdge(imgX, imgY, ann, threshold = 15) {
    const edges = [];

    // 檢查上下左右邊緣（使用固定閾值，不受縮放影響）
    if (Math.abs(imgY - ann.y) < threshold) edges.push('n');
    if (Math.abs(imgY - (ann.y + ann.height)) < threshold) edges.push('s');
    if (Math.abs(imgX - ann.x) < threshold) edges.push('w');
    if (Math.abs(imgX - (ann.x + ann.width)) < threshold) edges.push('e');

    return edges.join('');
}

function onMouseDown(e) {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // 滑鼠中鍵或 Ctrl + 左鍵 = 拖動模式
    if (e.button === 1 || e.ctrlKey) {
        isPanning = true;
        panStartX = mouseX;
        panStartY = mouseY;
        panStartOffsetX = offsetX;
        panStartOffsetY = offsetY;
        canvas.style.cursor = 'grabbing';
        e.preventDefault();
        return;
    }

    // 轉換為圖片座標（考慮縮放和偏移）
    const imgX = (mouseX - offsetX) / scale;
    const imgY = (mouseY - offsetY) / scale;

    startX = imgX;
    startY = imgY;
    currentMouseX = imgX;
    currentMouseY = imgY;

    // 檢查是否點擊【已選中】標註的邊緣（用於調整大小）
    // 只有選中的標註框才能被調整大小
    if (selectedAnnotation >= 0 && selectedAnnotation < annotations.length) {
        const ann = annotations[selectedAnnotation];
        const edge = getResizeEdge(imgX, imgY, ann, 15);

        if (edge) {
            saveHistory(); // 在開始調整大小前保存歷史記錄
            resizingAnnotation = selectedAnnotation;
            resizeEdge = edge;
            renderAnnotationsList();
            renderCanvas();
            return;
        }
    }

    // 檢查是否點擊現有標註內部（用於移動或雙擊切換類型）
    const clickedIndex = annotations.findIndex(ann =>
        imgX >= ann.x && imgX <= ann.x + ann.width &&
        imgY >= ann.y && imgY <= ann.y + ann.height
    );

    if (clickedIndex >= 0) {
        const currentTime = Date.now();

        // 檢測雙擊：同一個標註框在短時間內點擊兩次
        if (clickedIndex === lastClickedAnnotation &&
            currentTime - lastClickTime < DOUBLE_CLICK_DELAY) {
            // 雙擊 - 切換類型
            toggleAnnotationClass(clickedIndex);
            lastClickTime = 0; // 重置，避免三連擊
            lastClickedAnnotation = -1;
            return;
        }

        // 單擊 - 選中並準備拖動
        lastClickTime = currentTime;
        lastClickedAnnotation = clickedIndex;
        selectedAnnotation = clickedIndex;
        saveHistory(); // 在開始拖動前保存歷史記錄
        isDragging = true;
        dragStartX = imgX;
        dragStartY = imgY;
        renderAnnotationsList();
        renderCanvas();
    } else {
        isDrawing = true;
        selectedAnnotation = -1;
        lastClickedAnnotation = -1;
    }
}

function onMouseMove(e) {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // 轉換為圖片座標
    const imgX = (mouseX - offsetX) / scale;
    const imgY = (mouseY - offsetY) / scale;

    // 拖動模式
    if (isPanning) {
        const deltaX = mouseX - panStartX;
        const deltaY = mouseY - panStartY;
        offsetX = panStartOffsetX + deltaX;
        offsetY = panStartOffsetY + deltaY;
        renderCanvas();
        return;
    }

    // 調整標註框大小
    if (resizingAnnotation >= 0 && resizeEdge) {
        const ann = annotations[resizingAnnotation];

        if (resizeEdge.includes('n')) {
            const newHeight = ann.height + (ann.y - imgY);
            if (newHeight > 10) {
                ann.y = imgY;
                ann.height = newHeight;
            }
        }
        if (resizeEdge.includes('s')) {
            ann.height = Math.max(10, imgY - ann.y);
        }
        if (resizeEdge.includes('w')) {
            const newWidth = ann.width + (ann.x - imgX);
            if (newWidth > 10) {
                ann.x = imgX;
                ann.width = newWidth;
            }
        }
        if (resizeEdge.includes('e')) {
            ann.width = Math.max(10, imgX - ann.x);
        }

        renderCanvas();
        return;
    }

    // 拖動標註框
    if (isDragging && selectedAnnotation >= 0) {
        const ann = annotations[selectedAnnotation];
        const deltaX = imgX - dragStartX;
        const deltaY = imgY - dragStartY;

        ann.x += deltaX;
        ann.y += deltaY;

        dragStartX = imgX;
        dragStartY = imgY;

        renderCanvas();
        return;
    }

    // 繪製新標註框
    if (isDrawing) {
        currentMouseX = imgX;
        currentMouseY = imgY;
        renderCanvas();
        return;
    }

    // 更新游標樣式（當滑鼠懸停在標註框邊緣時）
    let cursorSet = false;
    for (let i = annotations.length - 1; i >= 0; i--) {
        const ann = annotations[i];
        const edge = getResizeEdge(imgX, imgY, ann, 15);

        if (edge) {
            const cursors = {
                'n': 'ns-resize',
                's': 'ns-resize',
                'e': 'ew-resize',
                'w': 'ew-resize',
                'ne': 'nesw-resize',
                'nw': 'nwse-resize',
                'se': 'nwse-resize',
                'sw': 'nesw-resize'
            };
            canvas.style.cursor = cursors[edge] || 'crosshair';
            cursorSet = true;
            break;
        }
    }

    if (!cursorSet) {
        // 檢查是否在標註框內部
        const insideAnn = annotations.some(ann =>
            imgX >= ann.x && imgX <= ann.x + ann.width &&
            imgY >= ann.y && imgY <= ann.y + ann.height
        );
        canvas.style.cursor = insideAnn ? 'move' : 'crosshair';
    }
}

function onMouseUp(e) {
    // 結束拖動模式
    if (isPanning) {
        isPanning = false;
        canvas.style.cursor = 'crosshair';
        return;
    }

    // 結束調整大小
    if (resizingAnnotation >= 0) {
        resizingAnnotation = -1;
        resizeEdge = null;
        autoSaveAnnotations(); // 自動儲存
        return;
    }

    // 結束拖動標註框
    if (isDragging) {
        isDragging = false;
        autoSaveAnnotations(); // 自動儲存
        return;
    }

    if (!isDrawing) return;
    isDrawing = false;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // 轉換為圖片座標
    const imgX = (mouseX - offsetX) / scale;
    const imgY = (mouseY - offsetY) / scale;

    const endX = imgX;
    const endY = imgY;

    const x = Math.min(startX, endX);
    const y = Math.min(startY, endY);
    const width = Math.abs(endX - startX);
    const height = Math.abs(endY - startY);

    // 忽略太小的框
    if (width < 10 || height < 10) return;

    saveHistory(); // 保存歷史記錄

    annotations.push({
        class: selectedClass,
        x: x,
        y: y,
        width: width,
        height: height
    });

    renderAnnotationsList();
    renderCanvas();
    autoSaveAnnotations(); // 自動儲存
}

// 渲染標註列表
function renderAnnotationsList() {
    const list = document.getElementById('annotationsList');

    if (annotations.length === 0) {
        list.innerHTML = '<div style="text-align: center; color: #64748b; padding: 20px;">尚無標註</div>';
        return;
    }

    list.innerHTML = annotations.map((ann, index) => {
        const className = ann.class === 0 ? '正常' : '瑕疵';
        const color = ann.class === 0 ? '#10b981' : '#ef4444';
        return `
            <div class="annotation-item ${index === selectedAnnotation ? 'selected' : ''}" 
                 onclick="selectAnnotation(${index})">
                <div class="label" style="color: ${color}">
                    ${className}
                    <span class="delete-btn" onclick="event.stopPropagation(); deleteAnnotation(${index})">×</span>
                </div>
                <div class="coords">
                    位置: (${Math.round(ann.x)}, ${Math.round(ann.y)})
                    大小: ${Math.round(ann.width)} × ${Math.round(ann.height)}
                </div>
            </div>
        `;
    }).join('');
}

// 切換標註類型（雙擊功能）
function toggleAnnotationClass(index) {
    if (index >= 0 && index < annotations.length) {
        saveHistory(); // 保存歷史記錄

        const ann = annotations[index];
        // 切換類型：0 (正常) ↔ 1 (瑕疵)
        ann.class = ann.class === 0 ? 1 : 0;

        // 更新顯示
        renderAnnotationsList();
        renderCanvas();
        autoSaveAnnotations(); // 自動儲存

        // 視覺反饋
        const className = ann.class === 0 ? '正常' : '瑕疵';
        console.log(`已切換為: ${className}`);
    }
}

// 選擇標註
function selectAnnotation(index) {
    selectedAnnotation = index;
    renderAnnotationsList();
    renderCanvas();
}

// 刪除標註
function deleteAnnotation(index) {
    saveHistory(); // 保存歷史記錄
    annotations.splice(index, 1);
    selectedAnnotation = -1;
    renderAnnotationsList();
    renderCanvas();
    autoSaveAnnotations(); // 自動儲存
}

// 刪除選中的標註
function deleteSelectedAnnotation() {
    if (selectedAnnotation >= 0) {
        deleteAnnotation(selectedAnnotation);
    }
}

// ========== 歷史記錄管理 (Undo/Redo) ==========

// 重置歷史記錄（載入新圖片時調用）
function resetHistory() {
    annotationHistory = [JSON.parse(JSON.stringify(annotations))];
    historyIndex = 0;
}

// 保存當前狀態到歷史記錄
function saveHistory() {
    // 移除當前索引之後的所有歷史記錄
    annotationHistory = annotationHistory.slice(0, historyIndex + 1);

    // 添加新的狀態（深拷貝）
    annotationHistory.push(JSON.parse(JSON.stringify(annotations)));
    historyIndex++;

    // 限制歷史記錄大小
    if (annotationHistory.length > maxHistorySize) {
        annotationHistory.shift();
        historyIndex--;
    }
}

// 還原 (Undo)
function undo() {
    if (historyIndex > 0) {
        historyIndex--;
        annotations = JSON.parse(JSON.stringify(annotationHistory[historyIndex]));
        selectedAnnotation = -1;
        renderAnnotationsList();
        renderCanvas();
        console.log(`還原 (${historyIndex + 1}/${annotationHistory.length})`);
    } else {
        console.log('無法還原：已在最早的狀態');
    }
}

// 取消還原 (Redo)
function redo() {
    if (historyIndex < annotationHistory.length - 1) {
        historyIndex++;
        annotations = JSON.parse(JSON.stringify(annotationHistory[historyIndex]));
        selectedAnnotation = -1;
        renderAnnotationsList();
        renderCanvas();
        console.log(`取消還原 (${historyIndex + 1}/${annotationHistory.length})`);
    } else {
        console.log('無法取消還原：已在最新的狀態');
    }
}

// ========== 結束歷史記錄管理 ==========

// 儲存標註
async function saveAnnotations() {
    if (currentIndex < 0) return;
    if (!currentImage) return;

    const file = currentFiles[currentIndex];
    const btn = document.getElementById('btnSave');
    btn.disabled = true;
    btn.textContent = '儲存中...';

    try {
        // 使用原始圖片尺寸，而非 canvas 尺寸，確保 YOLO 座標正確
        await axios.post('/api/annotate/save', {
            filename: file.name,
            annotations: annotations,
            image_width: currentImage.width,
            image_height: currentImage.height
        });

        // 更新檔案狀態
        file.labeled = annotations.length > 0;
        updateStats();
        renderFileList();

        btn.textContent = '✓ 已儲存';
        setTimeout(() => {
            btn.textContent = '💾 儲存標註 (Ctrl+S)';
            btn.disabled = false;
        }, 1500);
    } catch (error) {
        console.error('儲存失敗:', error);
        alert('儲存失敗');
        btn.textContent = '💾 儲存標註 (Ctrl+S)';
        btn.disabled = false;
    }
}

// 自動儲存（無UI反饋，靜默保存）
let autoSaveTimeout = null;
async function autoSaveAnnotations() {
    if (currentIndex < 0) return;
    if (!currentImage) return;

    // 防抖：延遲500ms後才執行保存，避免頻繁保存
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }

    autoSaveTimeout = setTimeout(async () => {
        const file = currentFiles[currentIndex];

        try {
            await axios.post('/api/annotate/save', {
                filename: file.name,
                annotations: annotations,
                image_width: currentImage.width,
                image_height: currentImage.height
            });

            // 更新檔案狀態
            file.labeled = annotations.length > 0;
            updateStats();
            renderFileList();

            console.log('✓ 自動儲存成功');
        } catch (error) {
            console.error('自動儲存失敗:', error);
        }
    }, 500);
}

// 自動標註當前圖片
async function autoLabelCurrentImage() {
    if (currentIndex < 0) {
        alert('請先選擇一張圖片');
        return;
    }

    const file = currentFiles[currentIndex];

    // 詢問信心閾值
    const thresholdInput = prompt('請輸入信心閾值 (0.0 - 1.0)，建議值：0.25', '0.25');
    if (thresholdInput === null) return; // 使用者取消

    const threshold = parseFloat(thresholdInput);
    if (isNaN(threshold) || threshold < 0 || threshold > 1) {
        alert('無效的閾值！請輸入 0.0 到 1.0 之間的數值');
        return;
    }

    // 詢問是否覆蓋已存在的標註
    let overwrite = false;
    if (file.labeled) {
        overwrite = confirm(`當前圖片已有標註，是否覆蓋？\n\n點擊「確定」將覆蓋現有標註\n點擊「取消」將保留現有標註並退出`);
        if (!overwrite) {
            return;
        }
    }

    const btn = document.getElementById('btnAutoLabelCurrent');

    if (!confirm(`對當前圖片「${file.name}」進行自動標註？\n信心閾值：${threshold}${overwrite ? '\n將覆蓋現有標註' : ''}`)) return;

    btn.disabled = true;
    btn.textContent = '⏳ 標註中...';

    try {
        // 使用現有的自動標註API，但只傳遞當前圖片
        const response = await axios.post('/api/annotate/auto_label', {
            images: [file.name],
            confidence_threshold: threshold,
            overwrite: overwrite
        });

        // 重新載入當前圖片的標註
        await loadImage(currentIndex);

        const message = `自動標註完成！\n\n影像: ${file.name}\n偵測到: ${response.data.total_detections} 個目標\n信心閾值: ${threshold}`;
        alert(message);

        // 更新檔案列表狀態
        loadFileList();
    } catch (error) {
        console.error('自動標註失敗:', error);
        alert('自動標註失敗：' + (error.response?.data?.error || error.message));
    } finally {
        btn.disabled = false;
        btn.textContent = '🤖 自動標註';
    }
}

// 導航圖片
function navigateImage(delta) {
    const filteredFiles = getFilteredFiles();

    if (filteredFiles.length === 0) return;

    // 找到當前圖片在過濾列表中的位置
    const currentFile = currentFiles[currentIndex];
    const filteredIndex = filteredFiles.findIndex(f => f.name === currentFile?.name);

    if (filteredIndex === -1) {
        // 當前圖片不在過濾列表中，載入過濾列表的第一張
        const newFile = filteredFiles[0];
        const newIndex = currentFiles.findIndex(f => f.name === newFile.name);
        if (newIndex !== -1) loadImage(newIndex);
        return;
    }

    // 在過濾列表中找到下一張/上一張
    let newFilteredIndex = filteredIndex + delta;

    // 邊界檢查
    if (newFilteredIndex < 0) newFilteredIndex = 0;
    if (newFilteredIndex >= filteredFiles.length) newFilteredIndex = filteredFiles.length - 1;

    // 如果索引沒變，代表已在邊界
    if (newFilteredIndex === filteredIndex) return;

    // 找到該圖片在主列表中的索引
    const newFile = filteredFiles[newFilteredIndex];
    const newIndex = currentFiles.findIndex(f => f.name === newFile.name);

    if (newIndex !== -1) {
        loadImage(newIndex);
    }
}

// 縮放
function zoom(factor) {
    if (!currentImage) return;

    // 取得容器尺寸
    const wrapper = document.querySelector('.canvas-wrapper');
    const wrapperWidth = wrapper.clientWidth - 20;
    const wrapperHeight = wrapper.clientHeight - 20;

    // 調整縮放比例
    const newScale = scale * factor;
    if (newScale >= 0.1 && newScale <= 10) {
        scale = newScale;

        // 計算新的 canvas 尺寸
        const newWidth = currentImage.width * scale;
        const newHeight = currentImage.height * scale;

        // canvas 大小至少為容器大小，或者是縮放後的圖片大小
        canvas.width = Math.max(wrapperWidth, newWidth);
        canvas.height = Math.max(wrapperHeight, newHeight);

        // 重新計算偏移，讓圖片置中（如果圖片比容器小）
        if (newWidth < wrapperWidth) {
            offsetX = (canvas.width - newWidth) / 2;
        } else {
            offsetX = 0;
        }
        if (newHeight < wrapperHeight) {
            offsetY = (canvas.height - newHeight) / 2;
        } else {
            offsetY = 0;
        }

        renderCanvas();
    }
}

function fitToScreen() {
    if (!currentImage) return;

    const wrapper = document.querySelector('.canvas-wrapper');
    const wrapperWidth = wrapper.clientWidth - 20;
    const wrapperHeight = wrapper.clientHeight - 20;

    const scaleX = wrapperWidth / currentImage.width;
    const scaleY = wrapperHeight / currentImage.height;
    scale = Math.min(scaleX, scaleY);

    // 設定 canvas 大小為容器大小
    canvas.width = wrapperWidth;
    canvas.height = wrapperHeight;

    // 置中圖片
    const imgWidth = currentImage.width * scale;
    const imgHeight = currentImage.height * scale;
    offsetX = (canvas.width - imgWidth) / 2;
    offsetY = (canvas.height - imgHeight) / 2;

    renderCanvas();
}

// 切換標籤顯示/隱藏
function toggleLabels() {
    showLabels = !showLabels;
    const btn = document.getElementById('btnToggleLabels');
    btn.title = showLabels ? '隱藏標籤' : '顯示標籤';
    renderCanvas(); // 重新繪製主畫布
}

// 鍵盤事件處理
function handleKeyPress(e) {
    // 忽略輸入框中的按鍵（但 checkbox 可以）
    if (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') return;
    if (e.target.tagName === 'TEXTAREA') return;

    switch (e.key) {
        case 'w':
        case 'W':
            setTool('draw');
            break;
        case 'd':
        case 'D':
        case 'ArrowRight':  // 右箭頭
            navigateImage(1);
            break;
        case 'a':
        case 'A':
        case 'ArrowLeft':  // 左箭頭
            navigateImage(-1);
            break;
        case 'Delete':
        case 'Backspace':  // 也支援 Backspace 鍵
            e.preventDefault();  // 防止瀏覽器後退
            if (selectedAnnotation !== -1) {
                // 如果有選中的標註框，刪除標註框
                deleteSelectedAnnotation();
            } else {
                // 如果沒有選中的標註框，刪除整張圖片
                deleteCurrentImage();
            }
            break;
        case '1':
            document.querySelector('.class-btn[data-class="0"]').click();
            break;
        case '2':
            document.querySelector('.class-btn[data-class="1"]').click();
            break;
        case 's':
            if (e.ctrlKey) {
                e.preventDefault();
                saveAnnotations();
            }
            break;
        case 'z':
        case 'Z':
            if (e.ctrlKey) {
                e.preventDefault();
                undo();
            }
            break;
        case 'y':
        case 'Y':
            if (e.ctrlKey) {
                e.preventDefault();
                redo();
            }
            break;
        case 'Escape':
            isDrawing = false;
            renderCanvas();
            break;
    }
}

// 篩選檔案
function filterFiles() {
    renderFileList();
    updateStats();
}

// 更新統計
function updateStats() {
    const selectedFolder = document.getElementById('folderSelector').value;

    // 根據資料夾篩選
    let statsFiles = currentFiles;
    if (selectedFolder) {
        // 使用 startsWith 確保只計算該資料夾下的檔案
        statsFiles = currentFiles.filter(f => f.name.startsWith(selectedFolder + '/'));
    }

    const total = statsFiles.length;
    const labeled = statsFiles.filter(f => f.labeled).length;
    const unlabeled = total - labeled;

    console.log(`Stats updated: Total=${total}, Folder="${selectedFolder}"`);

    document.getElementById('fileStats').innerHTML = `
        總計: ${total} | 已標: ${labeled} | 未標: ${unlabeled}
    `;
}

// 設定工具
function setTool(tool) {
    document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('btnDraw').classList.add('active');
}

// 切換說明
function toggleHelp() {
    document.getElementById('shortcuts').classList.toggle('show');
}

// 刪除當前影像
async function deleteCurrentImage() {
    if (currentIndex < 0) return;
    if (!confirm('確定要刪除此影像嗎？此操作無法復原！')) return;

    try {
        const file = currentFiles[currentIndex];

        // 調用 API 刪除檔案
        await axios.delete(`/api/annotate/image/${encodeURIComponent(file.name)}`);

        selectedFiles.delete(currentIndex);  // 從選中集合中移除
        currentFiles.splice(currentIndex, 1);

        // 更新所有大於當前索引的選中項目索引
        const newSelectedFiles = new Set();
        selectedFiles.forEach(idx => {
            if (idx > currentIndex) {
                newSelectedFiles.add(idx - 1);
            } else if (idx < currentIndex) {
                newSelectedFiles.add(idx);
            }
        });
        selectedFiles = newSelectedFiles;

        renderFileList();
        updateStats();

        if (currentFiles.length > 0) {
            loadImage(Math.min(currentIndex, currentFiles.length - 1));
        }
    } catch (error) {
        console.error('刪除失敗:', error);
        alert('刪除失敗');
    }
}

// 切換檔案選擇狀態
function toggleFileSelection(index) {
    if (selectedFiles.has(index)) {
        selectedFiles.delete(index);
    } else {
        selectedFiles.add(index);
    }
    renderFileList();  // 重新渲染以更新選取模式
    updateSelectedStats();
}

// 全選/取消全選
function toggleSelectAll() {
    const filteredFiles = getFilteredFiles();
    const filteredIndices = filteredFiles.map(file => currentFiles.indexOf(file));

    // 檢查是否所有過濾後的檔案都已選中
    const allSelected = filteredIndices.every(idx => selectedFiles.has(idx));

    if (allSelected) {
        // 取消全選
        filteredIndices.forEach(idx => selectedFiles.delete(idx));
    } else {
        // 全選
        filteredIndices.forEach(idx => selectedFiles.add(idx));
    }

    renderFileList();
    updateSelectedStats();
}

// 選取手動標註的圖片
function selectManualLabeled() {
    const filteredFiles = getFilteredFiles();
    let manualCount = 0;

    // 清除現有選擇
    selectedFiles.clear();

    // 遺歷所有已篩選的檔案，使用已載入的 label_source 資訊
    filteredFiles.forEach(file => {
        if (file.labeled && file.label_source === 'manual') {
            const fileIndex = currentFiles.indexOf(file);
            if (fileIndex >= 0) {
                selectedFiles.add(fileIndex);
                manualCount++;
            }
        }
    });

    renderFileList();
    updateSelectAllButton();
    updateSelectedStats();

    if (manualCount === 0) {
        alert('沒有找到手動標註的圖片');
    } else {
        console.log(`已選取 ${manualCount} 張手動標註的圖片`);
    }
}

// 選取自動標註的圖片
function selectAutoLabeled() {
    const filteredFiles = getFilteredFiles();
    let autoCount = 0;

    // 清除現有選擇
    selectedFiles.clear();

    // 遺歷所有已篩選的檔案，使用已載入的 label_source 資訊
    filteredFiles.forEach(file => {
        if (file.labeled && file.label_source === 'ai') {
            const fileIndex = currentFiles.indexOf(file);
            if (fileIndex >= 0) {
                selectedFiles.add(fileIndex);
                autoCount++;
            }
        }
    });

    renderFileList();
    updateSelectAllButton();
    updateSelectedStats();

    if (autoCount === 0) {
        alert('沒有找到自動標註的圖片');
    } else {
        console.log(`已選取 ${autoCount} 張自動標註的圖片`);
    }
}

// 更新全選按鈕文字
function updateSelectAllButton() {
    const btn = document.getElementById('btnSelectAll');
    const filteredFiles = getFilteredFiles();
    const filteredIndices = filteredFiles.map(file => currentFiles.indexOf(file));
    const allSelected = filteredIndices.length > 0 && filteredIndices.every(idx => selectedFiles.has(idx));

    btn.textContent = allSelected ? '☐ 取消全選' : '☑️ 全選';
}

// 更新選中數量顯示
function updateSelectedStats() {
    const selectedStatsDiv = document.getElementById('selectedStats');
    const selectedCountSpan = document.getElementById('selectedCount');

    if (selectedFiles.size > 0) {
        selectedCountSpan.textContent = selectedFiles.size;
        selectedStatsDiv.style.display = 'block';
    } else {
        selectedStatsDiv.style.display = 'none';
    }
}

// 顯示進度條
function showProgress(text = '處理中...', indeterminate = true) {
    const container = document.getElementById('progressContainer');
    const textSpan = document.getElementById('progressText');
    const percentSpan = document.getElementById('progressPercent');
    const bar = document.getElementById('progressBar');
    const barIndeterminate = document.getElementById('progressBarIndeterminate');

    container.style.display = 'block';
    textSpan.textContent = text;

    if (indeterminate) {
        // 不確定進度模式（動畫滑動）
        percentSpan.style.display = 'none';
        bar.style.display = 'none';
        barIndeterminate.style.display = 'block';
    } else {
        // 確定進度模式
        percentSpan.style.display = 'inline';
        percentSpan.textContent = '0%';
        bar.style.display = 'block';
        bar.style.width = '0%';
        barIndeterminate.style.display = 'none';
    }
}

// 更新進度條
function updateProgress(current, total, text = '處理中...') {
    const textSpan = document.getElementById('progressText');
    const percentSpan = document.getElementById('progressPercent');
    const bar = document.getElementById('progressBar');

    const percent = Math.round((current / total) * 100);
    textSpan.textContent = `${text} (${current}/${total})`;
    percentSpan.textContent = `${percent}%`;
    bar.style.width = `${percent}%`;
}

// 隱藏進度條
function hideProgress() {
    const container = document.getElementById('progressContainer');
    container.style.display = 'none';
}

// 批量刪除
async function batchDelete() {
    if (selectedFiles.size === 0) {
        alert('請先選擇要刪除的圖片');
        return;
    }

    if (!confirm(`確定要刪除 ${selectedFiles.size} 張圖片嗎？此操作無法復原！`)) {
        return;
    }

    const indicesToDelete = Array.from(selectedFiles).sort((a, b) => b - a); // 從後往前刪除
    let successCount = 0;
    let failCount = 0;

    showProgress('刪除中...');

    for (let i = 0; i < indicesToDelete.length; i++) {
        const index = indicesToDelete[i];
        const file = currentFiles[index];
        try {
            await axios.delete(`/api/annotate/image/${encodeURIComponent(file.name)}`);
            successCount++;
        } catch (error) {
            console.error(`刪除 ${file.name} 失敗:`, error);
            failCount++;
        }
        updateProgress(i + 1, indicesToDelete.length, '刪除中...');
    }

    hideProgress();

    // 從後往前移除檔案，避免索引錯亂
    for (const index of indicesToDelete) {
        currentFiles.splice(index, 1);
    }

    selectedFiles.clear();

    // 重新載入列表
    renderFileList();
    updateStats();
    updateSelectedStats();

    // 如果當前圖片被刪除，載入第一張
    if (currentIndex >= currentFiles.length) {
        if (currentFiles.length > 0) {
            loadImage(0);
        } else {
            currentIndex = -1;
            document.getElementById('canvasInfo').textContent = '未載入影像';
        }
    } else if (currentIndex >= 0) {
        loadImage(currentIndex);
    }

    alert(`批量刪除完成！
成功: ${successCount} 張
失敗: ${failCount} 張`);
}

// 批量反轉標記框類別（正常↔瑕疵）
async function batchSwapClass() {
    if (selectedFiles.size === 0) {
        alert('請先選擇要反轉類別的圖片');
        return;
    }

    if (!confirm(`確定要反轉 ${selectedFiles.size} 張圖片的所有標記框類別嗎？\n正常 ↔ 瑕疵`)) {
        return;
    }

    const indicesToSwap = Array.from(selectedFiles);
    let successCount = 0;
    let failCount = 0;
    let totalSwapped = 0;

    showProgress('反轉中...');

    for (let i = 0; i < indicesToSwap.length; i++) {
        const index = indicesToSwap[i];
        const file = currentFiles[index];
        
        try {
            // 讀取當前標註
            const response = await axios.get(`/api/annotate/annotations/${encodeURIComponent(file.name)}`);
            const imageData = response.data;
            
            if (imageData.annotations && imageData.annotations.length > 0) {
                // 反轉所有標記框的類別
                const swappedAnnotations = imageData.annotations.map(ann => ({
                    ...ann,
                    class: 1 - ann.class  // 0→1, 1→0
                }));
                
                // 需要取得圖片尺寸
                const img = new Image();
                await new Promise((resolve, reject) => {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = `/api/annotate/image/${encodeURIComponent(file.name)}`;
                });
                
                // 將 YOLO 格式轉換為像素座標格式（與前端一致）
                const pixelAnnotations = swappedAnnotations.map(ann => ({
                    class: ann.class,
                    x: (ann.x_center - ann.width / 2) * img.width,
                    y: (ann.y_center - ann.height / 2) * img.height,
                    width: ann.width * img.width,
                    height: ann.height * img.height
                }));
                
                // 保存反轉後的標註
                await axios.post('/api/annotate/save', {
                    filename: file.name,
                    annotations: pixelAnnotations,
                    image_width: img.width,
                    image_height: img.height
                });
                
                totalSwapped += swappedAnnotations.length;
                successCount++;
                
                // 更新本地快取（保持YOLO格式）
                file.annotations = swappedAnnotations;
            } else {
                // 沒有標註的圖片，跳過
                successCount++;
            }
        } catch (error) {
            console.error(`反轉 ${file.name} 失敗:`, error);
            failCount++;
        }
        
        updateProgress(i + 1, indicesToSwap.length, '反轉中...');
    }

    hideProgress();

    // 重新載入列表和當前圖片
    await loadFileList();
    if (currentIndex >= 0 && currentIndex < currentFiles.length) {
        loadImage(currentIndex);
    }

    alert(`批量反轉完成！
成功: ${successCount} 張圖片
失敗: ${failCount} 張圖片
反轉標記框: ${totalSwapped} 個`);
}

// 匯出資料集
async function exportDataset() {
    try {
        // 如果有選中的檔案，只匯出選中的；否則匯出所有已標註的
        let filesToExport = [];
        if (selectedFiles.size > 0) {
            // 收集選中檔案的名稱
            selectedFiles.forEach(index => {
                if (index >= 0 && index < currentFiles.length) {
                    const file = currentFiles[index];
                    if (file.labeled) {  // 只匯出已標註的
                        filesToExport.push(file.name);
                    }
                }
            });
            
            if (filesToExport.length === 0) {
                alert('選中的圖片中沒有已標註的圖片！');
                return;
            }
        }
        
        const response = await axios.post('/api/annotate/export', {
            files: filesToExport.length > 0 ? filesToExport : null
        });
        
        const message = filesToExport.length > 0 
            ? `資料集匯出成功！\n已選中: ${filesToExport.length} 張\n已匯出: ${response.data.exported} 張\n輸出目錄: ${response.data.output_dir}`
            : `資料集匯出成功！\n已標註: ${response.data.exported} 張\n輸出目錄: ${response.data.output_dir}`;
        
        alert(message);
    } catch (error) {
        console.error('匯出失敗:', error);
        alert('匯出失敗: ' + (error.response?.data?.error || error.message));
    }
}

// 擷取影格
async function extractFrames() {
    const interval = prompt('擷取間隔（秒）：', '2');
    const maxFrames = prompt('每個影片最大擷取數量：', '100');

    if (!interval || !maxFrames) return;

    const btn = document.getElementById('btnExtractFrames');
    btn.disabled = true;
    btn.textContent = '⏳ 擷取中...';

    try {
        const response = await axios.post('/api/annotate/extract_frames', {
            interval: parseInt(interval),
            max_frames: parseInt(maxFrames)
        });

        alert(`擷取完成！\n總共擷取: ${response.data.total_frames} 張影格\n處理影片: ${response.data.videos_processed} 個`);
        loadFileList();
    } catch (error) {
        console.error('擷取失敗:', error);
        alert('擷取失敗：' + (error.response?.data?.error || error.message));
    } finally {
        btn.disabled = false;
        btn.textContent = '📹 擷取影格';
    }
}

// 自動標註
let autoLabelAbortController = null;

async function autoLabel() {
    // 選擇模型
    const modelChoice = prompt('選擇自動標註模型：\n\n1 = YOLOv4 (舊模型，黑白圖片訓練)\n2 = YOLOv8 (COCO 預訓練，快速標註，邊界框精準)\n\n請輸入 1 或 2：', '2');
    if (modelChoice === null) return; // 使用者取消
    
    let modelType;
    if (modelChoice === '1') {
        modelType = 'yolov4';
    } else if (modelChoice === '2') {
        modelType = 'yolov8';
    } else {
        alert('無效的選擇！請輸入 1 或 2');
        return;
    }
    
    // YOLOv8 COCO 模型的額外說明
    if (modelType === 'yolov8') {
        const confirmCoco = confirm('YOLOv8 COCO 模型說明：\n\n' +
            '✅ 優點：\n' +
            '  • 80 個類別，通用物體檢測\n' +
            '  • 邊界框非常精準，貼合物體邊緣\n' +
            '  • 適合快速標註，減少手動微調\n\n' +
            '⚠️ 注意：\n' +
            '  • 所有檢測結果將標記為「正常」類別\n' +
            '  • 需手動調整為「瑕疵」類別（可使用批量反轉功能）\n\n' +
            '是否繼續？');
        if (!confirmCoco) return;
    }
    
    // 詢問信心閾值
    const thresholdInput = prompt('請輸入信心閾值 (0.0 - 1.0)，建議值：0.25', '0.25');
    if (thresholdInput === null) return; // 使用者取消
    
    const threshold = parseFloat(thresholdInput);
    if (isNaN(threshold) || threshold < 0 || threshold > 1) {
        alert('無效的閾值！請輸入 0.0 到 1.0 之間的數值');
        return;
    }
    
    // 詢問是否覆蓋已存在的標註
    const overwrite = confirm('是否覆蓋已存在的標註？\n\n點擊「確定」將覆蓋所有現有標註\n點擊「取消」將只處理未標註的圖片');

    const selectedFolder = document.getElementById('folderSelector').value;
    let targetImages = null;
    let folderText = '';

    // 如果有選中的圖片，只對選中的圖片進行操作
    if (selectedFiles.size > 0) {
        targetImages = Array.from(selectedFiles).map(idx => currentFiles[idx].name);
        folderText = `選中的 ${targetImages.length} 張圖片`;
    } else {
        folderText = selectedFolder ? `資料夾「${selectedFolder}」` : '所有影像';
    }

    if (!confirm(`使用現有模型自動標註${folderText}？\n信心閾值：${threshold}\n${overwrite ? '將覆蓋現有標註' : '只處理未標註的圖片'}`)) return;

    const btn = document.getElementById('btnAutoLabel');
    btn.disabled = true;
    btn.textContent = '⏳ 標註中...';

    autoLabelAbortController = new AbortController();

    showProgress('自動標註中...', false);

    try {
        const requestData = targetImages
            ? { images: targetImages, confidence_threshold: threshold, overwrite: overwrite, model: modelType }
            : { folder: selectedFolder, confidence_threshold: threshold, overwrite: overwrite, model: modelType };

        console.log('自動標註請求數據:', requestData);

        // 發送請求，API 會立即返回 task_id
        const response = await axios.post('/api/annotate/auto_label',
            requestData,
            { signal: autoLabelAbortController.signal }
        );

        const taskId = response.data.task_id;
        if (!taskId) {
            throw new Error('未獲得任務 ID');
        }

        console.log('獲得任務 ID:', taskId);

        // 開始輪詢進度
        const pollProgress = () => {
            return new Promise((resolve, reject) => {
                const progressInterval = setInterval(async () => {
                    try {
                        const progressRes = await axios.get(`/api/progress/${taskId}`);
                        const { current, total, labeled_count, status, report_url, total_detections, error } = progressRes.data;

                        const percent = total > 0 ? Math.round((current / total) * 100) : 0;

                        // 更新進度條
                        const textSpan = document.getElementById('progressText');
                        const percentSpan = document.getElementById('progressPercent');
                        const bar = document.getElementById('progressBar');

                        textSpan.textContent = `🤖 自動標註中... (${current}/${total}, 已標註 ${labeled_count || 0} 張)`;
                        percentSpan.textContent = `${percent}%`;
                        percentSpan.style.display = 'inline';
                        bar.style.width = `${percent}%`;
                        bar.style.display = 'block';

                        if (status === 'completed') {
                            clearInterval(progressInterval);
                            resolve({
                                total_images: total,
                                total_detections: total_detections || 0,
                                report_url: report_url
                            });
                        } else if (status === 'error') {
                            clearInterval(progressInterval);
                            reject(new Error(error || '自動標註失敗'));
                        }
                    } catch (error) {
                        console.error('獲取進度失敗:', error);
                    }
                }, 500);
            });
        };

        // 等待任務完成
        const result = await pollProgress();

        hideProgress();

        const message = `自動標註完成！\n\n處理影像: ${result.total_images} 張\n偵測到: ${result.total_detections} 個目標\n\n是否檢視報告？`;

        if (confirm(message) && result.report_url) {
            window.open(result.report_url, '_blank');
        }

        loadFileList();
        if (currentIndex >= 0) {
            loadImage(currentIndex);
        }
    } catch (error) {
        hideProgress();
        if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
            alert('自動標註已中斷');
        } else {
            console.error('自動標註失敗:', error);
            alert('自動標註失敗：' + (error.response?.data?.error || error.message));
        }
    } finally {
        autoLabelAbortController = null;
        btn.disabled = false;
        btn.textContent = '🤖 自動標註';
        btn.onclick = autoLabel;
    }
}

// 偵測重複圖片
let detectDuplicatesAbortController = null;
let detectBlanksAbortController = null;

async function detectDuplicates() {
    const selectedFolder = document.getElementById('folderSelector').value;
    let targetImages = null;
    let folderText = '';

    // 如果有選中的圖片，只對選中的圖片進行操作
    if (selectedFiles.size > 0) {
        targetImages = Array.from(selectedFiles).map(idx => currentFiles[idx].name);
        folderText = `選中的 ${targetImages.length} 張圖片`;
    } else {
        folderText = selectedFolder ? `資料夾「${selectedFolder}」` : '所有資料夾';
    }

    const threshold = prompt(`偵測${folderText}的重複圖片\n\n相似度閾值 (0-64, 建議5)：`, '5');
    if (!threshold) return;

    const btn = document.getElementById('btnDetectDuplicates');
    btn.disabled = true;
    btn.textContent = '⏳ 偵測中... (點擊中斷)';
    btn.onclick = () => {
        if (detectDuplicatesAbortController) {
            detectDuplicatesAbortController.abort();
            btn.textContent = '⏸️ 中斷中...';
        }
    };

    detectDuplicatesAbortController = new AbortController();

    showProgress('🔍 偵測重複圖片中...', false);

    // 開始輪詢進度的函數
    let duplicateProgressInterval = null;
    const startDuplicateProgress = (taskId) => {
        duplicateProgressInterval = setInterval(async () => {
            try {
                const response = await axios.get(`/api/progress/${taskId}`);
                const { current, total, duplicate_count } = response.data;
                const percent = Math.round((current / total) * 100);

                // 更新進度條
                const textSpan = document.getElementById('progressText');
                const percentSpan = document.getElementById('progressPercent');
                const bar = document.getElementById('progressBar');

                textSpan.textContent = `🔍 偵測重複圖片中... (${current}/${total}, 找到 ${duplicate_count || 0} 張)`;
                percentSpan.textContent = `${percent}%`;
                percentSpan.style.display = 'inline';
                bar.style.width = `${percent}%`;
                bar.style.display = 'block';

                if (response.data.status === 'completed') {
                    clearInterval(duplicateProgressInterval);
                }
            } catch (error) {
                console.error('獲取進度失敗:', error);
            }
        }, 500);
    };

    try {
        const requestData = {
            threshold: parseInt(threshold)
        };

        if (targetImages) {
            requestData.images = targetImages;
        } else {
            requestData.folder = selectedFolder;
        }

        const responsePromise = axios.post('/api/annotate/detect-duplicates',
            requestData,
            { signal: detectDuplicatesAbortController.signal }
        );

        // 等待一小段時間讓後端建立 task_id
        await new Promise(resolve => setTimeout(resolve, 100));

        // 先嘗試獲取 task_id 開始輪詢
        let taskIdObtained = false;
        const checkTaskId = setInterval(async () => {
            if (taskIdObtained) return;

            try {
                const partialResponse = await Promise.race([
                    responsePromise,
                    new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 50))
                ]);

                if (partialResponse && partialResponse.data && partialResponse.data.task_id) {
                    taskIdObtained = true;
                    clearInterval(checkTaskId);
                    startDuplicateProgress(partialResponse.data.task_id);
                }
            } catch (e) {
                // Response not ready yet, continue checking
            }
        }, 200);

        const response = await responsePromise;

        clearInterval(checkTaskId);
        if (duplicateProgressInterval) {
            clearInterval(duplicateProgressInterval);
            duplicateProgressInterval = null;
        }

        // 如果是後台處理模式，持續輪詢直到完成
        if (response.data.processing && response.data.task_id) {
            const finalTaskId = response.data.task_id;

            // 開始輪詢（如果還沒開始）
            if (!duplicateProgressInterval) {
                startDuplicateProgress(finalTaskId);
            }

            // 等待處理完成
            const waitForCompletion = setInterval(async () => {
                try {
                    const progressRes = await axios.get(`/api/progress/${finalTaskId}`);
                    if (progressRes.data.status === 'completed') {
                        clearInterval(waitForCompletion);
                        if (duplicateProgressInterval) {
                            clearInterval(duplicateProgressInterval);
                            duplicateProgressInterval = null;
                        }

                        hideProgress();

                        // 重新啟用按鈕
                        const dupBtn = document.getElementById('btnDetectDuplicates');
                        detectDuplicatesAbortController = null;
                        dupBtn.disabled = false;
                        dupBtn.textContent = '🔍 偵測重複圖片';
                        dupBtn.onclick = detectDuplicates;

                        // 調試信息
                        console.log('偵測完成，report_url:', progressRes.data.report_url);
                        console.log('完整響應:', progressRes.data);

                        // 從進度中獲取統計資料
                        const stats = progressRes.data.stats || {
                            total_files: progressRes.data.total || 0,
                            unique_files: 0,
                            total_duplicates: progressRes.data.duplicate_count || 0,
                            duplicate_groups: 0
                        };

                        // 優先使用 report_url 的存在來判斷是否有結果
                        const hasResults = progressRes.data.report_url && progressRes.data.report_url.length > 0;
                        const totalDuplicates = stats.total_duplicates || 0;

                        if (!hasResults && totalDuplicates === 0) {
                            alert('沒有找到重複圖片！');
                            return;
                        }

                        // 立即打開報告
                        if (progressRes.data.report_url) {
                            const reportWindow = window.open(progressRes.data.report_url, '_blank');
                            if (!reportWindow) {
                                alert('報告已生成，但瀏覽器阻止了彈窗。\n請允許彈窗或手動打開：' + progressRes.data.report_url);
                            } else {
                                const message = `找到重複圖片！\n\n` +
                                    `總圖片: ${stats.total_files}\n` +
                                    `唯一圖片: ${stats.unique_files || 0}\n` +
                                    `重複圖片: ${totalDuplicates}\n\n` +
                                    `報告已在新分頁開啟，請手動選擇要刪除的圖片`;
                                alert(message);
                            }
                        } else {
                            alert('處理完成但未生成報告URL');
                        }
                    }
                } catch (error) {
                    console.error('檢查完成狀態失敗:', error);
                }
            }, 1000);

            return;
        }

        const { stats, groups, report_url, task_id } = response.data;

        hideProgress();

        // 重啟按鈕
        const dupBtn = document.getElementById('btnDetectDuplicates');
        detectDuplicatesAbortController = null;
        dupBtn.disabled = false;
        dupBtn.textContent = '🔍 偵測重複圖片';
        dupBtn.onclick = detectDuplicates;

        // 優先判斷 report_url 是否存在，而非只看 total_duplicates
        const totalDuplicates = stats?.total_duplicates || 0;
        const hasReport = report_url && report_url.length > 0;

        if (!hasReport && totalDuplicates === 0) {
            alert('沒有找到重複圖片！');
            return;
        }

        // 顯示結果並檢視報告
        const message = `找到重複圖片！\n\n` +
            `總圖片: ${stats.total_files}\n` +
            `唯一圖片: ${stats.unique_files}\n` +
            `重複圖片: ${stats.total_duplicates}\n\n` +
            `請在報告中手動選擇要刪除的圖片`;

        alert(message);
        if (report_url) {
            window.open(report_url, '_blank');
        }
    } catch (error) {
        hideProgress();
        // 清除進度輪詢
        if (typeof duplicateProgressInterval !== 'undefined' && duplicateProgressInterval) {
            clearInterval(duplicateProgressInterval);
            duplicateProgressInterval = null;
        }
        // 重啟按鈕
        const dupBtn = document.getElementById('btnDetectDuplicates');
        detectDuplicatesAbortController = null;
        dupBtn.disabled = false;
        dupBtn.textContent = '🔍 偵測重複圖片';
        dupBtn.onclick = detectDuplicates;

        if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
            alert('偵測已中斷');
        } else {
            console.error('偵測失敗:', error);
            alert('偵測失敗：' + (error.response?.data?.error || error.message));
        }
    }
}

// 偵測空白圖片
async function detectBlanks() {
    const selectedFolder = document.getElementById('folderSelector').value;
    let targetImages = null;
    let folderText = '';

    // 如果有選中的圖片，只對選中的圖片進行操作
    if (selectedFiles.size > 0) {
        targetImages = Array.from(selectedFiles).map(idx => currentFiles[idx].name);
        folderText = `選中的 ${targetImages.length} 張圖片`;
    } else {
        folderText = selectedFolder ? `資料夾「${selectedFolder}」` : '所有資料夾';
    }

    const threshold = prompt(`偵測${folderText}的空白圖片\n\n標準差閾值 (建議25)：`, '25');
    if (!threshold) return;

    const btn = document.getElementById('btnDetectBlanks');
    btn.disabled = true;
    btn.textContent = '⏳ 偵測中... (點擊中斷)';
    btn.onclick = () => {
        if (detectBlanksAbortController) {
            detectBlanksAbortController.abort();
            btn.textContent = '⏸️ 中斷中...';
        }
    };

    detectBlanksAbortController = new AbortController();

    showProgress('⚪ 偵測空白圖片中...', false);  // 使用確定進度模式

    try {
        const requestData = {
            std_threshold: parseFloat(threshold)
        };

        if (targetImages) {
            requestData.images = targetImages;
        } else {
            requestData.folder = selectedFolder;
        }

        // 發送請求（不等待完成）
        const responsePromise = axios.post('/api/annotate/detect-blanks',
            requestData,
            { signal: detectBlanksAbortController.signal }
        );

        // 等待一小段時間讓後端創建 task_id
        await new Promise(resolve => setTimeout(resolve, 100));

        // 開始輪詢進度（使用臨時的定期檢查直到獲得task_id）
        let progressInterval = null;
        let taskIdObtained = false;

        const startProgressPolling = () => {
            progressInterval = setInterval(async () => {
                try {
                    // 先嘗試從已完成的請求獲取task_id
                    if (!taskIdObtained) {
                        const checkResponse = await Promise.race([
                            responsePromise,
                            new Promise((_, reject) => setTimeout(() => reject('timeout'), 50))
                        ]).catch(() => null);

                        if (checkResponse && checkResponse.data.task_id) {
                            taskIdObtained = true;
                            const taskId = checkResponse.data.task_id;

                            // 開始正式輪詢
                            const pollProgress = setInterval(async () => {
                                try {
                                    const progResponse = await axios.get(`/api/progress/${taskId}`);
                                    const { current, total, blank_count } = progResponse.data;
                                    const percent = Math.round((current / total) * 100);

                                    const textSpan = document.getElementById('progressText');
                                    const percentSpan = document.getElementById('progressPercent');
                                    const bar = document.getElementById('progressBar');

                                    textSpan.textContent = `⚪ 偵測空白圖片中... (${current}/${total}, 找到 ${blank_count} 張)`;
                                    percentSpan.textContent = `${percent}%`;
                                    percentSpan.style.display = 'inline';
                                    bar.style.width = `${percent}%`;
                                    bar.style.display = 'block';

                                    if (progResponse.data.status === 'completed') {
                                        clearInterval(pollProgress);
                                        clearInterval(progressInterval);
                                    }
                                } catch (error) {
                                    console.error('獲取進度失敗:', error);
                                }
                            }, 300);

                            clearInterval(progressInterval);
                            progressInterval = pollProgress;
                        }
                    }
                } catch (error) {
                    // 忽略
                }
            }, 200);
        };

        startProgressPolling();

        const response = await responsePromise;

        // 清除進度輪詢
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }

        // 如果是後台處理模式，持續輪詢直到完成
        if (response.data.processing && response.data.task_id) {
            const finalTaskId = response.data.task_id;

            // 等待處理完成
            const waitForCompletion = setInterval(async () => {
                try {
                    const progressRes = await axios.get(`/api/progress/${finalTaskId}`);
                    const { current, total, blank_count, status } = progressRes.data;
                    const percent = Math.round((current / total) * 100);

                    // 更新進度顯示
                    const textSpan = document.getElementById('progressText');
                    const percentSpan = document.getElementById('progressPercent');
                    const bar = document.getElementById('progressBar');

                    if (textSpan && percentSpan && bar) {
                        textSpan.textContent = `⚪ 偵測空白圖片中... (${current}/${total}, 找到 ${blank_count || 0} 張)`;
                        percentSpan.textContent = `${percent}%`;
                        percentSpan.style.display = 'inline';
                        bar.style.width = `${percent}%`;
                        bar.style.display = 'block';
                    }

                    if (status === 'completed') {
                        clearInterval(waitForCompletion);
                        hideProgress();

                        // 重新啟用按鈕
                        detectBlanksAbortController = null;
                        btn.disabled = false;
                        btn.textContent = '⚪ 偵測空白圖片';
                        btn.onclick = detectBlanks;

                        // 調試信息 - 顯示完整的響應數據
                        console.log('偵測完成，完整響應:', progressRes.data);
                        console.log('report_url:', progressRes.data.report_url);

                        // 立即打開報告
                        const reportUrl = progressRes.data.report_url;
                        if (reportUrl) {
                            const reportWindow = window.open(reportUrl, '_blank');
                            if (!reportWindow) {
                                alert('報告已生成，但瀏覽器阻止了彈窗。\n請允許彈窗或手動打開：' + reportUrl);
                            } else {
                                // 顯示完成訊息
                                const message = `偵測完成！\n\n總共檢查: ${total} 張\n空白圖片: ${blank_count || 0} 張\n\n報告已在新分頁開啟`;
                                alert(message);
                            }
                        } else {
                            alert(`偵測完成！\n\n總共檢查: ${total} 張\n空白圖片: ${blank_count || 0} 張\n\n但未生成報告URL\n\n響應數據: ${JSON.stringify(progressRes.data)}`);
                        }
                    }
                } catch (error) {
                    console.error('檢查完成狀態失敗:', error);
                    clearInterval(waitForCompletion);
                    hideProgress();
                    // 重新啟用按鈕
                    detectBlanksAbortController = null;
                    btn.disabled = false;
                    btn.textContent = '⚪ 偵測空白圖片';
                    btn.onclick = detectBlanks;
                    alert('輪詢進度失敗：' + error.message);
                }
            }, 500);

            return;
        }

        const { blank_count, total_files, space_saved_mb, blank_images, folder, report_url, task_id } = response.data;

        hideProgress();

        // 重啟按鈕
        detectBlanksAbortController = null;
        btn.disabled = false;
        btn.textContent = '⚪ 偵測空白圖片';
        btn.onclick = detectBlanks;

        if (blank_count === 0) {
            alert(`沒有找到空白圖片！\n\n範圍: ${folder}`);
            return;
        }

        // 顯示結果並檢視報告
        const viewMessage = `找到空白圖片！\n\n` +
            `範圍: ${folder}\n` +
            `總圖片: ${total_files}\n` +
            `空白圖片: ${blank_count}\n` +
            `可節省空間: ${space_saved_mb.toFixed(2)} MB\n\n` +
            `請在報告中手動選擇要刪除的圖片`;

        alert(viewMessage);
        if (report_url) {
            window.open(report_url, '_blank');
        }
    } catch (error) {
        hideProgress();
        // 清除空白偵測的進度輪詢
        if (typeof progressInterval !== 'undefined' && progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
        // 重啟按鈕
        detectBlanksAbortController = null;
        btn.disabled = false;
        btn.textContent = '⚪ 偵測空白圖片';
        btn.onclick = detectBlanks;

        if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
            alert('偵測已中斷');
        } else {
            console.error('偵測失敗:', error);
            alert('偵測失敗：' + (error.response?.data?.error || error.message));
        }
    }
}

// 過濾極端標記框
async function filterExtremeBoxes() {
    let targetImages = null;
    let folderText = '';

    // 檢查是否有選中的圖片
    if (selectedFiles.size > 0) {
        targetImages = Array.from(selectedFiles).map(idx => currentFiles[idx].name);
        folderText = `選中的 ${targetImages.length} 張圖片`;
    } else {
        folderText = selectedFolder ? `資料夾「${selectedFolder}」` : '所有資料夾';
    }

    const params = prompt(
        `過濾${folderText}的極端尺寸標記框\n\n格式: 最小尺寸,最大尺寸 (像素)\n建議: 50,800 (正常糖果約 350x350)`,
        '50,800'
    );
    if (!params) return;

    const [minSize, maxSize] = params.split(',').map(s => parseInt(s.trim()));
    if (isNaN(minSize) || isNaN(maxSize) || minSize <= 0 || maxSize <= minSize) {
        alert('無效的尺寸範圍！請輸入格式：最小值,最大值');
        return;
    }

    if (!confirm(`確認過濾標記框？\n範圍：${minSize}~${maxSize} 像素\n操作前會自動備份`)) {
        return;
    }

    const btn = document.getElementById('btnFilterExtremeBoxes');
    btn.disabled = true;
    btn.textContent = '⏳ 過濾中...';

    showProgress('🔷 過濾極端標記框中...', true);

    try {
        const requestData = {
            min_size: minSize,
            max_size: maxSize
        };

        if (targetImages) {
            requestData.images = targetImages;
        } else {
            requestData.folder = selectedFolder;
        }

        const response = await axios.post('/api/annotate/filter-extreme-boxes', requestData);

        hideProgress();

        const result = response.data;
        let message = `✅ 過濾完成！\n\n`;
        message += `📊 統計：\n`;
        message += `- 處理檔案：${result.modified_files}/${result.total_files}\n`;
        message += `- 過濾標記框：${result.filtered_boxes}/${result.total_boxes}\n`;
        if (result.backup_path) {
            message += `\n💾 備份位置：${result.backup_path}`;
        }

        alert(message);

        // 刷新當前圖片（如果有）
        if (currentIndex >= 0 && files[currentIndex]) {
            await loadImage(currentIndex);
        }

    } catch (error) {
        hideProgress();
        if (axios.isCancel(error)) {
            alert('⏸️ 操作已中斷');
        } else {
            console.error('過濾極端標記框失敗:', error);
            alert(`❌ 過濾失敗：${error.response?.data?.error || error.message}`);
        }
    } finally {
        btn.disabled = false;
        btn.textContent = '🔷 過濾極端標記框';
    }
}

// 全域函式：供報告視窗呼叫刪除圖片
window.deleteImagesFromReport = async function (filenames) {
    if (!filenames || filenames.length === 0) return;

    try {
        await batchDeleteImages(filenames);
        // 重新載入檔案列表
        await loadFileList();
        if (currentIndex >= 0 && currentIndex < currentFiles.length) {
            loadImage(currentIndex);
        }
    } catch (error) {
        console.error('刪除失敗:', error);
    }
};

// 跨窗口通訊 - 監聽來自報告頁面的刪除請求
if (typeof BroadcastChannel !== 'undefined') {
    const reportChannel = new BroadcastChannel('candy_report_channel');
    reportChannel.onmessage = (event) => {
        console.log('收到報告頁面訊息:', event.data);
        if (event.data.type === 'delete_images' && event.data.filenames) {
            window.deleteImagesFromReport(event.data.filenames);
        }
    };
    console.log('✅ BroadcastChannel 已啟動，監聽報告頁面');
} else {
    console.warn('⚠️ 瀏覽器不支援 BroadcastChannel');
}

// 批次刪除圖片
async function batchDeleteImages(filenames) {
    if (!filenames || filenames.length === 0) return;

    try {
        const response = await axios.post('/api/annotate/delete-images', {
            filenames: filenames
        });

        alert(`刪除完成！\n成功刪除: ${response.data.deleted} 張圖片`);

        // 重新載入檔案列表
        await loadFileList();

        // 如果當前顯示的圖片被刪除了，載入下一張
        if (currentIndex >= 0 && currentFiles.length > 0) {
            loadImage(Math.min(currentIndex, currentFiles.length - 1));
        }
    } catch (error) {
        console.error('批次刪除失敗:', error);
        alert('批次刪除失敗：' + (error.response?.data?.error || error.message));
    }
}

// 設置可拖動分隔條
function setupResizers() {
    // 左側分隔條
    const leftResizer = document.getElementById('leftResizer');
    const leftSidebar = document.getElementById('leftSidebar');

    // 右側分隔條
    const rightResizer = document.getElementById('rightResizer');
    const rightSidebar = document.getElementById('rightSidebar');

    // 從 localStorage 恢復上次的寬度
    const savedLeftWidth = localStorage.getItem('leftSidebarWidth');
    const savedRightWidth = localStorage.getItem('rightSidebarWidth');

    if (savedLeftWidth && leftSidebar) {
        leftSidebar.style.width = savedLeftWidth + 'px';
    }

    if (savedRightWidth && rightSidebar) {
        rightSidebar.style.width = savedRightWidth + 'px';
    }

    // 左側拖動邏輯
    if (leftResizer && leftSidebar) {
        let isResizingLeft = false;
        let startX = 0;
        let startWidth = 0;

        leftResizer.addEventListener('mousedown', function (e) {
            isResizingLeft = true;
            startX = e.clientX;
            startWidth = leftSidebar.offsetWidth;
            leftResizer.classList.add('resizing');
            e.preventDefault();
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'col-resize';
        });

        document.addEventListener('mousemove', function (e) {
            if (!isResizingLeft) return;
            const deltaX = e.clientX - startX;
            const newWidth = startWidth + deltaX;
            const minWidth = 150;
            const maxWidth = 500;

            if (newWidth >= minWidth && newWidth <= maxWidth) {
                leftSidebar.style.width = newWidth + 'px';
            }
        });

        document.addEventListener('mouseup', function () {
            if (isResizingLeft) {
                isResizingLeft = false;
                leftResizer.classList.remove('resizing');
                document.body.style.userSelect = '';
                document.body.style.cursor = '';

                // 保存當前寬度到 localStorage
                localStorage.setItem('leftSidebarWidth', leftSidebar.offsetWidth);
            }
        });
    }

    // 右側拖動邏輯
    if (rightResizer && rightSidebar) {
        let isResizingRight = false;
        let startX = 0;
        let startWidth = 0;

        rightResizer.addEventListener('mousedown', function (e) {
            isResizingRight = true;
            startX = e.clientX;
            startWidth = rightSidebar.offsetWidth;
            rightResizer.classList.add('resizing');
            e.preventDefault();
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'col-resize';
        });

        document.addEventListener('mousemove', function (e) {
            if (!isResizingRight) return;
            const deltaX = startX - e.clientX; // 注意右側是反向的
            const newWidth = startWidth + deltaX;
            const minWidth = 200;
            const maxWidth = 600;

            if (newWidth >= minWidth && newWidth <= maxWidth) {
                rightSidebar.style.width = newWidth + 'px';
            }
        });

        document.addEventListener('mouseup', function () {
            if (isResizingRight) {
                isResizingRight = false;
                rightResizer.classList.remove('resizing');
                document.body.style.userSelect = '';
                document.body.style.cursor = '';

                // 保存當前寬度到 localStorage
                localStorage.setItem('rightSidebarWidth', rightSidebar.offsetWidth);
            }
        });
    }
}

// 滑鼠滾輪縮放
function onMouseWheel(e) {
    e.preventDefault();

    if (!currentImage) return;

    // 取得滑鼠在畫布上的位置
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // 計算滑鼠在圖片上的相對位置（縮放前）
    const imgX = (mouseX - offsetX) / scale;
    const imgY = (mouseY - offsetY) / scale;

    // 調整縮放比例
    const zoomDelta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = scale * zoomDelta;

    // 限制縮放範圍
    if (newScale >= 0.1 && newScale <= 10) {
        scale = newScale;

        // 調整偏移量，使滑鼠位置保持不變
        offsetX = mouseX - imgX * scale;
        offsetY = mouseY - imgY * scale;

        renderCanvas();
    }
}

// ========== 預覽所有標記框功能 ==========

// 顯示預覽模態框
async function showPreviewModal() {
    const modal = document.getElementById('previewModal');
    const content = document.getElementById('previewContent');

    // 顯示載入中
    content.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 40px;">載入中...</div>';
    modal.classList.add('show');

    try {
        // 只顯示已選中的圖像
        const filesToShow = currentFiles.filter((f, index) => selectedFiles.has(index));

        if (filesToShow.length === 0) {
            content.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 40px;">請先選取要預覽的圖像</div>';
            return;
        }

        // 更新統計
        const labeled = filesToShow.filter(f => f.labeled).length;
        document.getElementById('previewTotal').textContent = filesToShow.length;
        document.getElementById('previewLabeled').textContent = labeled;
        document.getElementById('previewUnlabeled').textContent = filesToShow.length - labeled;

        // 生成預覽卡片
        const cards = await Promise.all(filesToShow.map(async (file, index) => {
            return createPreviewCard(file, index);
        }));

        content.innerHTML = cards.join('');

        // 等待 DOM 渲染完成後再繪製所有圖片
        setTimeout(() => {
            filesToShow.forEach((file, index) => {
                const imagePath = `/api/annotate/image/${encodeURIComponent(file.name)}`;
                const canvasId = `preview-canvas-${index}`;

                // 獲取標註
                axios.get(`/api/annotate/annotations/${encodeURIComponent(file.name)}`)
                    .then(response => {
                        const annotations = response.data.annotations || [];
                        drawPreviewWithAnnotations(canvasId, imagePath, annotations);
                    })
                    .catch(error => {
                        console.error(`無法載入 ${file.name} 的標註:`, error);
                        drawPreviewWithAnnotations(canvasId, imagePath, []);
                    });
            });
        }, 50);

        // 綁定點擊事件
        document.querySelectorAll('.preview-card').forEach((card, index) => {
            card.addEventListener('click', () => {
                closePreviewModal();
                const fileIndex = currentFiles.findIndex(f => f.name === filesToShow[index].name);
                if (fileIndex >= 0) {
                    loadImage(fileIndex);
                }
            });
        });
    } catch (error) {
        console.error('載入預覽失敗:', error);
        content.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #ef4444; padding: 40px;">載入失敗</div>';
    }
}

// 創建預覽卡片HTML
async function createPreviewCard(file, index) {
    const imagePath = `/api/annotate/image/${encodeURIComponent(file.name)}`;

    // 獲取標註信息
    let annotationCount = 0;
    let annotations = [];
    try {
        const response = await axios.get(`/api/annotate/annotations/${encodeURIComponent(file.name)}`);
        annotations = response.data.annotations || [];
        annotationCount = annotations.length;
    } catch (error) {
        console.error(`無法載入 ${file.name} 的標註:`, error);
    }

    const labelStatus = file.labeled ? 'labeled' : 'unlabeled';
    const labelText = file.labeled ? '✓ 已標註' : '○ 未標註';

    // 創建唯一的canvas ID
    const canvasId = `preview-canvas-${index}`;

    return `
        <div class="preview-card" data-index="${index}">
            <canvas id="${canvasId}" style="width: 100%; height: 200px; border-radius: 4px; background: rgba(0, 0, 0, 0.3);"></canvas>
            <div class="preview-info">
                <div class="preview-filename">${file.name}</div>
                <div>
                    <span class="preview-badge ${labelStatus}">${labelText}</span>
                    ${annotationCount > 0 ? `<span class="preview-badge count">${annotationCount} 個標記</span>` : ''}
                </div>
            </div>
        </div>
    `;
}

// 在預覽畫布上繪製圖片和標記框
function drawPreviewWithAnnotations(canvasId, imagePath, annotations) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
        // 設置canvas尺寸
        const containerWidth = canvas.offsetWidth;
        const containerHeight = 200;
        canvas.width = containerWidth;
        canvas.height = containerHeight;

        // 計算縮放以適應容器
        const scaleX = containerWidth / img.width;
        const scaleY = containerHeight / img.height;
        const scale = Math.min(scaleX, scaleY);

        const scaledWidth = img.width * scale;
        const scaledHeight = img.height * scale;
        const offsetX = (containerWidth - scaledWidth) / 2;
        const offsetY = (containerHeight - scaledHeight) / 2;

        // 清空畫布
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, containerWidth, containerHeight);

        // 繪製圖片
        ctx.drawImage(img, offsetX, offsetY, scaledWidth, scaledHeight);

        // 繪製標記框
        if (annotations && annotations.length > 0) {
            annotations.forEach(ann => {
                // YOLO格式轉換為像素座標
                const x_center = ann.x_center * img.width;
                const y_center = ann.y_center * img.height;
                const width = ann.width * img.width;
                const height = ann.height * img.height;

                const x = (x_center - width / 2) * scale + offsetX;
                const y = (y_center - height / 2) * scale + offsetY;
                const w = width * scale;
                const h = height * scale;

                // 繪製矩形框
                ctx.strokeStyle = ann.class === 0 ? '#10b981' : '#ef4444'; // 正常=綠色, 瑕疵=紅色
                ctx.lineWidth = 2;
                ctx.strokeRect(x, y, w, h);

                // 繪製類別標籤（根據開關決定是否顯示）
                if (showLabels) {
                    const label = ann.class === 0 ? '正常' : '瑕疵';
                    const labelText = ann.confidence ? `${label} ${(ann.confidence * 100).toFixed(0)}%` : label;
                    const labelWidth = ann.confidence ? 70 : 50;

                    ctx.fillStyle = ann.class === 0 ? '#10b981' : '#ef4444';
                    ctx.fillRect(x, y - 20, labelWidth, 20);
                    ctx.fillStyle = 'white';
                    ctx.font = '12px "Microsoft JhengHei", Arial';
                    ctx.fillText(labelText, x + 5, y - 6);
                }
            });
        }
    };

    img.onerror = () => {
        // 載入失敗時顯示錯誤
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ef4444';
        ctx.font = '14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('載入失敗', canvas.width / 2, canvas.height / 2);
    };

    img.src = imagePath;
}


// 關閉預覽模態框
function closePreviewModal() {
    const modal = document.getElementById('previewModal');
    modal.classList.remove('show');
}

// 按 Esc 鍵關閉預覽
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('previewModal');
        if (modal.classList.contains('show')) {
            closePreviewModal();
        }
    }
});

// ========== 結束預覽功能 ==========

// ========== 檔案列表框選功能 ==========

function onFileListMouseDown(e) {
    // 只在檔案列表空白區域開始框選
    if (e.target.id !== 'fileList' && !e.target.classList.contains('file-list')) {
        return;
    }
    
    isDragSelecting = true;
    const fileList = document.getElementById('fileList');
    const rect = fileList.getBoundingClientRect();
    
    dragSelectStart.x = e.clientX - rect.left + fileList.scrollTop;
    dragSelectStart.y = e.clientY - rect.top + fileList.scrollTop;
    dragSelectCurrent.x = dragSelectStart.x;
    dragSelectCurrent.y = dragSelectStart.y;
    
    // 創建選取框元素
    if (!dragSelectBox) {
        dragSelectBox = document.createElement('div');
        dragSelectBox.style.position = 'absolute';
        dragSelectBox.style.border = '2px solid #38bdf8';
        dragSelectBox.style.backgroundColor = 'rgba(56, 189, 248, 0.1)';
        dragSelectBox.style.pointerEvents = 'none';
        dragSelectBox.style.zIndex = '1000';
        fileList.style.position = 'relative';
        fileList.appendChild(dragSelectBox);
    }
    
    e.preventDefault();
}

function onFileListMouseMove(e) {
    if (!isDragSelecting) return;
    
    const fileList = document.getElementById('fileList');
    const rect = fileList.getBoundingClientRect();
    
    dragSelectCurrent.x = e.clientX - rect.left + fileList.scrollLeft;
    dragSelectCurrent.y = e.clientY - rect.top + fileList.scrollTop;
    
    // 更新選取框位置和大小
    const left = Math.min(dragSelectStart.x, dragSelectCurrent.x);
    const top = Math.min(dragSelectStart.y, dragSelectCurrent.y);
    const width = Math.abs(dragSelectCurrent.x - dragSelectStart.x);
    const height = Math.abs(dragSelectCurrent.y - dragSelectStart.y);
    
    if (dragSelectBox) {
        dragSelectBox.style.left = left + 'px';
        dragSelectBox.style.top = top + 'px';
        dragSelectBox.style.width = width + 'px';
        dragSelectBox.style.height = height + 'px';
        dragSelectBox.style.display = 'block';
    }
    
    // 檢測與檔案項目的碰撞
    updateDragSelection(left, top, width, height);
}

function onFileListMouseUp(e) {
    if (!isDragSelecting) return;
    
    isDragSelecting = false;
    
    // 移除選取框
    if (dragSelectBox) {
        dragSelectBox.style.display = 'none';
    }
    
    // 重新渲染列表以更新勾選狀態
    renderFileList();
    updateSelectedStats();
}

function updateDragSelection(boxLeft, boxTop, boxWidth, boxHeight) {
    const fileList = document.getElementById('fileList');
    const fileItems = fileList.querySelectorAll('.file-item');
    
    fileItems.forEach((item, index) => {
        const rect = item.getBoundingClientRect();
        const fileListRect = fileList.getBoundingClientRect();
        
        // 計算項目相對於檔案列表的位置
        const itemLeft = rect.left - fileListRect.left + fileList.scrollLeft;
        const itemTop = rect.top - fileListRect.top + fileList.scrollTop;
        const itemRight = itemLeft + rect.width;
        const itemBottom = itemTop + rect.height;
        
        const boxRight = boxLeft + boxWidth;
        const boxBottom = boxTop + boxHeight;
        
        // 檢測碰撞
        const isIntersecting = !(itemRight < boxLeft || 
                                 itemLeft > boxRight || 
                                 itemBottom < boxTop || 
                                 itemTop > boxBottom);
        
        if (isIntersecting) {
            // 找到對應的檔案索引
            const checkbox = item.querySelector('.file-checkbox');
            if (checkbox) {
                const fileIndex = parseInt(checkbox.dataset.index);
                selectedFiles.add(fileIndex);
                checkbox.checked = true;
            }
        }
    });
}

// ========== 結束檔案列表框選功能 ==========
