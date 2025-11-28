// WebSocket connection handler
const socket = io();

// Connection status
socket.on('connect', () => {
    console.log('Connected to Lucy Voice server');
    updateStatus('Connected', 'success');
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
