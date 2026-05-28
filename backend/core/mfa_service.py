"""
Multi-Factor Authentication (MFA) Service
==========================================

Provides TOTP-based two-factor authentication with backup codes.

Features:
- TOTP secret generation and validation
- QR code generation for authenticator apps
- Backup code generation and validation
- MFA state management in database
- Integration with user authentication flow

Dependencies:
- pyotp: TOTP implementation
- qrcode: QR code generation
- secrets: Cryptographically secure random generation

Author: Bob
Version: 1.0.0
"""

import logging
import secrets
import hashlib
import json
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from pathlib import Path
import sqlite3

try:
    import pyotp
    import qrcode
    from io import BytesIO
    import base64
except ImportError as e:
    raise ImportError(
        "MFA service requires additional dependencies. "
        "Install with: pip install pyotp qrcode[pil]"
    ) from e

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class MFAError(Exception):
    """Base exception for MFA-related errors."""
    pass


class MFANotEnabledError(MFAError):
    """Raised when MFA is not enabled for user."""
    pass


class InvalidTOTPCodeError(MFAError):
    """Raised when TOTP code validation fails."""
    pass


class InvalidBackupCodeError(MFAError):
    """Raised when backup code validation fails."""
    pass


class MFAAlreadyEnabledError(MFAError):
    """Raised when attempting to enable MFA when already enabled."""
    pass


# ============================================================================
# MFA SERVICE CLASS
# ============================================================================

class MFAService:
    """
    Multi-Factor Authentication Service
    
    Manages TOTP-based two-factor authentication including:
    - Secret generation and storage
    - QR code generation for authenticator apps
    - TOTP code verification
    - Backup code generation and validation
    - MFA state management
    
    Attributes:
        db_path (str): Path to SQLite database
        issuer_name (str): Application name for TOTP
        backup_codes_count (int): Number of backup codes to generate
    """
    
    def __init__(
        self,
        db_path: str = "petroflow.db",
        issuer_name: str = "PetroFlow",
        backup_codes_count: int = 10
    ):
        """
        Initialize MFA Service.
        
        Args:
            db_path: Path to SQLite database file
            issuer_name: Application name displayed in authenticator apps
            backup_codes_count: Number of backup codes to generate
        """
        self.db_path = Path(db_path)
        self.issuer_name = issuer_name
        self.backup_codes_count = backup_codes_count
        
        logger.info(f"MFA Service initialized with database: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection with row factory.
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _hash_backup_code(self, code: str) -> str:
        """
        Hash a backup code for secure storage.
        
        Args:
            code: Plain text backup code
            
        Returns:
            SHA-256 hash of the code
        """
        return hashlib.sha256(code.encode()).hexdigest()
    
    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret.
        
        Returns:
            Base32-encoded secret string
            
        Example:
            >>> mfa = MFAService()
            >>> secret = mfa.generate_secret()
            >>> print(len(secret))
            32
        """
        secret = pyotp.random_base32()
        logger.debug("Generated new TOTP secret")
        return secret
    
    def generate_backup_codes(self) -> List[str]:
        """
        Generate cryptographically secure backup codes.
        
        Returns:
            List of backup codes (format: XXXX-XXXX-XXXX)
            
        Example:
            >>> mfa = MFAService()
            >>> codes = mfa.generate_backup_codes()
            >>> len(codes)
            10
            >>> len(codes[0])
            14
        """
        codes = []
        for _ in range(self.backup_codes_count):
            # Generate 12 random digits
            code_parts = [
                str(secrets.randbelow(10000)).zfill(4)
                for _ in range(3)
            ]
            code = "-".join(code_parts)
            codes.append(code)
        
        logger.debug(f"Generated {len(codes)} backup codes")
        return codes
    
    def generate_qr_code(
        self,
        secret: str,
        user_email: str
    ) -> str:
        """
        Generate QR code for authenticator app setup.
        
        Args:
            secret: TOTP secret
            user_email: User's email address
            
        Returns:
            Base64-encoded PNG image of QR code
            
        Example:
            >>> mfa = MFAService()
            >>> secret = mfa.generate_secret()
            >>> qr_data = mfa.generate_qr_code(secret, "user@example.com")
            >>> qr_data.startswith("data:image/png;base64,")
            True
        """
        try:
            # Create TOTP URI
            totp = pyotp.TOTP(secret)
            uri = totp.provisioning_uri(
                name=user_email,
                issuer_name=self.issuer_name
            )
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(uri)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            logger.info(f"Generated QR code for user: {user_email}")
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            raise MFAError(f"Failed to generate QR code: {e}")
    
    def verify_totp_code(
        self,
        secret: str,
        code: str,
        window: int = 1
    ) -> bool:
        """
        Verify a TOTP code.
        
        Args:
            secret: TOTP secret
            code: 6-digit TOTP code to verify
            window: Time window for validation (default: 1 = ±30 seconds)
            
        Returns:
            True if code is valid, False otherwise
            
        Example:
            >>> mfa = MFAService()
            >>> secret = mfa.generate_secret()
            >>> totp = pyotp.TOTP(secret)
            >>> code = totp.now()
            >>> mfa.verify_totp_code(secret, code)
            True
        """
        try:
            totp = pyotp.TOTP(secret)
            is_valid = totp.verify(code, valid_window=window)
            
            if is_valid:
                logger.info("TOTP code verified successfully")
            else:
                logger.warning("Invalid TOTP code provided")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying TOTP code: {e}")
            return False
    
    def enable_mfa(
        self,
        user_id: int,
        secret: str,
        verification_code: str
    ) -> Tuple[bool, List[str]]:
        """
        Enable MFA for a user after verifying initial setup.
        
        Args:
            user_id: User ID
            secret: TOTP secret to store
            verification_code: Initial TOTP code for verification
            
        Returns:
            Tuple of (success: bool, backup_codes: List[str])
            
        Raises:
            InvalidTOTPCodeError: If verification code is invalid
            MFAAlreadyEnabledError: If MFA is already enabled
            
        Example:
            >>> mfa = MFAService()
            >>> secret = mfa.generate_secret()
            >>> totp = pyotp.TOTP(secret)
            >>> code = totp.now()
            >>> success, codes = mfa.enable_mfa(1, secret, code)
            >>> success
            True
        """
        try:
            # Verify the code first
            if not self.verify_totp_code(secret, verification_code):
                raise InvalidTOTPCodeError("Invalid verification code")
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if MFA is already enabled
            cursor.execute(
                "SELECT id FROM mfa_secrets WHERE user_id = ? AND is_active = 1",
                (user_id,)
            )
            if cursor.fetchone():
                conn.close()
                raise MFAAlreadyEnabledError("MFA is already enabled for this user")
            
            # Generate backup codes
            backup_codes = self.generate_backup_codes()
            hashed_codes = [self._hash_backup_code(code) for code in backup_codes]
            
            # Store MFA secret and backup codes
            cursor.execute("""
                INSERT INTO mfa_secrets (user_id, secret, backup_codes, is_active)
                VALUES (?, ?, ?, 1)
            """, (user_id, secret, json.dumps(hashed_codes)))
            
            # Update user table
            cursor.execute("""
                UPDATE users 
                SET mfa_enabled = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"MFA enabled for user_id: {user_id}")
            return True, backup_codes
            
        except (InvalidTOTPCodeError, MFAAlreadyEnabledError):
            raise
        except Exception as e:
            logger.error(f"Error enabling MFA: {e}")
            raise MFAError(f"Failed to enable MFA: {e}")
    
    def disable_mfa(self, user_id: int) -> bool:
        """
        Disable MFA for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
            
        Example:
            >>> mfa = MFAService()
            >>> mfa.disable_mfa(1)
            True
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Deactivate MFA secret
            cursor.execute("""
                UPDATE mfa_secrets 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            
            # Update user table
            cursor.execute("""
                UPDATE users 
                SET mfa_enabled = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"MFA disabled for user_id: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling MFA: {e}")
            raise MFAError(f"Failed to disable MFA: {e}")
    
    def verify_mfa(
        self,
        user_id: int,
        code: str,
        is_backup_code: bool = False
    ) -> bool:
        """
        Verify MFA code (TOTP or backup code).
        
        Args:
            user_id: User ID
            code: TOTP code or backup code
            is_backup_code: Whether the code is a backup code
            
        Returns:
            True if verification successful
            
        Raises:
            MFANotEnabledError: If MFA is not enabled
            InvalidTOTPCodeError: If TOTP code is invalid
            InvalidBackupCodeError: If backup code is invalid
            
        Example:
            >>> mfa = MFAService()
            >>> # Assuming MFA is enabled for user 1
            >>> mfa.verify_mfa(1, "123456")
            True
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get MFA secret
            cursor.execute("""
                SELECT secret, backup_codes 
                FROM mfa_secrets 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                raise MFANotEnabledError("MFA is not enabled for this user")
            
            secret = result['secret']
            backup_codes_json = result['backup_codes']
            
            if is_backup_code:
                # Verify backup code
                backup_codes = json.loads(backup_codes_json)
                hashed_code = self._hash_backup_code(code)
                
                if hashed_code not in backup_codes:
                    conn.close()
                    raise InvalidBackupCodeError("Invalid backup code")
                
                # Remove used backup code
                backup_codes.remove(hashed_code)
                cursor.execute("""
                    UPDATE mfa_secrets 
                    SET backup_codes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (json.dumps(backup_codes), user_id))
                
                conn.commit()
                logger.info(f"Backup code used for user_id: {user_id}")
                
            else:
                # Verify TOTP code
                if not self.verify_totp_code(secret, code):
                    conn.close()
                    raise InvalidTOTPCodeError("Invalid TOTP code")
                
                logger.info(f"TOTP code verified for user_id: {user_id}")
            
            conn.close()
            return True
            
        except (MFANotEnabledError, InvalidTOTPCodeError, InvalidBackupCodeError):
            raise
        except Exception as e:
            logger.error(f"Error verifying MFA: {e}")
            raise MFAError(f"Failed to verify MFA: {e}")
    
    def is_mfa_enabled(self, user_id: int) -> bool:
        """
        Check if MFA is enabled for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if MFA is enabled
            
        Example:
            >>> mfa = MFAService()
            >>> mfa.is_mfa_enabled(1)
            False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM mfa_secrets 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking MFA status: {e}")
            return False
    
    def get_remaining_backup_codes_count(self, user_id: int) -> int:
        """
        Get the number of remaining backup codes.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of remaining backup codes
            
        Example:
            >>> mfa = MFAService()
            >>> mfa.get_remaining_backup_codes_count(1)
            10
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT backup_codes FROM mfa_secrets 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return 0
            
            backup_codes = json.loads(result['backup_codes'])
            return len(backup_codes)
            
        except Exception as e:
            logger.error(f"Error getting backup codes count: {e}")
            return 0
    
    def regenerate_backup_codes(
        self,
        user_id: int,
        verification_code: str
    ) -> List[str]:
        """
        Regenerate backup codes after verification.
        
        Args:
            user_id: User ID
            verification_code: TOTP code for verification
            
        Returns:
            List of new backup codes
            
        Raises:
            MFANotEnabledError: If MFA is not enabled
            InvalidTOTPCodeError: If verification code is invalid
            
        Example:
            >>> mfa = MFAService()
            >>> codes = mfa.regenerate_backup_codes(1, "123456")
            >>> len(codes)
            10
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get MFA secret
            cursor.execute("""
                SELECT secret FROM mfa_secrets 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                raise MFANotEnabledError("MFA is not enabled for this user")
            
            secret = result['secret']
            
            # Verify TOTP code
            if not self.verify_totp_code(secret, verification_code):
                conn.close()
                raise InvalidTOTPCodeError("Invalid verification code")
            
            # Generate new backup codes
            backup_codes = self.generate_backup_codes()
            hashed_codes = [self._hash_backup_code(code) for code in backup_codes]
            
            # Update database
            cursor.execute("""
                UPDATE mfa_secrets 
                SET backup_codes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (json.dumps(hashed_codes), user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Backup codes regenerated for user_id: {user_id}")
            return backup_codes
            
        except (MFANotEnabledError, InvalidTOTPCodeError):
            raise
        except Exception as e:
            logger.error(f"Error regenerating backup codes: {e}")
            raise MFAError(f"Failed to regenerate backup codes: {e}")


# ============================================================================
# UNIT TESTS (as comments for reference)
# ============================================================================

"""
Unit Tests for MFAService

import unittest
from unittest.mock import Mock, patch
import tempfile
import os

class TestMFAService(unittest.TestCase):
    
    def setUp(self):
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.mfa = MFAService(db_path=self.db_path)
        
        # Initialize database schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT,
                mfa_enabled INTEGER DEFAULT 0,
                updated_at TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE mfa_secrets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                secret TEXT,
                backup_codes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('INSERT INTO users (id, email) VALUES (1, "test@example.com")')
        conn.commit()
        conn.close()
    
    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_generate_secret(self):
        secret = self.mfa.generate_secret()
        self.assertEqual(len(secret), 32)
        self.assertTrue(secret.isalnum())
    
    def test_generate_backup_codes(self):
        codes = self.mfa.generate_backup_codes()
        self.assertEqual(len(codes), 10)
        for code in codes:
            self.assertRegex(code, r'^\d{4}-\d{4}-\d{4}$')
    
    def test_verify_totp_code(self):
        secret = self.mfa.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        self.assertTrue(self.mfa.verify_totp_code(secret, code))
        self.assertFalse(self.mfa.verify_totp_code(secret, "000000"))
    
    def test_enable_mfa(self):
        secret = self.mfa.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        success, backup_codes = self.mfa.enable_mfa(1, secret, code)
        self.assertTrue(success)
        self.assertEqual(len(backup_codes), 10)
        self.assertTrue(self.mfa.is_mfa_enabled(1))
    
    def test_verify_mfa_with_totp(self):
        # Enable MFA first
        secret = self.mfa.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        self.mfa.enable_mfa(1, secret, code)
        
        # Verify with new code
        new_code = totp.now()
        self.assertTrue(self.mfa.verify_mfa(1, new_code))
    
    def test_verify_mfa_with_backup_code(self):
        # Enable MFA
        secret = self.mfa.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        success, backup_codes = self.mfa.enable_mfa(1, secret, code)
        
        # Verify with backup code
        self.assertTrue(self.mfa.verify_mfa(1, backup_codes[0], is_backup_code=True))
        
        # Backup code should be consumed
        self.assertEqual(self.mfa.get_remaining_backup_codes_count(1), 9)
    
    def test_disable_mfa(self):
        # Enable MFA first
        secret = self.mfa.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        self.mfa.enable_mfa(1, secret, code)
        
        # Disable MFA
        self.assertTrue(self.mfa.disable_mfa(1))
        self.assertFalse(self.mfa.is_mfa_enabled(1))

if __name__ == '__main__':
    unittest.main()
"""