"""
User Schemas
Pydantic models for user management requests/responses
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    ENGINEER = "engineer"
    OPERATOR = "operator"
    VIEWER = "viewer"
    MAINTENANCE = "maintenance"


class UserStatus(str, Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    role: UserRole = Field(UserRole.VIEWER, description="User role")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v.lower()


class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    role: UserRole
    is_active: bool
    is_admin: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for user list response"""
    users: List[UserResponse]
    total: int


class UserProfileUpdate(BaseModel):
    """Schema for user profile update"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    preferences: Optional[dict] = None


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_new_password(cls, v, values):
        """Validate new password"""
        if 'current_password' in values and v == values['current_password']:
            raise ValueError("New password must be different from current password")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserPermissions(BaseModel):
    """Schema for user permissions"""
    can_create_equipment: bool = False
    can_edit_equipment: bool = False
    can_delete_equipment: bool = False
    can_run_simulations: bool = False
    can_run_analysis: bool = False
    can_view_reports: bool = False
    can_export_data: bool = False
    can_manage_users: bool = False
    can_configure_system: bool = False


class UserWithPermissions(UserResponse):
    """Schema for user with permissions"""
    permissions: UserPermissions


class UserActivity(BaseModel):
    """Schema for user activity log"""
    id: int
    user_id: int
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True


class UserActivityListResponse(BaseModel):
    """Schema for user activity list"""
    activities: List[UserActivity]
    total: int


class UserStatistics(BaseModel):
    """Schema for user statistics"""
    user_id: int
    username: str
    total_logins: int
    last_login: Optional[datetime] = None
    equipment_created: int
    simulations_run: int
    analyses_run: int
    reports_generated: int
    active_sessions: int


class UserSession(BaseModel):
    """Schema for user session"""
    id: str
    user_id: int
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True


class UserSessionListResponse(BaseModel):
    """Schema for user session list"""
    sessions: List[UserSession]
    total: int


class UserPreferences(BaseModel):
    """Schema for user preferences"""
    theme: str = Field("light", description="UI theme (light, dark)")
    language: str = Field("en", description="Preferred language")
    timezone: str = Field("UTC", description="User timezone")
    notifications_enabled: bool = Field(True, description="Enable notifications")
    email_notifications: bool = Field(True, description="Enable email notifications")
    dashboard_layout: Optional[dict] = Field(None, description="Custom dashboard layout")
    default_unit_system: str = Field("metric", description="Preferred unit system")


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences"""
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    dashboard_layout: Optional[dict] = None
    default_unit_system: Optional[str] = None


class UserInvite(BaseModel):
    """Schema for inviting a new user"""
    email: EmailStr
    role: UserRole = UserRole.VIEWER
    message: Optional[str] = None


class UserInviteResponse(BaseModel):
    """Schema for user invite response"""
    invite_id: str
    email: EmailStr
    role: UserRole
    invited_by: int
    created_at: datetime
    expires_at: datetime
    status: str


class UserBulkCreate(BaseModel):
    """Schema for bulk user creation"""
    users: List[UserCreate] = Field(..., min_items=1, max_items=100)


class UserBulkCreateResponse(BaseModel):
    """Schema for bulk user creation response"""
    total_submitted: int
    successful: int
    failed: int
    created_users: List[UserResponse]
    errors: List[dict] = Field(default_factory=list)


class UserSearch(BaseModel):
    """Schema for user search"""
    query: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class UserExport(BaseModel):
    """Schema for exporting user data"""
    user_ids: Optional[List[int]] = None
    include_activity: bool = Field(False, description="Include activity logs")
    include_permissions: bool = Field(True, description="Include permissions")
    format: str = Field("csv", description="Export format (csv, json)")


class UserExportResponse(BaseModel):
    """Schema for user export response"""
    export_id: str
    status: str
    file_url: Optional[str] = None
    record_count: int
    created_at: datetime