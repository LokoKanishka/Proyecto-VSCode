// Voice input controls
const voiceBtn = document.getElementById('voice-btn');
const wakeWordToggle = document.getElementById('wake-word-toggle');

let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

// Request microphone permission
async function initMicrophone() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        return stream;
    } catch (error) {
        console.error('Microphone access denied:', error);
        updateStatus('Microphone access denied', 'error');
        return null;
    }
}

// Start recording
async function startRecording() {
    const stream = await initMicrophone();
    if (!stream) return;
    
    isRecording = true;
    audioChunks = [];
    
    mediaRecorder = new MediaRecorder(stream);
    
    mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
    };
    
    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        
        // Send audio to server
        lucySocket.emit('voice_input', {
            audio: await audioBlob.arrayBuffer()
        });
        
        updateStatus('Processing voice...', 'info');
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
    };
    
    mediaRecorder.start();
    
    voiceBtn.classList.add('recording');
    voiceBtn.querySelector('span').textContent = '⏹️';
    updateStatus('Recording...', 'warning');
}

// Stop recording
function stopRecording() {
    if (mediaRecorder && isRecording) {
        isRecording = false;
        mediaRecorder.stop();
        
        voiceBtn.classList.remove('recording');
        voiceBtn.querySelector('span').textContent = '🎤';
    }
}

// Voice button click
voiceBtn.addEventListener('click', () => {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
});

// Wake word toggle
wakeWordToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        updateStatus('Wake word mode enabled', 'success');
        // TODO: Implement continuous listening
        console.log('Wake word mode: ON');
    } else {
        updateStatus('Wake word mode disabled', 'info');
        console.log('Wake word mode: OFF');
    }
});

// Mode buttons
const modeButtons = document.querySelectorAll('.mode-button');
modeButtons.forEach(button => {
    button.addEventListener('click', () => {
        modeButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        
        const mode = button.textContent.toLowerCase();
        updateStatus(`Mode: ${mode}`, 'info');
    });
});

// Export for use in other modules
window.voiceControls = {
    startRecording,
    stopRecording,
    isRecording: () => isRecording
};
