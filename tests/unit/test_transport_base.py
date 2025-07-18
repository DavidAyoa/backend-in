#!/usr/bin/env python3
"""
Unit tests for transport base classes and configurations
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from transports.base import (
    TransportType, 
    TransportConfig, 
    SessionInfo, 
    BaseTransportManager
)
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext


class TestTransportType:
    """Test transport type enum"""
    
    @pytest.mark.unit
    def test_transport_type_values(self):
        """Test transport type enum values"""
        assert TransportType.WEBSOCKET.value == "websocket"
        assert TransportType.WEBRTC.value == "webrtc"
    
    @pytest.mark.unit
    def test_transport_type_string_conversion(self):
        """Test transport type string conversion"""
        assert str(TransportType.WEBSOCKET) == "websocket"
        assert str(TransportType.WEBRTC) == "webrtc"


class TestTransportConfig:
    """Test transport configuration"""
    
    @pytest.mark.unit
    def test_default_websocket_config(self):
        """Test default WebSocket configuration"""
        config = TransportConfig(transport_type=TransportType.WEBSOCKET)
        
        assert config.transport_type == TransportType.WEBSOCKET
        assert config.audio_in_enabled is True
        assert config.audio_out_enabled is True
        assert config.video_in_enabled is False
        assert config.video_out_enabled is False
        assert config.sample_rate == 24000
        assert config.channels == 1
        assert config.enable_vad is True
        assert config.enable_interruptions is True
    
    @pytest.mark.unit
    def test_webrtc_config_with_ice_servers(self):
        """Test WebRTC configuration with ICE servers"""
        ice_servers = ["stun:stun.example.com:3478"]
        config = TransportConfig(
            transport_type=TransportType.WEBRTC,
            ice_servers=ice_servers,
            use_turn=True,
            turn_username="user",
            turn_password="pass"
        )
        
        assert config.transport_type == TransportType.WEBRTC
        assert config.ice_servers == ice_servers
        assert config.use_turn is True
        assert config.turn_username == "user"
        assert config.turn_password == "pass"
    
    @pytest.mark.unit
    def test_get_default_ice_servers(self):
        """Test getting default ICE servers"""
        config = TransportConfig(transport_type=TransportType.WEBRTC)
        servers = config.get_default_ice_servers()
        
        assert len(servers) >= 2  # Should have STUN servers
        assert any("stun.l.google.com" in server for server in servers)
    
    @pytest.mark.unit
    def test_get_default_ice_servers_with_turn(self):
        """Test getting ICE servers with TURN configuration"""
        config = TransportConfig(
            transport_type=TransportType.WEBRTC,
            use_turn=True,
            turn_username="testuser",
            turn_password="testpass"
        )
        servers = config.get_default_ice_servers()
        
        # Should have both STUN and TURN servers
        assert len(servers) >= 3
        assert any(isinstance(server, dict) and "turn:" in server.get("urls", "") for server in servers)
    
    @pytest.mark.unit
    def test_get_vad_analyzer_disabled(self):
        """Test VAD analyzer when disabled"""
        config = TransportConfig(
            transport_type=TransportType.WEBSOCKET,
            enable_vad=False
        )
        
        vad = config.get_vad_analyzer()
        assert vad is None
    
    @pytest.mark.unit
    @patch('transports.base.SileroVADAnalyzer')
    def test_get_vad_analyzer_enabled(self, mock_silero):
        """Test VAD analyzer when enabled"""
        mock_analyzer = MagicMock()
        mock_silero.return_value = mock_analyzer
        
        config = TransportConfig(
            transport_type=TransportType.WEBSOCKET,
            enable_vad=True
        )
        
        vad = config.get_vad_analyzer()
        assert vad == mock_analyzer
        mock_silero.assert_called_once()
    
    @pytest.mark.unit
    def test_to_transport_params(self):
        """Test conversion to transport params"""
        config = TransportConfig(
            transport_type=TransportType.WEBSOCKET,
            audio_in_enabled=False,
            sample_rate=48000,
            channels=2
        )
        
        params = config.to_transport_params()
        
        assert params.audio_in_enabled is False
        assert params.audio_out_enabled is True
        assert params.audio_in_sample_rate == 48000
        assert params.audio_out_sample_rate == 48000
        assert params.audio_in_channels == 2
        assert params.audio_out_channels == 2


class TestSessionInfo:
    """Test session information"""
    
    @pytest.fixture
    def sample_context(self):
        """Create a sample OpenAI LLM context"""
        return OpenAILLMContext()
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample transport config"""
        return TransportConfig(transport_type=TransportType.WEBSOCKET)
    
    @pytest.mark.unit
    def test_session_info_creation(self, sample_context, sample_config):
        """Test session info creation"""
        session_id = "test-session-123"
        
        session_info = SessionInfo(
            session_id=session_id,
            transport_type=TransportType.WEBSOCKET,
            config=sample_config,
            context=sample_context
        )
        
        assert session_info.session_id == session_id
        assert session_info.transport_type == TransportType.WEBSOCKET
        assert session_info.config == sample_config
        assert session_info.context == sample_context
        assert session_info.pipeline is None
        assert session_info.task is None
        assert session_info.runner is None
        assert session_info.transport is None
        assert isinstance(session_info.created_at, datetime)
        assert isinstance(session_info.last_activity, datetime)
    
    @pytest.mark.unit
    def test_session_info_update_activity(self, sample_context, sample_config):
        """Test session activity update"""
        session_info = SessionInfo(
            session_id="test-session",
            transport_type=TransportType.WEBSOCKET,
            config=sample_config,
            context=sample_context
        )
        
        original_activity = session_info.last_activity
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.001)
        
        session_info.update_activity()
        
        assert session_info.last_activity > original_activity


class MockTransportManager(BaseTransportManager):
    """Mock transport manager for testing"""
    
    async def create_session(self, session_id: str, **kwargs):
        context = OpenAILLMContext()
        session_info = SessionInfo(
            session_id=session_id,
            transport_type=self.config.transport_type,
            config=self.config,
            context=context
        )
        self.active_sessions[session_id] = session_info
        return session_info
    
    async def destroy_session(self, session_id: str):
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        pass
    
    async def handle_client_message(self, session_id: str, message: dict):
        pass


class TestBaseTransportManager:
    """Test base transport manager"""
    
    @pytest.fixture
    def transport_config(self):
        """Create a test transport config"""
        return TransportConfig(transport_type=TransportType.WEBSOCKET)
    
    @pytest.fixture
    def transport_manager(self, transport_config):
        """Create a mock transport manager"""
        return MockTransportManager(transport_config)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_transport_manager_initialization(self, transport_manager, transport_config):
        """Test transport manager initialization"""
        assert transport_manager.config == transport_config
        assert transport_manager.active_sessions == {}
        assert transport_manager.logger is not None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_and_get_session(self, transport_manager):
        """Test creating and getting a session"""
        session_id = "test-session-456"
        
        # Create session
        session_info = await transport_manager.create_session(session_id)
        assert session_info.session_id == session_id
        
        # Get session
        retrieved_session = transport_manager.get_session(session_id)
        assert retrieved_session == session_info
        assert retrieved_session.session_id == session_id
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_destroy_session(self, transport_manager):
        """Test destroying a session"""
        session_id = "test-session-789"
        
        # Create session
        await transport_manager.create_session(session_id)
        assert session_id in transport_manager.active_sessions
        
        # Destroy session
        await transport_manager.destroy_session(session_id)
        assert session_id not in transport_manager.active_sessions
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_session_activity(self, transport_manager):
        """Test updating session activity"""
        session_id = "test-session-activity"
        
        # Create session
        await transport_manager.create_session(session_id)
        session_info = transport_manager.get_session(session_id)
        original_activity = session_info.last_activity
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.001)
        
        # Update activity
        transport_manager.update_session_activity(session_id)
        
        assert session_info.last_activity > original_activity
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_nonexistent_session_activity(self, transport_manager):
        """Test updating activity for non-existent session"""
        # Should not raise an error
        transport_manager.update_session_activity("nonexistent-session")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, transport_manager):
        """Test cleaning up inactive sessions"""
        # Create multiple sessions
        session_ids = ["session1", "session2", "session3"]
        for session_id in session_ids:
            await transport_manager.create_session(session_id)
        
        # Manually set old timestamps for some sessions
        old_time = datetime.now(timezone.utc).replace(year=2020)  # Very old timestamp
        transport_manager.active_sessions["session1"].last_activity = old_time
        transport_manager.active_sessions["session2"].last_activity = old_time
        
        # Cleanup with short timeout
        await transport_manager.cleanup_inactive_sessions(timeout_seconds=1)
        
        # Should have cleaned up the old sessions
        assert "session1" not in transport_manager.active_sessions
        assert "session2" not in transport_manager.active_sessions
        assert "session3" in transport_manager.active_sessions  # Recent session should remain
