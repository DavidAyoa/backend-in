#!/usr/bin/env python3
"""
Simplified WebRTC Transport Manager - thin wrapper following Pipecat best practices
"""

import asyncio
import uuid
from typing import Dict, Any, Optional

import structlog
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection
from pipecat.pipeline.pipeline import Pipeline

from transports.base import BaseTransportManager, TransportConfig, TransportType, SessionInfo
from bot.flexible_conversation import (
    create_webrtc_voice_conversation, 
    create_webrtc_text_conversation, 
    create_webrtc_hybrid_conversation
)

logger = structlog.get_logger()


class WebRTCTransportManager(BaseTransportManager):
    """Simplified WebRTC transport manager - thin wrapper"""
    
    def __init__(self, config: TransportConfig):
        if config.transport_type != TransportType.WEBRTC:
            raise ValueError("WebRTC transport manager requires WebRTC transport type")
        super().__init__(config)
        
    async def create_session(self, session_id: str, **kwargs) -> SessionInfo:
        """Create a new WebRTC session - simplified to delegate to conversation functions"""
        # Get WebRTC signaling data from client
        client_sdp = kwargs.get('client_sdp')
        sdp_type = kwargs.get('sdp_type', 'offer')
        agent_id = kwargs.get('agent_id')
        voice_input = kwargs.get('voice_input', True)
        voice_output = kwargs.get('voice_output', True)
        system_prompt = kwargs.get('system_prompt')
        
        if not client_sdp:
            raise ValueError("WebRTC session requires client SDP")
        
        try:
            # Create WebRTC connection with ICE servers
            ice_servers = self.config.get_default_ice_servers() or [{"urls": "stun:stun.l.google.com:19302"}]
            webrtc_connection = SmallWebRTCConnection(ice_servers=ice_servers)
            
            # Initialize and connect
            await webrtc_connection.initialize(sdp=client_sdp, type=sdp_type)
            await webrtc_connection.connect()
            
            # Create transport
            transport = SmallWebRTCTransport(
                webrtc_connection=webrtc_connection,
                params=self.config.to_transport_params(),
            )
            
            # Delegate to appropriate WebRTC conversation function
            if voice_input and voice_output:
                await create_webrtc_voice_conversation(
                    transport=transport,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            elif not voice_input and not voice_output:
                await create_webrtc_text_conversation(
                    transport=transport,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            else:
                await create_webrtc_hybrid_conversation(
                    transport=transport,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            
            # Return minimal session info
            session_info = SessionInfo(
                session_id=session_id,
                transport_type=TransportType.WEBRTC,
                config=self.config,
                transport=transport,  # Add this line
            )
            
            self.active_sessions[session_id] = session_info
            logger.info("WebRTC session created", session_id=session_id)
            return session_info
            
        except Exception as e:
            logger.error(
                "Failed to create WebRTC session",
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def destroy_session(self, session_id: str) -> None:
        """Not needed - handled automatically by conversation functions"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info("WebRTC session destroyed", session_id=session_id)
    
    async def get_session_answer(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the SDP answer for a WebRTC session"""
        session_info = self.get_session(session_id)
        if not session_info or not session_info.transport:
            return None
        
        try:
            if hasattr(session_info.transport, 'webrtc_connection'):
                # Wait for answer with timeout
                answer = None
                timeout_seconds = 10
                for _ in range(timeout_seconds * 10):  # Check every 100ms
                    answer = session_info.transport.webrtc_connection.get_answer()
                    if answer:
                        break
                    await asyncio.sleep(0.1)
                
                if not answer:
                    raise TimeoutError("SDP answer timeout")
                return answer
                
        except Exception as e:
            self.logger.error(
                "Error getting WebRTC session answer",
                session_id=session_id,
                error=str(e)
            )
        
        return None
    
