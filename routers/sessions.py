from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from models.user import User
from models.agent import Agent
from models.session import Session as SessionModel
from schemas.session import SessionCreate, SessionResponse, SessionUpdate
from routers.auth import verify_token
from services.livekit_service import livekit_service

router = APIRouter()

@router.post("/", response_model=SessionResponse)
def create_session(
    session: SessionCreate,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Verify agent belongs to user
    agent = db.query(Agent).filter(
        Agent.id == session.agent_id,
        Agent.user_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Generate unique room name
    room_name = f"room_{current_user.id}_{session.agent_id}_{uuid.uuid4().hex[:8]}"
    
    # Get agent to inherit context prompts if not provided
    agent = db.query(Agent).filter(Agent.id == session.agent_id).first()
    context_prompts = session.context_prompts if session.context_prompts is not None else agent.context_prompts
    
    db_session = SessionModel(
        user_id=current_user.id,
        agent_id=session.agent_id,
        room_name=room_name,
        mode=session.mode,
        conversation_context=session.conversation_context or {},
        context_prompts=context_prompts,
        session_prompt=session.session_prompt
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    return db_session

@router.get("/", response_model=List[SessionResponse])
def get_sessions(
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    sessions = db.query(SessionModel).filter(SessionModel.user_id == current_user.id).all()
    return sessions

@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

@router.put("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: int,
    session_update: SessionUpdate,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    db_session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update only provided fields
    update_data = session_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_session, field, value)
    
    db.commit()
    db.refresh(db_session)
    
    return db_session

@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    db_session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(db_session)
    db.commit()
    
    return {"message": "Session deleted successfully"}

@router.post("/{session_id}/join")
def join_session(
    session_id: int,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get session details for joining a LiveKit room"""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is not active")
    
    # Return session details needed for LiveKit connection
    return {
        "session_id": session.id,
        "room_name": session.room_name,
        "agent_id": session.agent_id,
        "mode": session.mode,
        "conversation_context": session.conversation_context,
        "session_prompt": session.session_prompt
    }

@router.post("/{session_id}/start")
async def start_livekit_session(
    session_id: int,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Start a LiveKit session and join the room"""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is not active")
    
    try:
        # Start the LiveKit session
        await livekit_service.join_room(
            session_id=session.id,
            room_name=session.room_name,
            mode=session.mode
        )
        
        return {
            "message": "LiveKit session started successfully",
            "session_id": session.id,
            "room_name": session.room_name,
            "mode": session.mode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start LiveKit session: {str(e)}")

@router.post("/{session_id}/message")
async def send_message(
    session_id: int,
    message: str,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Send a text message to the agent in an active session and return the agent's reply"""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is not active")
    
    try:
        # Send text message to the agent and get the reply
        reply = await livekit_service.send_text_message(session_id, message)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.put("/{session_id}/prompt")
async def update_session_prompt(
    session_id: int,
    new_prompt: str,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update the session prompt dynamically"""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Update the session prompt in LiveKit
        await livekit_service.update_session_prompt(session_id, new_prompt)
        
        return {"message": "Session prompt updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update session prompt: {str(e)}")

@router.post("/{session_id}/end")
async def end_livekit_session(
    session_id: int,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """End a LiveKit session"""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # End the LiveKit session
        await livekit_service.end_session(session_id)
        
        # Mark session as inactive in database
        session.is_active = False
        db.commit()
        
        return {"message": "LiveKit session ended successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end LiveKit session: {str(e)}") 