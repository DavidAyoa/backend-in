from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class SessionBase(BaseModel):
    agent_id: int
    mode: str = "voice"  # "voice", "text", "both"

class SessionCreate(SessionBase):
    context_prompts: Optional[list[str]] = None  # Override agent's context prompts
    conversation_context: Optional[Dict[str, Any]] = None  # Initial conversation context
    session_prompt: Optional[str] = None  # Override agent's initial prompt for this session

class SessionUpdate(BaseModel):
    conversation_context: Optional[Dict[str, Any]] = None
    context_prompts: Optional[list[str]] = None
    session_prompt: Optional[str] = None
    mode: Optional[str] = None
    is_active: Optional[bool] = None

class SessionResponse(SessionBase):
    id: int
    user_id: int
    room_name: str
    conversation_context: Dict[str, Any]
    context_prompts: list[str]
    session_prompt: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 