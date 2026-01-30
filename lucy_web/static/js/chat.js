// Chat functionality
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const modelSelector = document.getElementById('model-selector');
const currentModelDisplay = document.getElementById('current-model');

// Load available models
async function loadModels() {
    try {
        const response = await fetch('/api/models');
        const data = await response.json();
        
        if (data.models && data.models.length > 0) {
            modelSelector.innerHTML = '';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelector.appendChild(option);
            });
            
            // Set current model display
            currentModelDisplay.textContent = data.models[0];
        }
    } catch (error) {
        console.error('Error loading models:', error);
        modelSelector.innerHTML = '<option>Error loading models</option>';
    }
}

// Model selection change
modelSelector.addEventListener('change', () => {
    const selectedModel = modelSelector.value;
    currentModelDisplay.textContent = selectedModel;
    
    // Notify server of model change
    lucySocket.emit('update_config', {
        ollama_model: selectedModel
    });
    
    updateStatus(`Model changed to ${selectedModel}`, 'success');
});

// Add message to chat
function addMessage(type, content) {
    // Remove welcome message if present
    const welcomeMsg = chatMessages.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = type === 'user' ? 'You' : 'Lucy';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    messageDiv.appendChild(header);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send message
function sendMessage() {
    const message = userInput.value.trim();
    
    if (!message) return;
    
    // Clear input
    userInput.value = '';
    userInput.style.height = 'auto';
    
    // Send to server
    lucySocket.emit('chat_message', { message });
    
    updateStatus('Thinking...', 'info');
}

// Listen for messages from server
lucySocket.on('message', (data) => {
    addMessage(data.type, data.content);
    
    if (data.type === 'assistant') {
        updateStatus('Ready', 'success');
        const autoSpeak = document.getElementById('auto-speak-toggle').checked;
        if (autoSpeak) {
            // Prefer server audio (tts_audio event). Fallback to browser TTS.
            speakText(data.content);
        }
    }
});

// Send button click
sendBtn.addEventListener('click', sendMessage);

// Enter key to send (Shift+Enter for new line)
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Auto-resize textarea
userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = userInput.scrollHeight + 'px';
});

// Text-to-speech function
function speakText(text) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'es-ES';
        utterance.rate = 1.0;
        window.speechSynthesis.speak(utterance);
    }
}

// Play server-provided TTS audio
lucySocket.on('tts_audio', (data) => {
    const autoSpeak = document.getElementById('auto-speak-toggle').checked;
    if (!autoSpeak) return;
    try {
        const audioB64 = data.audio_b64;
        const mime = data.mime || 'audio/wav';
        const byteString = atob(audioB64);
        const arrayBuffer = new ArrayBuffer(byteString.length);
        const bufferView = new Uint8Array(arrayBuffer);
        for (let i = 0; i < byteString.length; i++) {
            bufferView[i] = byteString.charCodeAt(i);
        }
        const blob = new Blob([bufferView], { type: mime });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.play().finally(() => URL.revokeObjectURL(url));
    } catch (err) {
        console.error('Error reproduciendo TTS:', err);
    }
});

// Initialize
loadModels();
