"""
User management API endpoints
Clean endpoints for registration, login, and profile management
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, constr
from typing import Optional, Dict, Any

from services.auth_service import auth_service, get_current_user, get_admin_user
from models.user import User
from datetime import datetime
import sqlite3

# Define FastAPI router with clean paths
router = APIRouter(tags=["Authentication"])

# Request and Response Models
class UserRegistrationRequest(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=8)
    full_name: Optional[str] = ""

class UserLoginRequest(BaseModel):
    email_or_username: str
    password: str

class AuthResponse(BaseModel):
    user: Dict[str, Any]
    token: str
    expires_in: int = 86400  # 24 hours in seconds

class UserProfileResponse(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str]
    role: str
    status: str
    email_verified: bool
    created_at: str
    last_login: Optional[str]
    usage_stats: Dict[str, Any]

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: constr(min_length=8)

# Authentication endpoints
@router.post("/register", response_model=AuthResponse)
async def register_user(request: UserRegistrationRequest):
    """Register a new user"""
    user, token = auth_service.register_user(
        email=request.email,
        username=request.username,
        password=request.password,
        full_name=request.full_name
    )
    
    return {
        "user": user.to_dict(),
        "token": token,
        "expires_in": 86400
    }

@router.post("/login", response_model=AuthResponse)
async def login_user(request: UserLoginRequest):
    """Login a user"""
    user, token = auth_service.login_user(
        email_or_username=request.email_or_username,
        password=request.password
    )
    
    return {
        "user": user.to_dict(),
        "token": token,
        "expires_in": 86400
    }

@router.post("/refresh")
async def refresh_token(token: str):
    """Refresh JWT token"""
    new_token = auth_service.refresh_token(token)
    if not new_token:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {
        "token": new_token,
        "expires_in": 86400
    }

@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_user)):
    """Logout current user"""
    auth_service.logout_user(current_user.id)
    return {"message": "Logged out successfully"}

# Profile management endpoints
@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile"""
    return current_user.to_dict()

@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    request: UpdateProfileRequest, 
    current_user: User = Depends(get_current_user)
):
    """Update current user's profile"""
    update_data = request.dict(exclude_unset=True)
    updated = auth_service.update_user_profile(current_user, update_data)
    
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to update profile")
    
    # Refresh user data
    updated_user = auth_service.db.get_user_by_id(current_user.id)
    return updated_user.to_dict()

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """Change user password"""
    success = auth_service.change_password(
        current_user, 
        request.old_password, 
        request.new_password
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to change password")
    
    return {"message": "Password changed successfully"}

@router.get("/api-key")
async def get_api_key(current_user: User = Depends(get_current_user)):
    """Get current user's API key"""
    return {
        "api_key": current_user.api_key,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@router.post("/api-key/regenerate")
async def regenerate_api_key(current_user: User = Depends(get_current_user)):
    """Regenerate user's API key"""
    # Generate new API key
    new_api_key = auth_service.db._generate_api_key()
    
    # Update user with new API key
    with sqlite3.connect(auth_service.db.db_path) as conn:
        conn.execute(
            "UPDATE users SET api_key = ?, updated_at = ? WHERE id = ?",
            (new_api_key, datetime.utcnow().isoformat(), current_user.id)
        )
    
    return {
        "api_key": new_api_key,
        "message": "API key regenerated successfully",
        "warning": "Your old API key is now invalid"
    }

@router.get("/session")
async def get_session_info(current_user: User = Depends(get_current_user)):
    """Get current user session information"""
    return auth_service.get_user_session_info(current_user)

# Admin endpoints
@router.get("/users", dependencies=[Depends(get_admin_user)])
async def list_users(skip: int = 0, limit: int = 100):
    """List all users (admin only)"""
    # This would be implemented with proper pagination
    return {"message": "Admin endpoint - list users"}

@router.get("/stats", dependencies=[Depends(get_admin_user)])
async def get_user_stats():
    """Get user statistics (admin only)"""
    stats = auth_service.db.get_user_stats()
    return stats

# User management router (separate from auth)
user_router = APIRouter(tags=["Users"])

@user_router.get("/me", response_model=UserProfileResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information (alias for /auth/profile)"""
    return current_user.to_dict()

@user_router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user by ID (own profile or admin)"""
    if current_user.id != user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = auth_service.db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user.to_dict()

# Export both routers
__all__ = ["router", "user_router"]
