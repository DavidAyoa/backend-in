"""
Authentication service for user management
JWT-based authentication with session management
"""

import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from functools import wraps
import sqlite3
import json

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.user import User, UserDatabase, UserRole, UserStatus, user_db

# JWT Configuration
JWT_SECRET_KEY = secrets.token_urlsafe(32)  # In production, use environment variable
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security
security = HTTPBearer(auto_error=False)

class AuthService:
    """Authentication service with JWT and session management"""
    
    def __init__(self, db: UserDatabase):
        self.db = db
        self.jwt_secret = JWT_SECRET_KEY
        self.jwt_algorithm = JWT_ALGORITHM
        self.jwt_expiration = timedelta(hours=JWT_EXPIRATION_HOURS)
    
    def register_user(self, email: str, username: str, password: str, 
                     full_name: str = "") -> Tuple[User, str]:
        """Register a new user and return user + JWT token"""
        # Check if user already exists
        if self.db.get_user_by_email(email):
            raise HTTPException(status_code=400, detail="Email already registered")
        
        if self.db.get_user_by_username(username):
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Validate password strength
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
        # Create user (active by default for now)
        user = self.db.create_user(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            role=UserRole.FREE
        )
        
        # Set user as active (skip email verification for now)
        user.status = UserStatus.ACTIVE
        user.email_verified = True
        self.db.update_user(user)
        
        # Generate JWT token
        token = self._generate_jwt_token(user)
        
        return user, token
    
    def login_user(self, email_or_username: str, password: str) -> Tuple[User, str]:
        """Login user and return user + JWT token"""
        # Try to find user by email or username
        user = self.db.get_user_by_email(email_or_username)
        if not user:
            user = self.db.get_user_by_username(email_or_username)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not self.db.verify_password(user, password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if user is active
        if not user.is_active():
            raise HTTPException(status_code=401, detail="Account is not active")
        
        # Update last login
        self.db.update_last_login(user.id)
        
        # Generate JWT token
        token = self._generate_jwt_token(user)
        
        return user, token
    
    def authenticate_token(self, token: str) -> Optional[User]:
        """Authenticate JWT token and return user"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            user_id = payload.get("user_id")
            exp = payload.get("exp")
            
            if not user_id or not exp:
                return None
            
            # Check if token is expired
            if datetime.utcnow().timestamp() > exp:
                return None
            
            # Get user from database
            user = self.db.get_user_by_id(user_id)
            if not user or not user.is_active():
                return None
            
            return user
            
        except jwt.InvalidTokenError:
            return None
    
    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate API key and return user"""
        user = self.db.get_user_by_api_key(api_key)
        if user and user.is_active():
            return user
        return None
    
    def refresh_token(self, old_token: str) -> Optional[str]:
        """Refresh JWT token"""
        user = self.authenticate_token(old_token)
        if user:
            return self._generate_jwt_token(user)
        return None
    
    def logout_user(self, user_id: int):
        """Logout user (invalidate sessions)"""
        # In a more advanced implementation, you would invalidate the JWT token
        # For now, we just update the last login time
        pass
    
    def change_password(self, user: User, old_password: str, new_password: str) -> bool:
        """Change user password"""
        # Verify old password
        if not self.db.verify_password(user, old_password):
            raise HTTPException(status_code=400, detail="Invalid current password")
        
        # Validate new password
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
        
        # Update password
        return self.db.change_password(user, new_password)
    
    def update_user_profile(self, user: User, profile_data: Dict[str, Any]) -> bool:
        """Update user profile"""
        # Update allowed fields
        if "full_name" in profile_data:
            user.full_name = profile_data["full_name"]
        
        if "profile_data" in profile_data:
            user.profile_data.update(profile_data["profile_data"])
        
        return self.db.update_user(user)
    
    def verify_email(self, user: User) -> bool:
        """Mark user email as verified"""
        user.email_verified = True
        user.status = UserStatus.ACTIVE
        return self.db.update_user(user)
    
    def suspend_user(self, user_id: int) -> bool:
        """Suspend user account"""
        user = self.db.get_user_by_id(user_id)
        if user:
            user.status = UserStatus.SUSPENDED
            return self.db.update_user(user)
        return False
    
    def activate_user(self, user_id: int) -> bool:
        """Activate user account"""
        user = self.db.get_user_by_id(user_id)
        if user:
            user.status = UserStatus.ACTIVE
            return self.db.update_user(user)
        return False
    
    def upgrade_user_role(self, user_id: int, new_role: UserRole) -> bool:
        """Upgrade user role"""
        user = self.db.get_user_by_id(user_id)
        if user:
            user.role = new_role
            return self.db.update_user(user)
        return False
    
    def get_user_session_info(self, user: User) -> Dict[str, Any]:
        """Get user session information"""
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "status": user.status.value,
            "agent_limit": user.get_agent_limit(),
            "can_create_agents": user.can_create_agents(),
            "usage_stats": user.usage_stats
        }
    
    def _generate_jwt_token(self, user: User) -> str:
        """Generate JWT token for user"""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "exp": datetime.utcnow() + self.jwt_expiration,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

# Global auth service
auth_service = AuthService(user_db)

# FastAPI Dependencies
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """FastAPI dependency to get current authenticated user"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = auth_service.authenticate_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[User]:
    """FastAPI dependency to get current user (optional)"""
    if not credentials:
        return None
    
    return auth_service.authenticate_token(credentials.credentials)

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency to require admin user"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def get_pro_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency to require pro user or higher"""
    if current_user.role not in [UserRole.PRO, UserRole.ENTERPRISE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Pro subscription required")
    return current_user

# Decorators for role-based access
def require_role(required_role: UserRole):
    """Decorator to require specific user role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be used with the FastAPI dependencies
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_active_user(func):
    """Decorator to require active user"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper
