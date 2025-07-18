# Voice Agent Backend - Enhanced

A clean, scalable voice agent backend built with FastAPI and Pipecat, supporting both WebSocket and WebRTC transports with comprehensive testing and Docker support.

## Features

- **Flexible Conversation System**: Full input/output mode combinations (voice-to-voice, voice-to-text, text-to-voice, text-to-text)
- **Dynamic Mode Switching**: Seamless mode transitions during runtime
- **Dual Transport Support**: WebSocket and WebRTC transports with adaptive selection
- **Service Optimization**: Efficient resource pooling for STT, LLM, and TTS services
- **Robust Connection Management**: Limits and monitoring with detailed metrics
- **Comprehensive Testing**: Extensive test coverage with high pass rates
- **Production Rea
- Database cleanup

## Configuration

### Environment Variables

Key configuration options:

```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/google/credentials.json

# Server Settings
HOST=0.0.0.0
PORT=7860
MAX_CONNECTIONS=25

# Transport Settings
PREFERRED_TRANSPORT=websocket  # or webrtc
ENABLE_INTERRUPTIONS=true
ENABLE_VAD=true

# Service Pool
SERVICE_POOL_SIZE=5
ENABLE_SERVICE_REUSE=true
```

### Transport Configuration

```python
from transports.base import TransportConfig, TransportType

config = TransportConfig(
    transport_type=TransportType.WEBSOCKET,
    audio_in_enabled=True,
    audio_out_enabled=True,
    sample_rate=24000,
    enable_vad=True,
    enable_interruptions=True,
    # WebRTC specific
    ice_servers=["stun:stun.l.google.com:19302"],
    use_stun=True,
    # WebSocket specific
    websocket_timeout=300,
    max_message_size=16777216,
)
```

## API Endpoints

### Health and Status

- `GET /health` - Health check
- `GET /metrics` - Service metrics
- `GET /` - Service information

### Authentication

- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/profile` - User profile
- `GET /auth/api-key` - API key management

### Agents

- `POST /agents/` - Create agent
- `GET /agents/` - List agents
- `GET /agents/{id}` - Get agent
- `PUT /agents/{id}` - Update agent
- `DELETE /agents/{id}` - Delete agent

### WebSocket/WebRTC

- `WS /ws` - WebSocket endpoint
- `POST /webrtc/offer` - WebRTC offer endpoint
- `POST /webrtc/answer` - WebRTC answer endpoint

## Deployment

### Production Deployment

```bash
# Build production image
docker-compose build voice-agent

# Deploy with Docker Compose
docker-compose up -d voice-agent

# With optional services
docker-compose --profile redis --profile postgres up -d
```

### Environment-Specific Configs

- `.env` - Production configuration
- `.env.dev` - Development configuration
- `.env.test` - Test configuration

## Code Quality

### Linting and Formatting

```bash
# Check formatting
./scripts/dev.sh lint

# Fix formatting
./scripts/dev.sh format
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

### Type Checking

```bash
# Run mypy
uv run mypy .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Workflow

1. Setup development environment: `./scripts/dev.sh setup`
2. Start development server: `./scripts/dev.sh start`
3. Make changes
4. Run tests: `./scripts/dev.sh test`
5. Check linting: `./scripts/dev.sh lint`
6. Fix formatting: `./scripts/dev.sh format`
7. Commit changes

## Architecture Notes

### Transport Layer

- **Base Classes**: Common interfaces for all transports
- **Factory Pattern**: Automatic transport selection
- **Session Management**: Unified session handling
- **Event Handling**: Consistent event system

### Service Layer

- **Service Pool**: Efficient resource management
- **Pipeline Factory**: Reusable pipeline creation
- **Configuration Management**: Environment-based config

### Testing Strategy

- **Isolation**: Mock external dependencies
- **Fixtures**: Reusable test components
- **Coverage**: Comprehensive test coverage
- **CI/CD Ready**: Docker-based testing

## Future Enhancements

- [ ] Redis session storage
- [ ] PostgreSQL user management
- [ ] Horizontal scaling support
- [ ] Metrics and monitoring
- [ ] Rate limiting
- [ ] API versioning
- [ ] WebRTC client SDK
- [ ] Load balancing

## License

This project is licensed under the MIT License - see the LICENSE file for details.
