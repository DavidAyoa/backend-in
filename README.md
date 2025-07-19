# Pipecat Voice Agent Server - Complete API Documentation

🎙️ **A production-ready voice agent backend built with FastAPI and Pipecat**

Supporting flexible conversation modes, multi-agent management, WebSocket/WebRTC transports, and scalable architecture for up to 25+ concurrent users.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository>
cd backend-in

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start server
uv run python main.py
# Server runs on http://localhost:7860
```

## 📋 Table of Contents

- [🔧 Configuration](#-configuration)
- [🌐 API Endpoints](#-api-endpoints)
  - [System & Health](#system--health)
  - [Authentication](#authentication)
  - [User Management](#user-management) 
  - [Agent Management](#agent-management)
  - [WebSocket Connections](#websocket-connections)
  - [Session Management](#session-management)
- [💬 WebSocket Communication](#-websocket-communication)
- [🔄 Transport Selection](#-transport-selection)
- [🎯 Conversation Modes](#-conversation-modes)
- [📝 Request/Response Examples](#-requestresponse-examples)
- [🏗️ Architecture](#️-architecture)
- [🐳 Deployment](#-deployment)
- [🔍 Testing](#-testing)

## 🔧 Configuration

### Environment Variables

```bash
# API Keys (Required)
OPENAI_API_KEY=sk-your-openai-key
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-credentials.json

# Server Configuration
HOST=0.0.0.0
PORT=7860
MAX_CONNECTIONS=25
CONNECTION_TIMEOUT=300

# Transport Settings
PREFERRED_TRANSPORT=websocket
ENABLE_INTERRUPTIONS=true
ENABLE_VAD=true

# Service Optimization
SERVICE_POOL_SIZE=5
ENABLE_SERVICE_REUSE=true

# Database
DB_PATH=data/users.db
```

## 🌐 API Endpoints

### System & Health

#### GET `/` - Service Information
```bash
curl -X GET "http://localhost:7860/"
```

**Response:**
```json
{
  "service": "Voice Agent Server",
  "version": "1.0.0",
  "status": "running",
  "message": "Voice Agent Server",
  "features": [
    "authentication",
    "user_management", 
    "agent_management",
    "voice_processing",
    "websocket_support",
    "multi_agent_conversations",
    "flexible_conversation_modes"
  ]
}
```

#### GET `/health` - Health Check
```bash
curl -X GET "http://localhost:7860/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1703123456.789,
  "server_info": {
    "active_connections": 3,
    "max_connections": 25,
    "capacity_usage": "12.0%"
  }
}
```

#### GET `/metrics` - Detailed Metrics
```bash
curl -X GET "http://localhost:7860/metrics"
```

**Response:**
```json
{
  "connections": {
    "total": 150,
    "active": 5,
    "peak": 18,
    "rejected": 2,
    "capacity_used": "20.0%"
  },
  "performance": {
    "avg_session_duration": "245.50s",
    "max_connections": 25,
    "connection_timeout": 300
  },
  "timestamp": 1703123456.789
}
```

#### POST `/connect` - Connection Availability
```bash
curl -X POST "http://localhost:7860/connect" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "ws_url": "ws://localhost:7860/ws",
  "status": "available",
  "capacity": {
    "available_slots": 20,
    "total_capacity": 25
  }
}
```

### Authentication

#### POST `/auth/register` - User Registration
```bash
curl -X POST "http://localhost:7860/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe", 
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

**Response:**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "role": "user",
    "status": "active",
    "email_verified": false,
    "created_at": "2024-01-15T10:30:00Z"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400
}
```

#### POST `/auth/login` - User Login
```bash
curl -X POST "http://localhost:7860/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email_or_username": "user@example.com",
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "role": "user",
    "last_login": "2024-01-15T15:45:00Z"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400
}
```

#### GET `/auth/profile` - Get User Profile
```bash
curl -X GET "http://localhost:7860/auth/profile" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "user",
  "status": "active",
  "email_verified": false,
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-15T15:45:00Z",
  "usage_stats": {
    "agents_created": 3,
    "sessions_completed": 45,
    "total_voice_minutes": 120.5
  }
}
```

#### GET `/auth/api-key` - Get API Key
```bash
curl -X GET "http://localhost:7860/auth/api-key" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "api_key": "ak_live_1234567890abcdef",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### POST `/auth/api-key/regenerate` - Regenerate API Key
```bash
curl -X POST "http://localhost:7860/auth/api-key/regenerate" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "api_key": "ak_live_newkey567890xyz",
  "message": "API key regenerated successfully",
  "warning": "Your old API key is now invalid"
}
```

### User Management

#### GET `/users/me` - Get Current User Info
```bash
curl -X GET "http://localhost:7860/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Agent Management

#### POST `/agents/` - Create Agent
```bash
curl -X POST "http://localhost:7860/agents/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "agent_name": "Customer Support Bot",
    "description": "Helpful customer service assistant",
    "system_prompt": "You are a friendly customer support agent. Help users with their questions professionally.",
    "voice_settings": {
      "language_code": "en-US",
      "voice_name": "en-US-Journey-F",
      "speaking_rate": 1.0,
      "pitch": 0.0
    }
  }'
```

**Response:**
```json
{
  "id": 101,
  "agent_name": "Customer Support Bot",
  "description": "Helpful customer service assistant", 
  "system_prompt": "You are a friendly customer support agent...",
  "voice_settings": {
    "language_code": "en-US",
    "voice_name": "en-US-Journey-F",
    "speaking_rate": 1.0,
    "pitch": 0.0
  },
  "status": "active",
  "created_at": "2024-01-15T16:20:00Z",
  "updated_at": "2024-01-15T16:20:00Z"
}
```

#### GET `/agents/` - List User's Agents
```bash
curl -X GET "http://localhost:7860/agents/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
[
  {
    "id": 101,
    "agent_name": "Customer Support Bot",
    "description": "Helpful customer service assistant",
    "status": "active",
    "created_at": "2024-01-15T16:20:00Z"
  },
  {
    "id": 102, 
    "agent_name": "Sales Assistant",
    "description": "Product recommendation expert",
    "status": "active", 
    "created_at": "2024-01-15T16:25:00Z"
  }
]
```

#### GET `/agents/{agent_id}` - Get Specific Agent
```bash
curl -X GET "http://localhost:7860/agents/101" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### PUT `/agents/{agent_id}` - Update Agent
```bash
curl -X PUT "http://localhost:7860/agents/101" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "agent_name": "Advanced Customer Support Bot",
    "system_prompt": "You are an expert customer support agent with deep product knowledge."
  }'
```

#### DELETE `/agents/{agent_id}` - Delete Agent
```bash
curl -X DELETE "http://localhost:7860/agents/101" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "message": "Agent deleted successfully"
}
```

#### GET `/agents/marketplace/browse` - Browse Public Agents
```bash
curl -X GET "http://localhost:7860/agents/marketplace/browse?category=customer-service&limit=10"
```

**Response:**
```json
[
  {
    "id": 501,
    "agent_name": "Multilingual Support Bot",
    "description": "Customer support in 20+ languages",
    "category": "customer-service",
    "tags": ["multilingual", "support", "professional"],
    "clone_count": 47,
    "creator_username": "aidev",
    "creator_name": "AI Developer",
    "created_at": "2024-01-10T08:00:00Z"
  }
]
```

### Session Management

#### GET `/session-manager/stats` - Session Statistics
```bash
curl -X GET "http://localhost:7860/session-manager/stats" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "session_manager": {
    "total_sessions": 1247,
    "active_sessions": 8,
    "peak_sessions": 23,
    "avg_session_duration": 187.5
  },
  "active_connections": 8,
  "server_capacity": 25,
  "capacity_usage": "32.0%"
}
```

#### GET `/session-manager/sessions` - Active Sessions
```bash
curl -X GET "http://localhost:7860/session-manager/sessions" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
[
  {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "connected_at": 1703125800.123,
    "last_activity": 1703126000.456,
    "duration": 200.333,
    "ip_address": "192.168.1.100"
  }
]
```

### Text Chat Endpoint

#### POST `/chat/text` - Text-only Chat
```bash
curl -X POST "http://localhost:7860/chat/text" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, I need help with my order",
    "agent_id": 101,
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Response:**
```json
{
  "response": "Hello! I'd be happy to help you with your order. Can you please provide your order number?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": 101,
  "timestamp": 1703126100.789
}
```

## 💬 WebSocket Communication

### WebSocket Endpoints

#### 1. Basic WebSocket Connection
```
ws://localhost:7860/ws
```

**Usage:**
```javascript
const ws = new WebSocket('ws://localhost:7860/ws');
```

#### 2. Flexible Mode WebSocket
```
ws://localhost:7860/ws/flexible?voice_input=true&text_input=true&voice_output=true&text_output=true&enable_interruptions=true
```

**Parameters:**
- `voice_input`: Enable voice input (default: true)
- `text_input`: Enable text input (default: true)  
- `voice_output`: Enable voice output (default: true)
- `text_output`: Enable text output (default: true)
- `enable_interruptions`: Allow interruptions (default: true)
- `agent_id`: Specific agent ID (optional)
- `token`: Authentication token (optional)

**Usage:**
```javascript
const params = new URLSearchParams({
  voice_input: 'true',
  text_input: 'false', 
  voice_output: 'false',
  text_output: 'true',
  agent_id: '101'
});

const ws = new WebSocket(`ws://localhost:7860/ws/flexible?${params}`);
```

#### 3. Authenticated WebSocket
```
ws://localhost:7860/ws/auth?token=your_jwt_token&agent_id=101
```

**Usage:**
```javascript
const ws = new WebSocket('ws://localhost:7860/ws/auth?token=eyJhbG...&agent_id=101');
```

### WebSocket Message Format

The server uses **ProtobufFrameSerializer** for efficient message serialization.

**Text Message (Client to Server):**
```javascript
// Using PipecatClient
client.sendClientMessage('user-text', { text: 'Hello, how can you help me?' });
```

**Audio Message (Client to Server):**
```javascript
// Using PipecatClient audio recording
await client.startRecording();
// ... user speaks ...
await client.stopRecording();
```

**Server Responses:**
- Text responses: `textMessage` event
- Audio responses: `audioMessage` event  
- Transcriptions: `transcription` event
- System messages: `message` event

### PipecatClient Integration

```javascript
import { PipecatClient } from '@pipecat-ai/client-js';
import { WebSocketTransport, ProtobufFrameSerializer } from '@pipecat-ai/websocket-transport';

// Create transport
const transport = new WebSocketTransport({
  serializer: new ProtobufFrameSerializer(),
});

// Create client
const client = new PipecatClient({
  transport: transport,
  enableMic: true, // Enable microphone for voice input
});

// Set up event handlers
client.on('connected', () => {
  console.log('Connected to voice agent');
});

client.on('textMessage', (text) => {
  console.log('Bot response:', text);
});

client.on('audioMessage', (audioData) => {
  // Play audio response
  const audio = new Audio(URL.createObjectURL(new Blob([audioData])));
  audio.play();
});

// Connect
const wsUrl = 'ws://localhost:7860/ws/flexible?voice_input=true&text_input=true&voice_output=true&text_output=true';
await client.connect({ ws_url: wsUrl });

// Send text message
client.sendClientMessage('user-text', { text: 'Hello!' });

// Start voice recording
await client.startRecording();
```

## 🔄 Transport Selection

The server supports **intelligent transport selection** allowing clients to choose between WebRTC and WebSocket connections based on their needs and capabilities.

### Quick Selection Examples

#### Using HTTP Headers
```bash
# Request WebRTC transport
curl -H "X-Transport-Preference: webrtc" http://localhost:7860/connect

# Request WebSocket transport
curl -H "X-Transport-Preference: websocket" http://localhost:7860/connect
```

#### JavaScript Client Selection
```javascript
// Method 1: Explicit preference header
const response = await fetch('/connect', {
  headers: { 'X-Transport-Preference': 'webrtc' }
});
const connectionInfo = await response.json();

// Method 2: User-Agent detection
navigator.userAgent += ' webrtc-enabled';
const ws = new WebSocket('ws://localhost:7860/ws');

// Method 3: Progressive enhancement with fallback
async function connectWithFallback() {
  try {
    // Try WebRTC first for better performance
    const connection = await connectWebRTC();
    return { transport: 'webrtc', connection };
  } catch (error) {
    // Fallback to WebSocket
    const connection = await connectWebSocket();
    return { transport: 'websocket', connection };
  }
}
```

### Transport Comparison

| Feature | WebSocket | WebRTC |
|---------|-----------|---------|
| **Latency** | Medium (100-300ms) | Low (20-100ms) |
| **Audio Quality** | Good | Excellent |
| **Implementation** | Simple | Complex |
| **Browser Support** | Universal | Modern browsers |
| **Production Ready** | ✅ | ✅ (with proper setup) |

### Auto-Detection Methods

1. **X-Transport-Preference Header** (explicit)
2. **User-Agent Analysis** (webrtc/rtc keywords)
3. **Accept Header** (rtc media type)
4. **Environment Default** (PREFERRED_TRANSPORT)

**📖 For complete transport selection documentation, see [TRANSPORT_SELECTION.md](./TRANSPORT_SELECTION.md)**

## 🎯 Conversation Modes

The server supports flexible conversation modes that can be configured per WebSocket connection:

### Available Modes

| Mode | Voice Input | Text Input | Voice Output | Text Output | Description |
|------|-------------|------------|--------------|-------------|--------------|
| **Voice-to-Voice** | ✅ | ❌ | ✅ | ❌ | Traditional voice conversation |
| **Text-to-Text** | ❌ | ✅ | ❌ | ✅ | Chat interface |
| **Voice-to-Text** | ✅ | ❌ | ❌ | ✅ | Voice transcription |
| **Text-to-Voice** | ❌ | ✅ | ✅ | ❌ | Text-to-speech |
| **Multimodal** | ✅ | ✅ | ✅ | ✅ | All modes enabled |

### Mode Configuration Examples

#### Voice-Only Conversation
```
ws://localhost:7860/ws/flexible?voice_input=true&text_input=false&voice_output=true&text_output=false
```

#### Text Chat Only
```
ws://localhost:7860/ws/flexible?voice_input=false&text_input=true&voice_output=false&text_output=true
```

#### Voice Transcription Service
```
ws://localhost:7860/ws/flexible?voice_input=true&text_input=false&voice_output=false&text_output=true
```

#### Full Multimodal
```
ws://localhost:7860/ws/flexible?voice_input=true&text_input=true&voice_output=true&text_output=true
```

## 📝 Request/Response Examples

### Complete Authentication Flow

```bash
# 1. Register new user
REGISTER_RESPONSE=$(curl -s -X POST "http://localhost:7860/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "username": "devuser", 
    "password": "SecurePass123!",
    "full_name": "Developer User"
  }')

# Extract token
TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.token')

# 2. Create an agent
AGENT_RESPONSE=$(curl -s -X POST "http://localhost:7860/agents/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "agent_name": "Technical Support AI",
    "description": "Expert technical support agent",
    "system_prompt": "You are a technical support expert. Help users troubleshoot issues with clear, step-by-step instructions.",
    "voice_settings": {
      "language_code": "en-US",
      "voice_name": "en-US-Standard-J",
      "speaking_rate": 1.0,
      "pitch": 0.0
    }
  }')

# Extract agent ID
AGENT_ID=$(echo $AGENT_RESPONSE | jq -r '.id')

# 3. Check server capacity
CAPACITY_RESPONSE=$(curl -s -X POST "http://localhost:7860/connect")
echo "Server capacity: $(echo $CAPACITY_RESPONSE | jq -r '.capacity.available_slots') slots available"

# 4. Connect to WebSocket with specific agent
# ws://localhost:7860/ws/flexible?agent_id=$AGENT_ID&token=$TOKEN
```

### Error Handling Examples

#### Authentication Error
```bash
curl -X GET "http://localhost:7860/auth/profile" \
  -H "Authorization: Bearer invalid_token"
```

**Response (401):**
```json
{
  "detail": "Invalid authentication credentials"
}
```

#### Server at Capacity
```bash
curl -X POST "http://localhost:7860/connect"
```

**Response (503):**
```json
{
  "error": "Server at capacity",
  "message": "Please try again later",
  "capacity_info": {
    "total": 150,
    "active": 25,
    "peak": 25,
    "rejected": 15,
    "capacity_used": "100.0%"
  }
}
```

#### Invalid Agent Access
```bash
curl -X GET "http://localhost:7860/agents/999" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (404):**
```json
{
  "detail": "Agent not found"
}
```

### Rate Limiting & Usage Tracking

The server includes built-in rate limiting and usage tracking:

```bash
# Check usage stats
curl -X GET "http://localhost:7860/auth/profile" \
  -H "Authorization: Bearer $TOKEN" | jq '.usage_stats'
```

**Response:**
```json
{
  "agents_created": 5,
  "sessions_completed": 127,
  "total_voice_minutes": 340.75,
  "api_calls_today": 89,
  "monthly_usage": {
    "voice_minutes": 1205.25,
    "api_calls": 2847
  }
}
```

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Load Balancer │    │   Voice Agent   │
│                 │◄──►│   (Optional)    │◄──►│    Server       │
│ Web/Mobile/SDK  │    │                 │    │   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │   Pipecat AI    │
                                               │    Pipeline     │
┌─────────────────┐    ┌─────────────────┐    │                 │
│   OpenAI API    │    │   Google Cloud  │    │ STT → LLM → TTS │
│    (GPT-4)      │◄──►│   Speech APIs   │◄──►│                 │
│                 │    │                 │    └─────────────────┘
└─────────────────┘    └─────────────────┘
         │                       │              
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SQLite DB     │    │   Session Mgmt  │    │   Connection    │
│                 │    │                 │    │   Manager       │
│ Users & Agents  │    │ Active Sessions │    │ (25 max users)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Features

- **Connection Management**: Handles up to 25 concurrent WebSocket connections
- **Session Tracking**: Monitors active sessions with automatic cleanup
- **Service Pooling**: Optimized STT/LLM/TTS service reuse
- **Mode Flexibility**: Dynamic conversation mode switching
- **Authentication**: JWT-based auth with API key support
- **Agent Management**: Multi-agent support with marketplace
- **Monitoring**: Comprehensive metrics and health checks

## 🐳 Deployment

### Docker Deployment

```bash
# Build production image
docker build -t voice-agent-server .

# Run with environment variables
docker run -d \
  --name voice-agent \
  -p 7860:7860 \
  -e OPENAI_API_KEY=your-key \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/google-creds.json \
  -v ./google-creds.json:/app/google-creds.json:ro \
  -v ./data:/app/data \
  voice-agent-server
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  voice-agent:
    build: .
    ports:
      - "7860:7860"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_APPLICATION_CREDENTIALS=/app/google-creds.json
      - MAX_CONNECTIONS=25
      - PORT=7860
    volumes:
      - ./google-creds.json:/app/google-creds.json:ro
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7860/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Add Redis for session storage
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    profiles:
      - redis

  # Optional: Add PostgreSQL for advanced user management  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=voiceagent
      - POSTGRES_USER=voiceagent
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    profiles:
      - postgres

volumes:
  postgres_data:
```

### Production Configuration

```bash
# Production deployment
docker-compose --profile redis --profile postgres up -d

# Check status
docker-compose ps

# View logs
docker-compose logs voice-agent

# Monitor metrics
curl -s http://localhost:7860/metrics | jq '.connections'
```

## 🔍 Testing

### Test the Server

```bash
# Install test dependencies
uv sync --group test

# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=html

# Test specific endpoint
uv run pytest tests/test_auth.py::test_register_user -v
```

### Manual Testing with curl

```bash
# Test complete flow
./scripts/test-api.sh
```

### WebSocket Testing

```bash
# Install wscat for WebSocket testing
npm install -g wscat

# Test basic WebSocket
wscat -c ws://localhost:7860/ws

# Test flexible mode
wscat -c "ws://localhost:7860/ws/flexible?voice_input=false&text_input=true&voice_output=false&text_output=true"
```

### Load Testing

```bash
# Install artillery for load testing
npm install -g artillery

# Run load test
artillery run tests/load-test.yml
```

### Development Scripts

```bash
# Available development scripts
./scripts/dev.sh setup    # Setup development environment
./scripts/dev.sh start    # Start development server
./scripts/dev.sh test     # Run tests
./scripts/dev.sh lint     # Check code quality
./scripts/dev.sh format   # Format code
./scripts/dev.sh clean    # Clean up
```

## 📚 Additional Resources

- **Pipecat Documentation**: [pipecat.ai/docs](https://pipecat.ai/docs)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **OpenAI API Reference**: [platform.openai.com/docs](https://platform.openai.com/docs)
- **Google Speech APIs**: [cloud.google.com/speech-to-text](https://cloud.google.com/speech-to-text)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for new functionality
5. Run test suite: `uv run pytest`
6. Check code quality: `./scripts/dev.sh lint`
7. Commit changes: `git commit -m 'Add amazing feature'`
8. Push to branch: `git push origin feature/amazing-feature`
9. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
