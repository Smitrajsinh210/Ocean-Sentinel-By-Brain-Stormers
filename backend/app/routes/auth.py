"""
Ocean Sentinel - Authentication API Routes
FastAPI endpoints for user authentication and authorization
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.models.users import UserModel, UserCreate, UserLogin, UserResponse, Token
from app.config import settings
from app.utils.database import create_supabase_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = create_supabase_client()

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    result = await supabase.table('users')\
        .select('*')\
        .eq('id', user_id)\
        .eq('is_active', True)\
        .execute()
    
    if not result.data:
        raise credentials_exception
    
    return UserModel(**result.data[0])

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    """Register a new user"""
    try:
        logger.info(f"Registering new user: {user.email}")
        
        # Check if user already exists
        existing = await supabase.table('users')\
            .select('id')\
            .eq('email', user.email)\
            .execute()
        
        if existing.data:
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )
        
        # Hash password
        hashed_password = get_password_hash(user.password)
        
        # Create user record
        user_data = user.dict(exclude={'password'})
        user_data['id'] = str(uuid4())
        user_data['hashed_password'] = hashed_password
        user_data['created_at'] = datetime.utcnow().isoformat()
        user_data['is_active'] = True
        
        # Set default role if not specified
        if not user_data.get('role'):
            user_data['role'] = 'user'
        
        # Insert user
        result = await supabase.table('users').insert(user_data).execute()
        
        if result.data:
            created_user = UserModel(**result.data[0])
            logger.info(f"✅ User registered successfully: {user.email}")
            
            return UserResponse(
                success=True,
                message="User registered successfully",
                user=created_user
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to create user")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    """Authenticate user and return access token"""
    try:
        logger.info(f"Login attempt for user: {user_credentials.email}")
        
        # Get user from database
        result = await supabase.table('users')\
            .select('*')\
            .eq('email', user_credentials.email)\
            .eq('is_active', True)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        user_data = result.data[0]
        
        # Verify password
        if not verify_password(user_credentials.password, user_data['hashed_password']):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user_data['id'], "email": user_data['email'], "role": user_data['role']},
            expires_delta=access_token_expires
        )
        
        # Update last login
        await supabase.table('users')\
            .update({'last_login': datetime.utcnow().isoformat()})\
            .eq('id', user_data['id'])\
            .execute()
        
        logger.info(f"✅ User logged in successfully: {user_credentials.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserModel(**user_data)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.get("/me", response_model=UserModel)
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: dict,
    current_user: UserModel = Depends(get_current_user)
):
    """Update current user profile"""
    try:
        logger.info(f"Updating user profile: {current_user.email}")
        
        # Remove sensitive fields that shouldn't be updated via this endpoint
        restricted_fields = {'id', 'email', 'hashed_password', 'role', 'created_at', 'is_active'}
        update_data = {k: v for k, v in user_update.items() if k not in restricted_fields}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Update user
        result = await supabase.table('users')\
            .update(update_data)\
            .eq('id', str(current_user.id))\
            .execute()
        
        if result.data:
            updated_user = UserModel(**result.data[0])
            logger.info(f"✅ User profile updated: {current_user.email}")
            
            return UserResponse(
                success=True,
                message="Profile updated successfully",
                user=updated_user
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to update profile")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(status_code=500, detail="Profile update failed")

@router.post("/change-password", response_model=UserResponse)
async def change_password(
    password_data: dict,
    current_user: UserModel = Depends(get_current_user)
):
    """Change user password"""
    try:
        current_password = password_data.get('current_password')
        new_password = password_data.get('new_password')
        
        if not current_password or not new_password:
            raise HTTPException(
                status_code=400,
                detail="Both current_password and new_password are required"
            )
        
        if len(new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="New password must be at least 8 characters long"
            )
        
        logger.info(f"Password change request for user: {current_user.email}")
        
        # Get current hashed password
        result = await supabase.table('users')\
            .select('hashed_password')\
            .eq('id', str(current_user.id))\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_hashed = result.data[0]['hashed_password']
        
        # Verify current password
        if not verify_password(current_password, current_hashed):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        
        # Hash new password
        new_hashed = get_password_hash(new_password)
        
        # Update password
        update_result = await supabase.table('users')\
            .update({
                'hashed_password': new_hashed,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', str(current_user.id))\
            .execute()
        
        if update_result.data:
            logger.info(f"✅ Password changed successfully: {current_user.email}")
            
            return UserResponse(
                success=True,
                message="Password changed successfully",
                user=current_user
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to change password")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(status_code=500, detail="Password change failed")

@router.post("/logout", response_model=dict)
async def logout_user(current_user: UserModel = Depends(get_current_user)):
    """Logout user (invalidate token - client-side handling required)"""
    try:
        logger.info(f"User logout: {current_user.email}")
        
        # In a production system, you might want to maintain a token blacklist
        # For now, we'll just log the logout and let the client handle token removal
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.get("/users", response_model=list[UserModel])
async def list_users(
    current_user: UserModel = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """List all users (admin only)"""
    try:
        # Check admin permissions
        if current_user.role not in ['admin']:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        logger.info(f"Admin user list request from: {current_user.email}")
        
        result = await supabase.table('users')\
            .select('*')\
            .eq('is_active', True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        if result.data:
            return [UserModel(**user) for user in result.data]
        
        return []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")

@router.put("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    role_data: dict,
    current_user: UserModel = Depends(get_current_user)
):
    """Update user role (admin only)"""
    try:
        # Check admin permissions
        if current_user.role not in ['admin']:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        new_role = role_data.get('role')
        if not new_role:
            raise HTTPException(status_code=400, detail="Role is required")
        
        valid_roles = ['user', 'analyst', 'emergency_manager', 'admin']
        if new_role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )
        
        logger.info(f"Admin role update: {user_id} -> {new_role} by {current_user.email}")
        
        # Update user role
        result = await supabase.table('users')\
            .update({
                'role': new_role,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', str(user_id))\
            .execute()
        
        if result.data:
            updated_user = UserModel(**result.data[0])
            logger.info(f"✅ User role updated: {user_id}")
            
            return UserResponse(
                success=True,
                message=f"User role updated to {new_role}",
                user=updated_user
            )
        else:
            raise HTTPException(status_code=404, detail="User not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user role")
