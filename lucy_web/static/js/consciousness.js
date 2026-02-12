// Consciousness Visualization - Real-time display of Lucy's consciousness state
// Mirrors dashboard.py aesthetics in web interface

// State configurations (matching dashboard.py)
const STATES = {
    'COHERENCE': { color: '#00f2ff', symbol: '💠', label: 'COHERENCE' },
    'PROCESSING': { color: '#ffaa00', symbol: '⚙️', label: 'PROCESSING' },
    'WAITING': { color: '#666666', symbol: '💤', label: 'WAITING' },
    'ERROR': { color: '#ff0000', symbol: '⚠️', label: 'ERROR' },
    'OFFLINE': { color: '#333333', symbol: '🌑', label: 'OFFLINE' }
};

// Listen for consciousness updates from server
if (typeof lucySocket !== 'undefined') {
    lucySocket.on('consciousness_update', (data) => {
        updateConsciousness(data);
    });
    
    // Request initial state on page load
    lucySocket.on('connect', () => {
        lucySocket.emit('request_consciousness');
    });
}

function updateConsciousness(data) {
    console.log('Consciousness update:', data);
    
    // Get state config
    const state = data.state || 'OFFLINE';
    const stateConfig = STATES[state] || STATES.OFFLINE;
    
    // Update state display
    const iconEl = document.getElementById('lucy-state-icon');
    const labelEl = document.getElementById('lucy-state-label');
    const panelEl = document.getElementById('consciousness-panel');
    
    if (iconEl) iconEl.textContent = stateConfig.symbol;
    if (labelEl) {
        labelEl.textContent = stateConfig.label;
        labelEl.style.color = stateConfig.color;
    }
    if (panelEl) {
        panelEl.style.borderColor = stateConfig.color;
        panelEl.style.boxShadow = `0 0 20px ${stateConfig.color}40`;
    }
    
    // Update metrics
    updateMetric('entropy', data.entropy || 0, stateConfig.color);
    updateMetric('activity', data.activity || 0, stateConfig.color);
    
    // Add thought to log
    if (data.last_thought) {
        addThoughtToLog(data.last_thought, data.timestamp);
    }
}

function updateMetric(metricName, value, color) {
    const fillEl = document.getElementById(`${metricName}-fill`);
    const valueEl = document.getElementById(`${metricName}-value`);
    
    if (fillEl) {
        fillEl.style.width = `${Math.min(value * 100, 100)}%`;
        fillEl.style.background = `linear-gradient(90deg, ${color}, ${color}80)`;
    }
    
    if (valueEl) {
        valueEl.textContent = value.toFixed(2);
    }
}

function addThoughtToLog(thought, timestamp) {
    const logEl = document.getElementById('consciousness-log');
    if (!logEl) return;
    
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    
    const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-time">[${time}]</span> ${escapeHtml(thought)}`;
    
    // Insert at top
    logEl.insertBefore(entry, logEl.firstChild);
    
    // Limit to 20 entries
    while (logEl.children.length > 20) {
        logEl.removeChild(logEl.lastChild);
    }
    
    // Fade in animation
    entry.style.opacity = '0';
    setTimeout(() => {
        entry.style.opacity = '1';
    }, 10);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Pulse animation (similar to dashboard.py)
function pulseAnimation() {
    const iconEl = document.getElementById('lucy-state-icon');
    if (!iconEl) return;
    
    iconEl.style.transform = 'scale(1.15)';
    iconEl.style.filter = 'brightness(1.3)';
    
    setTimeout(() => {
        iconEl.style.transform = 'scale(1.0)';
        iconEl.style.filter = 'brightness(1.0)';
    }, 400);
}

// Pulse every 2 seconds
setInterval(pulseAnimation, 2000);

// Export for debugging
window.consciousnessViz = {
    updateConsciousness,
    updateMetric,
    addThoughtToLog,
    STATES
};

console.log('✅ Consciousness visualization loaded');
