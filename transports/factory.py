#!/usr/bin/env python3
"""
Simplified Transport factory - following Pipecat best practices
"""

import os
import structlog
from .base import BaseTransportManager, TransportConfig, TransportType
from .websocket.manager import WebSocketTransportManager

# Conditional import for WebRTC
try:
    from .webrtc.manager import WebRTCTransportManager
    _webrtc_available = True
except ImportError:
    _webrtc_available = False
    WebRTCTransportManager = None

logger = structlog.get_logger()


class TransportFactory:
    """Simplified factory for creating transport managers"""
    
    @staticmethod
    def create_transport_manager(transport_type: TransportType, **kwargs) -> BaseTransportManager:
        """Create a transport manager of the specified type"""
        
        # Create simple transport config
        config = TransportFactory._create_transport_config(transport_type, **kwargs)
        
        # Create appropriate transport manager
        if transport_type == TransportType.WEBSOCKET:
            return WebSocketTransportManager(config)
        elif transport_type == TransportType.WEBRTC:
            if not _webrtc_available or WebRTCTransportManager is None:
                raise ValueError("WebRTC transport is not available")
            return WebRTCTransportManager(config)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
    
    @staticmethod
    def _create_transport_config(transport_type: TransportType, **kwargs) -> TransportConfig:
        """Create basic transport configuration"""
        
        config = TransportConfig(
            transport_type=transport_type,
            audio_in_enabled=kwargs.get('audio_in_enabled', True),
            audio_out_enabled=kwargs.get('audio_out_enabled', True),
            video_in_enabled=kwargs.get('video_in_enabled', False),
            video_out_enabled=kwargs.get('video_out_enabled', False),
            sample_rate=int(os.getenv('SAMPLE_RATE', '24000')),
            channels=int(os.getenv('CHANNELS', '1')),
            enable_vad=kwargs.get('enable_vad', True),
            enable_interruptions=kwargs.get('enable_interruptions', True),
            
            # VAD configuration
            vad_stop_secs=float(os.getenv('VAD_STOP_SECS', '0.5')),
            vad_start_secs=float(os.getenv('VAD_START_SECS', '0.2')),
            vad_min_volume=float(os.getenv('VAD_MIN_VOLUME', '0.6')),
            
            # WebSocket specific
            websocket_timeout=int(os.getenv('WEBSOCKET_TIMEOUT', '300')),
            max_message_size=int(os.getenv('WS_MAX_SIZE', '16777216')),
            
            # WebRTC specific
            use_stun=kwargs.get('use_stun', True),
            use_turn=kwargs.get('use_turn', False),
            turn_username=kwargs.get('turn_username', os.getenv('TURN_USERNAME')),
            turn_password=kwargs.get('turn_password', os.getenv('TURN_PASSWORD')),
            ice_servers=kwargs.get('ice_servers', [])
        )
        
        # Override with any provided kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
