#!/usr/bin/env python3
"""
WebRTC Transport Manager using Pipecat's SmallWebRTCTransport
"""

import asyncio
import uuid
from typing import Dict, Any, Optional

import structlog
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

from transports.base import BaseTransportManager, TransportConfig, TransportType, SessionInfo
from services.session_manager import session_manager

logger = structlog.get_logger()


class WebRTCTransportManager(BaseTransportManager):
    """WebRTC transport manager using SmallWebRTCTransport"""
    
    def __init__(self, config: TransportConfig):
        if config.transport_type != TransportType.WEBRTC:
            raise ValueError("WebRTC transport manager requires WebRTC transport type")
        super().__init__(config)
        
    async def create_session(self, session_id: str, **kwargs) -> SessionInfo:
        """Create a new WebRTC session"""
        # Get WebRTC signaling data from client
        client_sdp = kwargs.get('client_sdp')
        sdp_type = kwargs.get('sdp_type', 'offer')
        
        if not client_sdp:
            raise ValueError("WebRTC session requires client SDP")
        
        try:
            # Create WebRTC connection
            ice_servers = self.config.get_default_ice_servers()
            webrtc_connection = SmallWebRTCConnection(ice_servers=ice_servers)
            
            # Initialize with client's SDP offer
            await webrtc_connection.initialize(sdp=client_sdp, type=sdp_type)
            
            # Create transport
            transport = SmallWebRTCTransport(
                webrtc_connection=webrtc_connection,
                params=self.config.to_transport_params(),
            )
            
            # Create LLM context
            context = OpenAILLMContext()
            
            # Create session info
            session_info = SessionInfo(
                session_id=session_id,
                transport_type=TransportType.WEBRTC,
                config=self.config,
                context=context,
                transport=transport
            )
            
            # Setup event handlers
            await self._setup_event_handlers(session_info, webrtc_connection)
            
            # Create and start pipeline
            from bot.pipeline_factory import create_pipeline
            pipeline = await create_pipeline(transport, context, self.config)
            session_info.pipeline = pipeline
            
            # Connect WebRTC
            await webrtc_connection.connect()
            
            # Store session
            self.active_sessions[session_id] = session_info
            
            self.logger.info(
                "WebRTC session created",
                session_id=session_id,
                ice_servers_count=len(ice_servers)
            )
            
            return session_info
            
        except Exception as e:
            self.logger.error(
                "Failed to create WebRTC session",
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def destroy_session(self, session_id: str) -> None:
        """Destroy a WebRTC session"""
        if session_id not in self.active_sessions:
            return
            
        session_info = self.active_sessions[session_id]
        
        try:
            # Stop pipeline
            if session_info.runner:
                await session_info.runner.stop()
            
            # Close WebRTC connection
            if session_info.transport and hasattr(session_info.transport, 'webrtc_connection'):
                await session_info.transport.webrtc_connection.close()
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            self.logger.info("WebRTC session destroyed", session_id=session_id)
            
        except Exception as e:
            self.logger.error(
                "Error destroying WebRTC session",
                session_id=session_id,
                error=str(e)
            )
    
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Send a message to a WebRTC session"""
        session_info = self.get_session(session_id)
        if not session_info or not session_info.transport:
            self.logger.warning(
                "Cannot send message to non-existent session",
                session_id=session_id
            )
            return
        
        try:
            # Send app message via WebRTC connection
            if hasattr(session_info.transport, 'webrtc_connection'):
                session_info.transport.webrtc_connection.send_app_message(message)
            
            self.update_session_activity(session_id)
            
        except Exception as e:
            self.logger.error(
                "Error sending message to WebRTC session",
                session_id=session_id,
                error=str(e)
            )
    
    async def handle_client_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Handle a message from a WebRTC client"""
        session_info = self.get_session(session_id)
        if not session_info:
            return
        
        try:
            message_type = message.get('type')
            
            if message_type == 'renegotiate':
                await self._handle_renegotiation(session_info, message)
            elif message_type == 'app_message':
                await self._handle_app_message(session_info, message)
            else:
                self.logger.warning(
                    "Unknown message type from WebRTC client",
                    session_id=session_id,
                    message_type=message_type
                )
            
            self.update_session_activity(session_id)
            
        except Exception as e:
            self.logger.error(
                "Error handling WebRTC client message",
                session_id=session_id,
                error=str(e)
            )
    
    async def get_session_answer(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the SDP answer for a WebRTC session"""
        session_info = self.get_session(session_id)
        if not session_info or not session_info.transport:
            return None
        
        try:
            if hasattr(session_info.transport, 'webrtc_connection'):
                return session_info.transport.webrtc_connection.get_answer()
        except Exception as e:
            self.logger.error(
                "Error getting WebRTC session answer",
                session_id=session_id,
                error=str(e)
            )
        
        return None
    
    async def _setup_event_handlers(self, session_info: SessionInfo, webrtc_connection: SmallWebRTCConnection):
        """Setup WebRTC event handlers"""
        
        @webrtc_connection.event_handler("connected")
        async def on_connected(connection):
            self.logger.info(
                "WebRTC connection established",
                session_id=session_info.session_id
            )
            # Start pipeline runner here if needed
        
        @webrtc_connection.event_handler("disconnected")
        async def on_disconnected(connection):
            self.logger.info(
                "WebRTC connection lost",
                session_id=session_info.session_id
            )
            await self.destroy_session(session_info.session_id)
        
        @webrtc_connection.event_handler("failed")
        async def on_failed(connection):
            self.logger.error(
                "WebRTC connection failed",
                session_id=session_info.session_id
            )
            await self.destroy_session(session_info.session_id)
        
        @webrtc_connection.event_handler("app-message")
        async def on_app_message(connection, message):
            await self.handle_client_message(session_info.session_id, {
                'type': 'app_message',
                'data': message
            })
    
    async def _handle_renegotiation(self, session_info: SessionInfo, message: Dict[str, Any]):
        """Handle WebRTC renegotiation"""
        if not hasattr(session_info.transport, 'webrtc_connection'):
            return
        
        sdp = message.get('sdp')
        sdp_type = message.get('sdp_type', 'offer')
        restart_pc = message.get('restart_pc', False)
        
        if sdp:
            await session_info.transport.webrtc_connection.renegotiate(
                sdp=sdp,
                type=sdp_type,
                restart_pc=restart_pc
            )
    
    async def _handle_app_message(self, session_info: SessionInfo, message: Dict[str, Any]):
        """Handle application message from WebRTC client"""
        data = message.get('data', {})
        
        # Handle different app message types
        if data.get('action') == 'text_input':
            # Handle text input from client
            text = data.get('text')
            if text and session_info.task:
                # Queue text frame to pipeline
                from pipecat.frames.frames import TextFrame
                await session_info.task.queue_frames([TextFrame(text)])
        
        # Add more app message handlers as needed
