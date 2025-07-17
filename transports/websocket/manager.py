#!/usr/bin/env python3
"""
WebSocket Transport Manager using Pipecat's WebsocketServerTransport
"""

import asyncio
import uuid
from typing import Dict, Any, Optional

import structlog
from pipecat.transports.network.websocket_server import (
    WebsocketServerTransport,
    WebsocketServerParams,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.frames.frames import LLMMessagesFrame

from transports.base import BaseTransportManager, TransportConfig, TransportType, SessionInfo
from services.session_manager import session_manager

logger = structlog.get_logger()


class WebSocketTransportManager(BaseTransportManager):
    """WebSocket transport manager using WebsocketServerTransport"""
    
    def __init__(self, config: TransportConfig):
        if config.transport_type != TransportType.WEBSOCKET:
            raise ValueError("WebSocket transport manager requires WebSocket transport type")
        super().__init__(config)
        self.server_transport = None
        self.host = "localhost"
        self.port = 8765
        
    async def initialize_server(self, host: str = "localhost", port: int = 8765):
        """Initialize the WebSocket server"""
        self.host = host
        self.port = port
        
        # Create WebSocket server transport parameters
        ws_params = WebsocketServerParams(
            audio_in_enabled=self.config.audio_in_enabled,
            audio_out_enabled=self.config.audio_out_enabled,
            add_wav_header=True,
            vad_analyzer=self.config.get_vad_analyzer(),
            session_timeout=self.config.websocket_timeout,
            serializer=ProtobufFrameSerializer(),
        )
        
        # Create the WebSocket server transport
        self.server_transport = WebsocketServerTransport(
            host=self.host,
            port=self.port,
            params=ws_params
        )
        
        # Setup event handlers
        await self._setup_server_event_handlers()
        
        self.logger.info(
            "WebSocket server initialized",
            host=self.host,
            port=self.port
        )
        
    async def create_session(self, session_id: str, **kwargs) -> SessionInfo:
        """Create a new WebSocket session"""
        client = kwargs.get('client')
        
        if not client:
            raise ValueError("WebSocket session requires client connection")
        
        if not self.server_transport:
            raise RuntimeError("WebSocket server not initialized")
        
        try:
            # Create LLM context
            context = OpenAILLMContext()
            
            # Create session info
            session_info = SessionInfo(
                session_id=session_id,
                transport_type=TransportType.WEBSOCKET,
                config=self.config,
                context=context,
                transport=self.server_transport
            )
            
            # Create and start pipeline (lazy import to avoid circular dependency)
            from bot.pipeline_factory import create_pipeline
            pipeline = await create_pipeline(self.server_transport, context, self.config)
            session_info.pipeline = pipeline
            
            # Store session
            self.active_sessions[session_id] = session_info
            
            self.logger.info(
                "WebSocket session created",
                session_id=session_id,
                client_address=getattr(client, 'remote_address', None)
            )
            
            return session_info
            
        except Exception as e:
            self.logger.error(
                "Failed to create WebSocket session",
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def destroy_session(self, session_id: str) -> None:
        """Destroy a WebSocket session"""
        if session_id not in self.active_sessions:
            return
            
        session_info = self.active_sessions[session_id]
        
        try:
            # Stop pipeline
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
    
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Send a message to a WebSocket session"""
        session_info = self.get_session(session_id)
        if not session_info or not session_info.transport:
            self.logger.warning(
                "Cannot send message to non-existent session",
                session_id=session_id
            )
            return
        
        try:
            # For WebSocket server transport, we typically send frames through the pipeline
            # rather than direct messages. This could be extended based on your needs.
            if session_info.task:
                # Convert message to appropriate frame type
                from pipecat.frames.frames import TextFrame
                if message.get('type') == 'text':
                    text_frame = TextFrame(message.get('text', ''))
                    await session_info.task.queue_frames([text_frame])
            
            self.update_session_activity(session_id)
            
        except Exception as e:
            self.logger.error(
                "Error sending message to WebSocket session",
                session_id=session_id,
                error=str(e)
            )
    
    async def handle_client_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Handle a message from a WebSocket client"""
        session_info = self.get_session(session_id)
        if not session_info:
            return
        
        try:
            message_type = message.get('type')
            
            if message_type == 'text_input':
                await self._handle_text_input(session_info, message)
            elif message_type == 'control':
                await self._handle_control_message(session_info, message)
            else:
                self.logger.warning(
                    "Unknown message type from WebSocket client",
                    session_id=session_id,
                    message_type=message_type
                )
            
            self.update_session_activity(session_id)
            
        except Exception as e:
            self.logger.error(
                "Error handling WebSocket client message",
                session_id=session_id,
                error=str(e)
            )
    
    async def start_server(self):
        """Start the WebSocket server"""
        if not self.server_transport:
            raise RuntimeError("WebSocket server not initialized")
        
        # The WebSocket server transport handles its own server startup
        # This is typically done when the pipeline starts
        self.logger.info(
            "WebSocket server ready to accept connections",
            host=self.host,
            port=self.port
        )
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server_transport:
            # Clean up all active sessions
            for session_id in list(self.active_sessions.keys()):
                await self.destroy_session(session_id)
            
            self.logger.info("WebSocket server stopped")
    
    async def _setup_server_event_handlers(self):
        """Setup WebSocket server event handlers"""
        if not self.server_transport:
            return
        
        @self.server_transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            # Generate session ID for this client
            session_id = str(uuid.uuid4())
            
            try:
                await self.create_session(session_id, client=client)
                
                # Start initial conversation if needed
                session_info = self.get_session(session_id)
                if session_info and session_info.task:
                    # Queue initial messages or greeting
                    initial_messages = [
                        {"role": "system", "content": "You are a helpful voice assistant."}
                    ]
                    await session_info.task.queue_frames([
                        LLMMessagesFrame(initial_messages)
                    ])
                
                self.logger.info(
                    "Client connected to WebSocket server",
                    session_id=session_id,
                    client_address=getattr(client, 'remote_address', None)
                )
                
            except Exception as e:
                self.logger.error(
                    "Error handling client connection",
                    error=str(e)
                )
        
        @self.server_transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            # Find session for this client and destroy it
            session_to_destroy = None
            for session_id, session_info in self.active_sessions.items():
                # In a real implementation, you'd track client-to-session mapping
                # For now, we'll destroy the first session (single client scenario)
                session_to_destroy = session_id
                break
            
            if session_to_destroy:
                await self.destroy_session(session_to_destroy)
            
            self.logger.info(
                "Client disconnected from WebSocket server",
                client_address=getattr(client, 'remote_address', None)
            )
        
        @self.server_transport.event_handler("on_session_timeout")
        async def on_session_timeout(transport, client):
            # Handle session timeout
            session_to_destroy = None
            for session_id, session_info in self.active_sessions.items():
                session_to_destroy = session_id
                break
            
            if session_to_destroy:
                await self.destroy_session(session_to_destroy)
            
            self.logger.info(
                "Session timeout for WebSocket client",
                client_address=getattr(client, 'remote_address', None)
            )
    
    async def _handle_text_input(self, session_info: SessionInfo, message: Dict[str, Any]):
        """Handle text input from WebSocket client"""
        text = message.get('text')
        if text and session_info.task:
            # Queue text frame to pipeline
            from pipecat.frames.frames import TextFrame
            await session_info.task.queue_frames([TextFrame(text)])
    
    async def _handle_control_message(self, session_info: SessionInfo, message: Dict[str, Any]):
        """Handle control messages from WebSocket client"""
        action = message.get('action')
        
        if action == 'interrupt':
            # Handle interruption
            if session_info.task:
                await session_info.task.interrupt()
        elif action == 'pause':
            # Handle pause
            if session_info.runner:
                await session_info.runner.pause()
        elif action == 'resume':
            # Handle resume
            if session_info.runner:
                await session_info.runner.resume()
        else:
            self.logger.warning(
                "Unknown control action",
                session_id=session_info.session_id,
                action=action
            )
