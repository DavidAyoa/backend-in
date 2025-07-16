# Voice Agent Backend Testing

## Overview

This directory contains comprehensive tests for the Voice Agent Backend API. The test suite covers all available routes including authentication, user management, agent operations, and WebSocket connections.

## Test Files

- **`test_api_comprehensive.py`** - Main comprehensive test suite covering all API endpoints
- **`../run_tests.py`** - Easy-to-use test runner script

## Running Tests

### Prerequisites

1. Make sure the server is running:
   ```bash
   python3 main.py
   ```

2. Install test dependencies (already included in project):
   - pytest
   - pytest-asyncio
   - httpx
   - websockets

### Running All Tests

```bash
# Using the test runner (recommended)
python3 run_tests.py

# Or run directly
python3 tests/test_api_comprehensive.py
```

## Test Coverage

### ✅ Working Routes (11/17 - 64.7% success rate)

#### Server Information
- `GET /` - Server info
- `GET /health` - Health check  
- `GET /metrics` - Metrics endpoint

#### Authentication & User Management
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/profile` - Get user profile
- `PUT /auth/profile` - Update user profile
- `GET /auth/api-key` - Get API key
- `GET /auth/session` - Session information

#### Security
- Invalid token rejection (401 responses)

#### Cleanup
- Test data cleanup

### ❌ Issues Found (6/17 routes failing)

#### Agent Management Issues
- `POST /agents/` - Agent creation failing (response validation error)
- `GET /agents/` - Agent listing failing (response validation error)
- `GET /agents/{id}` - Cannot test due to creation failure
- `PUT /agents/{id}` - Cannot test due to creation failure

**Error**: `voice_settings` field is being returned as a string instead of a dictionary, causing FastAPI response validation to fail.

#### WebSocket Issues
- `WebSocket /ws` - Authentication dependency error
- `WebSocket /ws/auth` - Authentication dependency error

**Error**: `HTTPBearer.__call__() missing 1 required positional argument: 'request'`

## Known Issues and Fixes Needed

### 1. Agent Voice Settings Serialization

**Problem**: The `voice_settings` field in agent responses is being stored/returned as a JSON string instead of a dictionary.

**Location**: `models/user.py` or agent creation/retrieval logic

**Fix Needed**: Ensure `voice_settings` is properly serialized/deserialized as a dictionary.

### 2. WebSocket Authentication

**Problem**: WebSocket endpoints have incorrect authentication dependency setup.

**Location**: `main.py` WebSocket endpoints

**Fix Needed**: Update WebSocket authentication to properly handle FastAPI dependencies for WebSocket connections.

## Test Results Summary

```
Total Tests: 17
Passed: 11 ✅
Failed: 6 ❌
Success Rate: 64.7%
Status: ⚠️  MODERATE - Some tests failed
```

## Adding New Tests

To add new test cases:

1. Add new test methods to the `VoiceAgentAPITester` class in `test_api_comprehensive.py`
2. Follow the existing pattern:
   ```python
   async def test_new_feature(self) -> bool:
       """Test description"""
       print("\\n=== Testing New Feature ===")
       
       try:
           # Test implementation
           if success:
               print("✅ Test passed")
               return True
           else:
               print("❌ Test failed")
               return False
       except Exception as e:
           print(f"❌ Test error: {e}")
           return False
   ```
3. Add the test to the `run_all_tests()` method
4. Update this README with the new test coverage

## Debugging Failed Tests

### Verbose Server Logs

Start the server with debug logging:
```bash
LOG_LEVEL=DEBUG python3 main.py
```

### Individual Test Debugging

You can run individual test methods by modifying the `run_all_tests()` method or adding debug prints.

### Database Inspection

Check the SQLite database for test data:
```bash
sqlite3 voice_agent.sqlite
.tables
SELECT * FROM users;
SELECT * FROM agents;
```

## CI/CD Integration

The test runner exits with:
- Exit code 0: Tests passed (≥80% success rate)
- Exit code 1: Tests failed (<80% success rate)

This makes it suitable for CI/CD pipelines:
```bash
python3 run_tests.py && echo "Tests passed" || echo "Tests failed"
```
