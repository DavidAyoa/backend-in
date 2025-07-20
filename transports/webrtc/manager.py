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
from pipecat.pipeline.runner import PipelineRunner

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
        # Check concurrent session limits
        max_sessions = getattr(self.config, 'max_concurrent_sessions', 10)
        if len(self.active_sessions) >= max_sessions:
            logger.warning(
                "Maximum concurrent sessions reached", 
                active_sessions=len(self.active_sessions),
                max_sessions=max_sessions
            )
            raise RuntimeError(f"Maximum concurrent sessions ({max_sessions}) reached")
        
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
            
            # Get task from appropriate WebRTC conversation function
            pipeline_task = None
            if voice_input and voice_output:
                pipeline_task = await create_webrtc_voice_conversation(
                    transport=transport,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            elif not voice_input and not voice_output:
                pipeline_task = await create_webrtc_text_conversation(
                    transport=transport,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            else:
                # For mixed modes, default to voice conversation
                pipeline_task = await create_webrtc_voice_conversation(
                    transport=transport,
                    agent_id=agent_id,
                    session_id=session_id,
                    system_prompt=system_prompt
                )
            
            # Store the pipeline task in session info
            from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
            
            # Create a simple context for the session info
            context = OpenAILLMContext([{"role": "system", "content": system_prompt or "You are a helpful AI assistant."}])
            
            session_info = SessionInfo(
                session_id=session_id,
                transport_type=TransportType.WEBRTC,
                config=self.config,
                context=context,
                transport=transport,
                pipeline_task=pipeline_task
            )
            
            self.active_sessions[session_id] = session_info
            
            # Run the pipeline task immediately with proper error handling
            if pipeline_task:
                runner = PipelineRunner(handle_sigint=False)
                # Start the pipeline in a background task so we can return the session info
                async def run_with_cleanup():
                    try:
                        logger.info(
                            "Starting WebRTC pipeline", 
                            session_id=session_id,
                            agent_id=agent_id,
                            voice_enabled=voice_input and voice_output
                        )
                        await runner.run(pipeline_task)
                    except Exception as e:
                        logger.error("WebRTC pipeline error", session_id=session_id, error=str(e), exc_info=True)
                        # Clean up session on pipeline error
                        await self.destroy_session(session_id)
                    finally:
                        logger.info("WebRTC pipeline ended", session_id=session_id)
                
                import asyncio
                asyncio.create_task(run_with_cleanup())
            
            logger.info("WebRTC session created and pipeline started", session_id=session_id)
            return session_info
            
        except Exception as e:
            logger.error(
                "Failed to create WebRTC session",
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def destroy_session(self, session_id: str) -> None:
        """Destroy a WebRTC session and clean up resources"""
        if session_id in self.active_sessions:
            session_info = self.active_sessions[session_id]
            
            # Stop the pipeline task if it exists
            if session_info.pipeline_task:
                try:
                    await session_info.pipeline_task.cancel()
                    logger.debug("Pipeline task cancelled", session_id=session_id)
                except Exception as e:
                    logger.debug("Error cancelling pipeline task", session_id=session_id, error=str(e))
            
            # Clean up transport resources
            if hasattr(session_info.transport, 'webrtc_connection'):
                try:
                    # Close WebRTC connection if needed
                    await session_info.transport.webrtc_connection.close()
                except Exception as e:
                    logger.debug("Error closing WebRTC connection", session_id=session_id, error=str(e))
            
            del self.active_sessions[session_id]
            logger.info("WebRTC session destroyed", session_id=session_id)
    
    async def get_session_answer(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the SDP answer for a WebRTC session using correct Pipecat API"""
        session_info = self.get_session(session_id)
        if not session_info or not session_info.transport:
            logger.warning("Session not found or no transport", session_id=session_id)
            return None
        
        try:
            if hasattr(session_info.transport, 'webrtc_connection'):
                webrtc_connection = session_info.transport.webrtc_connection
                
                # Get answer using correct Pipecat API
                answer = webrtc_connection.get_answer()
                if answer:
                    logger.info("WebRTC answer retrieved successfully", session_id=session_id)
                    return answer
                else:
                    logger.error("No SDP answer available from WebRTC connection", session_id=session_id)
                    return None
                
        except Exception as e:
            logger.error(
                "Error getting WebRTC session answer",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )
        
        return None
    
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Send a message to a WebRTC session"""
        session_info = self.get_session(session_id)
        if not session_info or not session_info.pipeline_task:
            logger.warning("Cannot send message - session not found or inactive", session_id=session_id)
            return
        
        try:
            # Convert message to appropriate frame and queue it
            from pipecat.frames.frames import TextFrame, LLMMessagesFrame
            
            if 'text' in message:
                frame = TextFrame(text=message['text'])
                await session_info.pipeline_task.queue_frames([frame])
            elif 'messages' in message:
                frame = LLMMessagesFrame(messages=message['messages'])
                await session_info.pipeline_task.queue_frames([frame])
            else:
                logger.warning("Unknown message format", session_id=session_id, message_keys=list(message.keys()))
                
        except Exception as e:
            logger.error("Error sending message to WebRTC session", session_id=session_id, error=str(e))
    
    async def handle_client_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Handle a message from a WebRTC client"""
        session_info = self.get_session(session_id)
        if not session_info:
            logger.warning("Cannot handle message - session not found", session_id=session_id)
            return
        
        try:
            # Update session activity
            self.update_session_activity(session_id)
            
            # For WebRTC, client messages are typically handled through the transport's data channels
            # or via the pipeline's audio/video streams. This method can be used for control messages.
            message_type = message.get('type', 'unknown')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send_message(session_id, {'type': 'pong', 'timestamp': message.get('timestamp')})
            elif message_type == 'control':
                # Handle control messages (pause, resume, etc.)
                control_action = message.get('action')
                logger.info("WebRTC control message received", session_id=session_id, action=control_action)
                # Control actions would be implemented based on requirements
            else:
                logger.debug("Unhandled client message type", session_id=session_id, message_type=message_type)
                
        except Exception as e:
            logger.error("Error handling client message", session_id=session_id, error=str(e))
    
