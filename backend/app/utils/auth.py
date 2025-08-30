"""
Ocean Sentinel - Authentication Utilities
JWT token handling and user authentication helpers
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.utils.database import create_supabase_client

logger = logging.getLogger(__name__)

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
supabase = create_supabase_client()

# Token and password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None

# Authentication dependencies
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = verify_token(token)
        
        if payload is None:
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except Exception:
        raise credentials_exception
    
    # Get user from database
    try:
        result = await supabase.table('users')\
            .select('*')\
            .eq('id', user_id)\
            .eq('is_active', True)\
            .execute()
        
        if not result.data:
            raise credentials_exception
        
        user_data = result.data[0]
        # Remove sensitive data
        user_data.pop('hashed_password', None)
        
        return user_data
        
    except Exception as e:
        logger.error(f"Error fetching user data: {e}")
        raise credentials_exception

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Get current user if token is provided, otherwise return None"""
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

# Role-based access control
class RoleChecker:
    """Check if user has required role"""
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: dict = Depends(get_current_user)):
        user_role = current_user.get('role')
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
            )
        return current_user

# Pre-defined role checkers
require_admin = RoleChecker(['admin'])
require_manager = RoleChecker(['admin', 'emergency_manager'])
require_analyst = RoleChecker(['admin', 'emergency_manager', 'analyst'])

# Permission utilities
def check_resource_access(user: dict, resource_owner_id: Optional[str] = None) -> bool:
    """Check if user can access a resource"""
    user_role = user.get('role')
    user_id = user.get('id')
    
    # Admins can access everything
    if user_role == 'admin':
        return True
    
    # Emergency managers can access most resources
    if user_role == 'emergency_manager':
        return True
    
    # Regular users can only access their own resources
    if resource_owner_id and user_id == resource_owner_id:
        return True
    
    # Analysts can read most data but not modify
    if user_role == 'analyst':
        return True  # Read access only - write access checked elsewhere
    
    return False

def require_resource_access(resource_owner_id: Optional[str] = None):
    """Dependency to check resource access"""
    def check_access(current_user: dict = Depends(get_current_user)):
        if not check_resource_access(current_user, resource_owner_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access this resource"
            )
        return current_user
    
    return check_access

# Session management
class SessionManager:
    """Manage user sessions and token blacklisting"""
    
    def __init__(self):
        self.blacklisted_tokens = set()  # In production, use Redis or database
    
    def blacklist_token(self, token: str):
        """Add token to blacklist"""
        self.blacklisted_tokens.add(token)
        logger.info("Token blacklisted")
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        return token in self.blacklisted_tokens
    
    async def logout_user(self, token: str, user_id: str):
        """Logout user and blacklist token"""
        self.blacklist_token(token)
        
        # Update last logout time in database
        try:
            await supabase.table('users')\
                .update({'last_logout': datetime.utcnow().isoformat()})\
                .eq('id', user_id)\
                .execute()
        except Exception as e:
            logger.error(f"Error updating logout time: {e}")

# Global session manager
session_manager = SessionManager()

# API key authentication for external integrations
async def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Verify API key for external integrations"""
    try:
        # In production, store API keys in database with proper hashing
        result = await supabase.table('api_keys')\
            .select('*')\
            .eq('key_hash', get_password_hash(api_key))\
            .eq('is_active', True)\
            .execute()
        
        if result.data:
            key_data = result.data[0]
            
            # Check expiration
            if key_data.get('expires_at'):
                expires_at = datetime.fromisoformat(key_data['expires_at'])
                if expires_at < datetime.utcnow():
                    return None
            
            # Update last used
            await supabase.table('api_keys')\
                .update({'last_used': datetime.utcnow().isoformat()})\
                .eq('id', key_data['id'])\
                .execute()
            
            return key_data
        
        return None
        
    except Exception as e:
        logger.error(f"API key verification error: {e}")
        return None

def get_api_key_user(api_key: str = Depends(security)):
    """Get user from API key authentication"""
    async def verify_key():
        key_data = await verify_api_key(api_key)
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        return key_data
    
    return verify_key

# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}  # In production, use Redis
    
    def is_allowed(self, identifier: str, limit: int, window: int) -> bool:
        """Check if request is allowed within rate limit"""
        now = datetime.utcnow()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove old requests outside the window
        cutoff = now - timedelta(seconds=window)
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] 
            if req_time > cutoff
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) < limit:
            self.requests[identifier].append(now)
            return True
        
        return False

# Global rate limiter
rate_limiter = RateLimiter()

def create_rate_limit_dependency(limit: int, window: int = 60):
    """Create rate limiting dependency"""
    def check_rate_limit(current_user: dict = Depends(get_current_user)):
        user_id = current_user.get('id')
        
        if not rate_limiter.is_allowed(user_id, limit, window):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit} requests per {window} seconds"
            )
        
        return current_user
    
    return check_rate_limit

# Audit logging
async def log_user_activity(
    user_id: str, 
    activity_type: str, 
    description: str, 
    metadata: Optional[Dict] = None
):
    """Log user activity for audit trail"""
    try:
        activity_record = {
            'user_id': user_id,
            'activity_type': activity_type,
            'description': description,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': 'N/A',  # Would get from request context
            'user_agent': 'N/A'   # Would get from request context
        }
        
        await supabase.table('user_activities').insert(activity_record).execute()
        
    except Exception as e:
        logger.error(f"Error logging user activity: {e}")

# Password policy validation
def validate_password_policy(password: str) -> Dict[str, Any]:
    """Validate password against security policy"""
    policy = {
        'min_length': 8,
        'require_uppercase': True,
        'require_lowercase': True,
        'require_numbers': True,
        'require_special': True
    }
    
    results = {
        'valid': True,
        'errors': []
    }
    
    if len(password) < policy['min_length']:
        results['valid'] = False
        results['errors'].append(f"Password must be at least {policy['min_length']} characters")
    
    if policy['require_uppercase'] and not any(c.isupper() for c in password):
        results['valid'] = False
        results['errors'].append("Password must contain at least one uppercase letter")
    
    if policy['require_lowercase'] and not any(c.islower() for c in password):
        results['valid'] = False
        results['errors'].append("Password must contain at least one lowercase letter")
    
    if policy['require_numbers'] and not any(c.isdigit() for c in password):
        results['valid'] = False
        results['errors'].append("Password must contain at least one number")
    
    if policy['require_special'] and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        results['valid'] = False
        results['errors'].append("Password must contain at least one special character")
    
    return results
