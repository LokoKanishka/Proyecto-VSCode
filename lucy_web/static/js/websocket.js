// WebSocket connection handler
const socket = io();

// Connection status
function setBackendInfo(backend) {
    const el = document.getElementById('audio-backend');
    if (el) el.textContent = backend || '--';
    const warn = document.getElementById('audio-warning');
    if (warn) {
        warn.style.display = (backend === 'none') ? 'block' : 'none';
    }
}

async function fetchHealth() {
    try {
        const res = await fetch('/api/health');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const backend = data.audio_backend || '--';
        setBackendInfo(backend);
        if (backend === 'none') {
            updateStatus('Sin backend de audio (instala soundfile o ffmpeg)', 'warning');
        }
        if (data.model) {
            const currentModelDisplay = document.getElementById('current-model');
            if (currentModelDisplay) currentModelDisplay.textContent = data.model;
        }
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
