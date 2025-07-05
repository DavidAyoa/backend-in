# Scoreexl Voice Server

A modern voice AI server that provides real-time voice and text conversation capabilities with customizable AI agents.

## Overview

Scoreexl Voice Server is a comprehensive API service that enables users to create, manage, and interact with AI agents through both voice and text modalities. The server handles user authentication, agent management, session control, and real-time communication.

## Core Features

- **🔐 User Authentication**: Secure registration, login, and JWT-based authentication
- **🤖 AI Agent Management**: Create and customize AI agents with personalized prompts and behaviors
- **💬 Session Management**: Manage conversation sessions with dynamic context switching
- **🎤 Multi-Modal Communication**: Support for voice, text, and hybrid conversation modes
- **📊 Persistent Storage**: SQLite database for reliable data persistence
- **🔄 Real-time Updates**: WebSocket support for live conversation streaming

## Goals

- Provide a seamless abstraction layer for voice AI interactions
- Enable users to create personalized AI agents with custom behaviors
- Support both voice and text communication modes
- Maintain conversation context across sessions
- Offer scalable and secure user management
- Provide intuitive API endpoints for easy integration

## Database

The server uses SQLite with the database file `scoreexl_voice.sqlite` for persistent storage of:
- User accounts and authentication data
- AI agent configurations and settings
- Active conversation sessions
- Conversation history and context

## API Endpoints

### Authentication

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password123"
}
```

#### Login User
```http
POST /auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

#### Get Current User
```http
GET /auth/me
Authorization: Bearer <access_token>
```

### Agent Management

#### Create Agent
```http
POST /agents/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "My Assistant",
  "initial_prompt": "You are a helpful AI assistant that specializes in coding.",
  "context_prompts": [
    "Always provide code examples when explaining concepts",
    "Use clear and concise language"
  ],
  "voice_enabled": true,
  "text_enabled": true,
  "response_type": "both"
}
```

#### List User's Agents
```http
GET /agents/
Authorization: Bearer <access_token>
```

#### Get Specific Agent
```http
GET /agents/{agent_id}
Authorization: Bearer <access_token>
```

#### Update Agent
```http
PUT /agents/{agent_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Updated Assistant Name",
  "initial_prompt": "Updated prompt...",
  "voice_enabled": false
}
```

#### Delete Agent
```http
DELETE /agents/{agent_id}
Authorization: Bearer <access_token>
```

### Session Management

#### Create Session
```http
POST /sessions/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "agent_id": 1,
  "mode": "voice",
  "session_prompt": "You are a Python programming expert. You ONLY know about Python programming and nothing else.",
  "conversation_context": {
    "topic": "python_programming",
    "user_level": "beginner"
  }
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "agent_id": 1,
  "room_name": "room_1_1_a1b2c3d4",
  "conversation_context": {
    "topic": "python_programming",
    "user_level": "beginner"
  },
  "context_prompts": ["Always be friendly and helpful", "Provide clear explanations"],
  "session_prompt": "You are a Python programming expert. You ONLY know about Python programming and nothing else.",
  "mode": "voice",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### List User's Sessions
```http
GET /sessions/
Authorization: Bearer <access_token>
```

#### Get Specific Session
```http
GET /sessions/{session_id}
Authorization: Bearer <access_token>
```

#### Update Session
```http
PUT /sessions/{session_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "mode": "text",
  "session_prompt": "You are now a JavaScript expert. You know everything about modern JavaScript, ES6+, React, Node.js, and web development.",
  "conversation_context": {
    "topic": "javascript",
    "language": "javascript",
    "user_level": "intermediate"
  }
}
```

#### Join Session
```http
POST /sessions/{session_id}/join
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "session_id": 1,
  "room_name": "room_1_1_a1b2c3d4",
  "agent_id": 1,
  "mode": "voice",
  "conversation_context": {
    "topic": "programming",
    "language": "python"
  }
}
```

#### Delete Session
```http
DELETE /sessions/{session_id}
Authorization: Bearer <access_token>
```

### LiveKit Integration

#### Start LiveKit Session
```http
POST /sessions/{session_id}/start
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "LiveKit session started successfully",
  "session_id": 1,
  "room_name": "room_1_1_a1b2c3d4",
  "mode": "voice"
}
```

#### Send Text Message
```http
POST /sessions/{session_id}/message
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "message": "Hello, can you help me with Python programming?"
}
```

#### Update Session Prompt
```http
PUT /sessions/{session_id}/prompt
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "new_prompt": "You are now a JavaScript expert. You know everything about modern JavaScript, ES6+, React, and Node.js."
}
```

#### End LiveKit Session
```http
POST /sessions/{session_id}/end
Authorization: Bearer <access_token>
```

### WebSocket Communication

#### Connect to WebSocket
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${session_id}`);

ws.onopen = function() {
    console.log('Connected to agent session');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

#### Send Text Message via WebSocket
```javascript
ws.send(JSON.stringify({
    type: "text_message",
    message: "Hello, can you help me with Python programming?"
}));
```

#### Update Session Prompt via WebSocket
```javascript
ws.send(JSON.stringify({
    type: "update_prompt",
    prompt: "You are now a JavaScript expert. You know everything about modern JavaScript."
}));
```

#### WebSocket Message Types
- `connected` - Connection established
- `livekit_started` - LiveKit session started
- `user_message` - User message sent
- `agent_response` - Agent response received
- `prompt_updated` - Session prompt updated
- `error` - Error message
- `ping/pong` - Connection health check

## Request Examples

### Complete User Registration Flow

1. **Register a new user:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice_dev",
    "email": "alice@example.com",
    "password": "my_secure_password"
  }'
```

2. **Login to get access token:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice_dev",
    "password": "my_secure_password"
  }'
```

3. **Create an AI agent:**
```bash
curl -X POST http://localhost:8000/agents/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Code Assistant",
    "initial_prompt": "You are an expert programming assistant. Help users with code reviews, debugging, and best practices.",
    "context_prompts": [
      "Always explain your reasoning",
      "Provide working code examples"
    ],
    "voice_enabled": true,
    "text_enabled": true,
    "response_type": "both"
  }'
```

4. **Create a conversation session:**
```bash
curl -X POST http://localhost:8000/sessions/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": 1,
    "mode": "voice",
    "session_prompt": "You are a Python programming expert. You ONLY know about Python programming and nothing else.",
    "conversation_context": {
      "topic": "python_programming",
      "user_level": "beginner"
    }
  }'
```

## Session Features

### Session-Specific Prompts
Each session can have a custom prompt that completely changes the agent's knowledge and behavior:

- **Agent Level**: Default `initial_prompt` (e.g., "You are a helpful AI assistant")
- **Session Level**: Custom `session_prompt` that overrides the agent's default prompt
- **Dynamic Updates**: Change the session prompt during active conversations

**Example Session Prompts:**
- Python Expert: `"You are a Python programming expert. You ONLY know about Python programming and nothing else."`
- Cooking Expert: `"You are a cooking expert. You know everything about recipes, ingredients, and cooking techniques."`
- JavaScript Expert: `"You are a JavaScript expert. You know everything about modern JavaScript, ES6+, React, and Node.js."`

### Response Types

#### Agent Response Types
- `"voice"` - Voice-only responses
- `"text"` - Text-only responses  
- `"both"` - Both voice and text responses

#### Session Modes
- `"voice"` - Voice conversation mode
- `"text"` - Text conversation mode
- `"both"` - Hybrid voice and text mode

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

Error responses include a `detail` field with the error message:

```json
{
  "detail": "Username already registered"
}
```

## Development

Built with modern Python technologies:
- **FastAPI** - High-performance web framework
- **SQLAlchemy** - Database ORM
- **SQLite** - Lightweight database
- **JWT** - Secure authentication
- **Pydantic** - Data validation 