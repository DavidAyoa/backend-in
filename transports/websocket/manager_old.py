#!/usr/bin/env python3
"""
Simplified WebSocket Transport Manager - following Pipecat best practices
"""

import uuid
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
import structlog

from transports.base import BaseTransportManager, TransportConfig, TransportType, SessionInfo
from bot.flexible_conversation import create_voice_conversation, create_text_conversation, create_hybrid_conversation

logger = structlog.get_logger()


class WebSocketTransportManager(BaseTransportManager):
    """Simplified WebSocket transport manager"""
    
    def __init__(self, config: TransportConfig):
        if config.transport_type != TransportType.WEBSOCKET:
            raise ValueError("WebSocket transport manager requires WebSocket transport type")
        super().__init__(config)
        
async def handle_websocket_endpoint(self, websocket: WebSocket):
session_id = str(uuid.uuid4())
await websocket.accept()
try:
await self.create_session_from_websocket(websocket, session_id)
await self.run_session(session_id)
except (WebSocketDisconnect, Exception) as e:
self.logger.error(
"WebSocket endpoint error", error=str(e), session_id=session_id)
finally:
await self.destroy_session(session_id)
        
        try:
            # Create FastAPI WebSocket transport parameters
            ws_params = FastAPIWebsocketParams(
                audio_in_enabled=self.config.audio_in_enabled,
                audio_out_enabled=self.config.audio_out_enabled,
                add_wav_header=True,
                vad_analyzer=self.config.get_vad_analyzer(),
                serializer=ProtobufFrameSerializer(),
            )
            
            # Create the FastAPI WebSocket transport
            transport = FastAPIWebsocketTransport(
                websocket=websocket,
                params=ws_params,
            )
            
# Call create_voice_conversation directly
await flexible_bot.create_voice_conversation(
websocket=websocket,
agent_id=None,
session_id=session_id
)
return SessionInfo(
session_id=session_id,
transport_type=TransportType.WEBSOCKET,
config=self.config,
)
            
            # Store session
            self.active_sessions[session_id] = session_info
            
            self.logger.info(
                "WebSocket session created",
                session_id=session_id,
                mode=mode.name if hasattr(mode, 'name') else str(mode)
            )
            
            return session_info
            
        except Exception as e:
            self.logger.error(
                "Failed to create WebSocket session",
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def run_session(self, session_id: str) -> None:
        """
        Run the pipeline for a WebSocket session
        This should be called after create_session_from_websocket
        """
        session_info = self.get_session(session_id)
        if not session_info:
            raise ValueError(f"Session {session_id} not found")
        
        try:
            # Start the pipeline runner with the task
            await session_info.runner.run(session_info.task)
            
        except Exception as e:
            self.logger.error(
                "Error running WebSocket session",
                session_id=session_id,
                error=str(e)
            )
            # Cleanup on error
            await self.destroy_session(session_id)
            raise
    
    async def destroy_session(self, session_id: str) -> None:
        """Destroy a WebSocket session"""
        if session_id not in self.active_sessions:
            return
            
        session_info = self.active_sessions[session_id]
        
        try:
            # Cleanup in flexible_bot first
            await flexible_bot.cleanup_session(session_id)
            
            # Stop pipeline runner
            if session_info.runner:
                await session_info.runner.stop()
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            self.logger.info("WebSocket session destroyed", session_id=session_id)
            
        except Exception as e:
            self.logger.error(
                "Error destroying WebSocket session",
                session_id=session_id,
                error=str(e)
            )
    
    async def send_message_to_session(self, session_id: str, message: Dict[str, Any]) -> None:
        """Send a message to a WebSocket session through the pipeline"""
        session_info = self.get_session(session_id)
        if not session_info or not session_info.task:
            self.logger.warning(
                "Cannot send message to non-existent session",
                session_id=session_id
            )
            return
        
        try:
            # Convert message to appropriate frame type and queue it
            if message.get('type') == 'text':
                text_frame = TextFrame(message.get('text', ''))
                await session_info.task.queue_frames([text_frame])
            elif message.get('type') == 'llm_messages':
                llm_frame = LLMMessagesFrame(message.get('messages', []))
                await session_info.task.queue_frames([llm_frame])
            
            self.update_session_activity(session_id)
            
        except Exception as e:
            self.logger.error(
                "Error sending message to WebSocket session",
                session_id=session_id,
                error=str(e)
            )
    
    async def handle_websocket_endpoint(
        self, 
        websocket: WebSocket, 
        session_id: Optional[str] = None,
        mode: Optional[ConversationMode] = None,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None
    ) -> None:
        """
        Complete WebSocket endpoint handler that can be used directly in FastAPI
        
        Usage:
        @app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str = None):
            await ws_manager.handle_websocket_endpoint(websocket, session_id)
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
            
        await websocket.accept()
        
        try:
            # Create session
            session_info = await self.create_session_from_websocket(
                websocket, session_id, mode
            )
            
            # Call connect callback if provided
            if on_connect:
                await on_connect(session_id, session_info)
            
            # Run the pipeline (this will handle the WebSocket communication)
            await self.run_session(session_id)
            
        except WebSocketDisconnect:
            self.logger.info("WebSocket disconnected", session_id=session_id)
        except Exception as e:
            self.logger.error(
                "Error in WebSocket endpoint",
                session_id=session_id,
                error=str(e)
            )
        finally:
            # Cleanup
            if on_disconnect:
                await on_disconnect(session_id)
            await self.destroy_session(session_id)
    
    # Legacy compatibility methods (these are not needed for the new architecture)
    async def create_session(self, session_id: str, **kwargs) -> SessionInfo:
        """Legacy method - use create_session_from_websocket instead"""
        raise NotImplementedError(
            "Use create_session_from_websocket instead for FastAPI WebSocket connections"
        )
    
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Legacy method - use send_message_to_session instead"""
        await self.send_message_to_session(session_id, message)
    
    async def handle_client_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Legacy method - messages are handled automatically by the pipeline"""
        self.logger.warning(
            "handle_client_message is not needed with FastAPIWebsocketTransport - "
            "messages are handled automatically by the pipeline"
        )