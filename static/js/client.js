let websocket = null;
let mediaRecorder = null;
let audioContext = null;
let isRecording = false;

// WebSocket connection
async function connect() {
    try {
        updateStatus('connecting', 'Connecting...');
        
        // Connect to your WebSocket server
        websocket = new WebSocket('ws://localhost:8765'); // Adjust port if needed
        
        websocket.onopen = function(event) {
            console.log('WebSocket connected');
            updateStatus('connected', 'Connected');
            document.getElementById('connectBtn').disabled = true;
            document.getElementById('disconnectBtn').disabled = false;
            document.getElementById('startRecordingBtn').disabled = false;
        };
        
        websocket.onmessage = function(event) {
            console.log('Received:', event.data);
            handleWebSocketMessage(event.data);
        };
        
        websocket.onclose = function(event) {
            console.log('WebSocket disconnected');
            updateStatus('disconnected', 'Disconnected');
            resetButtons();
        };
        
        websocket.onerror = function(error) {
            console.error('WebSocket error:', error);
            showError('WebSocket connection error');
            updateStatus('disconnected', 'Connection Error');
            resetButtons();
        };
        
    } catch (error) {
        console.error('Connection error:', error);
        showError('Failed to connect: ' + error.message);
        updateStatus('disconnected', 'Connection Failed');
    }
}

function disconnect() {
    if (websocket) {
        websocket.close();
        websocket = null;
    }
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    resetButtons();
}

async function startRecording() {
    try {
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                sampleRate: 16000, // Match your server's expected sample rate
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            } 
        });
        
        // Create audio context for processing
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000
        });
        
        // Set up MediaRecorder
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });
        
        mediaRecorder.ondataavailable = function(event) {
            if (event.data.size > 0 && websocket && websocket.readyState === WebSocket.OPEN) {
                // Convert to ArrayBuffer and send
                event.data.arrayBuffer().then(buffer => {
                    sendAudioData(buffer);
                });
            }
        };
        
        mediaRecorder.start(100); // Send data every 100ms
        isRecording = true;
        
        document.getElementById('startRecordingBtn').disabled = true;
        document.getElementById('stopRecordingBtn').disabled = false;
        
        addMessage('system', 'Recording started...');
        
    } catch (error) {
        console.error('Recording error:', error);
        showError('Failed to start recording: ' + error.message);
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    
    isRecording = false;
    document.getElementById('startRecordingBtn').disabled = false;
    document.getElementById('stopRecordingBtn').disabled = true;
    
    addMessage('system', 'Recording stopped.');
}

function sendAudioData(audioBuffer) {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        // Your server expects protobuf frames, but for simplicity 
        // this sends raw audio. You may need to adjust based on your serializer
        websocket.send(audioBuffer);
    }
}

function handleWebSocketMessage(data) {
    try {
        // Handle different types of messages from your server
        if (typeof data === 'string') {
            const message = JSON.parse(data);
            handleStructuredMessage(message);
        } else {
            // Handle binary audio data
            handleAudioResponse(data);
        }
    } catch (error) {
        console.error('Error handling message:', error);
    }
}

function handleStructuredMessage(message) {
    // Handle different message types based on your server's output
    if (message.type === 'transcript') {
        addMessage('user', message.text);
    } else if (message.type === 'response') {
        addMessage('bot', message.text);
    }
}

function handleAudioResponse(audioData) {
    // Play audio response from the bot
    if (audioContext) {
        audioContext.decodeAudioData(audioData.slice()).then(audioBuffer => {
            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioContext.destination);
            source.start();
        }).catch(error => {
            console.error('Audio playback error:', error);
        });
    }
}

function updateStatus(type, message) {
    const statusEl = document.getElementById('status');
    statusEl.className = `status ${type}`;
    statusEl.textContent = message;
}

function resetButtons() {
    document.getElementById('connectBtn').disabled = false;
    document.getElementById('disconnectBtn').disabled = true;
    document.getElementById('startRecordingBtn').disabled = true;
    document.getElementById('stopRecordingBtn').disabled = true;
}

function addMessage(sender, text) {
    const transcript = document.getElementById('transcript');
    const messageEl = document.createElement('div');
    messageEl.className = `message ${sender}-message`;
    
    const timestamp = new Date().toLocaleTimeString();
    messageEl.innerHTML = `<strong>${sender}:</strong> ${text} <small>(${timestamp})</small>`;
    
    transcript.appendChild(messageEl);
    transcript.scrollTop = transcript.scrollHeight;
}

function showError(message) {
    const errorEl = document.getElementById('error');
    errorEl.textContent = message;
    errorEl.style.display = 'block';
    setTimeout(() => {
        errorEl.style.display = 'none';
    }, 5000);
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    disconnect();
});
