from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List
import json
import logging
from routers.auth import verify_token
from services.livekit_service import livekit_service
from database import get_db
from models.session import Session as SessionModel
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket connected to session {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected from session {session_id}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast_to_session(self, message: str, session_id: int):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Remove broken connections
                    self.active_connections[session_id].remove(connection)

manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for real-time communication with agents"""
    
    # Connect to WebSocket
    await manager.connect(websocket, session_id)
    
    try:
        # Verify session exists and is active
        db = next(get_db())
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        
        if not session or not session.is_active:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Session not found or inactive"
            }))
            return
        
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connected",
            "session_id": session_id,
            "room_name": session.room_name,
            "mode": session.mode,
            "message": "Connected to agent session"
        }))
        
        # Start LiveKit session if not already started
        try:
            await livekit_service.join_room(
                session_id=session_id,
                room_name=session.room_name,
                mode=session.mode
            )
            
            await websocket.send_text(json.dumps({
                "type": "livekit_started",
                "message": "LiveKit session started successfully"
            }))
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Failed to start LiveKit session: {str(e)}"
            }))
            return
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                message_type = message_data.get("type")
                
                if message_type == "text_message":
                    # Send text message to agent
                    message = message_data.get("message", "")
                    await livekit_service.send_text_message(session_id, message)
                    
                    # Broadcast message to all connections in this session
                    await manager.broadcast_to_session(json.dumps({
                        "type": "user_message",
                        "message": message,
                        "session_id": session_id
                    }), session_id)
                
                elif message_type == "update_prompt":
                    # Update session prompt
                    new_prompt = message_data.get("prompt", "")
                    await livekit_service.update_session_prompt(session_id, new_prompt)
                    
                    await websocket.send_text(json.dumps({
                        "type": "prompt_updated",
                        "message": "Session prompt updated successfully"
                    }))
                
                elif message_type == "ping":
                    # Respond to ping
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "message": "pong"
                    }))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket, session_id) 