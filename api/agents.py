"""
Agent management API endpoints
Create, read, update, delete voice agents
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json

from services.auth_service import get_current_user, get_pro_user
from models.user import User, user_db
from middleware.rate_limiting import require_api_key_or_jwt, rate_limit_dependency, usage_tracker
from fastapi import Request

# Define FastAPI router
router = APIRouter(tags=["Agents"])

# Request and Response Models
class CreateAgentRequest(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default="", max_length=500)
    system_prompt: Optional[str] = Field(default="", max_length=2000)
    voice_settings: Optional[Dict[str, Any]] = Field(default_factory=dict)

class AgentResponse(BaseModel):
    id: int
    agent_name: str
    description: str
    system_prompt: str
    voice_settings: Dict[str, Any]
    status: str
    created_at: str
    updated_at: str

class UpdateAgentRequest(BaseModel):
    agent_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: Optional[str] = Field(None, max_length=2000)
    voice_settings: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None

class CloneAgentRequest(BaseModel):
    new_name: Optional[str] = Field(None, min_length=1, max_length=100)

class MarketplaceAgentResponse(BaseModel):
    id: int
    agent_name: str
    description: str
    system_prompt: str
    voice_settings: Dict[str, Any]
    category: str
    tags: List[str]
    clone_count: int
    creator_username: str
    creator_name: str
    created_at: str
    updated_at: str

# Agent endpoints
@router.post("/", response_model=AgentResponse)
async def create_agent(request: CreateAgentRequest, current_user: User = Depends(get_current_user)):
    """Create a new voice agent"""
    
    # Check if user can create agents
    current_agents = user_db.get_agents_by_user_id(current_user.id)
    if len(current_agents) >= current_user.get_agent_limit():
        raise HTTPException(
            status_code=403, 
            detail=f"Agent limit reached. {current_user.role.value} users can create up to {current_user.get_agent_limit()} agents."
        )
    
    # Create agent
    agent_id = user_db.create_agent(current_user.id, request.agent_name)
    if not agent_id:
        raise HTTPException(status_code=500, detail="Failed to create agent")
    
    # Update agent with additional details
    update_data = {
        "description": request.description,
        "system_prompt": request.system_prompt,
        "voice_settings": request.voice_settings
    }
    user_db.update_agent(agent_id, update_data)
    
    # Update user stats
    current_user.usage_stats["agents_created"] = current_user.usage_stats.get("agents_created", 0) + 1
    user_db.update_user(current_user)
    
    # Get created agent
    agent = user_db.get_agent_by_id(agent_id)
    return agent

@router.get("/", response_model=List[AgentResponse])
async def list_agents(current_user: User = Depends(get_current_user)):
    """List all agents for the current user"""
    agents = user_db.get_agents_by_user_id(current_user.id)
    return agents

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    """Get a specific agent by ID"""
    agent = user_db.get_agent_by_id(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return agent

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int, 
    request: UpdateAgentRequest, 
    current_user: User = Depends(get_current_user)
):
    """Update an existing agent"""
    agent = user_db.get_agent_by_id(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update agent
    updated = user_db.update_agent(agent_id, request.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update agent")
    
    # Get updated agent
    updated_agent = user_db.get_agent_by_id(agent_id)
    return updated_agent

@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, current_user: User = Depends(get_current_user)):
    """Delete an agent"""
    agent = user_db.get_agent_by_id(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete agent
    deleted = user_db.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete agent")
    
    return {"message": "Agent deleted successfully"}

@router.get("/{agent_id}/usage")
async def get_agent_usage(agent_id: int, current_user: User = Depends(get_current_user)):
    """Get usage statistics for an agent"""
    agent = user_db.get_agent_by_id(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get usage stats
    usage_stats = user_db.get_agent_usage_stats(agent_id)
    return usage_stats

# Marketplace endpoints
@router.get("/marketplace/browse", response_model=List[MarketplaceAgentResponse])
async def browse_marketplace(category: Optional[str] = None, limit: int = 50, offset: int = 0):
    """Browse public agents in the marketplace"""
    agents = user_db.get_public_agents(category=category, limit=limit, offset=offset)
    return agents

@router.get("/marketplace/search", response_model=List[MarketplaceAgentResponse])
async def search_marketplace(q: str, category: Optional[str] = None, limit: int = 50):
    """Search public agents in the marketplace"""
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
    
    agents = user_db.search_public_agents(q.strip(), category=category, limit=limit)
    return agents

@router.get("/marketplace/trending", response_model=List[MarketplaceAgentResponse])
async def get_trending_agents(limit: int = 10):
    """Get trending agents based on clone count"""
    agents = user_db.get_trending_agents(limit=limit)
    return agents

@router.get("/marketplace/stats")
async def get_marketplace_stats():
    """Get marketplace statistics"""
    stats = user_db.get_marketplace_stats()
    return stats

@router.post("/{agent_id}/clone", response_model=AgentResponse)
async def clone_agent(agent_id: int, request: CloneAgentRequest, current_user: User = Depends(get_current_user)):
    """Clone an agent from the marketplace"""
    # Check if user can create agents
    current_agents = user_db.get_agents_by_user_id(current_user.id)
    if len(current_agents) >= current_user.get_agent_limit():
        raise HTTPException(
            status_code=403, 
            detail=f"Agent limit reached. {current_user.role.value} users can create up to {current_user.get_agent_limit()} agents."
        )
    
    # Clone the agent
    clone_id = user_db.clone_agent(agent_id, current_user.id, request.new_name)
    if not clone_id:
        raise HTTPException(status_code=404, detail="Agent not found or not available for cloning")
    
    # Update user stats
    current_user.usage_stats["agents_created"] = current_user.usage_stats.get("agents_created", 0) + 1
    user_db.update_user(current_user)
    
    # Get cloned agent
    cloned_agent = user_db.get_agent_by_id(clone_id)
    return cloned_agent

@router.get("/{agent_id}/clones", response_model=List[MarketplaceAgentResponse])
async def get_agent_clones(agent_id: int, current_user: User = Depends(get_current_user)):
    """Get all clones of an agent (owner only)"""
    agent = user_db.get_agent_by_id(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    clones = user_db.get_agent_clones(agent_id)
    return clones

@router.put("/{agent_id}/visibility")
async def set_agent_visibility(agent_id: int, is_public: bool, current_user: User = Depends(get_current_user)):
    """Set agent visibility (public/private)"""
    agent = user_db.get_agent_by_id(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update visibility
    updated = user_db.update_agent(agent_id, {"is_public": is_public})
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update agent visibility")
    
    return {
        "message": f"Agent {'published to' if is_public else 'removed from'} marketplace",
        "is_public": is_public
    }

# Export router
__all__ = ["router"]
