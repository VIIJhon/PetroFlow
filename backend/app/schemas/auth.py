"""
Authentication Schemas
Pydantic models for authentication-related requests/responses
Authored by Jhon Villegas
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    full_name: Optional[str] = None
    is_active: bool
    role: str
    is_admin: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for token response"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    mfa_required: bool = False
    temp_token: Optional[str] = None


class TokenData(BaseModel):
    """Schema for token data"""
    username: Optional[str] = None


class PasswordReset(BaseModel):
    """Schema for password reset"""
    token: str
    new_password: str = Field(..., min_length=8)


class LoginMFARequest(BaseModel):
    """Schema for MFA verification during login"""
    temp_token: str
    mfa_code: str


class MFAVerifyRequest(BaseModel):
    """Schema for MFA verification / activation"""
    code: str


class MFASetupResponse(BaseModel):
    """Schema for MFA setup details"""
    mfa_secret: str
    provisioning_uri: str
    qr_code_base64: str


class MFAEnableResponse(BaseModel):
    """Schema for MFA enable results"""
    mfa_enabled: bool
    backup_codes: List[str]


class GoogleOAuthRequest(BaseModel):
    """Schema for Google OAuth authorization request"""
    redirect_uri: Optional[str] = None


class GoogleOAuthResponse(BaseModel):
    """Schema for Google OAuth authorization response"""
    authorization_url: str
    state: str


class GoogleUserInfo(BaseModel):
    """Schema for Google user information"""
    sub: str  # Google user ID
    email: EmailStr
    email_verified: bool
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None


class GoogleTokenRequest(BaseModel):
    """Schema for Google token exchange request"""
    code: str
    state: str


class GoogleTokenResponse(BaseModel):
    """Schema for Google OAuth token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    scope: str
    id_token: Optional[str] = None


class GoogleAuthCallbackRequest(BaseModel):
    """Schema for Google OAuth callback"""
    code: str
    state: str


class GoogleAuthCompleteResponse(BaseModel):
    """Schema for complete Google authentication response"""
    access_token: str  # PetroFlow JWT token
    refresh_token: str  # PetroFlow refresh token
    token_type: str = "bearer"
    user: UserResponse