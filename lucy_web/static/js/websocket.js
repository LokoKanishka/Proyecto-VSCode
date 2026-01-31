// WebSocket connection handler
const socket = io();

// Connection status
const statusHistory = [];
const MAX_HISTORY = 5;

function setBackendInfo(backend) {
    const el = document.getElementById('audio-backend');
    if (el) el.textContent = backend || '--';
    const warn = document.getElementById('audio-warning');
    if (warn) {
        warn.style.display = backend === 'none' ? 'block' : 'none';
    }
}

function updateMetricsPanel(metrics) {
    if (!metrics) return;
    document.getElementById('metric-asr').textContent = metrics.asr_ms ?? '—';
    document.getElementById('metric-llm').textContent = metrics.llm_ms ?? '—';
    document.getElementById('metric-total').textContent = metrics.total_ms ?? '—';
    document.getElementById('metric-audio').textContent = metrics.audio_duration_s
        ? Math.round(metrics.audio_duration_s * 1000)
        : '—';
}

function recordStatusHistory(entry) {
    if (!entry) return;
    statusHistory.unshift(entry);
    if (statusHistory.length > MAX_HISTORY) {
        statusHistory.pop();
    }
    renderStatusHistory();
}

function renderStatusHistory() {
    const container = document.getElementById('status-history');
    if (!container) return;
    container.innerHTML = statusHistory
        .map((entry) => {
            const time = new Date(entry.time).toLocaleTimeString();
            const metrics = entry.metrics
                ? ` (ASR ${entry.metrics.asr_ms ?? '—'} ms, LLM ${entry.metrics.llm_ms ?? '—'} ms)`
                : '';
            return `<div class="status-entry"><span class="status-time">${time}</span><span>${entry.message}${metrics}</span></div>`;
        })
        .join('');
}

function copyStatusHistory() {
    const text = statusHistory
        .map(
            (entry) =>
                `${new Date(entry.time).toLocaleTimeString()} - ${entry.message} ${
                    entry.metrics
                        ? `(ASR ${entry.metrics.asr_ms ?? '—'} ms, LLM ${entry.metrics.llm_ms ?? '—'} ms)`
                        : ''
                }`
        )
        .join('\n');
    navigator.clipboard.writeText(text).then(() => {
        updateStatus('Historial copiado al portapapeles.', 'success');
    });
}

function loadTtsMode() {
    const select = document.getElementById('tts-mode-select');
    const value = localStorage.getItem('lucy_tts_mode') || 'server';
    if (select) {
        select.value = value;
        select.addEventListener('change', () => {
            localStorage.setItem('lucy_tts_mode', select.value);
        });
    }
}

async function fetchHealth() {
    try {
        const res = await fetch('/api/health');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const backend = data.audio_backend || '--';
        setBackendInfo(backend);
        updateMetricsPanel(data.metrics);
        if (backend === 'none') {
            updateStatus('Sin backend de audio (instala soundfile o ffmpeg)', 'warning');
        }
        if (data.model) {
            const currentModelDisplay = document.getElementById('current-model');
            if (currentModelDisplay) currentModelDisplay.textContent = data.model;
        }
        recordStatusHistory({
            message: data.message || 'Health check',
            metrics: data.metrics,
            time: Date.now(),
        });
    } catch (err) {
        console.error('Health check failed', err);
        updateStatus('Health check failed', 'warning');
    }
}

socket.on('connect', () => {
    console.log('Connected to Lucy Voice server');
    updateStatus('Connected', 'success');
    fetchHealth();
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateStatus('Disconnected', 'error');
});

socket.on('error', (data) => {
    console.error('Socket error:', data);
    updateStatus(data.message || 'Error', 'error');
});

socket.on('status', (data) => {
    updateStatus(data.message, 'info');
    updateMetricsPanel(data.metrics);
    recordStatusHistory({
        message: data.message || 'Status update',
        metrics: data.metrics,
        time: Date.now(),
    });
});

function updateStatus(message, type = 'info') {
    const statusText = document.getElementById('status-text');
    const statusDot = document.querySelector('.status-dot');
    
    statusText.textContent = message;
    
    // Remove all status classes
    statusDot.classList.remove('status-success', 'status-error', 'status-warning');
    
    // Add appropriate class
    if (type === 'success') {
        statusDot.style.background = '#10b981';
    } else if (type === 'error') {
        statusDot.style.background = '#ef4444';
    } else if (type === 'warning') {
        statusDot.style.background = '#f59e0b';
    } else {
        statusDot.style.background = '#3b82f6';
    }
}

// Export for use in other modules
window.lucySocket = socket;
window.updateStatus = updateStatus;
window.setBackendInfo = setBackendInfo;
window.loadTtsMode = loadTtsMode;

loadTtsMode();
const copyHistoryBtn = document.getElementById('copy-history-btn');
if (copyHistoryBtn) {
    copyHistoryBtn.addEventListener('click', copyStatusHistory);
}

const busSparkline = document.getElementById('bus-sparkline');
let sparkRecords = [];

socket.on('bus_metrics_update', (payload) => {
    if (!payload || !payload.record) return;
    const { metrics } = payload.record;
    sparkRecords.push(metrics?.errors || 0);
    if (sparkRecords.length > 40) sparkRecords.shift();
    drawSparkline(sparkRecords);

    if (metrics?.errors > 0 && window.updateStatus) {
        updateStatus(`Errores recientes en el bus: ${metrics.errors}`, 'warning');
    }
});

socket.on('memory_event', (payload) => {
    if (!payload) return;
    updateStatus(`Memoria recuperada: ${payload.details || 'sin detalles'}`, 'info');
});

function drawSparkline(data) {
    if (!busSparkline || !busSparkline.getContext) return;
    const ctx = busSparkline.getContext('2d');
    const w = busSparkline.width;
    const h = busSparkline.height;
    ctx.clearRect(0, 0, w, h);
    if (!data.length) return;
    const max = Math.max(...data, 1);
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.beginPath();
    data.forEach((value, index) => {
        const x = (index / (data.length - 1 || 1)) * w;
        const y = h - (value / max) * h;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();
}
