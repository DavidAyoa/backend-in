from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.user import User
from models.agent import Agent
from schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from routers.auth import verify_token

router = APIRouter()

@router.post("/", response_model=AgentResponse)
def create_agent(
    agent: AgentCreate,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    db_agent = Agent(
        user_id=current_user.id,
        name=agent.name,
        initial_prompt=agent.initial_prompt,
        context_prompts=agent.context_prompts,
        voice_enabled=agent.voice_enabled,
        text_enabled=agent.text_enabled,
        response_type=agent.response_type
    )
    
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    
    return db_agent

@router.get("/", response_model=List[AgentResponse])
def get_agents(
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    agents = db.query(Agent).filter(Agent.user_id == current_user.id).all()
    return agents

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: int,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent

@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    db_agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()
    
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update only provided fields
    update_data = agent_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_agent, field, value)
    
    db.commit()
    db.refresh(db_agent)
    
    return db_agent

@router.delete("/{agent_id}")
def delete_agent(
    agent_id: int,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    db_agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()
    
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(db_agent)
    db.commit()
    
    return {"message": "Agent deleted successfully"} 