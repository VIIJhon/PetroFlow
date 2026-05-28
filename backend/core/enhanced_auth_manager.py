"""
Enhanced Authentication Manager
================================

Comprehensive authentication system with advanced security features.

Features:
- User registration and login
- Email/password authentication
- Multi-factor authentication (MFA/TOTP)
- JWT session management
- Password reset and recovery
- Email verification
- Password change with history
- Rate limiting integration
- License validation
- Comprehensive audit logging

Dependencies:
- bcrypt: Password hashing
- jwt: JSON Web Tokens
- secrets: Secure token generation

Author: Bob
Version: 1.0.0
"""

import logging
import secrets
import hashlib
import sqlite3
import jwt
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
from pathlib import Path
import json
import re

try:
    import bcrypt
except ImportError as e:
    raise ImportError(
        "Enhanced auth manager requires bcrypt. "
        "Install with: pip install bcrypt"
    ) from e

from .mfa_service import MFAService, MFANotEnabledError, InvalidTOTPCodeError
from .rate_limiter import RateLimiter, RateLimitExceededError, IPBlockedError
from .license_manager import LicenseManager

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class AuthError(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when credentials are invalid."""
    pass


class UserNotFoundError(AuthError):
    """Raised when user is not found."""
    pass


class UserAlreadyExistsError(AuthError):
    """Raised when user already exists."""
    pass


class EmailNotVerifiedError(AuthError):
    """Raised when email is not verified."""
    pass


class AccountInactiveError(AuthError):
    """Raised when account is inactive."""
    pass


class InvalidTokenError(AuthError):
    """Raised when token is invalid."""
    pass


class PasswordTooWeakError(AuthError):
    """Raised when password doesn't meet requirements."""
    pass


class PasswordReusedError(AuthError):
    """Raised when password was recently used."""
    pass


class MFARequiredError(AuthError):
    """Raised when MFA verification is required."""
    def __init__(self, user_id: int, temp_token: str):
        self.user_id = user_id
        self.temp_token = temp_token
        super().__init__("MFA verification required")


# ============================================================================
# ENHANCED AUTHENTICATION MANAGER
# ============================================================================

class EnhancedAuthManager:
    """
    Enhanced Authentication Manager
    
    Provides comprehensive authentication with:
    - Secure password hashing (bcrypt)
    - JWT session management
    - MFA integration
    - Rate limiting
    - Email verification
    - Password reset
    - License validation
    - Audit logging
    
    Attributes:
        db_path (str): Path to SQLite database
        jwt_secret (str): Secret key for JWT signing
        mfa_service: MFA service instance
        rate_limiter: Rate limiter instance
        license_manager: License manager instance
    """
    
    # Password requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    PASSWORD_HISTORY_COUNT = 5  # Remember last 5 passwords
    
    # JWT settings
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRE = 2592000  # 30 days
    JWT_TEMP_TOKEN_EXPIRE = 300  # 5 minutes (for MFA)
    
    def __init__(
        self,
        db_path: str = "petroflow.db",
        jwt_secret: Optional[str] = None,
        redis_url: Optional[str] = None
    ):
        """
        Initialize Enhanced Auth Manager.
        
        Args:
            db_path: Path to SQLite database
            jwt_secret: Secret key for JWT (generated if not provided)
            redis_url: Redis URL for rate limiting
        """
        self.db_path = Path(db_path)
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        
        # Initialize services
        self.mfa_service = MFAService(db_path=str(self.db_path))
        self.rate_limiter = RateLimiter(
            db_path=str(self.db_path),
            redis_url=redis_url
        )
        self.license_manager = LicenseManager(db_path=str(self.db_path))
        
        logger.info("Enhanced Auth Manager initialized")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except Exception:
            return False
    
    def _validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength.
        
        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        if len(password) < self.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {self.PASSWORD_MIN_LENGTH} characters"
        
        if self.PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if self.PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if self.PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if self.PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is strong"
    
    def _check_password_history(self, user_id: int, password: str) -> bool:
        """
        Check if password was recently used.
        
        Returns:
            True if password is in history (should not be reused)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT password_hash FROM password_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, self.PASSWORD_HISTORY_COUNT))
            
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                if self._verify_password(password, row['password_hash']):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking password history: {e}")
            return False
    
    def _add_to_password_history(self, user_id: int, password_hash: str):
        """Add password to history."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO password_history (user_id, password_hash)
                VALUES (?, ?)
            """, (user_id, password_hash))
            
            # Keep only last N passwords
            cursor.execute("""
                DELETE FROM password_history
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM password_history
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                )
            """, (user_id, user_id, self.PASSWORD_HISTORY_COUNT))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error adding to password history: {e}")
    
    def _generate_token(
        self,
        user_id: int,
        token_type: str = "access",
        additional_claims: Optional[Dict] = None
    ) -> str:
        """
        Generate JWT token.
        
        Args:
            user_id: User ID
            token_type: 'access', 'refresh', or 'temp'
            additional_claims: Additional JWT claims
            
        Returns:
            JWT token string
        """
        if token_type == "access":
            expire = datetime.utcnow() + timedelta(seconds=self.JWT_ACCESS_TOKEN_EXPIRE)
        elif token_type == "refresh":
            expire = datetime.utcnow() + timedelta(seconds=self.JWT_REFRESH_TOKEN_EXPIRE)
        else:  # temp
            expire = datetime.utcnow() + timedelta(seconds=self.JWT_TEMP_TOKEN_EXPIRE)
        
        payload = {
            "user_id": user_id,
            "type": token_type,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.JWT_ALGORITHM)
    
    def _verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify JWT token.
        
        Args:
            token: JWT token
            token_type: Expected token type
            
        Returns:
            Decoded token payload
            
        Raises:
            InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.JWT_ALGORITHM]
            )
            
            if payload.get("type") != token_type:
                raise InvalidTokenError("Invalid token type")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError:
            raise InvalidTokenError("Invalid token")
    
    def _log_login_attempt(
        self,
        email: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        failure_reason: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        """Log login attempt to database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO login_attempts 
                (user_id, email, ip_address, user_agent, success, failure_reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, email, ip_address, user_agent, 1 if success else 0, failure_reason))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging login attempt: {e}")
    
    def register(
        self,
        email: str,
        username: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_name: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            email: User email
            username: Username
            password: Password
            first_name: First name
            last_name: Last name
            company_name: Company name
            ip_address: Registration IP address
            
        Returns:
            Dictionary with user info and verification token
            
        Raises:
            UserAlreadyExistsError: If user already exists
            PasswordTooWeakError: If password is too weak
            RateLimitExceededError: If rate limit exceeded
            
        Example:
            >>> auth = EnhancedAuthManager()
            >>> result = auth.register("user@example.com", "username", "SecurePass123!")
            >>> print(result['user_id'])
        """
        try:
            # Check rate limit
            if ip_address:
                self.rate_limiter.check_rate_limit(ip_address, "registration")
            
            # Validate password strength
            is_valid, message = self._validate_password_strength(password)
            if not is_valid:
                raise PasswordTooWeakError(message)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("""
                SELECT id FROM users WHERE email = ? OR username = ?
            """, (email, username))
            
            if cursor.fetchone():
                conn.close()
                raise UserAlreadyExistsError("User with this email or username already exists")
            
            # Hash password
            password_hash = self._hash_password(password)
            
            # Generate verification token
            verification_token = secrets.token_urlsafe(32)
            
            # Insert user
            cursor.execute("""
                INSERT INTO users 
                (email, username, password_hash, first_name, last_name, 
                 company_name, is_active, is_verified)
                VALUES (?, ?, ?, ?, ?, ?, 1, 0)
            """, (email, username, password_hash, first_name, last_name, company_name))
            
            user_id = cursor.lastrowid
            
            # Add to password history
            self._add_to_password_history(user_id, password_hash)
            
            conn.commit()
            conn.close()
            
            logger.info(f"User registered: {email} (ID: {user_id})")
            
            return {
                "user_id": user_id,
                "email": email,
                "username": username,
                "verification_token": verification_token,
                "message": "Registration successful. Please verify your email."
            }
            
        except (UserAlreadyExistsError, PasswordTooWeakError, RateLimitExceededError):
            raise
        except Exception as e:
            logger.error(f"Error during registration: {e}")
            raise AuthError(f"Registration failed: {e}")
    
    def login(
        self,
        email: str,
        password: str,
        ip_address: str,
        user_agent: str = "",
        mfa_code: Optional[str] = None,
        temp_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and create session.
        
        Args:
            email: User email
            password: Password
            ip_address: Client IP address
            user_agent: Client user agent
            mfa_code: MFA code (if MFA enabled)
            temp_token: Temporary token from first login step
            
        Returns:
            Dictionary with tokens and user info
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            MFARequiredError: If MFA verification is required
            EmailNotVerifiedError: If email is not verified
            AccountInactiveError: If account is inactive
            RateLimitExceededError: If rate limit exceeded
            
        Example:
            >>> auth = EnhancedAuthManager()
            >>> result = auth.login("user@example.com", "password", "192.168.1.1")
            >>> print(result['access_token'])
        """
        try:
            # Check rate limit
            self.rate_limiter.check_rate_limit(ip_address, "login")
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get user
            cursor.execute("""
                SELECT id, email, username, password_hash, is_active, 
                       is_verified, mfa_enabled, first_name, last_name
                FROM users
                WHERE email = ?
            """, (email,))
            
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                self._log_login_attempt(
                    email, ip_address, user_agent, False, "User not found"
                )
                self.rate_limiter.record_failed_attempt(ip_address, "login", "User not found")
                raise InvalidCredentialsError("Invalid email or password")
            
            user_id = user['id']
            
            # Verify password (only if not using temp token)
            if not temp_token:
                if not self._verify_password(password, user['password_hash']):
                    conn.close()
                    self._log_login_attempt(
                        email, ip_address, user_agent, False, "Invalid password", user_id
                    )
                    self.rate_limiter.record_failed_attempt(
                        ip_address, "login", "Invalid password"
                    )
                    raise InvalidCredentialsError("Invalid email or password")
            
            # Check if account is active
            if not user['is_active']:
                conn.close()
                self._log_login_attempt(
                    email, ip_address, user_agent, False, "Account inactive", user_id
                )
                raise AccountInactiveError("Account is inactive")
            
            # Check if email is verified
            if not user['is_verified']:
                conn.close()
                self._log_login_attempt(
                    email, ip_address, user_agent, False, "Email not verified", user_id
                )
                raise EmailNotVerifiedError("Please verify your email before logging in")
            
            # Handle MFA
            if user['mfa_enabled']:
                if temp_token:
                    # Verify temp token
                    try:
                        payload = self._verify_token(temp_token, "temp")
                        if payload['user_id'] != user_id:
                            raise InvalidTokenError("Invalid temp token")
                    except InvalidTokenError:
                        conn.close()
                        raise InvalidCredentialsError("Invalid or expired MFA session")
                    
                    # Verify MFA code
                    if not mfa_code:
                        conn.close()
                        raise MFARequiredError(user_id, temp_token)
                    
                    try:
                        self.mfa_service.verify_mfa(user_id, mfa_code)
                    except (InvalidTOTPCodeError, MFANotEnabledError) as e:
                        conn.close()
                        self._log_login_attempt(
                            email, ip_address, user_agent, False, "Invalid MFA code", user_id
                        )
                        self.rate_limiter.record_failed_attempt(
                            ip_address, "login", "Invalid MFA code"
                        )
                        raise InvalidCredentialsError("Invalid MFA code")
                else:
                    # First step - generate temp token
                    temp_token = self._generate_token(user_id, "temp")
                    conn.close()
                    raise MFARequiredError(user_id, temp_token)
            
            # Update last login
            cursor.execute("""
                UPDATE users 
                SET last_login_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
            # Generate tokens
            access_token = self._generate_token(user_id, "access")
            refresh_token = self._generate_token(user_id, "refresh")
            
            # Log successful login
            self._log_login_attempt(
                email, ip_address, user_agent, True, None, user_id
            )
            
            # Reset rate limit
            self.rate_limiter.reset_limit(ip_address, "login")
            
            logger.info(f"User logged in: {email} (ID: {user_id})")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": self.JWT_ACCESS_TOKEN_EXPIRE,
                "user": {
                    "id": user_id,
                    "email": user['email'],
                    "username": user['username'],
                    "first_name": user['first_name'],
                    "last_name": user['last_name'],
                    "mfa_enabled": bool(user['mfa_enabled'])
                }
            }
            
        except (InvalidCredentialsError, MFARequiredError, EmailNotVerifiedError,
                AccountInactiveError, RateLimitExceededError):
            raise
        except Exception as e:
            logger.error(f"Error during login: {e}")
            raise AuthError(f"Login failed: {e}")
    
    def verify_email(self, user_id: int, verification_token: str) -> bool:
        """
        Verify user email.
        
        Args:
            user_id: User ID
            verification_token: Verification token
            
        Returns:
            True if successful
            
        Example:
            >>> auth = EnhancedAuthManager()
            >>> auth.verify_email(1, "token123")
            True
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET is_verified = 1, email_verified_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_verified = 0
            """, (user_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                logger.info(f"Email verified for user_id: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error verifying email: {e}")
            return False
    
    def request_password_reset(
        self,
        email: str,
        ip_address: str
    ) -> Optional[str]:
        """
        Request password reset.
        
        Args:
            email: User email
            ip_address: Client IP address
            
        Returns:
            Reset token if user exists, None otherwise
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
            
        Example:
            >>> auth = EnhancedAuthManager()
            >>> token = auth.request_password_reset("user@example.com", "192.168.1.1")
        """
        try:
            # Check rate limit
            self.rate_limiter.check_rate_limit(ip_address, "password_reset")
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                # Don't reveal if user exists
                logger.warning(f"Password reset requested for non-existent email: {email}")
                return None
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            
            logger.info(f"Password reset requested for: {email}")
            return reset_token
            
        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"Error requesting password reset: {e}")
            return None
    
    def reset_password(
        self,
        user_id: int,
        reset_token: str,
        new_password: str
    ) -> bool:
        """
        Reset user password.
        
        Args:
            user_id: User ID
            reset_token: Reset token
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            PasswordTooWeakError: If password is too weak
            PasswordReusedError: If password was recently used
            
        Example:
            >>> auth = EnhancedAuthManager()
            >>> auth.reset_password(1, "token123", "NewSecurePass123!")
            True
        """
        try:
            # Validate password strength
            is_valid, message = self._validate_password_strength(new_password)
            if not is_valid:
                raise PasswordTooWeakError(message)
            
            # Check password history
            if self._check_password_history(user_id, new_password):
                raise PasswordReusedError(
                    "Password was recently used. Please choose a different password."
                )
            
            # Hash new password
            password_hash = self._hash_password(new_password)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (password_hash, user_id))
            
            success = cursor.rowcount > 0
            
            if success:
                # Add to password history
                self._add_to_password_history(user_id, password_hash)
            
            conn.commit()
            conn.close()
            
            if success:
                logger.info(f"Password reset for user_id: {user_id}")
            
            return success
            
        except (PasswordTooWeakError, PasswordReusedError):
            raise
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False
    
    def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            InvalidCredentialsError: If current password is wrong
            PasswordTooWeakError: If new password is too weak
            PasswordReusedError: If password was recently used
            
        Example:
            >>> auth = EnhancedAuthManager()
            >>> auth.change_password(1, "OldPass123!", "NewPass123!")
            True
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get current password hash
            cursor.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                raise UserNotFoundError("User not found")
            
            # Verify current password
            if not self._verify_password(current_password, user['password_hash']):
                conn.close()
                raise InvalidCredentialsError("Current password is incorrect")
            
            conn.close()
            
            # Use reset_password for validation and update
            return self.reset_password(user_id, "", new_password)
            
        except (InvalidCredentialsError, UserNotFoundError, 
                PasswordTooWeakError, PasswordReusedError):
            raise
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dictionary with new access token
            
        Raises:
            InvalidTokenError: If refresh token is invalid
            
        Example:
            >>> auth = EnhancedAuthManager()
            >>> result = auth.refresh_access_token(refresh_token)
            >>> print(result['access_token'])
        """
        try:
            payload = self._verify_token(refresh_token, "refresh")
            user_id = payload['user_id']
            
            # Generate new access token
            access_token = self._generate_token(user_id, "access")
            
            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": self.JWT_ACCESS_TOKEN_EXPIRE
            }
            
        except InvalidTokenError:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise InvalidTokenError("Failed to refresh token")
    
    def validate_session(self, access_token: str) -> Dict[str, Any]:
        """
        Validate access token and return user info.
        
        Args:
            access_token: Access token
            
        Returns:
            Dictionary with user info
            
        Raises:
            InvalidTokenError: If token is invalid
            
        Example:
            >>> auth = EnhancedAuthManager()
            >>> user_info = auth.validate_session(access_token)
            >>> print(user_info['user_id'])
        """
        try:
            payload = self._verify_token(access_token, "access")
            user_id = payload['user_id']
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, email, username, first_name, last_name, 
                       is_active, mfa_enabled
                FROM users
                WHERE id = ?
            """, (user_id,))
            
            user = cursor.fetchone()
            conn.close()
            
            if not user or not user['is_active']:
                raise InvalidTokenError("User not found or inactive")
            
            return {
                "user_id": user['id'],
                "email": user['email'],
                "username": user['username'],
                "first_name": user['first_name'],
                "last_name": user['last_name'],
                "mfa_enabled": bool(user['mfa_enabled'])
            }
            
        except InvalidTokenError:
            raise
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            raise InvalidTokenError("Session validation failed")


# ============================================================================
# UNIT TESTS (as comments for reference)
# ============================================================================

"""
Unit Tests for EnhancedAuthManager

import unittest
import tempfile
import os

class TestEnhancedAuthManager(unittest.TestCase):
    
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.auth = EnhancedAuthManager(db_path=self.db_path)
        
        # Initialize database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Create necessary tables...
        conn.commit()
        conn.close()
    
    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_register(self):
        result = self.auth.register(
            "test@example.com",
            "testuser",
            "SecurePass123!",
            ip_address="192.168.1.1"
        )
        self.assertIn('user_id', result)
        self.assertIn('verification_token', result)
    
    def test_login(self):
        # Register first
        self.auth.register(
            "test@example.com",
            "testuser",
            "SecurePass123!",
            ip_address="192.168.1.1"
        )
        
        # Verify email
        self.auth.verify_email(1, "token")
        
        # Login
        result = self.auth.login(
            "test@example.com",
            "SecurePass123!",
            "192.168.1.1"
        )
        self.assertIn('access_token', result)
        self.assertIn('refresh_token', result)
    
    def test_password_strength_validation(self):
        with self.assertRaises(PasswordTooWeakError):
            self.auth.register(
                "test@example.com",
                "testuser",
                "weak",
                ip_address="192.168.1.1"
            )

if __name__ == '__main__':
    unittest.main()
"""