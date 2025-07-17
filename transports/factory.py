#!/usr/bin/env python3
"""
Transport factory for creating different transport types
"""

import os
from typing import Dict, Any, Optional

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
    """Factory for creating transport managers"""
    
    @staticmethod
    def create_transport_manager(transport_type: TransportType, **kwargs) -> BaseTransportManager:
        """Create a transport manager of the specified type"""
        
        # Create transport config
        config = TransportFactory._create_transport_config(transport_type, **kwargs)
        
        # Create appropriate transport manager
        if transport_type == TransportType.WEBSOCKET:
            return WebSocketTransportManager(config)
        elif transport_type == TransportType.WEBRTC:
            if not _webrtc_available or WebRTCTransportManager is None:
                raise ValueError("WebRTC transport is not available. Install with: pip install pipecat-ai[webrtc]")
            return WebRTCTransportManager(config)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
    
    @staticmethod
    def _create_transport_config(transport_type: TransportType, **kwargs) -> TransportConfig:
        """Create transport configuration from environment and kwargs"""
        
        # Base configuration from environment
        config = TransportConfig(
            transport_type=transport_type,
            audio_in_enabled=kwargs.get('audio_in_enabled', True),
            audio_out_enabled=kwargs.get('audio_out_enabled', True),
            video_in_enabled=kwargs.get('video_in_enabled', False),
            video_out_enabled=kwargs.get('video_out_enabled', False),
            sample_rate=int(os.getenv('SAMPLE_RATE', '24000')),
            channels=int(os.getenv('CHANNELS', '1')),
            enable_vad=kwargs.get('enable_vad', os.getenv('ENABLE_VAD', 'true').lower() == 'true'),
            enable_interruptions=kwargs.get('enable_interruptions', os.getenv('ENABLE_INTERRUPTIONS', 'true').lower() == 'true'),
            
            # VAD configuration
            vad_stop_secs=float(os.getenv('VAD_STOP_SECS', '0.5')),
            vad_start_secs=float(os.getenv('VAD_START_SECS', '0.2')),
            vad_min_volume=float(os.getenv('VAD_MIN_VOLUME', '0.6')),
            
            # WebSocket specific
            websocket_timeout=int(os.getenv('WEBSOCKET_TIMEOUT', os.getenv('CONNECTION_TIMEOUT', '300'))),
            max_message_size=int(os.getenv('WS_MAX_SIZE', '16777216')),
            
            # WebRTC specific
            use_stun=kwargs.get('use_stun', os.getenv('USE_STUN', 'true').lower() == 'true'),
            use_turn=kwargs.get('use_turn', os.getenv('USE_TURN', 'false').lower() == 'true'),
            turn_username=kwargs.get('turn_username', os.getenv('TURN_USERNAME')),
            turn_password=kwargs.get('turn_password', os.getenv('TURN_PASSWORD')),
        )
        
        # Override with any provided kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    @staticmethod
    def get_preferred_transport() -> TransportType:
        """Get the preferred transport type from environment"""
        transport_pref = os.getenv('PREFERRED_TRANSPORT', 'websocket').lower()
        
        if transport_pref == 'webrtc':
            return TransportType.WEBRTC
        else:
            return TransportType.WEBSOCKET
    
    @staticmethod
    def detect_client_transport(request_headers: Dict[str, str]) -> TransportType:
        """Detect preferred transport type from client request headers"""
        # Check for WebRTC capability indicators
        user_agent = request_headers.get('user-agent', '').lower()
        accept = request_headers.get('accept', '').lower()
        
        # Look for WebRTC indicators in headers
        if 'webrtc' in user_agent or 'rtc' in accept:
            return TransportType.WEBRTC
        
        # Check for custom transport preference header
        transport_pref = request_headers.get('x-transport-preference', '').lower()
        if transport_pref == 'webrtc':
            return TransportType.WEBRTC
        
        # Default to WebSocket
        return TransportType.WEBSOCKET
    
    @staticmethod
    def create_adaptive_transport_manager(request_headers: Optional[Dict[str, str]] = None, **kwargs) -> BaseTransportManager:
        """Create transport manager based on client capabilities and preferences"""
        
        # Determine transport type
        if request_headers:
            transport_type = TransportFactory.detect_client_transport(request_headers)
        else:
            transport_type = TransportFactory.get_preferred_transport()
        
        # Override with explicit transport type if provided
        if 'transport_type' in kwargs:
            transport_type = kwargs.pop('transport_type')
        
        logger.info(
            "Creating adaptive transport manager",
            transport_type=transport_type.value,
            has_headers=bool(request_headers)
        )
        
        return TransportFactory.create_transport_manager(transport_type, **kwargs)
