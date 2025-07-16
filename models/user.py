"""
User management database models
SQLite implementation with future PostgreSQL migration support
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import json

class UserRole(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"

class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

@dataclass
class User:
    """User model with all necessary fields"""
    id: Optional[int] = None
    email: str = ""
    username: str = ""
    password_hash: str = ""
    full_name: str = ""
    role: UserRole = UserRole.FREE
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    api_key: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    email_verified: bool = False
    profile_data: Dict[str, Any] = None
    usage_stats: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.profile_data is None:
            self.profile_data = {}
        if self.usage_stats is None:
            self.usage_stats = {
                "total_sessions": 0,
                "total_minutes": 0.0,
                "agents_created": 0,
                "last_session": None
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary (excluding sensitive data)"""
        data = asdict(self)
        # Remove sensitive fields
        data.pop('password_hash', None)
        data.pop('api_key', None)
        # Convert enums to strings
        data['role'] = self.role.value
        data['status'] = self.status.value
        # Convert datetime to string
        for field in ['created_at', 'updated_at', 'last_login']:
            if data[field]:
                data[field] = data[field].isoformat()
        return data
    
    def is_active(self) -> bool:
        """Check if user is active"""
        return self.status == UserStatus.ACTIVE
    
    def can_create_agents(self) -> bool:
        """Check if user can create agents based on role"""
        return self.role in [UserRole.PRO, UserRole.ENTERPRISE, UserRole.ADMIN]
    
    def get_agent_limit(self) -> int:
        """Get maximum number of agents user can create"""
        limits = {
            UserRole.FREE: 3,
            UserRole.PRO: 25,
            UserRole.ENTERPRISE: 100,
            UserRole.ADMIN: 999
        }
        return limits.get(self.role, 0)

class UserDatabase:
    """SQLite-based user database with migration support"""
    
    def __init__(self, db_path: str = "voice_agent.sqlite"):
        self.db_path = db_path
        self.init_database()
        
    def create_agent(self, user_id: int, agent_name: str) -> Optional[int]:
        """Create a new agent for the user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO agents (user_id, agent_name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, agent_name, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            return cursor.lastrowid

    def get_agents_by_user_id(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all agents for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM agents WHERE user_id = ?", (user_id,))
            agents = []
            for row in cursor.fetchall():
                agent = dict(row)
                # Parse JSON fields
                if agent.get('voice_settings'):
                    try:
                        agent['voice_settings'] = json.loads(agent['voice_settings'])
                    except (json.JSONDecodeError, TypeError):
                        agent['voice_settings'] = {}
                else:
                    agent['voice_settings'] = {}
                
                if agent.get('tags'):
                    try:
                        agent['tags'] = json.loads(agent['tags'])
                    except (json.JSONDecodeError, TypeError):
                        agent['tags'] = []
                else:
                    agent['tags'] = []
                
                agents.append(agent)
            return agents
    
    def get_agent_by_id(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """Get agent by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
            row = cursor.fetchone()
            if row:
                agent = dict(row)
                # Parse JSON fields
                if agent.get('voice_settings'):
                    try:
                        agent['voice_settings'] = json.loads(agent['voice_settings'])
                    except (json.JSONDecodeError, TypeError):
                        agent['voice_settings'] = {}
                else:
                    agent['voice_settings'] = {}
                return agent
            return None
    
    def update_agent(self, agent_id: int, update_data: Dict[str, Any]) -> bool:
        """Update agent information"""
        if not update_data:
            return True
        
        # Build dynamic update query
        update_fields = []
        values = []
        
        for field, value in update_data.items():
            if field in ['agent_name', 'description', 'system_prompt', 'status', 'category']:
                update_fields.append(f"{field} = ?")
                values.append(value)
            elif field in ['is_public', 'original_agent_id', 'clone_count']:
                update_fields.append(f"{field} = ?")
                values.append(value)
            elif field == 'voice_settings':
                update_fields.append("voice_settings = ?")
                values.append(json.dumps(value))
            elif field == 'tags':
                update_fields.append("tags = ?")
                values.append(json.dumps(value))
        
        if not update_fields:
            return True
        
        # Add updated_at
        update_fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(agent_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE agents SET {', '.join(update_fields)} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0
    
    def delete_agent(self, agent_id: int) -> bool:
        """Delete an agent"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
            return cursor.rowcount > 0
    
    def log_usage(self, user_id: int, usage_type: str, agent_id: Optional[int] = None, 
                  session_id: Optional[str] = None, tokens_used: int = 0, 
                  duration_seconds: float = 0, cost: float = 0) -> bool:
        """Log usage for tracking"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO usage_logs (user_id, agent_id, session_id, usage_type, 
                                      tokens_used, duration_seconds, cost, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, agent_id, session_id, usage_type,
                tokens_used, duration_seconds, cost,
                datetime.utcnow().isoformat()
            ))
            return cursor.rowcount > 0
    
    def get_agent_usage_stats(self, agent_id: int) -> Dict[str, Any]:
        """Get usage statistics for an agent"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(tokens_used) as total_tokens,
                    SUM(duration_seconds) as total_duration,
                    SUM(cost) as total_cost,
                    AVG(duration_seconds) as avg_duration
                FROM usage_logs 
                WHERE agent_id = ?
            """, (agent_id,))
            row = cursor.fetchone()
            
            return {
                "total_sessions": row[0] or 0,
                "total_tokens": row[1] or 0,
                "total_duration": row[2] or 0.0,
                "total_cost": row[3] or 0.0,
                "avg_duration": row[4] or 0.0
            }
    
    def get_user_usage_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        from_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(tokens_used) as total_tokens,
                    SUM(duration_seconds) as total_duration,
                    SUM(cost) as total_cost
                FROM usage_logs 
                WHERE user_id = ? AND created_at >= ?
            """, (user_id, from_date))
            row = cursor.fetchone()
            
            return {
                "total_sessions": row[0] or 0,
                "total_tokens": row[1] or 0,
                "total_duration": row[2] or 0.0,
                "total_cost": row[3] or 0.0,
                "period_days": days
            }
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'free',
                    status TEXT DEFAULT 'pending_verification',
                    api_key TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login TEXT,
                    email_verified BOOLEAN DEFAULT FALSE,
                    profile_data TEXT DEFAULT '{}',
                    usage_stats TEXT DEFAULT '{}'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    agent_name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    system_prompt TEXT DEFAULT '',
                    voice_settings TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'active',
                    is_public BOOLEAN DEFAULT FALSE,
                    original_agent_id INTEGER,
                    clone_count INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '[]',
                    category TEXT DEFAULT 'general',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (original_agent_id) REFERENCES agents (id) ON DELETE SET NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    agent_id INTEGER,
                    session_id TEXT,
                    usage_type TEXT NOT NULL, -- 'voice_session', 'api_call', 'stt', 'tts'
                    tokens_used INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0,
                    cost REAL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE SET NULL
                )
            """)
            
            # Create indexes one by one
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
    
    def _row_to_user(self, row) -> User:
        """Convert database row to User object"""
        return User(
            id=row[0],
            email=row[1],
            username=row[2],
            password_hash=row[3],
            full_name=row[4],
            role=UserRole(row[5]),
            status=UserStatus(row[6]),
            api_key=row[7],
            created_at=datetime.fromisoformat(row[8]) if row[8] else None,
            updated_at=datetime.fromisoformat(row[9]) if row[9] else None,
            last_login=datetime.fromisoformat(row[10]) if row[10] else None,
            email_verified=bool(row[11]),
            profile_data=json.loads(row[12]) if row[12] else {},
            usage_stats=json.loads(row[13]) if row[13] else {}
        )
    
    def create_user(self, email: str, username: str, password: str, 
                   full_name: str = "", role: UserRole = UserRole.FREE) -> User:
        """Create a new user"""
        user = User(
            email=email.lower(),
            username=username,
            password_hash=self._hash_password(password),
            full_name=full_name,
            role=role,
            api_key=self._generate_api_key()
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO users (email, username, password_hash, full_name, role, status, 
                                 api_key, created_at, updated_at, email_verified, profile_data, usage_stats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.email, user.username, user.password_hash, user.full_name,
                user.role.value, user.status.value, user.api_key,
                user.created_at.isoformat(), user.updated_at.isoformat(),
                user.email_verified, json.dumps(user.profile_data), json.dumps(user.usage_stats)
            ))
            user.id = cursor.lastrowid
        
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
    
    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
    
    def update_user(self, user: User) -> bool:
        """Update user information"""
        user.updated_at = datetime.utcnow()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE users SET email = ?, username = ?, full_name = ?, role = ?, 
                               status = ?, updated_at = ?, last_login = ?, email_verified = ?,
                               profile_data = ?, usage_stats = ?
                WHERE id = ?
            """, (
                user.email, user.username, user.full_name, user.role.value,
                user.status.value, user.updated_at.isoformat(),
                user.last_login.isoformat() if user.last_login else None,
                user.email_verified, json.dumps(user.profile_data),
                json.dumps(user.usage_stats), user.id
            ))
            return cursor.rowcount > 0
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user (and all related data)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cursor.rowcount > 0
    
    def verify_password(self, user: User, password: str) -> bool:
        """Verify user password"""
        return self._verify_password(password, user.password_hash)
    
    def change_password(self, user: User, new_password: str) -> bool:
        """Change user password"""
        user.password_hash = self._hash_password(new_password)
        user.updated_at = datetime.utcnow()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?
            """, (user.password_hash, user.updated_at.isoformat(), user.id))
            return cursor.rowcount > 0
    
    def update_last_login(self, user_id: int):
        """Update user's last login time"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users SET last_login = ? WHERE id = ?
            """, (datetime.utcnow().isoformat(), user_id))
    
    def get_users_by_role(self, role: UserRole) -> List[User]:
        """Get all users with specific role"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM users WHERE role = ?", (role.value,))
            return [self._row_to_user(row) for row in cursor.fetchall()]
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_users,
                    SUM(CASE WHEN role = 'free' THEN 1 ELSE 0 END) as free_users,
                    SUM(CASE WHEN role = 'pro' THEN 1 ELSE 0 END) as pro_users,
                    SUM(CASE WHEN role = 'enterprise' THEN 1 ELSE 0 END) as enterprise_users
                FROM users
            """)
            row = cursor.fetchone()
            return {
                "total_users": row[0],
                "active_users": row[1],
                "free_users": row[2],
                "pro_users": row[3],
                "enterprise_users": row[4]
            }
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_value = password_hash.split(':')
            return hashlib.sha256((password + salt).encode()).hexdigest() == hash_value
        except ValueError:
            return False
    
    def _generate_api_key(self) -> str:
        """Generate unique API key"""
        return f"va_{secrets.token_urlsafe(32)}"
    
    # Marketplace methods
    def get_public_agents(self, category: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get public agents for marketplace"""
        query = """
            SELECT a.*, u.username as creator_username, u.full_name as creator_name
            FROM agents a
            JOIN users u ON a.user_id = u.id
            WHERE a.is_public = TRUE AND a.status = 'active'
        """
        params = []
        
        if category:
            query += " AND a.category = ?"
            params.append(category)
        
        query += " ORDER BY a.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            agents = []
            for row in cursor.fetchall():
                agent = dict(row)
                # Parse JSON fields
                if agent.get('voice_settings'):
                    try:
                        agent['voice_settings'] = json.loads(agent['voice_settings'])
                    except (json.JSONDecodeError, TypeError):
                        agent['voice_settings'] = {}
                else:
                    agent['voice_settings'] = {}
                
                if agent.get('tags'):
                    try:
                        agent['tags'] = json.loads(agent['tags'])
                    except (json.JSONDecodeError, TypeError):
                        agent['tags'] = []
                else:
                    agent['tags'] = []
                
                agents.append(agent)
            return agents
    
    def search_public_agents(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search public agents by name, description, or tags"""
        search_query = """
            SELECT a.*, u.username as creator_username, u.full_name as creator_name
            FROM agents a
            JOIN users u ON a.user_id = u.id
            WHERE a.is_public = TRUE AND a.status = 'active'
            AND (a.agent_name LIKE ? OR a.description LIKE ? OR a.tags LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%", f"%{query}%"]
        
        if category:
            search_query += " AND a.category = ?"
            params.append(category)
        
        search_query += " ORDER BY a.created_at DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(search_query, params)
            agents = []
            for row in cursor.fetchall():
                agent = dict(row)
                # Parse JSON fields
                if agent.get('voice_settings'):
                    try:
                        agent['voice_settings'] = json.loads(agent['voice_settings'])
                    except (json.JSONDecodeError, TypeError):
                        agent['voice_settings'] = {}
                else:
                    agent['voice_settings'] = {}
                
                if agent.get('tags'):
                    try:
                        agent['tags'] = json.loads(agent['tags'])
                    except (json.JSONDecodeError, TypeError):
                        agent['tags'] = []
                else:
                    agent['tags'] = []
                
                agents.append(agent)
            return agents
    
    def clone_agent(self, agent_id: int, user_id: int, new_name: Optional[str] = None) -> Optional[int]:
        """Clone an agent for a user"""
        original_agent = self.get_agent_by_id(agent_id)
        if not original_agent:
            return None
        
        # Check if agent is public or user owns it
        if not original_agent.get('is_public', False) and original_agent.get('user_id') != user_id:
            return None
        
        # Create cloned agent
        clone_name = new_name or f"{original_agent['agent_name']} (Clone)"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO agents (user_id, agent_name, description, system_prompt, 
                                  voice_settings, category, tags, original_agent_id, 
                                  created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                clone_name,
                original_agent['description'],
                original_agent['system_prompt'],
                json.dumps(original_agent.get('voice_settings', {})),
                original_agent.get('category', 'general'),
                json.dumps(original_agent.get('tags', [])),
                agent_id,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            clone_id = cursor.lastrowid
            
            # Update clone count on original agent
            cursor.execute("""
                UPDATE agents SET clone_count = clone_count + 1 WHERE id = ?
            """, (agent_id,))
            
            return clone_id
    
    def get_agent_clones(self, agent_id: int) -> List[Dict[str, Any]]:
        """Get all clones of an agent"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT a.*, u.username as creator_username, u.full_name as creator_name
                FROM agents a
                JOIN users u ON a.user_id = u.id
                WHERE a.original_agent_id = ?
                ORDER BY a.created_at DESC
            """, (agent_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_public_agents,
                    SUM(clone_count) as total_clones,
                    COUNT(DISTINCT category) as total_categories,
                    COUNT(DISTINCT user_id) as total_creators
                FROM agents 
                WHERE is_public = TRUE AND status = 'active'
            """)
            row = cursor.fetchone()
            
            # Get category breakdown
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM agents 
                WHERE is_public = TRUE AND status = 'active'
                GROUP BY category
                ORDER BY count DESC
            """)
            categories = [{'category': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            return {
                "total_public_agents": row[0] or 0,
                "total_clones": row[1] or 0,
                "total_categories": row[2] or 0,
                "total_creators": row[3] or 0,
                "categories": categories
            }
    
    def get_trending_agents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending agents based on clone count and recent activity"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT a.*, u.username as creator_username, u.full_name as creator_name
                FROM agents a
                JOIN users u ON a.user_id = u.id
                WHERE a.is_public = TRUE AND a.status = 'active'
                ORDER BY a.clone_count DESC, a.created_at DESC
                LIMIT ?
            """, (limit,))
            
            agents = []
            for row in cursor.fetchall():
                agent = dict(row)
                # Parse JSON fields
                if agent.get('voice_settings'):
                    try:
                        agent['voice_settings'] = json.loads(agent['voice_settings'])
                    except (json.JSONDecodeError, TypeError):
                        agent['voice_settings'] = {}
                else:
                    agent['voice_settings'] = {}
                
                if agent.get('tags'):
                    try:
                        agent['tags'] = json.loads(agent['tags'])
                    except (json.JSONDecodeError, TypeError):
                        agent['tags'] = []
                else:
                    agent['tags'] = []
                
                agents.append(agent)
            return agents

# Global database instance
user_db = UserDatabase()
