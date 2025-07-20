#!/usr/bin/env python3
"""
Simplified WebSocket Transport Manager - thin wrapper following Pipecat best practices
"""

import uuid
from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
import structlog
from pipecat.pipeline.runner import PipelineRunner

from transports.base import BaseTransportManager, TransportConfig, TransportType
from bot.flexible_conversation import create_websocket_voice_conversation, create_websocket_text_conversation

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
        Proper WebSocket endpoint handler using PipelineRunner correctly
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        task = None
        
        try:
            await websocket.accept()
            
            # Create the pipeline task
            if voice_input and voice_output:
                task = await create_websocket_voice_conversation(
                    websocket=websocket,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            else:
                task = await create_websocket_text_conversation(
                    websocket=websocket,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            
            # Run the pipeline with proper runner
            if task:
                runner = PipelineRunner(handle_sigint=False)
                logger.info(
                    "Starting WebSocket pipeline", 
                    session_id=session_id, 
                    agent_id=agent_id,
                    voice_enabled=voice_input and voice_output
                )
                await runner.run(task)
        
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected normally", session_id=session_id)
        except Exception as e:
            logger.error("WebSocket error", session_id=session_id, error=str(e))
            try:
                if websocket.client_state != websocket.client_state.DISCONNECTED:
                    await websocket.close(code=1011, reason="Internal server error")
            except Exception:
                pass
        
        logger.info("WebSocket session ended", session_id=session_id)
    
    # Legacy compatibility - not needed in new architecture
    async def create_session(self, session_id: str, **kwargs):
        """Legacy method - use handle_websocket_endpoint instead"""
        raise NotImplementedError("Use handle_websocket_endpoint instead")
    
    async def destroy_session(self, session_id: str) -> None:
        """Not needed - handled automatically by conversation functions"""
        pass
    
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Send a message to a WebSocket session - not implemented for simplified manager"""
        logger.warning("WebSocket manager does not support send_message - use WebSocket directly", session_id=session_id)
    
    async def handle_client_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Handle a message from a WebSocket client - not implemented for simplified manager"""
        logger.debug("WebSocket manager handle_client_message called", session_id=session_id, message_type=message.get('type', 'unknown'))
