# Dual-Mode Voice and Text Conversations

This document explains the dual-mode functionality that allows seamless switching between voice and text conversations with dynamic control over voice output and transcript display.

## 🎯 Overview

The dual-mode system enables:
- **Voice Mode**: Full voice processing with speech-to-text and text-to-speech
- **Text Mode**: Pure text conversations without voice processing
- **Dynamic Mode Switching**: Switch between modes during conversation
- **Flexible Output Control**: Control whether to return voice, transcript, or both
- **Session Persistence**: Maintain conversation context across mode changes

## 🔧 Architecture

### Core Components

1. **DualModeServicePool**: Extended service pool with mode-specific configurations
2. **ConversationMode**: Configuration object defining conversation behavior
3. **Dual-Mode WebSocket Endpoint**: WebSocket with mode switching capabilities
4. **Text-Only Chat Endpoint**: Simple HTTP endpoint for pure text conversations

### Conversation Modes

```python
@dataclass
class ConversationMode:
    mode: Literal["voice", "text"] = "voice"
    return_voice: bool = True
    return_transcript: bool = True
    enable_interruptions: bool = True
```

## 🚀 Usage Examples

### 1. WebSocket Dual-Mode Connection

#### Voice Mode (Default)
```javascript
const ws = new WebSocket('ws://localhost:7860/ws/dual-mode?token=YOUR_TOKEN&agent_id=27');
```

#### Text Mode Only
```javascript
const ws = new WebSocket('ws://localhost:7860/ws/dual-mode?token=YOUR_TOKEN&agent_id=27&mode=text&return_voice=false');
```

#### Voice with Transcript
```javascript
const ws = new WebSocket('ws://localhost:7860/ws/dual-mode?token=YOUR_TOKEN&agent_id=27&mode=voice&return_transcript=true');
```

### 2. Mode Switching During Conversation

#### Switch to Text Mode
```javascript
ws.send(JSON.stringify({
    type: "mode_change",
    data: {
        mode: "text",
        return_voice: false,
        return_transcript: true
    }
}));
```

#### Switch to Voice Mode
```javascript
ws.send(JSON.stringify({
    type: "mode_change",
    data: {
        mode: "voice",
        return_voice: true,
        return_transcript: true
    }
}));
```

### 3. Sending Text Messages
```javascript
ws.send(JSON.stringify({
    type: "text_message",
    data: {
        text: "Hello, how are you today?"
    }
}));
```

### 4. HTTP Text-Only Chat

#### Simple Text Chat
```bash
curl -X POST http://localhost:7860/chat/text \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how can you help me?",
    "agent_id": 27
  }'
```

Response:
```json
{
  "response": "Hello! I'm here to help with your travel planning needs. What would you like to know?",
  "session_id": "uuid-session-id",
  "agent_id": 27,
  "timestamp": 1642345678.123
}
```

#### Continuing Text Conversation
```bash
curl -X POST http://localhost:7860/chat/text \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need help planning a trip to Paris",
    "agent_id": 27,
    "session_id": "uuid-session-id"
  }'
```

## 📡 WebSocket Message Types

### Incoming Messages (Client to Server)

#### Mode Change
```json
{
  "type": "mode_change",
  "data": {
    "mode": "text",
    "return_voice": false,
    "return_transcript": true,
    "enable_interruptions": false
  }
}
```

#### Text Message
```json
{
  "type": "text_message",
  "data": {
    "text": "Your message here"
  }
}
```

### Outgoing Messages (Server to Client)

#### Mode Info (Initial Connection)
```json
{
  "type": "mode_info",
  "data": {
    "mode": "voice",
    "return_voice": true,
    "return_transcript": true,
    "enable_interruptions": true
  }
}
```

#### Mode Changed Confirmation
```json
{
  "type": "mode_changed",
  "data": {
    "mode": "text",
    "return_voice": false,
    "return_transcript": true,
    "enable_interruptions": false
  }
}
```

#### Transcript
```json
{
  "type": "transcript",
  "data": {
    "text": "Hello, how are you?",
    "timestamp": 1642345678.123,
    "is_final": true,
    "source": "user"
  }
}
```

#### Assistant Response
```json
{
  "type": "assistant_response",
  "data": {
    "text": "I'm doing well, thank you! How can I help you today?",
    "timestamp": 1642345678.456
  }
}
```

## 🎮 Frontend Integration Examples

### React Hook for Dual-Mode Chat
```javascript
import { useState, useEffect, useRef } from 'react';

const useDualModeChat = (token, agentId) => {
  const [mode, setMode] = useState('voice');
  const [transcript, setTranscript] = useState('');
  const [responses, setResponses] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:7860/ws/dual-mode?token=${token}&agent_id=${agentId}&mode=${mode}`
    );

    ws.onopen = () => {
      setIsConnected(true);
      wsRef.current = ws;
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'mode_info':
        case 'mode_changed':
          setMode(data.data.mode);
          break;
        case 'transcript':
          setTranscript(data.data.text);
          break;
        case 'assistant_response':
          setResponses(prev => [...prev, data.data.text]);
          break;
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [token, agentId]);

  const switchMode = (newMode) => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({
        type: 'mode_change',
        data: {
          mode: newMode,
          return_voice: newMode === 'voice',
          return_transcript: true
        }
      }));
    }
  };

  const sendTextMessage = (text) => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({
        type: 'text_message',
        data: { text }
      }));
    }
  };

  return {
    mode,
    transcript,
    responses,
    isConnected,
    switchMode,
    sendTextMessage
  };
};
```

### Vue.js Component Example
```vue
<template>
  <div class="dual-mode-chat">
    <div class="mode-toggle">
      <button @click="switchMode('voice')" :class="{ active: mode === 'voice' }">
        Voice Mode
      </button>
      <button @click="switchMode('text')" :class="{ active: mode === 'text' }">
        Text Mode
      </button>
    </div>
    
    <div class="conversation">
      <div v-for="message in messages" :key="message.id" class="message">
        <div class="message-content">{{ message.text }}</div>
        <div class="message-meta">{{ message.type }} - {{ message.timestamp }}</div>
      </div>
    </div>
    
    <div v-if="mode === 'text'" class="text-input">
      <input 
        v-model="textMessage" 
        @keyup.enter="sendTextMessage"
        placeholder="Type your message..."
      />
      <button @click="sendTextMessage">Send</button>
    </div>
    
    <div v-if="mode === 'voice'" class="voice-controls">
      <button @click="startListening">Start Speaking</button>
      <div class="transcript">{{ currentTranscript }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DualModeChat',
  props: {
    token: String,
    agentId: Number
  },
  data() {
    return {
      mode: 'voice',
      messages: [],
      textMessage: '',
      currentTranscript: '',
      ws: null,
      isConnected: false
    };
  },
  mounted() {
    this.connectWebSocket();
  },
  methods: {
    connectWebSocket() {
      this.ws = new WebSocket(
        `ws://localhost:7860/ws/dual-mode?token=${this.token}&agent_id=${this.agentId}`
      );
      
      this.ws.onopen = () => {
        this.isConnected = true;
      };
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      };
      
      this.ws.onclose = () => {
        this.isConnected = false;
      };
    },
    
    handleMessage(data) {
      switch (data.type) {
        case 'mode_changed':
          this.mode = data.data.mode;
          break;
        case 'transcript':
          this.currentTranscript = data.data.text;
          if (data.data.is_final) {
            this.messages.push({
              id: Date.now(),
              text: data.data.text,
              type: 'user',
              timestamp: new Date().toLocaleTimeString()
            });
          }
          break;
        case 'assistant_response':
          this.messages.push({
            id: Date.now(),
            text: data.data.text,
            type: 'assistant',
            timestamp: new Date().toLocaleTimeString()
          });
          break;
      }
    },
    
    switchMode(newMode) {
      if (this.ws) {
        this.ws.send(JSON.stringify({
          type: 'mode_change',
          data: {
            mode: newMode,
            return_voice: newMode === 'voice',
            return_transcript: true
          }
        }));
      }
    },
    
    sendTextMessage() {
      if (this.textMessage.trim() && this.ws) {
        this.ws.send(JSON.stringify({
          type: 'text_message',
          data: { text: this.textMessage }
        }));
        this.textMessage = '';
      }
    },
    
    startListening() {
      // Implement voice listening logic
      console.log('Starting voice listening...');
    }
  }
};
</script>
```

## 🔧 Configuration Options

### WebSocket Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `token` | string | - | Authentication token |
| `agent_id` | integer | - | Agent ID to use |
| `mode` | string | "voice" | Initial mode ("voice" or "text") |
| `return_voice` | boolean | true | Whether to return voice output |
| `return_transcript` | boolean | true | Whether to return transcript |

### Mode Settings

| Setting | Description | Voice Mode | Text Mode |
|---------|-------------|------------|-----------|
| `mode` | Primary interaction mode | "voice" | "text" |
| `return_voice` | Enable audio output | true | false |
| `return_transcript` | Show text transcript | true | true |
| `enable_interruptions` | Allow interruptions | true | false |

## 🎯 Use Cases

### 1. Accessibility Support
- **Voice-first users**: Full voice interaction with optional transcript
- **Text-first users**: Pure text mode with no audio processing
- **Hearing impaired**: Voice input with text output only

### 2. Environment-Aware Switching
- **Quiet environments**: Switch to text mode
- **Hands-free scenarios**: Switch to voice mode
- **Mixed environments**: Voice with transcript for clarity

### 3. Multimodal Interfaces
- **Desktop applications**: Voice with visual transcript
- **Mobile apps**: Dynamic switching based on context
- **Web applications**: Toggle between modes based on user preference

### 4. Development and Testing
- **API testing**: Use text mode for rapid testing
- **Voice testing**: Use voice mode for audio pipeline testing
- **Integration testing**: Switch modes to test both pathways

## 🚀 Benefits

### For Users
- **Flexibility**: Choose the best interaction mode for current context
- **Accessibility**: Support for different accessibility needs
- **Context awareness**: Adapt to environment and situation
- **Seamless experience**: No interruption when switching modes

### For Developers
- **Single integration**: One WebSocket connection for both modes
- **Consistent API**: Same message format for both modes
- **Easy testing**: Simple text mode for development
- **Scalable**: Reduce audio processing load when not needed

## 📊 Performance Considerations

### Voice Mode
- **Higher resource usage**: STT, TTS, and audio processing
- **Higher latency**: Audio processing adds delay
- **Network bandwidth**: Audio data transfer

### Text Mode
- **Lower resource usage**: Only LLM processing
- **Lower latency**: Direct text processing
- **Minimal bandwidth**: Only text data transfer

### Dynamic Optimization
- **Automatic resource allocation**: Only activate needed services
- **Efficient switching**: Instant mode changes without reconnection
- **Session persistence**: Maintain context across mode changes

## 🔒 Security Considerations

### Authentication
- **Token-based authentication**: Required for all modes
- **Session validation**: Continuous session verification
- **Agent access control**: User can only access their agents

### Data Privacy
- **Session isolation**: Each session maintains separate context
- **Secure transmission**: WebSocket with TLS in production
- **No permanent storage**: Conversations not stored permanently

### Rate Limiting
- **Per-user limits**: Prevent abuse of text and voice endpoints
- **Session limits**: Maximum concurrent sessions per user
- **Resource quotas**: Prevent resource exhaustion

---

## 📝 Quick Start

1. **Connect with Voice Mode**:
   ```javascript
   const ws = new WebSocket('ws://localhost:7860/ws/dual-mode?token=YOUR_TOKEN&agent_id=27');
   ```

2. **Switch to Text Mode**:
   ```javascript
   ws.send(JSON.stringify({
     type: "mode_change",
     data: { mode: "text", return_voice: false, return_transcript: true }
   }));
   ```

3. **Send Text Message**:
   ```javascript
   ws.send(JSON.stringify({
     type: "text_message",
     data: { text: "Hello!" }
   }));
   ```

4. **Use HTTP Text Chat**:
   ```bash
   curl -X POST http://localhost:7860/chat/text \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"message": "Hello!", "agent_id": 27}'
   ```

This dual-mode system provides the flexibility you need for modern conversational AI applications with seamless switching between voice and text interactions.
