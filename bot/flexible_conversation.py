#!/usr/bin/env python3
"""
Flexible Conversation Bot Implementation
Following Pipecat best practices with proper pipeline management
"""

import asyncio
import json
import uuid
from typing import Dict, Optional, Any, Literal
from dataclasses import dataclass
from datetime import datetime, timezone

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
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.transcriptions.language import Language
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.frames.frames import Frame, TextFrame, AudioRawFrame, TranscriptionFrame, StartFrame, EndFrame, CancelFrame

# Import configuration
from config import config
from services.session_manager import session_manager
from models.user import user_db
from bot.fast_api import ServicePool

load_dotenv(override=True)

# Configure logging
slog = structlog.get_logger()

@dataclass
class ConversationMode:
    """Configuration for flexible conversation mode"""
    # Input modes
    voice_input: bool = True
    text_input: bool = True
    
    # Output modes
    voice_output: bool = True
    text_output: bool = True
    
    # Additional settings
    enable_interruptions: bool = True
    
    @property
    def mode(self) -> str:
        """Get a descriptive mode string"""
        inputs = []
        outputs = []
        
        if self.voice_input:
            inputs.append("voice")
        if self.text_input:
            inputs.append("text")
            
        if self.voice_output:
            outputs.append("voice")
        if self.text_output:
            outputs.append("text")
            
        input_str = "+".join(inputs) if inputs else "none"
        output_str = "+".join(outputs) if outputs else "none"
        
        return f"{input_str}_to_{output_str}"
    
    @property
    def has_voice_input(self) -> bool:
        """Check if voice input is enabled"""
        return self.voice_input
    
    @property 
    def has_text_input(self) -> bool:
        """Check if text input is enabled"""
        return self.text_input
    
    @property
    def has_voice_output(self) -> bool:
        """Check if voice output is enabled"""
        return self.voice_output
    
    @property
    def has_text_output(self) -> bool:
        """Check if text output is enabled"""
        return self.text_output
    
    @classmethod
    def voice_only(cls) -> 'ConversationMode':
        """Voice input and output only"""
        return cls(voice_input=True, text_input=False, voice_output=True, text_output=False)
    
    @classmethod
    def text_only(cls) -> 'ConversationMode':
        """Text input and output only"""
        return cls(voice_input=False, text_input=True, voice_output=False, text_output=True)
    
    @classmethod
    def voice_to_text(cls) -> 'ConversationMode':
        """Voice input to text output"""
        return cls(voice_input=True, text_input=False, voice_output=False, text_output=True)
    
    @classmethod
    def text_to_voice(cls) -> 'ConversationMode':
        """Text input to voice output"""
        return cls(voice_input=False, text_input=True, voice_output=True, text_output=False)
    
    @classmethod
    def full_multimodal(cls) -> 'ConversationMode':
        """All input and output modes enabled"""
        return cls(voice_input=True, text_input=True, voice_output=True, text_output=True)
    
    def validate(self) -> bool:
        """Validate mode configuration"""
        # Must have at least one input and one output
        has_input = self.voice_input or self.text_input
        has_output = self.voice_output or self.text_output
        return has_input and has_output

@dataclass
class SessionInfo:
    """Information about an active session"""
    session_id: str
    mode: ConversationMode
    context: OpenAILLMContext
    pipeline: Optional[Pipeline] = None
    task: Optional[PipelineTask] = None
    runner: Optional[PipelineRunner] = None
    transport: Optional[FastAPIWebsocketTransport] = None
    created_at: datetime = None
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.last_activity is None:
            self.last_activity = datetime.now(timezone.utc)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)

class ModeAwareFrameProcessor(FrameProcessor):
    """Frame processor that filters frames based on conversation mode"""
    
    def __init__(self, session_id: str, bot: 'FlexibleConversationBot'):
        super().__init__()
        self.session_id = session_id
        self.bot = bot
        
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames based on current mode"""
        # Always call super() first for proper initialization
        await super().process_frame(frame, direction)
        
        # Always pass through StartFrame and EndFrame without checking
        if isinstance(frame, (StartFrame, EndFrame)):
            await self.push_frame(frame, direction)
            return
            
        if self.session_id not in self.bot.active_sessions:
            # Pass through frame if session not found
            await self.push_frame(frame, direction)
            return
            
        session = self.bot.active_sessions[self.session_id]
        mode = session.mode
        
        # Update session activity
        session.update_activity()
        
        # Handle audio input frames
        if isinstance(frame, AudioRawFrame):
            if not mode.has_voice_input:
                # Drop audio frames if voice input is disabled
                slog.debug("Dropping audio frame - voice input disabled", session_id=self.session_id)
                return
            
        # Handle text input frames (from client)
        if isinstance(frame, TextFrame) and direction == FrameDirection.DOWNSTREAM:
            if mode.has_text_input:
                # Convert TextFrame to TranscriptionFrame to trigger LLM processing
                slog.debug("Converting text input to transcription", session_id=self.session_id, text=frame.text)
                transcript_frame = TranscriptionFrame(
                    text=frame.text,
                    user_id="user",
                    timestamp=getattr(frame, 'timestamp', None)
                )
                await self._send_transcript(transcript_frame)
                await self.push_frame(transcript_frame, direction)
                return
            else:
                slog.debug("Dropping text input - text input disabled", session_id=self.session_id)
                return
        
        # Handle text output frames (to client)
        elif isinstance(frame, TextFrame) and direction == FrameDirection.UPSTREAM:
            if not mode.has_text_output:
                # Drop text frames if text output is disabled
                slog.debug("Dropping text frame - text output disabled", session_id=self.session_id)
                return
            else:
                # Send text response to client
                await self._send_text_response(frame)
            
        # Handle transcript frames
        if isinstance(frame, TranscriptionFrame):
            if mode.has_text_output:
                # Send transcript to client if text output is enabled
                await self._send_transcript(frame)
            # Always pass through transcripts for processing
            await self.push_frame(frame, direction)
            return
            
        # Pass through allowed frames
        await self.push_frame(frame, direction)
    
    async def _send_transcript(self, frame):
        """Send transcript to client via WebSocket"""
        session = self.bot.active_sessions[self.session_id]
        if session.transport and session.transport._client:
            try:
                await session.transport._client.send(json.dumps({
                    "type": "transcript",
                    "data": {
                        "text": frame.text,
                        "timestamp": getattr(frame, 'timestamp', None),
                        "is_final": getattr(frame, 'is_final', True),
                        "source": "user"
                    }
                }))
            except Exception as e:
                slog.error("Error sending transcript", session_id=self.session_id, error=str(e))
    
    async def _send_text_response(self, frame: TextFrame):
        """Send text response to client via WebSocket"""
        session = self.bot.active_sessions[self.session_id]
        if session.transport and session.transport._client:
            try:
                await session.transport._client.send(json.dumps({
                    "type": "assistant_response",
                    "data": {
                        "text": frame.text,
                        "timestamp": getattr(frame, 'timestamp', None),
                        "source": "assistant"
                    }
                }))
            except Exception as e:
                slog.error("Error sending text response", session_id=self.session_id, error=str(e))

class FlexibleConversationBot:
    """Flexible conversation bot with proper pipeline management"""
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionInfo] = {}
        self.service_pool = ServicePool()
        slog.info("Initialized FlexibleConversationBot")
    
    async def create_session(
        self, 
        websocket,
        session_id: Optional[str] = None,
        agent_id: Optional[int] = None,
        system_prompt: Optional[str] = None,
        initial_mode: ConversationMode = ConversationMode()
    ) -> str:
        """Create a new session with specified mode"""
        
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Create or get session context
        if session_id not in session_manager.sessions:
            session_manager.create_session(session_id, agent_id, system_prompt)
        
        agent_session = session_manager.get_session(session_id)
        
        # Use agent session's context if available
        if agent_session:
            context = agent_session.context
        else:
            # Fallback to default context
            context = OpenAILLMContext([
                {
                    "role": "system",
                    "content": system_prompt or config.get_system_prompt(),
                },
                {
                    "role": "user",
                    "content": "Start by greeting the user warmly and introducing yourself.",
                }
            ])
        
        # Create session info
        session = SessionInfo(
            session_id=session_id,
            mode=initial_mode,
            context=context
        )
        
        # Add session to active sessions first
        self.active_sessions[session_id] = session
        
        # Initialize pipeline for this session
        await self._initialize_session_pipeline(session_id, session, websocket, agent_id)
        
        slog.info("Created session", session_id=session_id, mode=initial_mode.mode, agent_id=agent_id)
        return session_id
    
    async def switch_mode(self, session_id: str, new_mode: ConversationMode):
        """Switch session to new mode by recreating pipeline"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        # Preserve context
        old_context = session.context
        
        # Stop current pipeline
        if session.task:
            try:
                await session.task.cancel()
            except Exception as e:
                slog.warning("Error canceling task", session_id=session_id, error=str(e))
        
        # Update mode and recreate pipeline
        session.mode = new_mode
        await self._initialize_session_pipeline(session_id, session, session.transport.websocket)
        
        # Restore context
        session.context = old_context
        
        slog.info("Switched mode", session_id=session_id, new_mode=new_mode.mode)
    
    async def _initialize_session_pipeline(
        self, 
        session_id: str, 
        session: SessionInfo, 
        websocket,
        agent_id: Optional[int] = None
    ):
        """Initialize pipeline for session based on current mode"""
        mode = session.mode
        
        # Create services for this mode
        services = await self._create_services_for_mode(session_id, mode, agent_id)
        
        # Create transport for this mode
        transport = await self._create_transport_for_mode(mode, websocket)
        session.transport = transport
        
        # Build pipeline components
        pipeline_components = await self._build_pipeline_components(
            session_id, mode, services, transport, session.context
        )
        
        # Create pipeline
        pipeline = Pipeline(pipeline_components)
        session.pipeline = pipeline
        
        # Create task with mode-specific parameters
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=mode.enable_interruptions,
                enable_metrics=config.ENABLE_METRICS,
                enable_usage_metrics=config.ENABLE_METRICS,
                interruption_strategies=[
                    MinWordsInterruptionStrategy(min_words=3)
                ] if mode.enable_interruptions else []
            )
        )
        session.task = task
        
        # Create runner
        runner = PipelineRunner(handle_sigint=False)
        session.runner = runner
        
        # Set up event handlers
        await self._setup_event_handlers(session_id, transport, task)
        
        # Run the pipeline (wait for completion)
        await self._run_pipeline(session_id, runner, task)
    
    async def _create_services_for_mode(self, session_id: str, mode: ConversationMode, agent_id: Optional[int] = None):
        """Create services optimized for the specific mode"""
        services = {}
        
        # Always create LLM service
        services['llm'] = self.service_pool.get_llm_service(session_id)
        
        # Create STT only if voice input is enabled
        if mode.has_voice_input:
            services['stt'] = self.service_pool.get_stt_service(session_id)
            services['vad'] = self.service_pool.get_vad_analyzer(session_id)
        
        # Create TTS only if voice output is enabled
        if mode.has_voice_output:
            services['tts'] = self.service_pool.get_tts_service(session_id, agent_id)
        
        return services
    
    async def _create_transport_for_mode(self, mode: ConversationMode, websocket) -> FastAPIWebsocketTransport:
        """Create transport optimized for the specific mode"""
        
        # Configure transport parameters based on mode
        params = FastAPIWebsocketParams(
            audio_in_enabled=mode.has_voice_input,
            audio_out_enabled=mode.has_voice_output,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer() if mode.has_voice_input else None,
            serializer=ProtobufFrameSerializer(),
        )
        
        return FastAPIWebsocketTransport(
            websocket=websocket,
            params=params
        )
    
    async def _build_pipeline_components(
        self, 
        session_id: str,
        mode: ConversationMode, 
        services: Dict[str, Any], 
        transport: FastAPIWebsocketTransport,
        context: OpenAILLMContext
    ) -> list:
        """Build pipeline components based on mode"""
        
        # Create context aggregator
        context_aggregator = services['llm'].create_context_aggregator(context)
        
        # Create mode-aware frame processor
        frame_processor = ModeAwareFrameProcessor(session_id, self)
        
        # Build pipeline components
        components = [transport.input()]
        
        # Add frame processor early in pipeline
        components.append(frame_processor)
        
        # Add STT for voice input
        if mode.has_voice_input and 'stt' in services:
            # STT Mute Filter for better interruption control
            # Only mute for voice interactions to avoid blocking text input
            stt_mute_filter = STTMuteFilter(
                config=STTMuteConfig(
                    strategies={
                        STTMuteStrategy.FUNCTION_CALL,
                    } if mode.has_voice_output else set()  # Only mute for voice output
                )
            )
            components.extend([stt_mute_filter, services['stt']])
        
        # Add core processing components
        components.extend([
            context_aggregator.user(),
            services['llm'],
        ])
        
        # Add TTS for voice output
        if mode.has_voice_output and 'tts' in services:
            components.append(services['tts'])
        
        # Add output and context aggregator
        components.extend([
            transport.output(),
            context_aggregator.assistant(),
        ])
        
        return components
    
    async def _setup_event_handlers(self, session_id: str, transport: FastAPIWebsocketTransport, task: PipelineTask):
        """Set up event handlers for the session"""
        
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            slog.info("Client connected", session_id=session_id)
            # Don't send anything immediately to avoid race conditions
        
        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            slog.info("Client disconnected", session_id=session_id)
            await self.cleanup_session(session_id)
    
    async def _handle_websocket_message(self, session_id: str, transport: FastAPIWebsocketTransport, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "mode_change":
                # Handle mode change request
                new_mode_data = data.get("data", {})
                new_mode = ConversationMode(
                    voice_input=new_mode_data.get("voice_input", True),
                    text_input=new_mode_data.get("text_input", True),
                    voice_output=new_mode_data.get("voice_output", True),
                    text_output=new_mode_data.get("text_output", True),
                    enable_interruptions=new_mode_data.get("enable_interruptions", True)
                )
                
                # Validate mode
                if not new_mode.validate():
                    await transport._client.send(json.dumps({
                        "type": "error",
                        "data": {
                            "message": "Invalid mode configuration: must have at least one input and one output"
                        }
                    }))
                    return
                
                await self.switch_mode(session_id, new_mode)
                
                # Send confirmation
                await transport._client.send(json.dumps({
                    "type": "mode_changed",
                    "data": {
                        "mode": new_mode.mode,
                        "voice_input": new_mode.voice_input,
                        "text_input": new_mode.text_input,
                        "voice_output": new_mode.voice_output,
                        "text_output": new_mode.text_output,
                        "enable_interruptions": new_mode.enable_interruptions
                    }
                }))
                
            elif message_type == "text_message":
                # Handle text-only messages
                await self._handle_text_message(session_id, data.get("data", {}))
                
        except json.JSONDecodeError:
            slog.warning("Invalid JSON message received", session_id=session_id)
        except Exception as e:
            slog.error("Error processing message", session_id=session_id, error=str(e))
    
    async def _handle_text_message(self, session_id: str, data: Dict[str, Any]):
        """Handle text message input"""
        text_content = data.get("text", "")
        if not text_content:
            return
        
        session = self.active_sessions[session_id]
        
        # Add to context
        session.context.messages.append({
            "role": "user",
            "content": text_content
        })
        
        # Send transcript if text output is enabled
        if session.mode.has_text_output:
            await session.transport._client.send(json.dumps({
                "type": "transcript",
                "data": {
                    "text": text_content,
                    "is_final": True,
                    "source": "user"
                }
            }))
        
        # Process through LLM
        # This would typically be handled by the pipeline, but for text mode
        # we might need to manually trigger processing
        slog.debug("Processed text message", session_id=session_id, text_length=len(text_content))
    
    async def _run_pipeline(self, session_id: str, runner: PipelineRunner, task: PipelineTask):
        """Run the pipeline for a session"""
        try:
            await runner.run(task)
        except Exception as e:
            slog.error("Pipeline error", session_id=session_id, error=str(e))
            await self.cleanup_session(session_id)
    
    async def cleanup_session(self, session_id: str):
        """Clean up session resources"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        
        # Cancel task
        if session.task:
            try:
                await session.task.cancel()
            except Exception as e:
                slog.debug("Error canceling task", session_id=session_id, error=str(e))
        
        # Close transport
        if session.transport:
            try:
                await session.transport._client.disconnect()
            except Exception as e:
                slog.debug("Error closing transport", session_id=session_id, error=str(e))
        
        # Remove from active sessions (if still present)
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Clean up service pool
        await self.service_pool.cleanup_session(session_id)
        
        slog.info("Cleaned up session", session_id=session_id)
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        return self.active_sessions.get(session_id)
    
    def get_active_sessions(self) -> Dict[str, SessionInfo]:
        """Get all active sessions"""
        return self.active_sessions.copy()
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        total_sessions = len(self.active_sessions)
        voice_sessions = sum(1 for s in self.active_sessions.values() if s.mode.voice_input)
        text_sessions = sum(1 for s in self.active_sessions.values() if s.mode.text_input)
        
        return {
            "total_sessions": total_sessions,
            "voice_sessions": voice_sessions,
            "text_sessions": text_sessions,
            "sessions_by_mode": {
                "voice": voice_sessions,
                "text": text_sessions
            }
        }

# Global instance
flexible_bot = FlexibleConversationBot()

# Export for use in main application
__all__ = ['FlexibleConversationBot', 'ConversationMode', 'SessionInfo', 'flexible_bot']
