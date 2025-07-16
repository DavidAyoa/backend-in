"""
Pipeline implementation for Voice Agent Backend
Following pipecat documentation patterns for Google STT/TTS and OpenAI LLM
"""
import asyncio
import platform
import structlog
from typing import AsyncGenerator

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.google.stt import GoogleSTTService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.network.websocket_server import (
    WebsocketServerTransport,
    WebsocketServerParams
)

from .config import config

logger = structlog.get_logger()

class VoiceAgentPipeline:
    """Voice Agent Pipeline using Google STT/TTS and OpenAI LLM"""
    
    def __init__(self):
        self.transport = None
        self.pipeline = None
        self.task = None
        self.runner = None
        
    async def create_transport(self) -> WebsocketServerTransport:
        """Create WebSocket transport with VAD and serialization"""
        logger.info("Creating WebSocket transport", host=config.HOST, port=config.PORT)
        
        transport = WebsocketServerTransport(
            host=config.HOST,
            port=config.PORT,
            params=WebsocketServerParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,  # Official example uses False
                vad_analyzer=SileroVADAnalyzer(),
                serializer=None,
                session_timeout=config.SESSION_TIMEOUT
            )
        )
        
        # Event handlers
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info("Client connected", client_address=client.remote_address)
            
        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            logger.info("Client disconnected", client_address=client.remote_address)
            
        return transport
    
    async def create_stt_service(self) -> GoogleSTTService:
        """Create Google Speech-to-Text service"""
        logger.info("Creating Google STT service", model=config.GOOGLE_STT_MODEL, language=config.GOOGLE_STT_LANGUAGE)
        
        return GoogleSTTService(
            credentials_path=config.GOOGLE_APPLICATION_CREDENTIALS,
            params=GoogleSTTService.InputParams(
                model=config.GOOGLE_STT_MODEL,
                language=config.GOOGLE_STT_LANGUAGE,
                enable_interim_results=config.GOOGLE_STT_ENABLE_INTERIM,
                enable_automatic_punctuation=True
            )
        )
    
    async def create_llm_service(self) -> OpenAILLMService:
        """Create OpenAI LLM service"""
        logger.info("Creating OpenAI LLM service", model=config.OPENAI_MODEL)
        
        return OpenAILLMService(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            temperature=config.OPENAI_TEMPERATURE,
            stream=config.ENABLE_STREAMING
        )
    
    async def create_tts_service(self) -> GoogleTTSService:
        """Create Google Text-to-Speech service"""
        logger.info("Creating Google TTS service", voice=config.GOOGLE_TTS_VOICE)
        
        return GoogleTTSService(
            credentials_path=config.GOOGLE_APPLICATION_CREDENTIALS,
            voice_id=config.GOOGLE_TTS_VOICE,
            sample_rate=config.GOOGLE_TTS_SAMPLE_RATE
        )
    
    async def create_pipeline(self) -> Pipeline:
        """Create the complete pipeline"""
        logger.info("Creating voice agent pipeline")
        
        # Create services
        self.transport = await self.create_transport()
        stt = await self.create_stt_service()
        llm = await self.create_llm_service()
        tts = await self.create_tts_service()
        
        # Set up conversation context
        messages = [
            {
                "role": "system",
                "content": config.get_system_prompt()
            }
        ]
        
        context = OpenAILLMContext(messages)
        context_aggregator = llm.create_context_aggregator(context)
        
        # Create pipeline with streaming support
        self.pipeline = Pipeline([
            self.transport.input(),              # Receive streaming audio
            stt,                                 # Stream speech-to-text
            context_aggregator.user(),           # Add to conversation context
            llm,                                 # Stream LLM text responses
            tts,                                 # Stream text-to-speech
            self.transport.output(),             # Send streaming audio
            context_aggregator.assistant()       # Capture assistant responses
        ])
        
        logger.info("Pipeline created successfully")
        return self.pipeline
    
    async def run(self) -> None:
        """Run the voice agent pipeline"""
        if not config.validate():
            logger.error("Configuration validation failed")
            return
        
        logger.info("Starting voice agent pipeline")
        
        try:
            # Create pipeline
            await self.create_pipeline()
            
            # Create task
            self.task = PipelineTask(
                self.pipeline,
                params=PipelineParams(
                    allow_interruptions=config.ENABLE_INTERRUPTIONS,
                    enable_metrics=True,
                    enable_usage_metrics=True
                )
            )
            
            # Create runner with platform-appropriate signal handling
            # Disable signal handling on Windows, enable on Unix-like systems
            is_windows = platform.system().lower() == "windows"
            self.runner = PipelineRunner(handle_sigint=not is_windows)
            
            logger.info(f"Platform: {platform.system()}, Signal handling: {not is_windows}")
            await self.runner.run(self.task)
            
        except Exception as e:
            logger.error("Pipeline failed", error=str(e))
            raise
    
    async def stop(self) -> None:
        """Stop the pipeline gracefully"""
        logger.info("Stopping voice agent pipeline")
        
        if self.task:
            try:
                # Cancel the task
                await self.task.cancel()
            except Exception as e:
                logger.warning("Error stopping task", error=str(e))
        
        if self.transport:
            try:
                await self.transport.cleanup()
            except Exception as e:
                logger.warning("Error cleaning up transport", error=str(e))

# Global pipeline instance
pipeline = VoiceAgentPipeline()
