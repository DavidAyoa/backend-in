# Live Conversation Mode Tests

This directory contains integration tests for live conversation modes that test real WebSocket connections against a running server.

## Overview

The `test_live_conversation_modes.py` file provides comprehensive testing for:

- **Voice-to-Voice Mode**: Audio input → Audio output
- **Text-to-Text Mode**: Text input → Text output  
- **Voice-to-Text Mode**: Audio input → Text output
- **Text-to-Voice Mode**: Text input → Audio output
- **Multimodal Mode**: Both audio and text input/output
- **Invalid Mode**: Properly reject invalid configurations

## Prerequisites

1. **Server must be running**: Start the server first with `python main.py`
2. **Dependencies**: Install test dependencies with `pip install -r requirements-test.txt`

## Running the Tests

### Using pytest (Recommended)

```bash
# Run all live conversation tests
pytest tests/integration/test_live_conversation_modes.py -v

# Run specific test
pytest tests/integration/test_live_conversation_modes.py::test_voice_to_voice_conversation_mode -v

# Run with integration marker
pytest -m integration tests/integration/test_live_conversation_modes.py -v

# Skip if server not running
pytest tests/integration/test_live_conversation_modes.py -v --tb=short
```

### Using standalone execution

```bash
# Run all tests with detailed output
python tests/integration/test_live_conversation_modes.py
```

## Test Features

### Audio Generation
- Generates synthetic sine wave audio for testing
- Configurable frequency, duration, and sample rate
- Converts to 16-bit PCM format for WebSocket transmission

### WebSocket Testing
- Tests real WebSocket connections to `/ws/flexible` endpoint
- Validates different conversation mode configurations
- Handles timeouts and connection errors gracefully

### Server Health Checks
- Verifies server is running before executing tests
- Automatically skips tests if server is unavailable
- Provides clear error messages for debugging

## Test Configuration

The tests connect to:
- **Server URL**: `http://localhost:7860`
- **WebSocket URL**: `ws://localhost:7860/ws/flexible`
- **Health endpoint**: `http://localhost:7860/health`

## Expected Behavior

Each test:
1. Connects to the appropriate WebSocket endpoint with mode parameters
2. Sends test data (audio or text)
3. Waits for appropriate response type
4. Validates response format and content
5. Reports success/failure with detailed logs

## Troubleshooting

### Server Not Running
```
pytest.skip: Server is not running. Start server with: python main.py
```
**Solution**: Start the server first: `python main.py`

### Import Errors
```
ImportError: No module named 'numpy'
```
**Solution**: Install dependencies: `pip install -r requirements-test.txt`

### Connection Timeouts
**Causes**: 
- Server overloaded or slow processing
- Network connectivity issues
- Invalid WebSocket endpoint

**Solutions**:
- Check server logs for errors
- Verify server is responding to health checks
- Increase timeout values if needed

### Audio Processing Issues
**Causes**:
- Audio format not supported
- Audio processing pipeline errors
- Missing audio dependencies

**Solutions**:
- Check server audio configuration
- Verify Pipecat audio components are properly installed
- Review server logs for audio processing errors

## Integration with CI/CD

These tests are marked with `@pytest.mark.integration` and can be:
- Skipped in unit test runs: `pytest -m "not integration"`
- Run only for integration testing: `pytest -m integration`
- Included in full test suite runs

## Performance Considerations

- Tests include brief delays between operations for server processing
- Timeout values are configured for reasonable response times
- Audio generation is lightweight (synthetic sine waves)
- WebSocket connections are properly closed after each test
