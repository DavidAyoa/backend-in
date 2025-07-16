# Multi-Agent Conversation Management

This document explains how the server now supports multiple agents with isolated conversation contexts.

## Overview

The enhanced system allows:
- Creating multiple agents with different system prompts
- Each agent can maintain multiple simultaneous conversations
- Complete context isolation between different conversations
- WebSocket connections can specify which agent to use
- Session management and monitoring

## Architecture

### Components

1. **AgentSessionManager** (`services/session_manager.py`)
   - Manages multiple conversation sessions
   - Provides context isolation between sessions
   - Handles session lifecycle and cleanup

2. **AgentSession** 
   - Represents a single conversation session
   - Contains isolated LLM service and context
   - Tracks activity and message history

3. **Enhanced WebSocket Endpoints**
   - Support agent selection via query parameters
   - Use agent-specific system prompts
   - Maintain separate contexts per session

## Usage

### 1. Create Agents via API

```bash
# Create a customer service agent
POST /agents/
{
  "agent_name": "Customer Support",
  "system_prompt": "You are a helpful customer service representative. Always be polite and professional.",
  "description": "Handles customer inquiries and support requests"
}

# Create a technical support agent
POST /agents/
{
  "agent_name": "Technical Support", 
  "system_prompt": "You are a technical support specialist with deep knowledge of our products.",
  "description": "Provides technical assistance and troubleshooting"
}
```

### 2. Connect to WebSocket with Agent Selection

```javascript
// Connect with specific agent
const ws = new WebSocket('ws://localhost:8000/ws/auth?token=YOUR_TOKEN&agent_id=1');

// Connect without specific agent (uses default prompt)
const ws = new WebSocket('ws://localhost:8000/ws/auth?token=YOUR_TOKEN');
```

### 3. Multiple Conversations

Each WebSocket connection creates a new session, even for the same agent:

```javascript
// Customer 1 connects to Customer Support agent
const ws1 = new WebSocket('ws://localhost:8000/ws/auth?token=TOKEN1&agent_id=1');

// Customer 2 connects to same Customer Support agent
const ws2 = new WebSocket('ws://localhost:8000/ws/auth?token=TOKEN2&agent_id=1');

// Both have completely separate conversation contexts
```

## Session Management

### Monitor Sessions

```bash
# Get session statistics
GET /session-manager/stats

# List all sessions (admin) or user's sessions
GET /session-manager/sessions

# Clean up inactive sessions (admin only)
POST /session-manager/cleanup?max_age_hours=24
```

### Session Lifecycle

1. **Session Creation**: When WebSocket connects with agent_id
2. **Context Initialization**: Agent's system prompt becomes initial context
3. **Conversation**: Messages are added to session-specific context
4. **Session Cleanup**: When WebSocket disconnects or manually deleted

## Context Isolation

Each session maintains:
- **Separate LLM service instance**
- **Independent conversation history** 
- **Isolated message context**
- **Individual activity tracking**

Example with two simultaneous conversations:

```
Session 1 (Agent 1):
- System: "You are a customer service rep..."
- User: "I need help with my order"
- Assistant: "I'd be happy to help..."

Session 2 (Agent 1): 
- System: "You are a customer service rep..."
- User: "What are your hours?"
- Assistant: "We're open 24/7..."
```

## API Endpoints

### Agent Management
- `POST /agents/` - Create new agent
- `GET /agents/` - List user's agents
- `PUT /agents/{id}` - Update agent
- `DELETE /agents/{id}` - Delete agent

### Session Management
- `GET /session-manager/stats` - Get session statistics
- `GET /session-manager/sessions` - List sessions
- `POST /session-manager/cleanup` - Clean up inactive sessions
- `DELETE /session-manager/sessions/{id}` - Delete specific session

### WebSocket Endpoints
- `ws://localhost:8000/ws?agent_id=ID` - Connect with optional agent
- `ws://localhost:8000/ws/auth?token=TOKEN&agent_id=ID` - Authenticated connection

## Implementation Details

### Session Manager Features

```python
# Create session with custom prompt
session_id = session_manager.create_session(
    agent_id=1,
    system_prompt="Custom prompt for this session"
)

# Get session
session = session_manager.get_session(session_id)

# Add messages to specific session
session_manager.add_user_message(session_id, "Hello")
session_manager.add_assistant_message(session_id, "Hi there!")

# Clean up
session_manager.delete_session(session_id)
```

### Context Isolation

Each `AgentSession` creates:
- Own `OpenAILLMService` instance
- Own `OpenAILLMContext` with messages
- Own `context_aggregator` for pipeline

This ensures complete isolation between conversations.

## Benefits

1. **Scalability**: Multiple conversations per agent
2. **Isolation**: No cross-talk between conversations  
3. **Flexibility**: Different agents for different use cases
4. **Monitoring**: Full session tracking and management
5. **Resource Management**: Automatic cleanup of inactive sessions

## Best Practices

1. **Agent Design**: Create agents with specific, clear system prompts
2. **Session Monitoring**: Regularly check session statistics
3. **Cleanup**: Use automated cleanup for inactive sessions
4. **Error Handling**: Handle WebSocket disconnections gracefully
5. **Authentication**: Use authenticated endpoints for production

## Testing

Run the test script to verify functionality:

```bash
python test_multi_agent.py
```

This tests session creation, context isolation, and API endpoints.
