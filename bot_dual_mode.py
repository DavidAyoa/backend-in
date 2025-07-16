#!/usr/bin/env python3
"""
Dual-Mode Bot Implementation
Supports both voice and text-only conversations with dynamic mode switching
"""

import os
import sys
import asyncio
import json
from typing import Dict, Optional, Any, Literal
from dataclasses import dataclass

from dotenv import load_dotenv
from loguru import logger
import structlog

from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
from pipecat.audio.interruptions.min_words_interruption_strategy import MinWordsInterruptionStrategy
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.processors.filters.stt_mute_filter import STTMuteFilter, STTMuteConfig, STTMuteStrategy
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.transcriptions.language import Language
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.frames.frames import Frame, TextFrame, AudioRawFrame, TranscriptionFrame

# Import configuration
from config import config
from services.session_manager import session_manager
from models.user import user_db
from bot_fast_api_enhanced import ServicePool

load_dotenv(override=True)

# Configure logging
slog = structlog.get_logger()

@dataclass
class ConversationMode:
    """Configuration for conversation mode"""
    mode: Literal["voice", "text"] = "voice"
    return_voice: bool = True
    return_transcript: bool = True
    enable_interruptions: bool = True

class DualModeServicePool(ServicePool):
    """Extended service pool with dual-mode support"""
    
    def __init__(self):
        super().__init__()
        self._mode_settings: Dict[str, ConversationMode] = {}
    
    def set_mode(self, session_id: str, mode: ConversationMode):
        """Set conversation mode for a session"""
        self._mode_settings[session_id] = mode
        slog.info("Mode set for session", session_id=session_id, mode=mode.mode)
    
    def get_mode(self, session_id: str) -> ConversationMode:
        """Get conversation mode for a session"""
        return self._mode_settings.get(session_id, ConversationMode())
    
    async def cleanup_session(self, session_id: str):
        """Clean up session including mode settings"""
        if session_id in self._mode_settings:
            del self._mode_settings[session_id]
        await super().cleanup_session(session_id)

# Enhanced service pool
dual_mode_service_pool = DualModeServicePool()

class DualModeFrameProcessor:
    """Process frames based on conversation mode"""
    
    def __init__(self, session_id: str, websocket, service_pool: DualModeServicePool):
        self.session_id = session_id
        self.websocket = websocket
        self.service_pool = service_pool
    
    async def process_frame(self, frame: Frame):
        """Process frame based on current mode"""
        mode = self.service_pool.get_mode(self.session_id)
        
        if isinstance(frame, TranscriptionFrame):
            # Always send transcript if enabled
            if mode.return_transcript:
                await self.websocket.send_text(json.dumps({
                    "type": "transcript",
                    "data": {
                        "text": frame.text,
                        "timestamp": frame.timestamp if hasattr(frame, 'timestamp') else None,
                        "is_final": getattr(frame, 'is_final', True)
                    }
                }))
        
        elif isinstance(frame, AudioRawFrame):
            # Only send audio if voice mode is enabled
            if mode.mode == "voice" and mode.return_voice:
                # This would be handled by the standard pipeline
                pass
        
        elif isinstance(frame, TextFrame):
            # Send text response based on mode
            response_data = {
                "type": "assistant_response",
                "data": {
                    "text": frame.text,
                    "timestamp": frame.timestamp if hasattr(frame, 'timestamp') else None
                }
            }
            
            if mode.mode == "text" or mode.return_transcript:
                await self.websocket.send_text(json.dumps(response_data))

async def run_dual_mode_bot(
    websocket_client, 
    session_id: Optional[str] = None, 
    agent_id: Optional[int] = None, 
    system_prompt: Optional[str] = None,
    initial_mode: ConversationMode = ConversationMode()
):
    """Enhanced bot runner with dual-mode support"""
    
    # Generate session ID if not provided
    if session_id is None:
        import uuid
        session_id = str(uuid.uuid4())
    
    # Set initial mode
    dual_mode_service_pool.set_mode(session_id, initial_mode)
    
    # Create or get session with agent-specific context
    if session_id not in session_manager.sessions:
        session_id = session_manager.create_session(session_id, agent_id, system_prompt)
    
    agent_session = session_manager.get_session(session_id)
    
    slog.info("Starting dual-mode bot session", session_id=session_id, mode=initial_mode.mode)
    
    try:
        # Get current mode
        current_mode = dual_mode_service_pool.get_mode(session_id)
        
        # Get services from pool
        stt = dual_mode_service_pool.get_stt_service(session_id)
        tts = dual_mode_service_pool.get_tts_service(session_id, agent_id)
        llm = dual_mode_service_pool.get_llm_service(session_id)
        vad_analyzer = dual_mode_service_pool.get_vad_analyzer(session_id)
        
        # Create transport with dynamic audio settings
        ws_transport = FastAPIWebsocketTransport(
            websocket=websocket_client,
            params=FastAPIWebsocketParams(
                audio_in_enabled=current_mode.mode == "voice",
                audio_out_enabled=current_mode.mode == "voice" and current_mode.return_voice,
                add_wav_header=False,
                vad_analyzer=vad_analyzer if current_mode.mode == "voice" else None,
                serializer=ProtobufFrameSerializer(),
            ),
        )
        
        # STT Mute Filter for better interruption control
        stt_mute_filter = STTMuteFilter(
            config=STTMuteConfig(
                strategies={
                    STTMuteStrategy.MUTE_UNTIL_FIRST_BOT_COMPLETE,
                    STTMuteStrategy.FUNCTION_CALL,
                }
            )
        )
        
        # Use agent session's context and LLM if available, otherwise create default
        if agent_session:
            context = agent_session.context
            context_aggregator = agent_session.context_aggregator
            llm = agent_session.llm  # Use session-specific LLM
        else:
            # Fallback to default context
            context = OpenAILLMContext(
                [
                    {
                        "role": "system",
                        "content": config.get_system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": "Start by greeting the user warmly and introducing yourself.",
                    }
                ],
            )
            context_aggregator = llm.create_context_aggregator(context)
        
        # RTVI events for Pipecat client UI
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
        
        # Create frame processor for dual-mode handling
        frame_processor = DualModeFrameProcessor(session_id, websocket_client, dual_mode_service_pool)
        
        # Build pipeline based on mode
        pipeline_components = [ws_transport.input()]
        
        if current_mode.mode == "voice":
            pipeline_components.extend([
                stt_mute_filter,
                stt,
            ])
        
        pipeline_components.extend([
            context_aggregator.user(),
            rtvi,
            llm,
        ])
        
        if current_mode.mode == "voice" and current_mode.return_voice:
            pipeline_components.append(tts)
        
        pipeline_components.extend([
            ws_transport.output(),
            context_aggregator.assistant(),
        ])
        
        # Create pipeline
        pipeline = Pipeline(pipeline_components)
        
        # Create task with optimized parameters
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                enable_metrics=config.ENABLE_METRICS,
                enable_usage_metrics=config.ENABLE_METRICS,
                allow_interruptions=current_mode.enable_interruptions,
                interruption_strategies=[
                    MinWordsInterruptionStrategy(min_words=3)
                ] if current_mode.enable_interruptions else []
            ),
            observers=[RTVIObserver(rtvi)] if config.ENABLE_METRICS else [],
        )
        
        # Event handlers
        @rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            slog.info("Client ready", session_id=session_id)
            await rtvi.set_bot_ready()
            await task.queue_frames([context_aggregator.user().get_context_frame()])
        
        @ws_transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            slog.info("Client connected to transport", session_id=session_id)
            # Send initial mode info
            await websocket_client.send_text(json.dumps({
                "type": "mode_info",
                "data": {
                    "mode": current_mode.mode,
                    "return_voice": current_mode.return_voice,
                    "return_transcript": current_mode.return_transcript,
                    "enable_interruptions": current_mode.enable_interruptions
                }
            }))
        
        @ws_transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            slog.info("Client disconnected from transport", session_id=session_id)
            await task.cancel()
        
        # Handle mode switching messages
        @ws_transport.event_handler("on_message")
        async def on_message(transport, message):
            try:
                data = json.loads(message)
                if data.get("type") == "mode_change":
                    new_mode_data = data.get("data", {})
                    new_mode = ConversationMode(
                        mode=new_mode_data.get("mode", current_mode.mode),
                        return_voice=new_mode_data.get("return_voice", current_mode.return_voice),
                        return_transcript=new_mode_data.get("return_transcript", current_mode.return_transcript),
                        enable_interruptions=new_mode_data.get("enable_interruptions", current_mode.enable_interruptions)
                    )
                    dual_mode_service_pool.set_mode(session_id, new_mode)
                    
                    # Send confirmation
                    await websocket_client.send_text(json.dumps({
                        "type": "mode_changed",
                        "data": {
                            "mode": new_mode.mode,
                            "return_voice": new_mode.return_voice,
                            "return_transcript": new_mode.return_transcript,
                            "enable_interruptions": new_mode.enable_interruptions
                        }
                    }))
                    
                    slog.info("Mode changed", session_id=session_id, new_mode=new_mode.mode)
                
                elif data.get("type") == "text_message":
                    # Handle text-only messages
                    text_content = data.get("data", {}).get("text", "")
                    if text_content:
                        # Add to context and process
                        context_aggregator.user().add_message({"role": "user", "content": text_content})
                        
                        # Send transcript if enabled
                        if current_mode.return_transcript:
                            await websocket_client.send_text(json.dumps({
                                "type": "transcript",
                                "data": {
                                    "text": text_content,
                                    "is_final": True,
                                    "source": "user"
                                }
                            }))
            
            except json.JSONDecodeError:
                slog.warning("Invalid JSON message received", session_id=session_id)
            except Exception as e:
                slog.error("Error processing message", session_id=session_id, error=str(e))
        
        # Create runner
        runner = PipelineRunner(handle_sigint=False)
        
        # Register services for cleanup
        dual_mode_service_pool.register_session(session_id, {
            'task': task,
            'runner': runner,
            'pipeline': pipeline,
            'transport': ws_transport
        })
        
        # Run the pipeline
        await runner.run(task)
        
    except Exception as e:
        slog.error("Dual-mode bot error", session_id=session_id, error=str(e))
        raise
    finally:
        # Clean up session
        await dual_mode_service_pool.cleanup_session(session_id)

# Export for use in main application
__all__ = ['run_dual_mode_bot', 'dual_mode_service_pool', 'ConversationMode', 'DualModeServicePool']
