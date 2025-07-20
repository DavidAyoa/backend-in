#!/usr/bin/env python3
"""
Simplified Conversation Bot Implementation
Following Pipecat best practices with minimal complexity and proper separation of concerns
"""

import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone

from dotenv import load_dotenv
import structlog

from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
from pipecat.frames.frames import (
    Frame, TranscriptionFrame, LLMMessagesFrame
)

# Import your existing config and services
from config import config
from services.session_manager import session_manager

load_dotenv(override=True)
slog = structlog.get_logger()

@dataclass
class BotConfig:
    """Simple configuration for bot modes"""
    enable_voice_input: bool = True
    enable_voice_output: bool = True
    enable_interruptions: bool = True
    agent_id: Optional[int] = None
    session_id: Optional[str] = None
    system_prompt: Optional[str] = None

# Removed SimpleTextProcessor - using standard Pipecat processors instead

def get_context(session_id: Optional[str], system_prompt: Optional[str]) -> OpenAILLMContext:
    """Simple context creation - let Pipecat handle the complexity"""
    if session_id and session_id in session_manager.sessions:
        session = session_manager.get_session(session_id)
        if session and session.context:
            slog.info("Using existing session context", session_id=session_id)
            return session.context
    
    # Create new context
    prompt = system_prompt or config.get_system_prompt()
    context = OpenAILLMContext([
        {"role": "system", "content": prompt}
    ])
    
    slog.info("Created new session context", session_id=session_id)
    return context

class PipecatConversationBot:
    """Simplified conversation bot following Pipecat patterns"""
    
    def __init__(self):
        slog.info("Initialized PipecatConversationBot")
    
    async def create_pipeline(
        self,
        websocket,
        bot_config: BotConfig
    ) -> PipelineTask:
        """Create a pipeline with proper component ordering"""
        
        # Get session context using simplified approach
        context = get_context(bot_config.session_id, bot_config.system_prompt)
        
        # Create services
        transport = await self._create_transport(websocket, bot_config)
        llm_service = self._create_llm_service()
        context_aggregator = llm_service.create_context_aggregator(context)
        
        # Build pipeline components in correct Pipecat order
        components = [
            transport.input(),    # Input from transport
        ]
        
        # Add STT if voice input enabled
        if bot_config.enable_voice_input:
            stt_service = self._create_stt_service()
            components.append(stt_service)
        
        # Context aggregator user side (captures user messages)
        components.append(context_aggregator.user())
        
        # LLM service processes the conversation
        components.append(llm_service)
        
        # Add TTS if voice output enabled
        if bot_config.enable_voice_output:
            tts_service = self._create_tts_service(bot_config.agent_id)
            components.append(tts_service)
        
        # Context aggregator assistant side (captures assistant responses) - BEFORE output
        components.append(context_aggregator.assistant())
        
        # Output to transport
        components.append(transport.output())
        
        # Create pipeline and task
        pipeline = Pipeline(components)
        task = self._create_pipeline_task(pipeline, bot_config)
        
        # Set up transport event handlers - this is where WebSocket communication happens
        await self._setup_transport_handlers(transport, task, bot_config)
        
        return task
    
    def _create_pipeline_task(self, pipeline: Pipeline, bot_config: BotConfig) -> PipelineTask:
        """Create pipeline task with appropriate parameters following Pipecat best practices"""
        task_params = PipelineParams(
            allow_interruptions=bot_config.enable_interruptions,
            enable_metrics=getattr(config, 'ENABLE_METRICS', False),
            enable_usage_metrics=getattr(config, 'ENABLE_METRICS', False),
            # Audio processing configuration
            audio_in_sample_rate=16000,  # Standard sample rate for STT services
            audio_out_sample_rate=24000,  # Higher quality for TTS output
        )
        
        return PipelineTask(
            pipeline, 
            params=task_params,
            # Idle detection configuration - 5 minutes timeout
            idle_timeout_secs=300,
            cancel_on_idle_timeout=True,
            # Enable checking for dangling tasks
            check_dangling_tasks=True,
            # Conversation ID for tracking
            conversation_id=bot_config.session_id
        )
    
    async def _create_transport(self, transport_or_websocket, bot_config: BotConfig):
        """Create transport with appropriate configuration"""
        
        # If it's already a SmallWebRTCTransport, return it as-is
        if isinstance(transport_or_websocket, SmallWebRTCTransport):
            return transport_or_websocket
        
        # Otherwise, create a FastAPI WebSocket transport
        # Configure VAD if voice input is enabled
        vad_analyzer = None
        if bot_config.enable_voice_input:
            vad_analyzer = SileroVADAnalyzer(
                params=VADParams(min_speech_duration_ms=500)
            )
        
        params = FastAPIWebsocketParams(
            audio_in_enabled=bot_config.enable_voice_input,
            audio_out_enabled=bot_config.enable_voice_output,
            add_wav_header=False,
            vad_analyzer=vad_analyzer,
            serializer=ProtobufFrameSerializer(),
        )
        
        return FastAPIWebsocketTransport(
            websocket=transport_or_websocket,
            params=params
        )
    
    def _create_llm_service(self) -> OpenAILLMService:
        """Create LLM service"""
        return OpenAILLMService(
            api_key=config.OPENAI_API_KEY,
            model=getattr(config, 'LLM_MODEL', "gpt-4o-mini"),
        )
    
    def _create_stt_service(self) -> GoogleSTTService:
        """Create STT service"""
        return GoogleSTTService(
            credentials=config.GOOGLE_CREDENTIALS,
            language="en-US",
        )
    
    def _create_tts_service(self, agent_id: Optional[int] = None) -> GoogleTTSService:
        """Create TTS service with agent-specific voice selection"""
        # Simple voice selection based on agent_id
        voice_map = {
            1: "en-US-Chirp3-HD-Achernar",
            2: "en-US-Chirp3-HD-Achird",
            3: "en-US-Chirp3-HD-Aoede",
            4: "en-US-Chirp3-HD-Charon",
            5: "en-US-Chirp3-HD-Despina",
        }
        
        voice_name = voice_map.get(agent_id, "en-US-Chirp3-HD-Laomedeia")
        
        return GoogleTTSService(
            credentials=config.GOOGLE_CREDENTIALS,
            voice_id=voice_name,
            language="en-US",
        )
    
    async def _setup_transport_handlers(
        self, 
        transport, 
        task: PipelineTask,
        bot_config: BotConfig
    ):
        """Set up simplified transport event handlers"""
        
        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            slog.info("First participant joined", session_id=bot_config.session_id)
            # Send initial greeting through the pipeline using proper frame
            await task.queue_frame(
                LLMMessagesFrame([{"role": "user", "content": "Hello!"}])
            )
        
        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            slog.info("Participant left", session_id=bot_config.session_id, reason=reason)
            # Gracefully end the task when participant leaves
            await task.stop_when_done()
        
        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            slog.info("Client disconnected", session_id=bot_config.session_id)
            # Immediately cancel on disconnect
            await task.cancel()
        
        @transport.event_handler("on_client_closed")
        async def on_client_closed(transport, client):
            slog.info("Client connection closed", session_id=bot_config.session_id)
            # Immediately cancel on close
            await task.cancel()

# Simplified factory functions - Return tasks, don't run them
async def create_websocket_voice_conversation(
    websocket, 
    agent_id: Optional[int] = None, 
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    activity_tracker: Optional = None
):
    """Create a WebSocket voice-enabled conversation - Returns task, doesn't run it"""
    bot = PipecatConversationBot()
    bot_config = BotConfig(
        enable_voice_input=True,
        enable_voice_output=True,
        enable_interruptions=True,
        agent_id=agent_id,
        session_id=session_id,
        system_prompt=system_prompt
    )
    
    # Return the task instead of running it
    return await bot.create_pipeline(websocket, bot_config)

async def create_websocket_text_conversation(
    websocket, 
    agent_id: Optional[int] = None, 
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    activity_tracker: Optional = None
):
    """Create a WebSocket text-only conversation - Returns task, doesn't run it"""
    bot = PipecatConversationBot()
    bot_config = BotConfig(
        enable_voice_input=False,
        enable_voice_output=False,
        enable_interruptions=False,
        agent_id=agent_id,
        session_id=session_id,
        system_prompt=system_prompt
    )
    
    # Return the task instead of running it
    return await bot.create_pipeline(websocket, bot_config)


async def create_webrtc_voice_conversation(
    transport: SmallWebRTCTransport,
    agent_id: Optional[int] = None, 
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None
):
    """Create a WebRTC voice-enabled conversation - Returns task, doesn't run it"""
    bot = PipecatConversationBot()
    bot_config = BotConfig(
        enable_voice_input=True,
        enable_voice_output=True,
        enable_interruptions=True,
        agent_id=agent_id,
        session_id=session_id,
        system_prompt=system_prompt
    )
    
    # Return the task instead of running it
    return await bot.create_pipeline(transport, bot_config)

async def create_webrtc_text_conversation(
    transport: SmallWebRTCTransport,
    agent_id: Optional[int] = None, 
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None
):
    """Create a WebRTC text-only conversation - Returns task, doesn't run it"""
    bot = PipecatConversationBot()
    bot_config = BotConfig(
        enable_voice_input=False,
        enable_voice_output=False,
        enable_interruptions=False,
        agent_id=agent_id,
        session_id=session_id,
        system_prompt=system_prompt
    )
    
    # Return the task instead of running it
    return await bot.create_pipeline(transport, bot_config)

async def create_webrtc_hybrid_conversation(
    transport: SmallWebRTCTransport,
    agent_id: Optional[int] = None, 
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None
):
    """Create a WebRTC-enabled conversation with both voice and text - Returns task, doesn't run it"""
    bot = PipecatConversationBot()
    bot_config = BotConfig(
        enable_voice_input=True,
        enable_voice_output=True,
        enable_interruptions=True,
        agent_id=agent_id,
        session_id=session_id,
        system_prompt=system_prompt
    )
    
    # Return the task instead of running it
    return await bot.create_pipeline(transport, bot_config)

# Export the main functions
__all__ = [
    'PipecatConversationBot', 
    'BotConfig',
    'get_context',
    'create_websocket_voice_conversation',
    'create_websocket_text_conversation',
    'create_webrtc_voice_conversation',
    'create_webrtc_text_conversation',
    'create_webrtc_hybrid_conversation'
]
