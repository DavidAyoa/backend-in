# Enhanced Voice Agent Server

## Overview

This enhanced server provides robust support for 25 concurrent users with:
- Connection management and limits
- Resource pooling for AI services
- Health monitoring and metrics
- Proper error handling and cleanup
- Configurable settings via environment variables

## Quick Start

### 1. Setup Environment
```bash
# Copy environment template
cp .env.template .env

# Edit .env with your API keys
nano .env
```

### 2. Required API Keys
- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Google Cloud credentials JSON file

### 3. Start the Server
```bash
# Using the enhanced server
python server_enhanced.py

# Or using the enhanced bot directly
python bot_fast_api_enhanced.py
```

## Key Features

### Connection Management
- **Hard limit**: 25 concurrent connections (configurable)
- **Graceful rejection**: Returns proper error when at capacity
- **Automatic cleanup**: Removes stale connections after timeout
- **Connection tracking**: Monitors active sessions with metrics

### Resource Optimization
- **Service pooling**: Reuses AI service instances across sessions
- **Memory management**: Proper cleanup of resources on disconnect
- **Session isolation**: Each session has its own context and state
- **Garbage collection**: Automatic cleanup of unused resources

### Monitoring & Health
- **Health endpoint**: `/health` - Server status and capacity
- **Metrics endpoint**: `/metrics` - Detailed performance metrics
- **Connection info**: Real-time connection statistics
- **Performance tracking**: Session duration and resource usage

## API Endpoints

### WebSocket
- `ws://localhost:7860/ws` - Main voice agent connection

### HTTP Endpoints
- `GET /` - Server information
- `POST /connect` - Connection endpoint with capacity check
- `GET /health` - Health check with capacity info
- `GET /metrics` - Detailed server metrics

### Example Health Response
```json
{
  "status": "healthy",
  "timestamp": 1705234567.89,
  "server_info": {
    "active_connections": 12,
    "max_connections": 25,
    "capacity_usage": "48.0%"
  }
}
```

### Example Metrics Response
```json
{
  "connections": {
    "total": 150,
    "active": 12,
    "peak": 23,
    "rejected": 5,
    "capacity_used": "48.0%"
  },
  "performance": {
    "avg_session_duration": "125.50s",
    "max_connections": 25,
    "connection_timeout": 300
  },
  "timestamp": 1705234567.89
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONNECTIONS` | 25 | Maximum concurrent connections |
| `CONNECTION_TIMEOUT` | 300 | Connection timeout in seconds |
| `PORT` | 7860 | Server port |
| `LOG_LEVEL` | INFO | Logging level |
| `ENABLE_METRICS` | true | Enable performance metrics |
| `OPENAI_MODEL` | gpt-3.5-turbo | OpenAI model to use |
| `GOOGLE_TTS_VOICE` | en-US-Chirp3-HD-Achernar | Google TTS voice |

### Performance Tuning

**For Higher Capacity:**
```bash
MAX_CONNECTIONS=50
CONNECTION_TIMEOUT=180
WS_PING_INTERVAL=30
```

**For Lower Latency:**
```bash
VAD_STOP_SECS=0.3
VAD_START_SECS=0.1
WS_PING_INTERVAL=15
```

**For Better Resource Management:**
```bash
CLEANUP_INTERVAL=30
ENABLE_METRICS=false
ACCESS_LOG=false
```

## Testing

### Load Testing
```bash
# Test connection limits
for i in {1..30}; do
  curl -X POST http://localhost:7860/connect &
done

# Monitor health during load
watch -n 1 "curl -s http://localhost:7860/health | jq"
```

### Connection Testing
```bash
# Test WebSocket connection
wscat -c ws://localhost:7860/ws

# Test capacity rejection
# (connect 26 clients simultaneously)
```

### Performance Monitoring
```bash
# Real-time metrics
curl -s http://localhost:7860/metrics | jq

# Health check
curl -s http://localhost:7860/health | jq
```

## Troubleshooting

### Common Issues

1. **Server at capacity**
   - Check current connections: `curl localhost:7860/health`
   - Increase `MAX_CONNECTIONS` or wait for sessions to end

2. **Memory issues**
   - Monitor service pool stats in `/metrics`
   - Restart server to clear resource pools

3. **High latency**
   - Reduce `VAD_STOP_SECS` and `VAD_START_SECS`
   - Disable metrics: `ENABLE_METRICS=false`

4. **Connection timeouts**
   - Increase `CONNECTION_TIMEOUT`
   - Check network stability

### Logging

Logs are structured JSON and include:
- Connection events (connect/disconnect)
- Error details with session IDs
- Performance metrics
- Resource cleanup events

```bash
# View logs
tail -f server.log | jq

# Filter by session
tail -f server.log | jq 'select(.session_id == "uuid-here")'
```

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 7860
CMD ["python", "server_enhanced.py"]
```

### Production Settings
```bash
# Production environment
LOG_LEVEL=WARNING
ACCESS_LOG=false
ENABLE_METRICS=true
MAX_CONNECTIONS=25
CONNECTION_TIMEOUT=300
```

## Next Steps

This enhanced server provides a solid foundation for scaling. When ready, you can add:
- Redis for session management
- PostgreSQL for persistence
- WebRTC for lower latency
- Load balancing for horizontal scaling
- Advanced monitoring and alerting

The modular design makes it easy to integrate with ChatGPT suggestions and Pipecat documentation updates.
