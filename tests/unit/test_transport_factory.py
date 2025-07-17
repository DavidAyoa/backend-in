#!/usr/bin/env python3
"""
Unit tests for transport factory
"""

import pytest
from unittest.mock import patch, MagicMock

from transports.base import TransportType
from transports.factory import TransportFactory
from transports.websocket.manager import WebSocketTransportManager


class TestTransportFactory:
    """Test the transport factory"""
    
    @pytest.mark.unit
    def test_create_websocket_transport_manager(self):
        """Test creating WebSocket transport manager"""
        manager = TransportFactory.create_transport_manager(TransportType.WEBSOCKET)
        assert isinstance(manager, WebSocketTransportManager)
        assert manager.config.transport_type == TransportType.WEBSOCKET
    
    @pytest.mark.unit
    @patch('transports.factory._webrtc_available', False)
    @patch('transports.factory.WebRTCTransportManager', None)
    def test_create_webrtc_transport_manager(self):
        """Test creating WebRTC transport manager when not available"""
        with pytest.raises(ValueError, match="WebRTC transport is not available"):
            TransportFactory.create_transport_manager(TransportType.WEBRTC)
    
    @pytest.mark.unit
    def test_invalid_transport_type(self):
        """Test invalid transport type raises error"""
        with pytest.raises(ValueError, match="Unsupported transport type"):
            TransportFactory.create_transport_manager("invalid_type")
    
    @pytest.mark.unit
    def test_get_preferred_transport_default(self):
        """Test getting preferred transport with default"""
        transport_type = TransportFactory.get_preferred_transport()
        assert transport_type == TransportType.WEBSOCKET
    
    @pytest.mark.unit
    def test_get_preferred_transport_webrtc(self):
        """Test getting preferred transport as WebRTC"""
        with patch.dict('os.environ', {'PREFERRED_TRANSPORT': 'webrtc'}):
            transport_type = TransportFactory.get_preferred_transport()
            assert transport_type == TransportType.WEBRTC
    
    @pytest.mark.unit
    def test_detect_client_transport_websocket(self):
        """Test detecting WebSocket from client headers"""
        headers = {
            'user-agent': 'Mozilla/5.0 (Test Browser)',
            'accept': 'text/html,application/xhtml+xml'
        }
        
        transport_type = TransportFactory.detect_client_transport(headers)
        assert transport_type == TransportType.WEBSOCKET
    
    @pytest.mark.unit
    def test_detect_client_transport_webrtc_user_agent(self):
        """Test detecting WebRTC from user agent"""
        headers = {
            'user-agent': 'WebRTC Client/1.0',
            'accept': 'application/json'
        }
        
        transport_type = TransportFactory.detect_client_transport(headers)
        assert transport_type == TransportType.WEBRTC
    
    @pytest.mark.unit
    def test_detect_client_transport_webrtc_preference(self):
        """Test detecting WebRTC from preference header"""
        headers = {
            'user-agent': 'Test Client',
            'x-transport-preference': 'webrtc'
        }
        
        transport_type = TransportFactory.detect_client_transport(headers)
        assert transport_type == TransportType.WEBRTC
    
    @pytest.mark.unit
    @patch('transports.factory._webrtc_available', False)
    @patch('transports.factory.WebRTCTransportManager', None)
    def test_create_adaptive_transport_manager_webrtc_not_available(self):
        """Test creating adaptive transport manager when WebRTC is not available"""
        headers = {
            'user-agent': 'Test Client',
            'x-transport-preference': 'webrtc'
        }
        
        with pytest.raises(ValueError, match="WebRTC transport is not available"):
            TransportFactory.create_adaptive_transport_manager(headers)
    
    @pytest.mark.unit
    def test_create_adaptive_transport_manager_override(self):
        """Test creating adaptive transport manager with override"""
        headers = {
            'x-transport-preference': 'webrtc'
        }
        
        manager = TransportFactory.create_adaptive_transport_manager(
            headers,
            transport_type=TransportType.WEBSOCKET
        )
        assert isinstance(manager, WebSocketTransportManager)
    
    @pytest.mark.unit
    def test_transport_config_creation(self):
        """Test transport configuration creation"""
        config = TransportFactory._create_transport_config(
            TransportType.WEBSOCKET,
            audio_in_enabled=False,
            sample_rate=48000
        )
        
        assert config.transport_type == TransportType.WEBSOCKET
        assert config.audio_in_enabled is False
        assert config.sample_rate == 48000
    
    @pytest.mark.unit
    def test_transport_config_from_env(self):
        """Test transport configuration from environment"""
        with patch.dict('os.environ', {
            'SAMPLE_RATE': '48000',
            'ENABLE_VAD': 'false',
            'WEBSOCKET_TIMEOUT': '60'
        }):
            config = TransportFactory._create_transport_config(TransportType.WEBSOCKET)
            
            assert config.sample_rate == 48000
            assert config.enable_vad is False
            assert config.websocket_timeout == 60
