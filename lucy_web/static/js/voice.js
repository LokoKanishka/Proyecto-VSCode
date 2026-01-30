// Voice input controls
const voiceBtn = document.getElementById('voice-btn');
const wakeWordToggle = document.getElementById('wake-word-toggle');

let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let recordTimeout = null;
const MAX_RECORD_MS = 8000; // evitar grabaciones infinitas

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
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

        // Convert to base64 for consistent transport
        const arrayBuffer = await audioBlob.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);
        let binary = '';
        for (let i = 0; i < uint8Array.byteLength; i++) {
            binary += String.fromCharCode(uint8Array[i]);
        }
        const audioB64 = btoa(binary);

        lucySocket.emit('voice_input', {
            audio_b64: audioB64,
            mime: audioBlob.type || 'audio/webm'
        });
        
        updateStatus('Processing voice...', 'info');
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
    };
    
    mediaRecorder.start();
    recordTimeout = setTimeout(() => {
        if (isRecording) stopRecording();
    }, MAX_RECORD_MS);
    
    voiceBtn.classList.add('recording');
    voiceBtn.querySelector('span').textContent = '⏹️';
    updateStatus('Recording...', 'warning');
}

// Stop recording
function stopRecording() {
    if (mediaRecorder && isRecording) {
        isRecording = false;
        mediaRecorder.stop();
        if (recordTimeout) {
            clearTimeout(recordTimeout);
            recordTimeout = null;
        }
        
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

// Wake word toggle (auto rearm when server responde)
let autoListenEnabled = false;
wakeWordToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        updateStatus('Modo escucha continua habilitado', 'success');
        autoListenEnabled = true;
        if (!isRecording) startRecording();
    } else {
        updateStatus('Modo escucha continua deshabilitado', 'info');
        autoListenEnabled = false;
        if (isRecording) stopRecording();
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

// Rearme al recibir estados del servidor
if (window.lucySocket) {
    lucySocket.on('status', (data) => {
        const msg = (data && data.message || "").toLowerCase();
        const shouldRearm = autoListenEnabled && !isRecording && (
            msg.includes('voice turn completed') ||
            msg.includes('no speech detected')
        );
        if (shouldRearm) {
            startRecording();
        }
    });
}
