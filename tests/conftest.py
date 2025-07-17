#!/usr/bin/env python3
"""
Pytest configuration and fixtures for voice agent backend tests
"""

import asyncio
import os
import tempfile
import pytest
from typing import AsyncGenerator, Dict, Any

# Set test environment
os.environ["TESTING"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"

# Create temporary database for tests
test_db_path = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

# Mock API keys for testing
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "test-google-creds"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def transport_config():
    """Create a test transport configuration"""
    from transports.base import TransportConfig, TransportType
    
    return TransportConfig(
        transport_type=TransportType.WEBSOCKET,
        audio_in_enabled=True,
        audio_out_enabled=True,
        sample_rate=16000,  # Lower for testing
        enable_vad=False,   # Disable VAD for testing
        enable_interruptions=False,
        websocket_timeout=30,
    )


@pytest.fixture
def webrtc_transport_config():
    """Create a test WebRTC transport configuration"""
    from transports.base import TransportConfig, TransportType
    
    return TransportConfig(
        transport_type=TransportType.WEBRTC,
        audio_in_enabled=True,
        audio_out_enabled=True,
        sample_rate=16000,
        enable_vad=False,
        enable_interruptions=False,
        ice_servers=["stun:stun.l.google.com:19302"],
        use_stun=True,
        use_turn=False,
    )


@pytest.fixture
def mock_service_pool():
    """Create a mock service pool for testing"""
    from unittest.mock import AsyncMock, MagicMock
    
    service_pool = MagicMock()
    service_pool.get_stt_service = AsyncMock()
    service_pool.get_llm_service = AsyncMock()
    service_pool.get_tts_service = AsyncMock()
    service_pool.return_stt_service = AsyncMock()
    service_pool.return_llm_service = AsyncMock()
    service_pool.return_tts_service = AsyncMock()
    service_pool.get_stats = AsyncMock(return_value={
        "stt_services": {"total_created": 1, "available": 1},
        "llm_services": {"total_created": 1, "available": 1},
        "tts_services": {"total_created": 1, "available": 1}
    })
    
    return service_pool


@pytest.fixture
def mock_transport_manager():
    """Create a mock transport manager for testing"""
    from unittest.mock import AsyncMock, MagicMock
    
    manager = MagicMock()
    manager.create_session = AsyncMock()
    manager.destroy_session = AsyncMock()
    manager.send_message = AsyncMock()
    manager.handle_client_message = AsyncMock()
    manager.get_session = MagicMock(return_value=None)
    manager.update_session_activity = MagicMock()
    manager.cleanup_inactive_sessions = AsyncMock()
    
    return manager


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing"""
    from unittest.mock import AsyncMock, MagicMock
    
    websocket = MagicMock()
    websocket.accept = AsyncMock()
    websocket.close = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.receive_json = AsyncMock()
    websocket.client = MagicMock()
    websocket.client.host = "127.0.0.1"
    websocket.application_state = MagicMock()
    websocket.application_state.name = "CONNECTED"
    
    return websocket


@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Test user data for authentication tests"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def test_agent_data() -> Dict[str, Any]:
    """Test agent data for agent tests"""
    return {
        "agent_name": "Test Agent",
        "description": "A test voice agent",
        "system_prompt": "You are a helpful test assistant.",
        "voice_settings": {
            "voice_id": "en-US-Chirp3-HD-Charon",
            "speech_rate": 1.0,
            "pitch": 0.0
        },
        "transport_config": {
            "transport_type": "websocket",
            "audio_in_enabled": True,
            "audio_out_enabled": True
        }
    }


@pytest.fixture
def test_session_data() -> Dict[str, Any]:
    """Test session data"""
    return {
        "session_id": "test-session-123",
        "transport_type": "websocket",
        "client_info": {
            "user_agent": "test-client",
            "ip_address": "127.0.0.1"
        }
    }


@pytest.fixture
def test_webrtc_sdp() -> str:
    """Test WebRTC SDP offer for testing"""
    return """v=0
o=- 123456789 987654321 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=msid-semantic: WMS
m=audio 9 UDP/TLS/RTP/SAVPF 111
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=ice-ufrag:test
a=ice-pwd:testpassword
a=ice-options:trickle
a=fingerprint:sha-256 AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99
a=setup:actpass
a=mid:0
a=extmap:1 urn:ietf:params:rtp-hdrext:ssrc-audio-level
a=extmap:2 http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time
a=extmap:3 http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01
a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid
a=extmap:5 urn:ietf:params:rtp-hdrext:sdes:rtp-stream-id
a=extmap:6 urn:ietf:params:rtp-hdrext:sdes:repaired-rtp-stream-id
a=sendrecv
a=msid:test testtrack
a=rtcp-mux
a=rtpmap:111 opus/48000/2
a=rtcp-fb:111 transport-cc
a=fmtp:111 minptime=10;useinbandfec=1
a=ssrc:123456789 cname:test
a=ssrc:123456789 msid:test testtrack
a=ssrc:123456789 mslabel:test
a=ssrc:123456789 label:testtrack
"""


# Test cleanup
@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Clean up test database after each test"""
    yield
    # Clean up test database
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except OSError:
            pass


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
