#!/usr/bin/env python3
"""
Agent Session Manager
Manages multiple agents with isolated conversation contexts
"""

import os
import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone

from pipecat.services.openai.llm import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from config import config
import structlog

slog = structlog.get_logger()

class AgentSession:
    """Represents a single agent session with its own context"""
    
    def __init__(self, session_id: str, agent_id: Optional[int] = None, system_prompt: Optional[str] = None):
        self.session_id = session_id
        self.agent_id = agent_id
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        
        # Create isolated LLM service for this session
        self.llm = OpenAILLMService(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            params=OpenAILLMService.InputParams(
                temperature=config.OPENAI_TEMPERATURE,
                max_tokens=config.OPENAI_MAX_TOKENS,
            ),
            stream=config.ENABLE_STREAMING
        )
        
        # Create context with system prompt
        initial_prompt = system_prompt or config.get_system_prompt()
        self.context = OpenAILLMContext(
            messages=[{
                "role": "system",
                "content": initial_prompt
            }]
        )
        
        # Create context aggregator
        self.context_aggregator = self.llm.create_context_aggregator(self.context)
        
        slog.info("Created agent session", session_id=session_id, agent_id=agent_id)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)
    
    def add_user_message(self, message: str):
        """Add a user message to the context"""
        self.context.messages.append({
            "role": "user",
            "content": message
        })
        self.update_activity()
    
    def add_assistant_message(self, message: str):
        """Add an assistant message to the context"""
        self.context.messages.append({
            "role": "assistant", 
            "content": message
        })
        self.update_activity()
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the current context"""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "message_count": len(self.context.messages),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }
    
    def get_conversation_history(self, include_system: bool = False) -> List[Dict[str, Any]]:
        """Get the complete conversation history"""
        history = []
        for message in self.context.messages:
            if not include_system and message.get("role") == "system":
                continue
            history.append({
                "role": message["role"],
                "content": message["content"],
                "timestamp": getattr(message, 'timestamp', None)
            })
        return history
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from the conversation"""
        history = self.get_conversation_history(include_system=False)
        return history[-limit:] if len(history) > limit else history

class AgentSessionManager:
    """Manages multiple agent sessions with context isolation"""
    
    def __init__(self):
        self.sessions: Dict[str, AgentSession] = {}
        slog.info("Initialized AgentSessionManager")
    
    def create_session(self, session_id: Optional[str] = None, agent_id: Optional[int] = None, 
                      system_prompt: Optional[str] = None) -> str:
        """Create a new agent session with its own context"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if session_id in self.sessions:
            slog.warning("Session already exists", session_id=session_id)
            return session_id
        
        session = AgentSession(session_id, agent_id, system_prompt)
        self.sessions[session_id] = session
        
        slog.info("Created new session", session_id=session_id, agent_id=agent_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get an existing session"""
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()
        return session
    
    def update_context(self, session_id: str, new_messages: List[Dict[str, str]]):
        """Update the context for a specific session"""
        session = self.get_session(session_id)
        if session:
            session.context.messages.extend(new_messages)
            session.update_activity()
            slog.debug("Updated context", session_id=session_id, new_message_count=len(new_messages))
    
    def add_user_message(self, session_id: str, message: str):
        """Add a user message to a session's context"""
        session = self.get_session(session_id)
        if session:
            session.add_user_message(message)
    
    def add_assistant_message(self, session_id: str, message: str):
        """Add an assistant message to a session's context"""
        session = self.get_session(session_id)
        if session:
            session.add_assistant_message(message)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and clean up resources"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            slog.info("Deleted session", session_id=session_id)
            return True
        return False
    
    def list_sessions(self, agent_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by agent_id"""
        sessions = []
        for session in self.sessions.values():
            if agent_id is None or session.agent_id == agent_id:
                sessions.append(session.get_context_summary())
        return sessions
    
    def get_session_count(self) -> int:
        """Get the total number of active sessions"""
        return len(self.sessions)
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """Clean up sessions that haven't been active for a specified time"""
        from datetime import timedelta
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        inactive_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.last_activity < cutoff_time
        ]
        
        for session_id in inactive_sessions:
            self.delete_session(session_id)
        
        if inactive_sessions:
            slog.info("Cleaned up inactive sessions", count=len(inactive_sessions))
        
        return len(inactive_sessions)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the session manager"""
        return {
            "total_sessions": len(self.sessions),
            "sessions_by_agent": {},  # Could be expanded to group by agent_id
            "oldest_session": min(
                (session.created_at for session in self.sessions.values()),
                default=None
            ),
            "most_recent_activity": max(
                (session.last_activity for session in self.sessions.values()),
                default=None
            )
        }

# Global session manager instance
session_manager = AgentSessionManager()

# Export for use in other modules
__all__ = ["AgentSessionManager", "AgentSession", "session_manager"]
