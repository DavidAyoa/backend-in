#!/usr/bin/env python3
"""
Enhanced Voice Agent Server
Focus: Stability and 25 concurrent user support
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
class ConnectionInfo:
    """Track individual connection information"""
    client_id: str
    websocket: WebSocket
    connected_at: float
    last_activity: float
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

@dataclass
class ServerMetrics:
    """Track server performance metrics"""
    total_connections: int = 0
    active_connections: int = 0
    peak_connections: int = 0
    rejected_connections: int = 0
    avg_session_duration: float = 0
    
    def update_peak(self, current: int):
        self.peak_connections = max(self.peak_connections, current)
    
    def add_connection(self):
        self.total_connections += 1
        self.active_connections += 1
        self.update_peak(self.active_connections)
    
    def remove_connection(self, duration: float):
        self.active_connections = max(0, self.active_connections - 1)
        # Update rolling average session duration
        if self.avg_session_duration == 0:
            self.avg_session_duration = duration
        else:
            self.avg_session_duration = (self.avg_session_duration * 0.9) + (duration * 0.1)

class ConnectionManager:
    """Manage WebSocket connections with limits and monitoring"""
    
    def __init__(self):
        self.max_connections = int(os.getenv("MAX_CONNECTIONS", "25"))
        self.connection_timeout = int(os.getenv("CONNECTION_TIMEOUT", "300"))  # 5 minutes
        self.connections: Dict[str, ConnectionInfo] = {}
        self.metrics = ServerMetrics()
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the connection manager"""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Connection manager started", max_connections=self.max_connections)
    
    async def stop(self):
        """Stop the connection manager"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for client_id in list(self.connections.keys()):
            await self.disconnect(client_id)
        
        logger.info("Connection manager stopped")
    
    async def connect(self, websocket: WebSocket) -> Optional[str]:
        """Attempt to connect a new client"""
        # Check capacity
        if len(self.connections) >= self.max_connections:
            self.metrics.rejected_connections += 1
            logger.warning("Connection rejected - server at capacity",
                         active_connections=len(self.connections),
                         max_connections=self.max_connections)
            await websocket.close(code=1008, reason="Server at capacity")
            return None
        
        # Generate client ID
        client_id = str(uuid.uuid4())
        
        # Accept connection
        await websocket.accept()
        
        # Store connection info
        current_time = time.time()
        connection_info = ConnectionInfo(
            client_id=client_id,
            websocket=websocket,
            connected_at=current_time,
            last_activity=current_time,
            ip_address=websocket.client.host if websocket.client else None
        )
        
        self.connections[client_id] = connection_info
        self.metrics.add_connection()
        
        logger.info("Client connected",
                   client_id=client_id,
                   ip_address=connection_info.ip_address,
                   active_connections=len(self.connections))
        
        return client_id
    
    async def disconnect(self, client_id: str):
        """Disconnect a client and clean up"""
        if client_id not in self.connections:
            return
        
        connection_info = self.connections[client_id]
        session_duration = time.time() - connection_info.connected_at
        
        # Close WebSocket if still open (refined state check per FastAPI/Starlette)
        try:
            if connection_info.websocket.client_state != WebSocketState.DISCONNECTED:
                await connection_info.websocket.close()
        except Exception as e:
            logger.debug("Error closing WebSocket", client_id=client_id, error=str(e))
        
        # Remove from connections
        del self.connections[client_id]
        self.metrics.remove_connection(session_duration)
        
        logger.info("Client disconnected",
                   client_id=client_id,
                   session_duration=f"{session_duration:.2f}s",
                   active_connections=len(self.connections))
    
    def update_activity(self, client_id: str):
        """Update last activity for a connection"""
        if client_id in self.connections:
            self.connections[client_id].last_activity = time.time()
    
    def get_connection(self, client_id: str) -> Optional[ConnectionInfo]:
        """Get connection info"""
        return self.connections.get(client_id)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup error", error=str(e))
    
    async def _cleanup_stale_connections(self):
        """Clean up connections that haven't been active"""
        current_time = time.time()
        stale_clients = []
        
        for client_id, conn_info in self.connections.items():
            if current_time - conn_info.last_activity > self.connection_timeout:
                stale_clients.append(client_id)
        
        for client_id in stale_clients:
            logger.info("Cleaning up stale connection", client_id=client_id)
            await self.disconnect(client_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current server metrics"""
        # Calculate capacity usage with safe division [docs.python.org](https://docs.python.org/3/library/stdtypes.html)
        capacity_pct = 0.0
        if self.max_connections > 0:
            capacity_pct = (self.metrics.active_connections / self.max_connections) * 100
        
        return {
            "connections": {
                "total": self.metrics.total_connections,
                "active": self.metrics.active_connections,
                "peak": self.metrics.peak_connections,
                "rejected": self.metrics.rejected_connections,
                "capacity_used": f"{capacity_pct:.1f}%"
            },
            "performance": {
                "avg_session_duration": f"{self.metrics.avg_session_duration:.2f}s",
                "max_connections": self.max_connections,
                "connection_timeout": self.connection_timeout
            },
            "timestamp": time.time()
        }

# Global connection manager
connection_manager = ConnectionManager()

# Import authentication routers
from api.auth import router as auth_router, user_router

# Import agents router  
from api.agents import router as agents_router

# Import flexible conversation functions
from bot.flexible_conversation import create_voice_conversation, create_text_conversation, create_hybrid_conversation

# Import transport factory for simplified transport management
from transports.factory import TransportFactory
from transports.base import TransportType

# Pydantic models for chat
class TextChatRequest(BaseModel):
    message: str
    agent_id: Optional[int] = None
    session_id: Optional[str] = None

class TextChatResponse(BaseModel):
    response: str
    session_id: str
    agent_id: Optional[int] = None
    timestamp: float

# NEW: For WebRTC SDP offer (integrates with your WebRTC manager)
class WebRTCOffer(BaseModel):
    sdp: str
    type: str = "offer"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    await connection_manager.start()
    logger.info("Application started")
    
    yield
    
    # Shutdown
    await connection_manager.stop()
    logger.info("Application shut down")

# Initialize FastAPI app
app = FastAPI(
    title="Voice Agent Server",
    description="Enhanced server with connection management",
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
    return {
        "session_manager": {
            "total_sessions": connection_manager.metrics.total_connections,
            "active_sessions": connection_manager.metrics.active_connections,
            "peak_sessions": connection_manager.metrics.peak_connections,
            "avg_session_duration": connection_manager.metrics.avg_session_duration
        },
        "active_connections": connection_manager.metrics.active_connections,
        "server_capacity": connection_manager.max_connections,
        "capacity_usage": f"{(connection_manager.metrics.active_connections / connection_manager.max_connections) * 100:.1f}%" if connection_manager.max_connections > 0 else "0.0%"
    }

@app.get("/session-manager/sessions")
async def get_sessions(current_user: User = Depends(get_current_user)):
    """Get current sessions"""
    sessions = []
    for client_id, connection_info in connection_manager.connections.items():
        sessions.append({
            "session_id": client_id,
            "connected_at": connection_info.connected_at,
            "last_activity": connection_info.last_activity,
            "duration": time.time() - connection_info.connected_at,
            "ip_address": connection_info.ip_address
        })
    return sessions

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    agent_id: Optional[int] = None,
    voice_input: bool = True,
    voice_output: bool = True,
    system_prompt: Optional[str] = None
):
    """Simplified WebSocket endpoint using conversation functions directly"""
    # Don't use connection manager for this - let Pipecat handle it
    
    # TODO: Add authentication validation with token
    
    try:
        # Delegate to appropriate conversation function
        if voice_input and voice_output:
            await create_voice_conversation(
                websocket=websocket,
                agent_id=agent_id,
                session_id=str(uuid.uuid4()),
                system_prompt=system_prompt
            )
        elif not voice_input and not voice_output:
            await create_text_conversation(
                websocket=websocket,
                agent_id=agent_id,
                session_id=str(uuid.uuid4()),
                system_prompt=system_prompt
            )
        else:
            await create_hybrid_conversation(
                websocket=websocket,
                agent_id=agent_id,
                session_id=str(uuid.uuid4()),
                system_prompt=system_prompt
            )
        
        logger.info("WebSocket conversation completed")
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally")
    except Exception as e:
        logger.error("WebSocket error", error=str(e))

# NEW: WebRTC offer endpoint with adaptive transport management
@app.post("/webrtc/offer")
async def webrtc_offer(
    request: Request,
    offer: WebRTCOffer,
    transport_type: str = "small_webrtc",  # Ensure it's WebRTC
    token: Optional[str] = None,
    agent_id: Optional[int] = None,
    voice_input: bool = True,
    text_input: bool = True,
    voice_output: bool = True,
    text_output: bool = True,
    enable_interruptions: bool = True
):
    if transport_type != "small_webrtc":
        raise HTTPException(status_code=400, detail="Invalid transport type for this endpoint")
    
    # Capacity check
    if connection_manager.metrics.active_connections >= connection_manager.max_connections:
        raise HTTPException(status_code=503, detail="Server at capacity")
    
    client_id = str(uuid.uuid4())  # Generate session ID
    
    try:
        # Extract headers for adaptive transport detection
        headers = dict(request.headers)
        
        # Configure initial mode
        initial_mode = FlexibleConversationMode(
            voice_input=voice_input,
            text_input=text_input,
            voice_output=voice_output,
            text_output=text_output,
            enable_interruptions=enable_interruptions
        )
        
        # Validate mode
        if not initial_mode.validate():
            raise HTTPException(status_code=400, detail="Invalid mode configuration")
        
        # Create adaptive transport manager (WebRTC for this endpoint)
        transport_manager = TransportFactory.create_adaptive_transport_manager(
            request_headers=headers,
            transport_type=TransportType.WEBRTC,  # Force WebRTC for this endpoint
            audio_in_enabled=voice_input,
            audio_out_enabled=voice_output,
            enable_vad=voice_input,
            enable_interruptions=enable_interruptions
        )
        
        # Create session through transport manager with SDP data
        session_info = await transport_manager.create_session(
            session_id=client_id,
            client_sdp=offer.sdp,
            sdp_type=offer.type,
            mode=initial_mode
        )
        
        # Get SDP answer from the session
        answer = await transport_manager.get_session_answer(client_id)
        if not answer:
            raise HTTPException(status_code=500, detail="Failed to generate SDP answer")
        
        logger.info("WebRTC session created via transport manager", 
                   session_id=client_id, 
                   transport_type="webrtc")
        
        return {"sdp": answer["sdp"], "type": answer["type"]}
        
    except Exception as e:
        logger.error("WebRTC offer error", client_id=client_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"WebRTC session creation failed: {str(e)}")

@app.post("/connect")
async def bot_connect(request: Request) -> Dict[Any, Any]:
    """Connect endpoint with capacity checking"""
    metrics = connection_manager.get_metrics()
    
    # Check if server is at capacity
    if metrics["connections"]["active"] >= connection_manager.max_connections:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Server at capacity",
                "message": "Please try again later",
                "capacity_info": metrics["connections"]
            }
        )
    
    # Always point to the unified WebSocket endpoint
    ws_url = "ws://localhost:7860/ws"
    
    return {
        "ws_url": ws_url,
        "status": "available",
        "capacity": {
            "available_slots": connection_manager.max_connections - metrics["connections"]["active"],
            "total_capacity": connection_manager.max_connections
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    metrics = connection_manager.get_metrics()
    
    # Determine health status
    capacity_used = 0.0
    if connection_manager.max_connections > 0:
        capacity_used = (metrics["connections"]["active"] / connection_manager.max_connections)
    
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
            "active_connections": metrics["connections"]["active"],
            "max_connections": connection_manager.max_connections,
            "capacity_usage": metrics["connections"]["capacity_used"]
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Detailed metrics endpoint"""
    return connection_manager.get_metrics()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Voice Agent Server",
        "version": "1.0.0",
        "status": "running",
        "message": "Voice Agent Server",
        "features": [
            "authentication",
            "user_management",
            "agent_management",
            "voice_processing",
            "websocket_support",
            "webrtc_support",
            "multi_agent_conversations",
            "flexible_conversation_modes",
            "adaptive_transport_management"
        ]
    }

async def main():
    """Main function with optimized configuration"""
    try:
        # Optimized uvicorn configuration (suggest Gunicorn for production scaling [mangum.io](https://mangum.io/deploying-asgi-applications-best-practices-and-tools/))
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=int(os.getenv("PORT", "7860")),
            loop="asyncio",  # Explicit asyncio loop [docs.python.org](https://docs.python.org/3/library/asyncio.html)
            ws_max_size=16 * 1024 * 1024,  # 16MB max message size
            ws_ping_interval=20,           # Ping every 20 seconds
            ws_ping_timeout=10,            # Ping timeout 10 seconds
            timeout_keep_alive=30,         # Keep-alive timeout
            limit_concurrency=connection_manager.max_connections,
            access_log=False,              # Disable for performance
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        logger.info("Server starting",
                   max_connections=connection_manager.max_connections,
                   port=int(os.getenv("PORT", "7860")))
        
        await server.serve()
        
    except* Exception as exc_group:  # Fine-grained exceptions [docs.python.org](https://docs.python.org/3/contents.html)
        logger.error("Server error", error=str(exc_group))
        raise

if __name__ == "__main__":
    asyncio.run(main())