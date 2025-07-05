from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    room_name = Column(String, unique=True, nullable=False)
    conversation_context = Column(JSON, default=dict)  # Current conversation context
    context_prompts = Column(JSON, default=list)  # Session-specific context prompts
    session_prompt = Column(Text, nullable=True)  # Override agent's initial prompt for this session
    mode = Column(String, default="voice")  # "voice", "text", "both"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")
    agent = relationship("Agent", back_populates="sessions")
    conversation_history = relationship("ConversationHistory", back_populates="session") 