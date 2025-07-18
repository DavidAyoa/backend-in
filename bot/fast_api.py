#!/usr/bin/env python3
"""
Enhanced Bot FastAPI Implementation
Optimized for concurrent users with resource management
"""

import os
import sys
import asyncio
import weakref
from typing import Dict, Optional, Any

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

# Import configuration
from config import config
from services.session_manager import session_manager
from models.user import user_db

load_dotenv(override=True)

# Configure logging
slog = structlog.get_logger()

class ServicePool:
    """Pool of reusable AI services for better resource management"""
    
    def __init__(self):
        self._stt_pool: Dict[str, GoogleSTTService] = {}
        self._tts_pool: Dict[str, GoogleTTSService] = {}
        self._llm_pool: Dict[str, OpenAILLMService] = {}
        self._vad_pool: Dict[str, SileroVADAnalyzer] = {}
        self._active_services: Dict[str, Dict[str, Any]] = {}
        
    def get_stt_service(self, session_id: str) -> GoogleSTTService:
        """Get or create STT service for session"""
        if session_id not in self._stt_pool:
            self._stt_pool[session_id] = GoogleSTTService(
                credentials_path=config.GOOGLE_APPLICATION_CREDENTIALS,
                params=GoogleSTTService.InputParams(
                    languages=Language.EN_US,
                    model=config.GOOGLE_STT_MODEL,
                    enable_automatic_punctuation=True,
                    enable_interim_results=config.GOOGLE_STT_ENABLE_INTERIM
                )
            )
            slog.debug("Created STT service", session_id=session_id)
        return self._stt_pool[session_id]
    
    def get_tts_service(self, session_id: str, agent_id: Optional[int] = None) -> GoogleTTSService:
        """Get or create TTS service using agent-specific voice settings"""
        if session_id not in self._tts_pool:
            agent = user_db.get_agent_by_id(agent_id) if agent_id else None
            voice_settings = agent.get('voice_settings', {}) if agent else {}
            voice_id = voice_settings.get('voice_id', config.GOOGLE_TTS_VOICE)

            self._tts_pool[session_id] = GoogleTTSService(
                credentials_path=config.GOOGLE_APPLICATION_CREDENTIALS,
                voice_id=voice_id,
                params=GoogleTTSService.InputParams(
                    language=voice_settings.get('language', 'en-US'),
                )
            )
            slog.debug("Created TTS service with agent-specific voice", session_id=session_id, voice_id=voice_id)
        return self._tts_pool[session_id]
    
    def get_llm_service(self, session_id: str) -> OpenAILLMService:
        """Get or create LLM service for session"""
        if session_id not in self._llm_pool:
            self._llm_pool[session_id] = OpenAILLMService(
                api_key=config.OPENAI_API_KEY,
                model=config.OPENAI_MODEL,
                params=OpenAILLMService.InputParams(
                    temperature=config.OPENAI_TEMPERATURE,
                    max_tokens=config.OPENAI_MAX_TOKENS,
                ),
                stream=config.ENABLE_STREAMING
            )
            slog.debug("Created LLM service", session_id=session_id)
        return self._llm_pool[session_id]
    
    def get_vad_analyzer(self, session_id: str) -> SileroVADAnalyzer:
        """Get or create VAD analyzer for session"""
        if session_id not in self._vad_pool:
            self._vad_pool[session_id] = SileroVADAnalyzer(
                params=VADParams(
                    stop_secs=config.VAD_STOP_SECS,
                    start_secs=config.VAD_START_SECS,
                    min_volume=config.VAD_MIN_VOLUME
                )
            )
            slog.debug("Created VAD analyzer", session_id=session_id)
        return self._vad_pool[session_id]
    
    def register_session(self, session_id: str, services: Dict[str, Any]):
        """Register active services for a session"""
        self._active_services[session_id] = services
    
    async def cleanup_session(self, session_id: str):
        """Clean up services for a session"""
        try:
            # Clean up active services
            if session_id in self._active_services:
                services = self._active_services[session_id]
                
                # Clean up pipeline runner
                if 'runner' in services:
                    runner = services['runner']
                    if hasattr(runner, 'cleanup'):
                        await runner.cleanup()
                
                # Clean up task
                if 'task' in services:
                    task = services['task']
                    if hasattr(task, 'cancel'):
                        await task.cancel()
                
                del self._active_services[session_id]
            
            # Remove from pools
            pools = [self._stt_pool, self._tts_pool, self._llm_pool, self._vad_pool]
            for pool in pools:
                if session_id in pool:
                    del pool[session_id]
            
            slog.info("Cleaned up session services", session_id=session_id)
            
        except Exception as e:
            slog.error("Error cleaning up session", session_id=session_id, error=str(e))
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            "stt_services": len(self._stt_pool),
            "tts_services": len(self._tts_pool),
            "llm_services": len(self._llm_pool),
            "vad_analyzers": len(self._vad_pool),
            "active_sessions": len(self._active_services)
        }

# Global service pool
service_pool = ServicePool()

def get_system_instruction() -> str:
    """Get system instruction for the AI assistant"""
    return config.get_system_prompt()

async def run_bot(websocket_client, session_id: Optional[str] = None, agent_id: Optional[int] = None, system_prompt: Optional[str] = None):
    """Enhanced bot runner with resource management"""
    
    # Generate session ID if not provided
    if session_id is None:
        import uuid
        session_id = str(uuid.uuid4())
    
    # Create or get session with agent-specific context
    if session_id not in session_manager.sessions:
        session_id = session_manager.create_session(session_id, agent_id, system_prompt)
    
    agent_session = session_manager.get_session(session_id)
    
    slog.info("Starting bot session", session_id=session_id)
    
    try:
        # Get services from pool
        stt = service_pool.get_stt_service(session_id)
        tts = service_pool.get_tts_service(session_id, agent_id)
        llm = service_pool.get_llm_service(session_id)
        vad_analyzer = service_pool.get_vad_analyzer(session_id)
        
        # Create transport
        ws_transport = FastAPIWebsocketTransport(
            websocket=websocket_client,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                vad_analyzer=vad_analyzer,
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
                        "content": get_system_instruction(),
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
        
        # Create pipeline
        pipeline = Pipeline(
            [
                ws_transport.input(),
                stt_mute_filter,
                stt,
                context_aggregator.user(),
                rtvi,
                llm,
                tts,
                ws_transport.output(),
                context_aggregator.assistant(),
            ]
        )
        
        # Create task with optimized parameters
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                enable_metrics=config.ENABLE_METRICS,
                enable_usage_metrics=config.ENABLE_METRICS,
                allow_interruptions=config.ENABLE_INTERRUPTIONS,
                interruption_strategies=[
                    MinWordsInterruptionStrategy(min_words=3)
                ] if config.ENABLE_INTERRUPTIONS else []
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
        
        @ws_transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            slog.info("Client disconnected from transport", session_id=session_id)
            await task.cancel()
        
        # Create runner
        runner = PipelineRunner(handle_sigint=False)
        
        # Register services for cleanup
        service_pool.register_session(session_id, {
            'task': task,
            'runner': runner,
            'pipeline': pipeline,
            'transport': ws_transport
        })
        
        # Run the pipeline
        await runner.run(task)
        
    except Exception as e:
        slog.error("Bot error", session_id=session_id, error=str(e))
        raise
    finally:
        # Clean up session
        await service_pool.cleanup_session(session_id)

def get_service_pool_stats() -> Dict[str, Any]:
    """Get service pool statistics"""
    return service_pool.get_pool_stats()

# Export for backward compatibility
__all__ = ['run_bot', 'get_service_pool_stats', 'service_pool']
