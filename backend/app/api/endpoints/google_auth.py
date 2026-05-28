"""
Google OAuth Authentication Endpoints
Handles Google OAuth 2.0 authentication flow
Authored by Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import logging
import secrets

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    GoogleOAuthResponse,
    GoogleAuthCompleteResponse,
    GoogleUserInfo,
    UserResponse
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash
)
from app.api.deps import get_current_active_user
from app.config import settings
from app.services.google_oauth_service import google_oauth_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/login", response_model=GoogleOAuthResponse)
async def google_login():
    """
    Initiate Google OAuth flow
    Returns authorization URL for user to authenticate with Google
    """
    try:
        auth_data = google_oauth_service.get_authorization_url()
        return GoogleOAuthResponse(
            authorization_url=auth_data["url"],
            state=auth_data["state"]
        )
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google authentication"
        )


@router.get("/callback")
async def google_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback
    Exchange code for tokens and create/update user
    Redirects to frontend with JWT token
    """
    try:
        # Verify state parameter to prevent CSRF
        if not google_oauth_service.verify_state(state):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter"
            )
        
        # Exchange code for tokens
        token_data = await google_oauth_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token"
            )
        
        # Get user info from Google
        user_info = await google_oauth_service.get_user_info(access_token)
        google_id = user_info.get("sub")
        email = user_info.get("email")
        
        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain user information"
            )
        
        # Check if user exists by google_id
        user = db.query(User).filter(User.google_id == google_id).first()
        
        if not user:
            # Check if user exists by email
            user = db.query(User).filter(User.email == email).first()
            
            if user:
                # Link existing account with Google
                user.google_id = google_id
                user.google_email = email
                user.google_picture = user_info.get("picture")
                user.oauth_provider = "google"
                user.oauth_access_token = access_token
                user.oauth_refresh_token = refresh_token
                user.oauth_token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
            else:
                # Create new user
                username = email.split("@")[0]
                # Ensure username is unique
                base_username = username
                counter = 1
                while db.query(User).filter(User.username == username).first():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User(
                    email=email,
                    username=username,
                    hashed_password=get_password_hash(secrets.token_urlsafe(32)),  # Random password
                    full_name=user_info.get("name"),
                    role=UserRole.VIEWER,
                    is_active=True,
                    is_verified=user_info.get("email_verified", False),
                    google_id=google_id,
                    google_email=email,
                    google_picture=user_info.get("picture"),
                    oauth_provider="google",
                    oauth_access_token=access_token,
                    oauth_refresh_token=refresh_token,
                    oauth_token_expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
                )
                db.add(user)
        else:
            # Update existing Google user
            user.oauth_access_token = access_token
            if refresh_token:
                user.oauth_refresh_token = refresh_token
            user.oauth_token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
            user.google_picture = user_info.get("picture")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        # Generate PetroFlow JWT tokens
        petroflow_access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        petroflow_refresh_token = create_refresh_token(
            data={"sub": user.username},
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        # Redirect to frontend with tokens
        # In production, use proper frontend URL from settings
        frontend_url = getattr(settings, 'FRONTEND_URL', "http://localhost:3000")
        redirect_url = f"{frontend_url}/auth/callback?access_token={petroflow_access_token}&refresh_token={petroflow_refresh_token}"
        
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/token", response_model=GoogleAuthCompleteResponse)
async def google_token_exchange(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    Exchange Google authorization code for PetroFlow JWT tokens
    Alternative to callback endpoint for API-based flows
    """
    try:
        # Verify state parameter
        if not google_oauth_service.verify_state(state):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter"
            )
        
        # Exchange code for tokens
        token_data = await google_oauth_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token"
            )
        
        # Get user info from Google
        user_info = await google_oauth_service.get_user_info(access_token)
        google_id = user_info.get("sub")
        email = user_info.get("email")
        
        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain user information"
            )
        
        # Check if user exists by google_id
        user = db.query(User).filter(User.google_id == google_id).first()
        
        if not user:
            # Check if user exists by email
            user = db.query(User).filter(User.email == email).first()
            
            if user:
                # Link existing account with Google
                user.google_id = google_id
                user.google_email = email
                user.google_picture = user_info.get("picture")
                user.oauth_provider = "google"
                user.oauth_access_token = access_token
                user.oauth_refresh_token = refresh_token
                user.oauth_token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
            else:
                # Create new user
                username = email.split("@")[0]
                # Ensure username is unique
                base_username = username
                counter = 1
                while db.query(User).filter(User.username == username).first():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User(
                    email=email,
                    username=username,
                    hashed_password=get_password_hash(secrets.token_urlsafe(32)),
                    full_name=user_info.get("name"),
                    role=UserRole.VIEWER,
                    is_active=True,
                    is_verified=user_info.get("email_verified", False),
                    google_id=google_id,
                    google_email=email,
                    google_picture=user_info.get("picture"),
                    oauth_provider="google",
                    oauth_access_token=access_token,
                    oauth_refresh_token=refresh_token,
                    oauth_token_expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
                )
                db.add(user)
        else:
            # Update existing Google user
            user.oauth_access_token = access_token
            if refresh_token:
                user.oauth_refresh_token = refresh_token
            user.oauth_token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
            user.google_picture = user_info.get("picture")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        # Generate PetroFlow JWT tokens
        petroflow_access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        petroflow_refresh_token = create_refresh_token(
            data={"sub": user.username},
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        return GoogleAuthCompleteResponse(
            access_token=petroflow_access_token,
            refresh_token=petroflow_refresh_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                is_active=user.is_active,
                role=user.role.value,
                is_admin=user.role == UserRole.ADMIN,
                created_at=user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exchanging Google token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token exchange failed"
        )


@router.get("/user", response_model=GoogleUserInfo)
async def get_google_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get Google user information for current authenticated user
    """
    if not current_user.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not authenticated with Google"
        )
    
    try:
        # Check if token is expired
        if current_user.oauth_token_expires_at and current_user.oauth_token_expires_at < datetime.utcnow():
            # Token expired, need to refresh
            if not current_user.oauth_refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google token expired and no refresh token available"
                )
            
            # Refresh token logic would go here
            # For now, return cached info
        
        return GoogleUserInfo(
            sub=current_user.google_id,
            email=current_user.google_email or current_user.email,
            email_verified=current_user.is_verified,
            name=current_user.full_name,
            picture=current_user.google_picture
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Google user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


@router.post("/logout")
async def google_logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout user and revoke Google OAuth tokens
    """
    try:
        # Revoke Google tokens if available
        if current_user.oauth_access_token:
            await google_oauth_service.revoke_token(current_user.oauth_access_token)
        
        if current_user.oauth_refresh_token:
            await google_oauth_service.revoke_token(current_user.oauth_refresh_token)
        
        # Clear OAuth tokens from database
        current_user.oauth_access_token = None
        current_user.oauth_refresh_token = None
        current_user.oauth_token_expires_at = None
        db.commit()
        
        return {"message": "Successfully logged out from Google"}
    except Exception as e:
        logger.error(f"Error during Google logout: {e}")
        # Don't fail the logout even if revocation fails
        return {"message": "Logged out (token revocation may have failed)"}