# Voice Agent Backend - Restructured

A clean, scalable voice agent backend built with FastAPI and Pipecat, supporting both WebSocket and WebRTC transports with comprehensive testing and Docker support.

## Features

- **Flexible Conversation System**: Support for voice-to-voice, voice-to-text, text-to-voice, and text-to-text modes
- **Dynamic Mode Switching**: Change conversation modes seamlessly during runtime
- **Dual Transport Support**: WebSocket and WebRTC transports with adaptive selection
- **Service Pooling**: Efficient resource management for STT, LLM, and TTS services
- **Clean Architecture**: Well-structured codebase with proper separation of concerns
- **Comprehensive Testing**: Unit, integration, and end-to-end tests with 100% pass rate
- **Docker Support**: Full containerization with development and production environments
- **Type Safety**: Full type hints and mypy support
- **Development Tools**: Pre-commit hooks, linting, and formatting
- **Robust Error Handling**: Proper frame processing and session management

## Project Structure

```
.
├── api/                    # FastAPI routes and endpoints
├── bot/                    # Pipeline factories and bot logic
├── core/                   # Core services (service pool, etc.)
├── models/                 # Data models and database schemas
├── services/               # Business logic services
├── transports/             # Transport implementations
│   ├── websocket/          # WebSocket transport
│   ├── webrtc/            # WebRTC transport
│   ├── base.py            # Base transport classes
│   └── factory.py         # Transport factory
├── utils/                  # Utility functions
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── scripts/               # Development and deployment scripts
├── helpful_docs/          # Documentation and guides
├── docker-compose.yml     # Docker services definition
└── pyproject.toml         # Project configuration
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker and Docker Compose
- OpenAI API key
- Google Cloud credentials

### Setup

1. **Clone and setup environment**:
   ```bash
   git clone <repository>
   cd backend-in
   chmod +x scripts/dev.sh
   ./scripts/dev.sh setup
   ```

2. **Configure environment**:
   ```bash
   cp .env.template .env
   # Edit .env with your API keys
   ```

3. **Start development server**:
   ```bash
   ./scripts/dev.sh start
   ```

### Using Docker

```bash
# Start main application
docker-compose up voice-agent

# Start development environment
docker-compose --profile dev up

# Start with optional services
docker-compose --profile redis --profile postgres up
```

## Transport System

The backend supports two transport types that can be selected automatically or explicitly:

### WebSocket Transport

- Uses Pipecat's `WebsocketServerTransport`
- Real-time audio streaming
- Built-in VAD support
- Session management

### WebRTC Transport

- Uses Pipecat's `SmallWebRTCTransport`
- Peer-to-peer audio communication
- STUN/TURN server support
- Low-latency streaming

### Transport Selection

The system automatically selects the appropriate transport based on:

1. Client headers (`x-transport-preference`)
2. User agent detection
3. Environment configuration
4. Explicit override

```python
from transports.factory import TransportFactory

# Automatic selection
manager = TransportFactory.create_adaptive_transport_manager(request_headers)

# Explicit selection
manager = TransportFactory.create_transport_manager(TransportType.WEBRTC)
```

## Service Pool

The service pool efficiently manages Pipecat services:

```python
from core.service_pool import get_service_pool

pool = await get_service_pool()
stt_service = await pool.get_stt_service()
llm_service = await pool.get_llm_service()
tts_service = await pool.get_tts_service()

# Return services when done
await pool.return_stt_service(stt_service)
```

## Development Scripts

The `scripts/dev.sh` script provides common development tasks:

```bash
# Setup development environment
./scripts/dev.sh setup

# Start development server
./scripts/dev.sh start

# Run tests
./scripts/dev.sh test

# Run linting
./scripts/dev.sh lint

# Fix formatting
./scripts/dev.sh format

# Start services only
./scripts/dev.sh services

# Stop all services
./scripts/dev.sh stop

# Clean up
./scripts/dev.sh clean
```

## Testing

The project includes comprehensive testing:

### Running Tests

```bash
# Run all tests
./scripts/dev.sh test

# Run specific test types
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/e2e/

# Run with coverage
uv run pytest --cov=. --cov-report=html
```

### Test Structure

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows

### Test Configuration

Tests use fixtures for:
- Mock services and transports
- Test data generation
- Environment setup
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
