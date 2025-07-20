#!/usr/bin/env python3
"""
Base transport classes and interfaces for voice agent transports.
"""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADAnalyzer

logger = structlog.get_logger()


class TransportType(Enum):
    """Supported transport types"""
    WEBSOCKET = "websocket"
    WEBRTC = "webrtc"
    
    def __str__(self):
        return self.value


@dataclass
class TransportConfig:
    """Base configuration for transports"""
    transport_type: TransportType
    audio_in_enabled: bool = True
    audio_out_enabled: bool = True
    video_in_enabled: bool = False
    video_out_enabled: bool = False
    sample_rate: int = 24000
    channels: int = 1
    enable_vad: bool = True
    enable_interruptions: bool = True
    
    # VAD Configuration
    vad_analyzer: Optional[VADAnalyzer] = None
    vad_stop_secs: float = 0.5
    vad_start_secs: float = 0.2
    vad_min_volume: float = 0.6
    
    # WebRTC specific
    ice_servers: Optional[list] = None
    use_stun: bool = True
    use_turn: bool = False
    turn_username: Optional[str] = None
    turn_password: Optional[str] = None
    
    # WebSocket specific
    websocket_timeout: int = 300
    max_message_size: int = 16777216
    
    def get_default_ice_servers(self) -> list:
        """Get default ICE servers configuration"""
        if self.ice_servers:
            return self.ice_servers
            
        servers = []
        if self.use_stun:
            servers.extend([
                "stun:stun.l.google.com:19302",
                "stun:stun1.l.google.com:19302"
            ])
        
        if self.use_turn and self.turn_username and self.turn_password:
            # Add TURN server configuration
            servers.append({
                "urls": "turn:turn.example.com:3478",
                "username": self.turn_username,
                "credential": self.turn_password
            })
        
        return servers
    
    def get_vad_analyzer(self) -> Optional[VADAnalyzer]:
        """Get VAD analyzer instance"""
        if not self.enable_vad:
            return None
            
        if self.vad_analyzer:
            return self.vad_analyzer
            
        # Default to Silero VAD
        return SileroVADAnalyzer()
    
    def to_transport_params(self) -> TransportParams:
        """Convert to Pipecat TransportParams"""
        return TransportParams(
            audio_in_enabled=self.audio_in_enabled,
            audio_out_enabled=self.audio_out_enabled,
            video_in_enabled=self.video_in_enabled,
            video_out_enabled=self.video_out_enabled,
            audio_in_sample_rate=self.sample_rate,
            audio_out_sample_rate=self.sample_rate,
            audio_in_channels=self.channels,
            audio_out_channels=self.channels,
            vad_analyzer=self.get_vad_analyzer(),
        )


@dataclass
class SessionInfo:
    """Information about an active session"""
    session_id: str
    transport_type: TransportType
    config: TransportConfig
    context: OpenAILLMContext
    pipeline: Optional[Pipeline] = None
    task: Optional[PipelineTask] = None
    pipeline_task: Optional[PipelineTask] = None  # For compatibility
    runner: Optional[PipelineRunner] = None
    transport: Optional[BaseTransport] = None
    created_at: datetime = None
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.last_activity is None:
            self.last_activity = datetime.now(timezone.utc)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)


class BaseTransportManager(ABC):
    """Base class for transport managers"""
    
    def __init__(self, config: TransportConfig):
        self.config = config
        self.active_sessions: Dict[str, SessionInfo] = {}
        self.logger = logger.bind(transport_type=config.transport_type.value)
        
    @abstractmethod
    async def create_session(self, session_id: str, **kwargs) -> SessionInfo:
        """Create a new session with this transport"""
        pass
    
    @abstractmethod
    async def destroy_session(self, session_id: str) -> None:
        """Destroy a session"""
        pass
    
    @abstractmethod
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Send a message to a session"""
        pass
    
    @abstractmethod
    async def handle_client_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Handle a message from a client"""
        pass
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session info"""
        return self.active_sessions.get(session_id)
    
    def update_session_activity(self, session_id: str):
        """Update session activity"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].update_activity()
    
    async def cleanup_inactive_sessions(self, timeout_seconds: int = 300):
        """Clean up inactive sessions"""
        now = datetime.now(timezone.utc)
        inactive_sessions = []
        
        for session_id, session_info in self.active_sessions.items():
            if (now - session_info.last_activity).total_seconds() > timeout_seconds:
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            self.logger.info("Cleaning up inactive session", session_id=session_id)
            await self.destroy_session(session_id)
