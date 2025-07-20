#!/usr/bin/env python3
"""
Enhanced Voice Agent Server - Pipecat Compatible
Focus: Stability and 25 concurrent user support using Pipecat's native transport system
"""

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Set
from dataclasses import dataclass, field

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.websockets import WebSocketState
import structlog

# Pipecat imports - using native transport system
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomObject, DailyRoomProperties
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.base_input import BaseInputTransport
from pipecat.transports.base_output import BaseOutputTransport
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.frames.frames import Frame, AudioRawFrame, TextFrame
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.transports.network.fastapi_websocket import FastAPIWebsocketTransport, FastAPIWebsocketParams
from pipecat.transports.network.websocket_server import WebsocketServerParams

# Load environment variables
load_dotenv(override=True)

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@dataclass
class SessionInfo:
    """Track individual session information for capacity management"""
    session_id: str
    created_at: float
    last_activity: float
    transport_type: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    pipeline_task: Optional[PipelineTask] = None

@dataclass
class ServerMetrics:
    """Track server performance metrics"""
    total_sessions: int = 0
    active_sessions: int = 0
    peak_sessions: int = 0
    rejected_sessions: int = 0
    avg_session_duration: float = 0
    
    def update_peak(self, current: int):
        self.peak_sessions = max(self.peak_sessions, current)
    
    def add_session(self):
        self.total_sessions += 1
        self.active_sessions += 1
        self.update_peak(self.active_sessions)
    
    def remove_session(self, duration: float):
        self.active_sessions = max(0, self.active_sessions - 1)
        # Update rolling average session duration
        if self.avg_session_duration == 0:
            self.avg_session_duration = duration
        else:
            self.avg_session_duration = (self.avg_session_duration * 0.9) + (duration * 0.1)

class SessionManager:
    """Lightweight session tracking that doesn't interfere with Pipecat's transport handling"""
    
    def __init__(self):
        self.max_sessions = int(os.getenv("MAX_SESSIONS", "25"))
        self.session_timeout = int(os.getenv("SESSION_TIMEOUT", "300"))  # 5 minutes
        self.sessions: Dict[str, SessionInfo] = {}
        self.metrics = ServerMetrics()
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the session manager"""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Session manager started", max_sessions=self.max_sessions)
    
    async def stop(self):
        """Stop the session manager"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Stop all active pipeline tasks
        for session_id in list(self.sessions.keys()):
            await self.end_session(session_id)
        
        logger.info("Session manager stopped")
    
    def can_accept_session(self) -> bool:
        """Check if we can accept a new session"""
        return len(self.sessions) < self.max_sessions
    
    def register_session(self, session_id: str, transport_type: str, 
                        pipeline_task: Optional[PipelineTask] = None,
                        ip_address: Optional[str] = None) -> bool:
        """Register a new session"""
        if not self.can_accept_session():
            self.metrics.rejected_sessions += 1
            logger.warning("Session rejected - server at capacity",
                         active_sessions=len(self.sessions),
                         max_sessions=self.max_sessions)
            return False
        
        current_time = time.time()
        session_info = SessionInfo(
            session_id=session_id,
            created_at=current_time,
            last_activity=current_time,
            transport_type=transport_type,
            ip_address=ip_address,
            pipeline_task=pipeline_task
        )
        
        self.sessions[session_id] = session_info
        self.metrics.add_session()
        
        logger.info("Session registered",
                   session_id=session_id,
                   transport_type=transport_type,
                   ip_address=ip_address,
                   active_sessions=len(self.sessions))
        
        return True
    
    async def end_session(self, session_id: str):
        """End a session and clean up"""
        if session_id not in self.sessions:
            return
        
        session_info = self.sessions[session_id]
        session_duration = time.time() - session_info.created_at
        
        # Cancel pipeline task if exists
        if session_info.pipeline_task:
            try:
                await session_info.pipeline_task.cancel()
            except Exception as e:
                logger.debug("Error cancelling pipeline task", session_id=session_id, error=str(e))
        
        # Remove from sessions
        del self.sessions[session_id]
        self.metrics.remove_session(session_duration)
        
        logger.info("Session ended",
                   session_id=session_id,
                   session_duration=f"{session_duration:.2f}s",
                   active_sessions=len(self.sessions))
    
    def update_activity(self, session_id: str):
        """Update last activity for a session"""
        if session_id in self.sessions:
            self.sessions[session_id].last_activity = time.time()
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session info"""
        return self.sessions.get(session_id)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of stale sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup error", error=str(e))
    
    async def _cleanup_stale_sessions(self):
        """Clean up sessions that haven't been active"""
        current_time = time.time()
        stale_sessions = []
        
        for session_id, session_info in self.sessions.items():
            if current_time - session_info.last_activity > self.session_timeout:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            logger.info("Cleaning up stale session", session_id=session_id)
            await self.end_session(session_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current server metrics"""
        capacity_pct = 0.0
        if self.max_sessions > 0:
            capacity_pct = (self.metrics.active_sessions / self.max_sessions) * 100
        
        return {
            "sessions": {
                "total": self.metrics.total_sessions,
                "active": self.metrics.active_sessions,
                "peak": self.metrics.peak_sessions,
                "rejected": self.metrics.rejected_sessions,
                "capacity_used": f"{capacity_pct:.1f}%"
            },
            "performance": {
                "avg_session_duration": f"{self.metrics.avg_session_duration:.2f}s",
                "max_sessions": self.max_sessions,
                "session_timeout": self.session_timeout
            },
            "timestamp": time.time()
        }

# Global session manager
session_manager = SessionManager()

# Import authentication routers
from api.auth import router as auth_router, user_router

# Import agents router  
from api.agents import router as agents_router

# Pydantic models
class TextChatRequest(BaseModel):
    message: str
    agent_id: Optional[int] = None
    session_id: Optional[str] = None

class TextChatResponse(BaseModel):
    response: str
    session_id: str
    agent_id: Optional[int] = None
    timestamp: float

class WebRTCOffer(BaseModel):
    sdp: str
    type: str = "offer"

# Custom processor for activity tracking
class ActivityTracker(FrameProcessor):
    def __init__(self, session_id: str, session_manager: SessionManager):
        super().__init__()
        self.session_id = session_id
        self.session_manager = session_manager
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Update activity on any frame
        self.session_manager.update_activity(self.session_id)
        await self.push_frame(frame, direction)

# Import the conversation functions from flexible_conversation
from bot.flexible_conversation import (
    create_websocket_voice_conversation,
    create_websocket_text_conversation,
    create_webrtc_voice_conversation,
    create_webrtc_text_conversation
)

# Import WebRTC transport manager
from transports.webrtc.manager import WebRTCTransportManager
from transports.base import TransportConfig, TransportType

# Global WebRTC transport manager
webrtc_config = TransportConfig(transport_type=TransportType.WEBRTC)
webrtc_manager = WebRTCTransportManager(webrtc_config)

async def run_webrtc_bot(webrtc_connection, session_id, agent_id, mode):
    """Run the bot pipeline for WebRTC using proper PipelineRunner"""
    try:
        # Create transport with proper TransportParams
        from pipecat.transports.base_transport import TransportParams
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        
        transport = SmallWebRTCTransport(
            webrtc_connection=webrtc_connection,
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer()
            )
        )
        
        # Create conversation task
        if mode == "voice":
            task = await create_webrtc_voice_conversation(
                transport=transport,
                agent_id=agent_id,
                session_id=session_id
            )
        else:
            task = await create_webrtc_text_conversation(
                transport=transport,
                agent_id=agent_id,
                session_id=session_id
            )
        
        # Run the pipeline with PipelineRunner
        runner = PipelineRunner(handle_sigint=False)
        await runner.run(task)
        
    except Exception as e:
        logger.error("WebRTC bot error", session_id=session_id, error=str(e))

async def create_pipecat_voice_conversation(
    websocket: WebSocket,
    agent_id: Optional[int] = None,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None
):
    """Create a voice conversation using proper PipelineRunner"""
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Register session first
    if not session_manager.register_session(
        session_id, 
        "websocket_voice",
        ip_address=websocket.client.host if websocket.client else None
    ):
        await websocket.close(code=1008, reason="Server at capacity")
        return
    
    try:
        # Use the flexible conversation function
        task = await create_websocket_voice_conversation(
            websocket=websocket,
            agent_id=agent_id,
            session_id=session_id,
            system_prompt=system_prompt or "You are a helpful voice assistant. Keep responses concise and natural for voice interaction."
        )
        
        # Update session with pipeline task
        session_info = session_manager.get_session(session_id)
        if session_info:
            session_info.pipeline_task = task
        
        # Run the pipeline with PipelineRunner
        runner = PipelineRunner(handle_sigint=False)
        await runner.run(task)
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("Voice conversation error", session_id=session_id, error=str(e))
    finally:
        await session_manager.end_session(session_id)

async def create_pipecat_text_conversation(
    websocket: WebSocket,
    agent_id: Optional[int] = None,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None
):
    """Create a text-only conversation using flexible conversation architecture"""
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Register session first
    if not session_manager.register_session(
        session_id, 
        "websocket_text",
        ip_address=websocket.client.host if websocket.client else None
    ):
        await websocket.close(code=1008, reason="Server at capacity")
        return
    
    try:
        # Use the flexible conversation function (it creates its own services)
        task = await create_websocket_text_conversation(
            websocket=websocket,
            agent_id=agent_id,
            session_id=session_id,
            system_prompt=system_prompt or "You are a helpful text-based assistant."
        )
        
        # Update session with pipeline task
        session_info = session_manager.get_session(session_id)
        if session_info:
            session_info.pipeline_task = task
        
        # Run the pipeline with PipelineRunner
        runner = PipelineRunner(handle_sigint=False)
        await runner.run(task)
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("Text conversation error", session_id=session_id, error=str(e))
    finally:
        await session_manager.end_session(session_id)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    await session_manager.start()
    logger.info("Application started")
    
    yield
    
    # Shutdown
    await session_manager.stop()
    logger.info("Application shut down")

# Initialize FastAPI app
app = FastAPI(
    title="Voice Agent Server",
    description="Enhanced server with Pipecat native transport integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with proper prefixes
app.include_router(auth_router, prefix="/auth")
app.include_router(user_router, prefix="/users")
app.include_router(agents_router, prefix="/agents")

# Session manager endpoints
from services.auth_service import get_current_user
from models.user import User
from fastapi import Depends

@app.get("/session-manager/stats")
async def get_session_manager_stats(current_user: User = Depends(get_current_user)):
    """Get session manager statistics"""
    return session_manager.get_metrics()

@app.get("/session-manager/sessions")
async def get_sessions(current_user: User = Depends(get_current_user)):
    """Get current sessions"""
    sessions = []
    for session_id, session_info in session_manager.sessions.items():
        sessions.append({
            "session_id": session_id,
            "created_at": session_info.created_at,
            "last_activity": session_info.last_activity,
            "duration": time.time() - session_info.created_at,
            "transport_type": session_info.transport_type,
            "ip_address": session_info.ip_address
        })
    return sessions

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    agent_id: Optional[int] = None,
    mode: str = "voice"  # "voice" or "text"
):
    """Unified WebSocket endpoint using Pipecat's native transport system"""
    
    # TODO: Add authentication validation with token
    
    session_id = str(uuid.uuid4())
    
    try:
        if mode == "voice":
            await create_pipecat_voice_conversation(
                websocket=websocket,
                agent_id=agent_id,
                session_id=session_id
            )
        elif mode == "text":
            await create_pipecat_text_conversation(
                websocket=websocket,
                agent_id=agent_id,
                session_id=session_id
            )
        else:
            await websocket.close(code=1008, reason="Invalid mode")
        
        logger.info("WebSocket conversation completed", session_id=session_id)
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))

@app.post("/connect")
async def bot_connect(request: Request) -> Dict[Any, Any]:
    """Connect endpoint with capacity checking"""
    
    # Check if server can accept new sessions
    if not session_manager.can_accept_session():
        metrics = session_manager.get_metrics()
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Server at capacity",
                "message": "Please try again later",
                "capacity_info": metrics["sessions"]
            }
        )
    
    # Return WebSocket URL
    ws_url = "ws://localhost:7860/ws"
    
    return {
        "ws_url": ws_url,
        "status": "available",
        "capacity": {
            "available_slots": session_manager.max_sessions - session_manager.metrics.active_sessions,
            "total_capacity": session_manager.max_sessions
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    metrics = session_manager.get_metrics()
    
    # Determine health status
    capacity_used = 0.0
    if session_manager.max_sessions > 0:
        capacity_used = (session_manager.metrics.active_sessions / session_manager.max_sessions)
    
    if capacity_used >= 0.9:
        status = "warning"
    elif capacity_used >= 1.0:
        status = "critical"
    else:
        status = "healthy"
    
    return {
        "status": status,
        "timestamp": time.time(),
        "server_info": {
            "active_sessions": session_manager.metrics.active_sessions,
            "max_sessions": session_manager.max_sessions,
            "capacity_usage": metrics["sessions"]["capacity_used"]
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Detailed metrics endpoint"""
    return session_manager.get_metrics()

# Add missing WebRTC imports
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection

# Simplified single endpoint for WebRTC connection
@app.post("/webrtc/connect")
async def webrtc_connect(
    offer: WebRTCOffer,
    agent_id: Optional[int] = None,
    mode: str = "voice"
):
    """Single endpoint for WebRTC connection with immediate answer"""
    session_id = str(uuid.uuid4())
    
    try:
        # Create WebRTC connection
        ice_servers = [{"urls": "stun:stun.l.google.com:19302"}]
        webrtc_connection = SmallWebRTCConnection(ice_servers=ice_servers)
        
        await webrtc_connection.initialize(sdp=offer.sdp, type=offer.type)
        await webrtc_connection.connect()
        
        # Get answer immediately
        answer = webrtc_connection.get_answer()
        
        # Create and run bot in background
        asyncio.create_task(run_webrtc_bot(webrtc_connection, session_id, agent_id, mode))
        
        return {
            "session_id": session_id,
            "answer": answer
        }
        
    except Exception as e:
        logger.error("WebRTC connection failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Legacy WebRTC endpoints for compatibility
@app.post("/webrtc/offer")
async def webrtc_offer(
    offer: WebRTCOffer,
    request: Request,
    agent_id: Optional[int] = None,
    mode: str = "voice",  # "voice" or "text"
    system_prompt: Optional[str] = None
):
    """Handle WebRTC SDP offer and create session"""
    
    # Check capacity
    if not session_manager.can_accept_session():
        raise HTTPException(
            status_code=503,
            detail={"error": "Server at capacity", "message": "Please try again later"}
        )
    
    session_id = str(uuid.uuid4())
    
    try:
        # Register session with server's session manager
        if not session_manager.register_session(
            session_id, 
            "webrtc",
            ip_address=request.client.host if request.client else None
        ):
            raise HTTPException(status_code=503, detail="Server at capacity")
        
        # Create WebRTC session using the transport manager
        voice_input = mode in ["voice", "hybrid"]
        voice_output = mode in ["voice", "hybrid"]
        
        session_info = await webrtc_manager.create_session(
            session_id=session_id,
            client_sdp=offer.sdp,
            sdp_type=offer.type,
            agent_id=agent_id,
            voice_input=voice_input,
            voice_output=voice_output,
            system_prompt=system_prompt
        )
        
        # Update server session manager with the pipeline task
        server_session = session_manager.get_session(session_id)
        if server_session and session_info.pipeline_task:
            server_session.pipeline_task = session_info.pipeline_task
        
        logger.info("WebRTC session created", session_id=session_id, mode=mode)
        
        return {
            "session_id": session_id,
            "status": "offer_received",
            "message": "SDP offer processed, waiting for connection establishment"
        }
        
    except Exception as e:
        logger.error("WebRTC offer processing failed", session_id=session_id, error=str(e))
        await session_manager.end_session(session_id)
        raise HTTPException(status_code=500, detail=f"Failed to process offer: {str(e)}")

@app.get("/webrtc/answer/{session_id}")
async def webrtc_answer(session_id: str):
    """Get WebRTC SDP answer for a session"""
    
    try:
        # Get answer from WebRTC manager
        answer = await webrtc_manager.get_session_answer(session_id)
        
        if not answer:
            raise HTTPException(
                status_code=404, 
                detail="Session not found or answer not ready"
            )
        
        logger.info("WebRTC answer retrieved", session_id=session_id)
        return answer
        
    except Exception as e:
        logger.error("Failed to get WebRTC answer", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get answer: {str(e)}")

@app.delete("/webrtc/session/{session_id}")
async def end_webrtc_session(session_id: str):
    """End a WebRTC session"""
    
    try:
        # Clean up WebRTC manager session
        await webrtc_manager.destroy_session(session_id)
        
        # Clean up server session manager
        await session_manager.end_session(session_id)
        
        logger.info("WebRTC session ended", session_id=session_id)
        return {"status": "session_ended", "session_id": session_id}
        
    except Exception as e:
        logger.error("Failed to end WebRTC session", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")

@app.get("/webrtc/session/{session_id}/status")
async def get_webrtc_session_status(session_id: str):
    """Get WebRTC session status"""
    
    # Check server session manager
    server_session = session_manager.get_session(session_id)
    if not server_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check WebRTC manager session
    webrtc_session = webrtc_manager.get_session(session_id)
    
    return {
        "session_id": session_id,
        "transport_type": server_session.transport_type,
        "created_at": server_session.created_at,
        "last_activity": server_session.last_activity,
        "duration": time.time() - server_session.created_at,
        "webrtc_connected": webrtc_session is not None,
        "pipeline_active": server_session.pipeline_task is not None
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Voice Agent Server",
        "version": "1.0.0",
        "status": "running",
        "message": "Voice Agent Server with Pipecat Native Transport",
        "features": [
            "authentication",
            "user_management", 
            "agent_management",
            "voice_processing",
            "websocket_support",
            "webrtc_support",
            "pipecat_native_transport",
            "session_capacity_management",
            "activity_tracking"
        ]
    }

async def main():
    """Main function with optimized configuration"""
    try:
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=int(os.getenv("PORT", "7860")),
            loop="asyncio",
            ws_max_size=16 * 1024 * 1024,  # 16MB max message size
            ws_ping_interval=20,           # Ping every 20 seconds
            ws_ping_timeout=10,            # Ping timeout 10 seconds
            timeout_keep_alive=30,         # Keep-alive timeout
            limit_concurrency=session_manager.max_sessions,
            access_log=False,              # Disable for performance
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        logger.info("Server starting",
                   max_sessions=session_manager.max_sessions,
                   port=int(os.getenv("PORT", "7860")))
        
        await server.serve()
        
    except Exception as e:
        logger.error("Server error", error=str(e))
        raise

if __name__ == "__main__":
    asyncio.run(main())