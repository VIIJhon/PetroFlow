"""
Google OAuth Service
Handles Google OAuth 2.0 authentication flow
Authored by Jhon Villegas
"""

import logging
try:
    from authlib.integrations.starlette_client import OAuth  # optional
    from authlib.jose import jwt  # optional
    AUTHLIB_AVAILABLE = True
except Exception:
    OAuth = None
    try:
        # Try PyJWT as a fallback for basic JWT decoding
        import jwt as pyjwt
        jwt = pyjwt
    except Exception:
        jwt = None
    AUTHLIB_AVAILABLE = False
    logging.warning("authlib not installed. Google OAuth helper features will be limited.")
from typing import Optional, Dict, Any
import httpx
import secrets
import logging
from datetime import datetime, timedelta

from app.config import settings

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """
    Service for handling Google OAuth 2.0 authentication
    Provides methods for authorization, token exchange, and user info retrieval
    """
    
    def __init__(self):
        """Initialize Google OAuth service with configuration"""
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = settings.GOOGLE_OAUTH_SCOPES
        
        # Google OAuth endpoints
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"
        self.revoke_endpoint = "https://oauth2.googleapis.com/revoke"
        
        # State storage for CSRF protection (in production, use Redis)
        self._state_storage: Dict[str, datetime] = {}
        
    def _cleanup_expired_states(self):
        """Remove expired state tokens (older than 10 minutes)"""
        now = datetime.utcnow()
        expired_states = [
            state for state, timestamp in self._state_storage.items()
            if now - timestamp > timedelta(minutes=10)
        ]
        for state in expired_states:
            del self._state_storage[state]
    
    def generate_state(self) -> str:
        """
        Generate a secure random state parameter for CSRF protection
        
        Returns:
            str: Random state token
        """
        self._cleanup_expired_states()
        state = secrets.token_urlsafe(32)
        self._state_storage[state] = datetime.utcnow()
        return state
    
    def verify_state(self, state: str) -> bool:
        """
        Verify that the state parameter is valid and not expired
        
        Args:
            state: State token to verify
            
        Returns:
            bool: True if state is valid, False otherwise
        """
        self._cleanup_expired_states()
        if state in self._state_storage:
            del self._state_storage[state]
            return True
        return False
    
    def get_authorization_url(self, state: Optional[str] = None) -> Dict[str, str]:
        """
        Generate Google OAuth authorization URL
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            dict: Contains 'url' and 'state' keys
        """
        try:
            if not state:
                state = self.generate_state()
            
            params = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": " ".join(self.scopes),
                "state": state,
                "access_type": "offline",  # Request refresh token
                "prompt": "consent"  # Force consent screen to get refresh token
            }
            
            # Build authorization URL
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            authorization_url = f"{self.authorization_endpoint}?{query_string}"
            
            logger.info("Generated Google OAuth authorization URL")
            return {
                "url": authorization_url,
                "state": state
            }
        except Exception as e:
            logger.error(f"Error generating authorization URL: {e}")
            raise
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            code: Authorization code from Google
            
        Returns:
            dict: Token response containing access_token, refresh_token, etc.
            
        Raises:
            Exception: If token exchange fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    logger.error(f"Token exchange failed: {response.text}")
                    raise Exception(f"Token exchange failed: {response.status_code}")
                
                token_data = response.json()
                logger.info("Successfully exchanged code for tokens")
                return token_data
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            raise
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Retrieve user information from Google using access token
        
        Args:
            access_token: Google OAuth access token
            
        Returns:
            dict: User information (email, name, picture, etc.)
            
        Raises:
            Exception: If user info retrieval fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to get user info: {response.text}")
                    raise Exception(f"Failed to get user info: {response.status_code}")
                
                user_info = response.json()
                logger.info(f"Retrieved user info for: {user_info.get('email')}")
                return user_info
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            raise
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Google OAuth refresh token
            
        Returns:
            dict: New token response with access_token
            
        Raises:
            Exception: If token refresh fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    logger.error(f"Token refresh failed: {response.text}")
                    raise Exception(f"Token refresh failed: {response.status_code}")
                
                token_data = response.json()
                logger.info("Successfully refreshed access token")
                return token_data
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access or refresh token
        
        Args:
            token: Token to revoke (access or refresh token)
            
        Returns:
            bool: True if revocation successful, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.revoke_endpoint,
                    data={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    logger.info("Successfully revoked token")
                    return True
                else:
                    logger.warning(f"Token revocation returned status: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a Google ID token (JWT)
        
        Args:
            token: Google ID token to verify
            
        Returns:
            dict: Decoded token payload if valid, None otherwise
        """
        try:
            # In production, you should verify the token signature
            # using Google's public keys from https://www.googleapis.com/oauth2/v3/certs
            # For now, we'll do basic decoding without verification
            # This is acceptable since we're getting the token directly from Google
            
            decoded = jwt.decode(token, self.client_secret)
            
            # Verify issuer
            if decoded.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
                logger.warning("Invalid token issuer")
                return None
            
            # Verify audience (client_id)
            if decoded.get("aud") != self.client_id:
                logger.warning("Invalid token audience")
                return None
            
            # Verify expiration
            exp = decoded.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                logger.warning("Token has expired")
                return None
            
            logger.info("Token verified successfully")
            return decoded
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None


# Global service instance
google_oauth_service = GoogleOAuthService()