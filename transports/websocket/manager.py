#!/usr/bin/env python3
"""
Simplified WebSocket Transport Manager - thin wrapper following Pipecat best practices
"""

import uuid
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
import structlog

from transports.base import BaseTransportManager, TransportConfig, TransportType
from bot.flexible_conversation import create_voice_conversation, create_text_conversation, create_hybrid_conversation

logger = structlog.get_logger()


class WebSocketTransportManager(BaseTransportManager):
    """Simplified WebSocket transport manager - thin wrapper"""
    
    def __init__(self, config: TransportConfig):
        if config.transport_type != TransportType.WEBSOCKET:
            raise ValueError("WebSocket transport manager requires WebSocket transport type")
        super().__init__(config)
    
    async def handle_websocket_endpoint(
        self, 
        websocket: WebSocket, 
        agent_id: Optional[int] = None,
        session_id: Optional[str] = None,
        voice_input: bool = True,
        voice_output: bool = True,
        system_prompt: Optional[str] = None
    ) -> None:
        """
        Simplified WebSocket endpoint handler that delegates to conversation functions
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        try:
            # Determine conversation type and delegate to flexible_conversation
            if voice_input and voice_output:
                await create_voice_conversation(
                    websocket=websocket,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            elif not voice_input and not voice_output:
                await create_text_conversation(
                    websocket=websocket,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            else:
                await create_hybrid_conversation(
                    websocket=websocket,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
        
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected", session_id=session_id)
        except Exception as e:
            logger.error("WebSocket error", session_id=session_id, error=str(e))
    
    # Legacy compatibility - not needed in new architecture
    async def create_session(self, session_id: str, **kwargs):
        """Legacy method - use handle_websocket_endpoint instead"""
        raise NotImplementedError("Use handle_websocket_endpoint instead")
    
    async def destroy_session(self, session_id: str) -> None:
        """Not needed - handled automatically by conversation functions"""
        pass
