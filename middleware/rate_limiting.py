"""
Rate limiting and API key authentication middleware
"""

import time
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta

from models.user import User, UserRole, user_db

class RateLimiter:
    """Rate limiter with different limits per user role"""
    
    def __init__(self):
        # Store request timestamps per user
        self._requests: Dict[str, deque] = defaultdict(deque)
        # Role-based limits (requests per minute)
        self.limits = {
            UserRole.FREE: 60,      # 60 requests per minute
            UserRole.PRO: 600,      # 600 requests per minute  
            UserRole.ENTERPRISE: 3600,  # 3600 requests per minute
            UserRole.ADMIN: 10000   # 10000 requests per minute
        }
        # Voice session limits (concurrent sessions)
        self.voice_limits = {
            UserRole.FREE: 1,       # 1 concurrent voice session
            UserRole.PRO: 5,        # 5 concurrent voice sessions
            UserRole.ENTERPRISE: 25, # 25 concurrent voice sessions
            UserRole.ADMIN: 100     # 100 concurrent voice sessions
        }
    
    def is_allowed(self, user_id: str, user_role: UserRole) -> Tuple[bool, Dict]:
        """Check if request is allowed based on rate limits"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        user_requests = self._requests[user_id]
        while user_requests and user_requests[0] < minute_ago:
            user_requests.popleft()
        
        # Check current limit
        limit = self.limits.get(user_role, self.limits[UserRole.FREE])
        current_count = len(user_requests)
        
        if current_count >= limit:
            return False, {
                "allowed": False,
                "limit": limit,
                "current": current_count,
                "reset_time": int(minute_ago + 60),
                "retry_after": 60
            }
        
        # Add current request
        user_requests.append(now)
        
        return True, {
            "allowed": True,
            "limit": limit,
            "current": current_count + 1,
            "remaining": limit - current_count - 1,
            "reset_time": int(now + 60)
        }
    
    def get_voice_limit(self, user_role: UserRole) -> int:
        """Get voice session limit for user role"""
        return self.voice_limits.get(user_role, self.voice_limits[UserRole.FREE])

# Global rate limiter instance
rate_limiter = RateLimiter()

class APIKeyAuth:
    """API Key authentication handler"""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
    
    async def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate user by API key"""
        if not api_key or not api_key.startswith("va_"):
            return None
        
        user = user_db.get_user_by_api_key(api_key)
        if user and user.is_active():
            return user
        return None
    
    async def get_current_user_api_key(self, request: Request) -> Optional[User]:
        """Get current user from API key (for API endpoints)"""
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # Remove "Bearer "
            user = await self.authenticate_api_key(api_key)
            if user:
                return user
        
        # Try X-API-Key header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            user = await self.authenticate_api_key(api_key)
            if user:
                return user
        
        # Try query parameter
        api_key = request.query_params.get("api_key")
        if api_key:
            user = await self.authenticate_api_key(api_key)
            if user:
                return user
        
        return None

# Global API key auth instance
api_key_auth = APIKeyAuth()

async def rate_limit_dependency(request: Request) -> Dict:
    """FastAPI dependency for rate limiting"""
    # Try to get user (from JWT or API key)
    user = None
    
    # Try JWT first
    try:
        from services.auth_service import get_current_user_optional
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            from services.auth_service import auth_service
            user = auth_service.authenticate_token(token)
    except:
        pass
    
    # Try API key if no JWT user
    if not user:
        user = await api_key_auth.get_current_user_api_key(request)
    
    # Default to FREE role for unauthenticated users
    user_id = str(user.id) if user else request.client.host
    user_role = user.role if user else UserRole.FREE
    
    # Check rate limit
    allowed, rate_info = rate_limiter.is_allowed(user_id, user_role)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_info["reset_time"]),
                "Retry-After": str(rate_info["retry_after"])
            }
        )
    
    # Add rate limit headers for successful requests
    request.state.rate_limit_headers = {
        "X-RateLimit-Limit": str(rate_info["limit"]),
        "X-RateLimit-Remaining": str(rate_info["remaining"]),
        "X-RateLimit-Reset": str(rate_info["reset_time"])
    }
    
    return rate_info

async def get_current_user_api_or_jwt(request: Request) -> Optional[User]:
    """Get current user from either API key or JWT token"""
    # Try API key first
    user = await api_key_auth.get_current_user_api_key(request)
    if user:
        return user
    
    # Try JWT token
    try:
        from services.auth_service import auth_service
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user = auth_service.authenticate_token(token)
            if user:
                return user
    except:
        pass
    
    return None

async def require_api_key_or_jwt(request: Request) -> User:
    """Require either valid API key or JWT token"""
    user = await get_current_user_api_or_jwt(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Valid API key or JWT token required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

# Usage tracking for API calls
class UsageTracker:
    """Track API usage for billing and analytics"""
    
    @staticmethod
    async def log_api_usage(user: User, endpoint: str, method: str, 
                           tokens_used: int = 0, duration: float = 0):
        """Log API usage to database"""
        try:
            user_db.log_usage(
                user_id=user.id,
                usage_type="api_call",
                tokens_used=tokens_used,
                duration_seconds=duration,
                cost=0.0  # Calculate cost based on pricing model
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to log usage: {e}")

usage_tracker = UsageTracker()

__all__ = [
    "rate_limiter", 
    "api_key_auth", 
    "rate_limit_dependency", 
    "get_current_user_api_or_jwt",
    "require_api_key_or_jwt",
    "usage_tracker"
]
