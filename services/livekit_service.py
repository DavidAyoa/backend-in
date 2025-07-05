import asyncio
import logging
from typing import Optional, Dict, Any
import os
import subprocess
from database import get_db
from models.session import Session as SessionModel
from models.agent import Agent as AgentModel
from livekit import rtc

logger = logging.getLogger(__name__)

class LiveKitAgentService:
    """Service that abstracts LiveKit for the API"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_processes: Dict[str, subprocess.Popen] = {}
    
    async def create_session_agent(self, session_id: int, agent_id: int, session_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Create a session agent configuration"""
        
        # Get agent and session data from database
        db = next(get_db())
        db_agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
        db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        
        if not db_agent or not db_session:
            raise ValueError("Agent or session not found")
        
        # Use session_prompt if provided, otherwise use agent's initial_prompt
        instructions = session_prompt if session_prompt else db_agent.initial_prompt
        
        # Create agent configuration
        agent_config = {
            "id": agent_id,
            "session_id": session_id,
            "instructions": instructions,
            "name": db_agent.name,
            "voice_enabled": db_agent.voice_enabled,
            "text_enabled": db_agent.text_enabled
        }
        
        # Store the agent for this session
        session_key = f"session_{session_id}"
        self.session_agents[session_key] = agent_config
        
        return agent_config
    
    async def start_voice_session(self, session_id: int, room_name: str, mode: str = "voice") -> Dict[str, Any]:
        """Start a voice session (simulated for now)"""
        
        # Get session data
        db = next(get_db())
        db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        
        if not db_session:
            raise ValueError("Session not found")
        
        # Create the agent for this session
        agent_config = await self.create_session_agent(
            session_id=session_id,
            agent_id=db_session.agent_id,
            session_prompt=db_session.session_prompt
        )
        
        # Create session configuration
        session_config = {
            "session_id": session_id,
            "room_name": room_name,
            "mode": mode,
            "agent": agent_config,
            "status": "active",
            "created_at": db_session.created_at
        }
        
        # Store the session
        session_key = f"session_{session_id}"
        self.active_sessions[session_key] = session_config
        
        logger.info(f"Started session {session_id} in room {room_name} with mode {mode}")
        
        return session_config
    
    async def join_room(self, session_id: int, room_name: str, mode: str = "voice"):
        """Join a room with the session agent (simulated)"""
        
        # Start the voice session
        session_config = await self.start_voice_session(session_id, room_name, mode)
        
        # For now, we'll simulate the LiveKit connection
        # In a real implementation, this would connect to LiveKit
        logger.info(f"Simulated joining room {room_name} for session {session_id}")
        
        # Launch agent job if not already running
        session_key = f"session_{session_id}"
        if session_key not in self.agent_processes:
            env = os.environ.copy()
            env["AGENT_INSTRUCTIONS"] = self.session_agents[session_key]["instructions"]
            process = subprocess.Popen([
                "python", "livekit_agent_entrypoint.py", "dev"
            ], env=env)
            self.agent_processes[session_key] = process
        return session_config
    
    async def send_text_message(self, session_id: int, message: str) -> str:
        """Send a text message to the agent and return the reply"""
        session_key = f"session_{session_id}"
        session_config = self.active_sessions.get(session_key)
        if not session_config:
            raise ValueError("Session not active")
        room_name = session_config["room_name"]
        # Connect to the room as a temporary participant to send/receive text
        # (In production, use a persistent backend participant or a message broker)
        url = os.environ.get("LIVEKIT_WS_URL")
        token = os.environ.get("LIVEKIT_API_TOKEN")
        async with rtc.Room.connect(url, token) as room:
            # Send the message to the agent
            info = await room.local_participant.send_text(message, topic="user-message")
            # Wait for the agent's reply (listen for text on a topic)
            reply = None
            async for event in room.events():
                if event.event == "text_received":
                    if event.data.topic == "agent-reply":
                        reply = event.data.text
                        break
            return reply or "No reply received."
    
    async def update_session_prompt(self, session_id: int, new_prompt: str):
        """Update the session prompt dynamically"""
        
        session_key = f"session_{session_id}"
        if session_key not in self.session_agents:
            raise ValueError("Session not found")
        
        # Update the agent's instructions
        agent_config = self.session_agents[session_key]
        agent_config["instructions"] = new_prompt
        
        # Update database
        db = next(get_db())
        db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if db_session:
            db_session.session_prompt = new_prompt
            db.commit()
        
        logger.info(f"Updated session {session_id} prompt")
    
    async def end_session(self, session_id: int):
        """End a session"""
        
        session_key = f"session_{session_id}"
        
        if session_key in self.active_sessions:
            session_config = self.active_sessions[session_key]
            # Clean up the session
            session_config["status"] = "ended"
            del self.active_sessions[session_key]
        
        if session_key in self.session_agents:
            del self.session_agents[session_key]
        
        # Stop agent process if running
        if session_key in self.agent_processes:
            process = self.agent_processes[session_key]
            process.terminate()
            del self.agent_processes[session_key]
        logger.info(f"Ended session {session_id}")
    
    def get_session_status(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get the status of a session"""
        session_key = f"session_{session_id}"
        return self.active_sessions.get(session_key)

# Global instance
livekit_service = LiveKitAgentService() 