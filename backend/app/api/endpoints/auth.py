"""
Authentication API Endpoints
Handles user authentication, registration, MFA/TOTP lifecycle, and Google OAuth
Authored by Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import logging
import pyotp
import qrcode
import io
import base64
import json
import secrets

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    UserCreate,
    Token,
    UserResponse,
    PasswordReset,
    LoginMFARequest,
    MFAVerifyRequest,
    MFASetupResponse,
    MFAEnableResponse,
    GoogleOAuthResponse,
    GoogleAuthCallbackRequest,
    GoogleAuthCompleteResponse,
    GoogleUserInfo
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    decode_token
)
from app.api.deps import get_current_active_user
from app.config import settings
from app.services.google_oauth_service import google_oauth_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user in the database
    Authored by Jhon Villegas
    """
    try:
        # Check if email already exists
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
            
        # Check if username already exists
        existing_username = db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
            
        # Hash password and create User record
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=UserRole.VIEWER,  # Default role for self-registration
            is_active=True,
            is_verified=False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "is_active": new_user.is_active,
            "role": new_user.role.value,
            "is_admin": new_user.role == UserRole.ADMIN,
            "created_at": new_user.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login user. If MFA is enabled, return a temporary token.
    Authored by Jhon Villegas
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        # Get user from database (supports username or email login)
        user = db.query(User).filter(
            (User.username == form_data.username) | (User.email == form_data.username)
        ).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise credentials_exception
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is deactivated"
            )
            
        # Check if MFA is enabled for user
        if user.mfa_enabled:
            # Generate a temporary short-lived token (valid for 5 minutes)
            temp_token = create_access_token(
                data={"sub": user.username, "type": "temp"},
                expires_delta=timedelta(minutes=5)
            )
            return Token(
                mfa_required=True,
                temp_token=temp_token
            )
            
        # Update last login time
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Generate standard access and refresh tokens
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = create_refresh_token(
            data={"sub": user.username},
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            mfa_required=False
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise credentials_exception


@router.post("/login/mfa", response_model=Token)
async def login_mfa(
    mfa_data: LoginMFARequest,
    db: Session = Depends(get_db)
):
    """
    Verify MFA code or backup code using a temporary token
    Authored by Jhon Villegas
    """
    try:
        # Decode and verify the temporary token
        payload = decode_token(mfa_data.temp_token)
        username = payload.get("sub")
        token_type = payload.get("type")
        
        if not username or token_type != "temp":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid temporary authentication token"
            )
            
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active or not user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user or MFA not enabled"
            )
            
        mfa_verified = False
        
        # 1. Try to verify using TOTP authenticator
        if user.mfa_secret:
            totp = pyotp.TOTP(user.mfa_secret)
            if totp.verify(mfa_data.mfa_code, valid_window=1):
                mfa_verified = True
                
        # 2. If not verified, check backup codes
        if not mfa_verified and user.mfa_backup_codes:
            backup_codes = json.loads(user.mfa_backup_codes)
            if mfa_data.mfa_code in backup_codes:
                backup_codes.remove(mfa_data.mfa_code)
                user.mfa_backup_codes = json.dumps(backup_codes)
                mfa_verified = True
                logger.info(f"User {username} successfully logged in using backup code")
                
        if not mfa_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid multi-factor authentication code"
            )
            
        # Update last login time
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Generate final tokens
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = create_refresh_token(
            data={"sub": user.username},
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            mfa_required=False
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during MFA login: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify MFA code"
        )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate secret and QR code for setting up MFA
    Authored by Jhon Villegas
    """
    try:
        # Generate new random Base32 secret
        mfa_secret = pyotp.random_base32()
        
        # Provisioning URI
        totp = pyotp.TOTP(mfa_secret)
        provisioning_uri = totp.provisioning_uri(
            current_user.email,
            issuer_name="PetroFlow"
        )
        
        # Generate Base64 QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # Store temporary secret in user profile until enabled
        current_user.mfa_secret = mfa_secret
        db.commit()
        
        return MFASetupResponse(
            mfa_secret=mfa_secret,
            provisioning_uri=provisioning_uri,
            qr_code_base64=qr_code_base64
        )
    except Exception as e:
        logger.error(f"Error generating MFA setup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate MFA setup"
        )


@router.post("/mfa/enable", response_model=MFAEnableResponse)
async def mfa_enable(
    verify_data: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verify initial TOTP code to fully enable MFA and return 10 backup codes
    Authored by Jhon Villegas
    """
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup has not been initiated"
        )
        
    try:
        totp = pyotp.TOTP(current_user.mfa_secret)
        if not totp.verify(verify_data.code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code is incorrect"
            )
            
        # Generate 10 secure backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(10)]
        
        current_user.mfa_enabled = True
        current_user.mfa_backup_codes = json.dumps(backup_codes)
        db.commit()
        
        return MFAEnableResponse(
            mfa_enabled=True,
            backup_codes=backup_codes
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling MFA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable MFA"
        )


@router.post("/mfa/disable")
async def mfa_disable(
    verify_data: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Disable MFA by providing a valid TOTP code
    Authored by Jhon Villegas
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already disabled"
        )
        
    try:
        totp = pyotp.TOTP(current_user.mfa_secret)
        if not totp.verify(verify_data.code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code is incorrect"
            )
            
        current_user.mfa_enabled = False
        current_user.mfa_secret = None
        current_user.mfa_backup_codes = None
        db.commit()
        
        return {"message": "Multi-factor authentication disabled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling MFA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable MFA"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token
    Authored by Jhon Villegas
    """
    try:
        payload = decode_token(refresh_token)
        username = payload.get("sub")
        token_type = payload.get("type")
        
        if not username or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
            
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or not found"
            )
            
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            mfa_required=False
        )
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout current user
    Authored by Jhon Villegas
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current active user profile information
    Authored by Jhon Villegas
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "role": current_user.role.value,
        "is_admin": current_user.role == UserRole.ADMIN,
        "created_at": current_user.created_at
    }