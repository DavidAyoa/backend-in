from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AgentBase(BaseModel):
    name: str
    initial_prompt: str
    context_prompts: Optional[List[str]] = []
    voice_enabled: bool = True
    text_enabled: bool = True
    response_type: str = "both"  # "voice", "text", "both"

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    initial_prompt: Optional[str] = None
    context_prompts: Optional[List[str]] = None
    voice_enabled: Optional[bool] = None
    text_enabled: Optional[bool] = None
    response_type: Optional[str] = None

class AgentResponse(AgentBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 