"""
Ocean Sentinel - User Models
Pydantic models for user management and authentication
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator, EmailStr

class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    role: Optional[str] = Field(default="user", description="User role")
    agency: Optional[str] = Field(None, max_length=255, description="Associated agency/organization")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User preferences")
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['user', 'analyst', 'emergency_manager', 'admin']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v

class UserCreate(UserBase):
    """Model for creating new users"""
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    min_alert_severity: Optional[int] = Field(default=3, ge=1, le=5, description="Minimum alert severity")
    email_notifications: bool = Field(default=True, description="Enable email notifications")
    sms_notifications: bool = Field(default=False, description="Enable SMS notifications")
    push_notifications: bool = Field(default=True, description="Enable push notifications")

class UserLogin(BaseModel):
    """Model for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class UserUpdate(BaseModel):
    """Model for updating user information"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    agency: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    preferences: Optional[Dict[str, Any]] = None
    min_alert_severity: Optional[int] = Field(None, ge=1, le=5)
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None

class UserModel(UserBase):
    """Complete user model with database fields"""
    id: UUID = Field(..., description="Unique user identifier")
    hashed_password: Optional[str] = Field(None, description="Hashed password (excluded from responses)")
    min_alert_severity: int = Field(default=3, description="Minimum alert severity")
    email_notifications: bool = Field(default=True, description="Email notifications enabled")
    sms_notifications: bool = Field(default=False, description="SMS notifications enabled")
    push_notifications: bool = Field(default=True, description="Push notifications enabled")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    is_active: bool = Field(default=True, description="Account active status")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        
        # Exclude sensitive fields from API responses
        fields = {
            'hashed_password': {'write_only': True}
        }

class UserSummary(BaseModel):
    """Simplified user summary for lists"""
    id: UUID
    email: EmailStr
    name: str
    role: str
    agency: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    """Authentication token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserModel = Field(..., description="Authenticated user information")

class UserResponse(BaseModel):
    """Response model for user operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    user: Optional[UserModel] = Field(None, description="User data")

class UserStatistics(BaseModel):
    """User system statistics"""
    total_users: int = Field(..., description="Total registered users")
    active_users: int = Field(..., description="Active users")
    users_by_role: Dict[str, int] = Field(..., description="Users grouped by role")
    users_by_agency: Dict[str, int] = Field(..., description="Users grouped by agency")
    recent_logins: int = Field(..., description="Users logged in recently")
    notification_preferences: Dict[str, int] = Field(..., description="Notification preference stats")

class UserActivity(BaseModel):
    """User activity tracking"""
    user_id: UUID = Field(..., description="User identifier")
    activity_type: str = Field(..., description="Type of activity")
    description: str = Field(..., description="Activity description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional activity data")
    timestamp: datetime = Field(..., description="Activity timestamp")
    
    @validator('activity_type')
    def validate_activity_type(cls, v):
        allowed_types = [
            'login', 'logout', 'threat_created', 'threat_updated', 'alert_sent',
            'profile_updated', 'password_changed', 'role_changed'
        ]
        if v not in allowed_types:
            raise ValueError(f'Activity type must be one of: {", ".join(allowed_types)}')
        return v

class UserPreferences(BaseModel):
    """Detailed user preferences model"""
    alert_frequency: str = Field(default="immediate", description="Alert frequency setting")
    dashboard_layout: Dict[str, Any] = Field(default_factory=dict, description="Dashboard layout preferences")
    map_defaults: Dict[str, Any] = Field(default_factory=dict, description="Default map settings")
    notification_channels: Dict[str, bool] = Field(default_factory=dict, description="Enabled notification channels")
    threat_type_filters: Dict[str, bool] = Field(default_factory=dict, description="Threat type display filters")
    geographic_focus: Optional[Dict[str, float]] = Field(None, description="Geographic area of focus")
    
    @validator('alert_frequency')
    def validate_alert_frequency(cls, v):
        allowed_frequencies = ['immediate', 'hourly', 'daily', 'critical_only']
        if v not in allowed_frequencies:
            raise ValueError(f'Alert frequency must be one of: {", ".join(allowed_frequencies)}')
        return v

class UserFilter(BaseModel):
    """Filtering options for user queries"""
    role: Optional[str] = Field(None, description="Filter by user role")
    agency: Optional[str] = Field(None, description="Filter by agency")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    last_login_after: Optional[datetime] = Field(None, description="Filter by last login")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
