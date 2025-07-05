from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    initial_prompt = Column(Text, nullable=False)
    context_prompts = Column(JSON, default=list)  # List of context prompts
    voice_enabled = Column(Boolean, default=True)
    text_enabled = Column(Boolean, default=True)
    response_type = Column(String, default="both")  # "voice", "text", "both"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="agents")
    sessions = relationship("Session", back_populates="agent") 