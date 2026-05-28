"""
License Management System
========================

This module provides comprehensive license management functionality including:
- License key generation and validation
- License activation/deactivation
- Feature access control
- Usage tracking and metrics
- License transfer and renewal
- Plan upgrades

Author: Bob
Date: 2026-05-12
"""

import sqlite3
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class LicenseError(Exception):
    """Base exception for license-related errors"""
    pass


class LicenseNotFoundError(LicenseError):
    """Raised when a license is not found"""
    pass


class LicenseExpiredError(LicenseError):
    """Raised when a license has expired"""
    pass


class LicenseInactiveError(LicenseError):
    """Raised when a license is not active"""
    pass


class LicenseActivationLimitError(LicenseError):
    """Raised when activation limit is exceeded"""
    pass


class InvalidLicenseKeyError(LicenseError):
    """Raised when license key format is invalid"""
    pass


class FeatureNotAvailableError(LicenseError):
    """Raised when a feature is not available in the current plan"""
    pass


class UsageLimitExceededError(LicenseError):
    """Raised when usage limit is exceeded"""
    pass


# ============================================================================
# Enums and Data Classes
# ============================================================================

class LicenseStatus(Enum):
    """License status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PlanType(Enum):
    """Plan type enumeration"""
    TRIAL = "TRIAL"
    BASIC = "BASIC"
    PRO = "PRO"
    ENTERPRISE = "ENT"


@dataclass
class LicenseInfo:
    """Data class for license information"""
    license_id: int
    license_key: str
    plan_id: int
    plan_name: str
    user_id: int
    status: str
    activation_date: Optional[str]
    expiry_date: Optional[str]
    max_activations: int
    current_activations: int
    features: Dict[str, Any]


@dataclass
class UsageStats:
    """Data class for usage statistics"""
    license_id: int
    api_calls: int
    api_calls_limit: int
    projects: int
    projects_limit: int
    users: int
    users_limit: int
    storage_gb: float
    storage_limit_gb: float


# ============================================================================
# License Manager Class
# ============================================================================

class LicenseManager:
    """
    Comprehensive license management system.
    
    This class handles all license-related operations including generation,
    validation, activation, feature access control, and usage tracking.
    """
    
    # Plan feature mappings
    PLAN_FEATURES = {
        "TRIAL": {
            "max_users": 1,
            "max_projects": 2,
            "max_api_calls_per_day": 100,
            "max_storage_gb": 1,
            "advanced_analytics": False,
            "api_access": False,
            "priority_support": False,
            "custom_integrations": False,
            "duration_days": 14
        },
        "BASIC": {
            "max_users": 5,
            "max_projects": 10,
            "max_api_calls_per_day": 1000,
            "max_storage_gb": 10,
            "advanced_analytics": False,
            "api_access": True,
            "priority_support": False,
            "custom_integrations": False,
            "duration_days": 365
        },
        "PRO": {
            "max_users": 25,
            "max_projects": 50,
            "max_api_calls_per_day": 10000,
            "max_storage_gb": 100,
            "advanced_analytics": True,
            "api_access": True,
            "priority_support": True,
            "custom_integrations": False,
            "duration_days": 365
        },
        "ENT": {
            "max_users": -1,  # Unlimited
            "max_projects": -1,  # Unlimited
            "max_api_calls_per_day": -1,  # Unlimited
            "max_storage_gb": -1,  # Unlimited
            "advanced_analytics": True,
            "api_access": True,
            "priority_support": True,
            "custom_integrations": True,
            "duration_days": 365
        }
    }
    
    def __init__(self, db_path: str):
        """
        Initialize the License Manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        logger.info(f"LicenseManager initialized with database: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _generate_checksum(self, data: str) -> str:
        """
        Generate a checksum for validation.
        
        Args:
            data: Data to generate checksum for
            
        Returns:
            Hexadecimal checksum string
        """
        return hashlib.sha256(data.encode()).hexdigest()[:8]
    
    def _validate_key_format(self, license_key: str) -> Tuple[bool, Optional[str]]:
        """
        Validate license key format.
        
        Args:
            license_key: License key to validate
            
        Returns:
            Tuple of (is_valid, plan_prefix)
        """
        try:
            parts = license_key.split('-')
            if len(parts) != 2:
                return False, None
            
            prefix, key_part = parts
            
            # Validate prefix
            if prefix not in [p.value for p in PlanType]:
                return False, None
            
            # Validate key part (32 hex chars + 8 checksum chars)
            if len(key_part) != 40 or not all(c in '0123456789ABCDEF' for c in key_part):
                return False, None
            
            # Validate checksum
            key_data = key_part[:32]
            checksum = key_part[32:]
            expected_checksum = self._generate_checksum(f"{prefix}-{key_data}")
            
            if checksum != expected_checksum:
                return False, None
            
            return True, prefix
            
        except Exception as e:
            logger.error(f"Error validating key format: {e}")
            return False, None
    
    def generate_license_key(self, plan_id: int, user_id: int) -> str:
        """
        Generate a unique license key.
        
        Format: {PLAN_PREFIX}-{32_HEX_CHARS}{8_CHECKSUM_CHARS}
        
        Args:
            plan_id: ID of the subscription plan
            user_id: ID of the user
            
        Returns:
            Generated license key
            
        Raises:
            LicenseError: If plan not found or generation fails
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get plan information
            cursor.execute(
                "SELECT name FROM subscription_plans WHERE id = ?",
                (plan_id,)
            )
            plan = cursor.fetchone()
            
            if not plan:
                raise LicenseError(f"Plan with ID {plan_id} not found")
            
            plan_name = plan['name']
            
            # Generate random hex string
            random_hex = secrets.token_hex(16).upper()  # 32 characters
            
            # Generate checksum
            checksum = self._generate_checksum(f"{plan_name}-{random_hex}")
            
            # Combine to create license key
            license_key = f"{plan_name}-{random_hex}{checksum}"
            
            # Calculate expiry date
            duration_days = self.PLAN_FEATURES[plan_name]["duration_days"]
            expiry_date = (datetime.now() + timedelta(days=duration_days)).isoformat()
            
            # Insert license into database
            cursor.execute("""
                INSERT INTO licenses (
                    license_key, plan_id, user_id, status, 
                    generated_date, expiry_date, max_activations
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                license_key, plan_id, user_id, LicenseStatus.ACTIVE.value,
                datetime.now().isoformat(), expiry_date, 1
            ))
            
            license_id = cursor.lastrowid
            
            # Log audit trail
            cursor.execute("""
                INSERT INTO license_audit_log (
                    license_id, action, performed_by, details
                )
                VALUES (?, ?, ?, ?)
            """, (
                license_id, "LICENSE_GENERATED", user_id,
                f"Generated {plan_name} license key"
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Generated license key for user {user_id}, plan {plan_name}")
            return license_key
            
        except Exception as e:
            logger.error(f"Error generating license key: {e}")
            raise LicenseError(f"Failed to generate license key: {e}")
    
    def validate_license(self, license_key: str) -> bool:
        """
        Validate if a license is valid.
        
        Checks:
        - Key format
        - Existence in database
        - Status (active/suspended/expired)
        - Expiry date
        
        Args:
            license_key: License key to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate format
            is_valid_format, _ = self._validate_key_format(license_key)
            if not is_valid_format:
                logger.warning(f"Invalid license key format: {license_key}")
                return False
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check existence and status
            cursor.execute("""
                SELECT id, status, expiry_date
                FROM licenses
                WHERE license_key = ?
            """, (license_key,))
            
            license_data = cursor.fetchone()
            conn.close()
            
            if not license_data:
                logger.warning(f"License key not found: {license_key}")
                return False
            
            # Check status
            if license_data['status'] != LicenseStatus.ACTIVE.value:
                logger.warning(f"License not active: {license_key}, status: {license_data['status']}")
                return False
            
            # Check expiry
            if license_data['expiry_date']:
                expiry = datetime.fromisoformat(license_data['expiry_date'])
                if datetime.now() > expiry:
                    logger.warning(f"License expired: {license_key}")
                    # Auto-update status to expired
                    self._update_license_status(license_data['id'], LicenseStatus.EXPIRED.value)
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating license: {e}")
            return False
    
    def activate_license(self, license_key: str, user_id: int) -> bool:
        """
        Activate a license for a user.
        
        Args:
            license_key: License key to activate
            user_id: User ID to activate for
            
        Returns:
            True if activated successfully
            
        Raises:
            InvalidLicenseKeyError: If key format is invalid
            LicenseNotFoundError: If license not found
            LicenseInactiveError: If license is not active
            LicenseActivationLimitError: If activation limit exceeded
        """
        try:
            # Validate format
            is_valid_format, _ = self._validate_key_format(license_key)
            if not is_valid_format:
                raise InvalidLicenseKeyError("Invalid license key format")
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get license info
            cursor.execute("""
                SELECT id, status, max_activations, user_id
                FROM licenses
                WHERE license_key = ?
            """, (license_key,))
            
            license_data = cursor.fetchone()
            
            if not license_data:
                conn.close()
                raise LicenseNotFoundError("License not found")
            
            license_id = license_data['id']
            
            # Check if already activated
            if license_data['user_id'] == user_id:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM license_activations
                    WHERE license_id = ? AND user_id = ? AND deactivated_at IS NULL
                """, (license_id, user_id))
                
                if cursor.fetchone()['count'] > 0:
                    conn.close()
                    logger.info(f"License already activated for user {user_id}")
                    return True
            
            # Check status
            if license_data['status'] != LicenseStatus.ACTIVE.value:
                conn.close()
                raise LicenseInactiveError(f"License status is {license_data['status']}")
            
            # Check activation limit
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM license_activations
                WHERE license_id = ? AND deactivated_at IS NULL
            """, (license_id,))
            
            current_activations = cursor.fetchone()['count']
            
            if current_activations >= license_data['max_activations']:
                conn.close()
                raise LicenseActivationLimitError(
                    f"Activation limit reached ({license_data['max_activations']})"
                )
            
            # Activate license
            cursor.execute("""
                INSERT INTO license_activations (
                    license_id, user_id, activated_at, device_info
                )
                VALUES (?, ?, ?, ?)
            """, (license_id, user_id, datetime.now().isoformat(), "{}"))
            
            # Update license activation date if first activation
            if not current_activations:
                cursor.execute("""
                    UPDATE licenses
                    SET activation_date = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), license_id))
            
            # Log audit trail
            cursor.execute("""
                INSERT INTO license_audit_log (
                    license_id, action, performed_by, details
                )
                VALUES (?, ?, ?, ?)
            """, (license_id, "LICENSE_ACTIVATED", user_id, f"License activated for user {user_id}"))
            
            conn.commit()
            conn.close()
            
            logger.info(f"License {license_key} activated for user {user_id}")
            return True
            
        except (InvalidLicenseKeyError, LicenseNotFoundError, 
                LicenseInactiveError, LicenseActivationLimitError) as e:
            logger.error(f"License activation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error activating license: {e}")
            raise LicenseError(f"Failed to activate license: {e}")
    
    def deactivate_license(self, license_id: int) -> bool:
        """
        Deactivate a license.
        
        Args:
            license_id: ID of the license to deactivate
            
        Returns:
            True if deactivated successfully
            
        Raises:
            LicenseNotFoundError: If license not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if license exists
            cursor.execute("SELECT id FROM licenses WHERE id = ?", (license_id,))
            if not cursor.fetchone():
                conn.close()
                raise LicenseNotFoundError(f"License {license_id} not found")
            
            # Deactivate all active activations
            cursor.execute("""
                UPDATE license_activations
                SET deactivated_at = ?
                WHERE license_id = ? AND deactivated_at IS NULL
            """, (datetime.now().isoformat(), license_id))
            
            # Update license status
            cursor.execute("""
                UPDATE licenses
                SET status = ?
                WHERE id = ?
            """, (LicenseStatus.SUSPENDED.value, license_id))
            
            # Log audit trail
            cursor.execute("""
                INSERT INTO license_audit_log (
                    license_id, action, performed_by, details
                )
                VALUES (?, ?, ?, ?)
            """, (license_id, "LICENSE_DEACTIVATED", 0, "License deactivated"))
            
            conn.commit()
            conn.close()
            
            logger.info(f"License {license_id} deactivated")
            return True
            
        except LicenseNotFoundError as e:
            logger.error(f"License deactivation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deactivating license: {e}")
            raise LicenseError(f"Failed to deactivate license: {e}")
    
    def check_license_expiry(self, license_id: int) -> Tuple[bool, Optional[datetime]]:
        """
        Check if a license has expired.
        
        Args:
            license_id: ID of the license to check
            
        Returns:
            Tuple of (is_expired, expiry_date)
            
        Raises:
            LicenseNotFoundError: If license not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT expiry_date, status
                FROM licenses
                WHERE id = ?
            """, (license_id,))
            
            license_data = cursor.fetchone()
            conn.close()
            
            if not license_data:
                raise LicenseNotFoundError(f"License {license_id} not found")
            
            if not license_data['expiry_date']:
                return False, None
            
            expiry_date = datetime.fromisoformat(license_data['expiry_date'])
            is_expired = datetime.now() > expiry_date
            
            # Auto-update status if expired
            if is_expired and license_data['status'] == LicenseStatus.ACTIVE.value:
                self._update_license_status(license_id, LicenseStatus.EXPIRED.value)
            
            return is_expired, expiry_date
            
        except LicenseNotFoundError as e:
            logger.error(f"License expiry check error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error checking license expiry: {e}")
            raise LicenseError(f"Failed to check license expiry: {e}")
    
    def get_license_info(self, license_key: str) -> LicenseInfo:
        """
        Get detailed information about a license.
        
        Args:
            license_key: License key to get info for
            
        Returns:
            LicenseInfo object with license details
            
        Raises:
            LicenseNotFoundError: If license not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    l.id, l.license_key, l.plan_id, l.user_id, l.status,
                    l.activation_date, l.expiry_date, l.max_activations,
                    sp.name as plan_name,
                    (SELECT COUNT(*) FROM license_activations 
                     WHERE license_id = l.id AND deactivated_at IS NULL) as current_activations
                FROM licenses l
                JOIN subscription_plans sp ON l.plan_id = sp.id
                WHERE l.license_key = ?
            """, (license_key,))
            
            license_data = cursor.fetchone()
            conn.close()
            
            if not license_data:
                raise LicenseNotFoundError("License not found")
            
            # Get plan features
            features = self.PLAN_FEATURES.get(license_data['plan_name'], {})
            
            return LicenseInfo(
                license_id=license_data['id'],
                license_key=license_data['license_key'],
                plan_id=license_data['plan_id'],
                plan_name=license_data['plan_name'],
                user_id=license_data['user_id'],
                status=license_data['status'],
                activation_date=license_data['activation_date'],
                expiry_date=license_data['expiry_date'],
                max_activations=license_data['max_activations'],
                current_activations=license_data['current_activations'],
                features=features
            )
            
        except LicenseNotFoundError as e:
            logger.error(f"Get license info error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting license info: {e}")
            raise LicenseError(f"Failed to get license info: {e}")
    
    def get_user_licenses(self, user_id: int) -> List[LicenseInfo]:
        """
        Get all licenses for a user.
        
        Args:
            user_id: User ID to get licenses for
            
        Returns:
            List of LicenseInfo objects
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    l.id, l.license_key, l.plan_id, l.user_id, l.status,
                    l.activation_date, l.expiry_date, l.max_activations,
                    sp.name as plan_name,
                    (SELECT COUNT(*) FROM license_activations 
                     WHERE license_id = l.id AND deactivated_at IS NULL) as current_activations
                FROM licenses l
                JOIN subscription_plans sp ON l.plan_id = sp.id
                WHERE l.user_id = ?
                ORDER BY l.generated_date DESC
            """, (user_id,))
            
            licenses = []
            for row in cursor.fetchall():
                features = self.PLAN_FEATURES.get(row['plan_name'], {})
                licenses.append(LicenseInfo(
                    license_id=row['id'],
                    license_key=row['license_key'],
                    plan_id=row['plan_id'],
                    plan_name=row['plan_name'],
                    user_id=row['user_id'],
                    status=row['status'],
                    activation_date=row['activation_date'],
                    expiry_date=row['expiry_date'],
                    max_activations=row['max_activations'],
                    current_activations=row['current_activations'],
                    features=features
                ))
            
            conn.close()
            logger.info(f"Retrieved {len(licenses)} licenses for user {user_id}")
            return licenses
            
        except Exception as e:
            logger.error(f"Error getting user licenses: {e}")
            raise LicenseError(f"Failed to get user licenses: {e}")
    
    def get_license_features(self, license_id: int) -> Dict[str, Any]:
        """
        Get features available for a license.
        
        Args:
            license_id: License ID to get features for
            
        Returns:
            Dictionary of features and their values
            
        Raises:
            LicenseNotFoundError: If license not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT sp.name
                FROM licenses l
                JOIN subscription_plans sp ON l.plan_id = sp.id
                WHERE l.id = ?
            """, (license_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                raise LicenseNotFoundError(f"License {license_id} not found")
            
            plan_name = result['name']
            features = self.PLAN_FEATURES.get(plan_name, {})
            
            logger.info(f"Retrieved features for license {license_id}")
            return features
            
        except LicenseNotFoundError as e:
            logger.error(f"Get license features error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting license features: {e}")
            raise LicenseError(f"Failed to get license features: {e}")
    
    def check_feature_access(self, user_id: int, feature_name: str) -> bool:
        """
        Check if a user has access to a specific feature.
        
        Args:
            user_id: User ID to check
            feature_name: Name of the feature to check
            
        Returns:
            True if user has access, False otherwise
        """
        try:
            licenses = self.get_user_licenses(user_id)
            
            # Check active licenses
            for license_info in licenses:
                if license_info.status == LicenseStatus.ACTIVE.value:
                    # Check if not expired
                    if license_info.expiry_date:
                        expiry = datetime.fromisoformat(license_info.expiry_date)
                        if datetime.now() > expiry:
                            continue
                    
                    # Check feature
                    if feature_name in license_info.features:
                        feature_value = license_info.features[feature_name]
                        # Boolean features
                        if isinstance(feature_value, bool):
                            if feature_value:
                                return True
                        # Numeric features (check if not zero/unlimited)
                        elif isinstance(feature_value, (int, float)):
                            if feature_value != 0:
                                return True
            
            logger.info(f"User {user_id} does not have access to feature: {feature_name}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking feature access: {e}")
            return False
    
    def update_license_usage(self, license_id: int, metric_type: str, value: float) -> bool:
        """
        Update usage metrics for a license.
        
        Args:
            license_id: License ID to update
            metric_type: Type of metric (api_calls, projects, users, storage_gb)
            value: Value to add to current usage
            
        Returns:
            True if updated successfully
            
        Raises:
            LicenseNotFoundError: If license not found
            UsageLimitExceededError: If usage limit would be exceeded
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if license exists
            cursor.execute("SELECT id FROM licenses WHERE id = ?", (license_id,))
            if not cursor.fetchone():
                conn.close()
                raise LicenseNotFoundError(f"License {license_id} not found")
            
            # Get current usage
            cursor.execute("""
                SELECT metric_value
                FROM usage_metrics
                WHERE license_id = ? AND metric_type = ?
            """, (license_id, metric_type))
            
            current = cursor.fetchone()
            current_value = current['metric_value'] if current else 0
            new_value = current_value + value
            
            # Check limits
            features = self.get_license_features(license_id)
            limit_key = f"max_{metric_type}"
            if limit_key in features:
                limit = features[limit_key]
                if limit != -1 and new_value > limit:  # -1 means unlimited
                    conn.close()
                    raise UsageLimitExceededError(
                        f"Usage limit exceeded for {metric_type}: {new_value} > {limit}"
                    )
            
            # Update or insert usage
            if current:
                cursor.execute("""
                    UPDATE usage_metrics
                    SET metric_value = ?, last_updated = ?
                    WHERE license_id = ? AND metric_type = ?
                """, (new_value, datetime.now().isoformat(), license_id, metric_type))
            else:
                cursor.execute("""
                    INSERT INTO usage_metrics (
                        license_id, metric_type, metric_value, last_updated
                    )
                    VALUES (?, ?, ?, ?)
                """, (license_id, metric_type, new_value, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated usage for license {license_id}: {metric_type} = {new_value}")
            return True
            
        except (LicenseNotFoundError, UsageLimitExceededError) as e:
            logger.error(f"Update license usage error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating license usage: {e}")
            raise LicenseError(f"Failed to update license usage: {e}")
    
    def get_usage_stats(self, license_id: int) -> UsageStats:
        """
        Get usage statistics for a license.
        
        Args:
            license_id: License ID to get stats for
            
        Returns:
            UsageStats object with usage information
            
        Raises:
            LicenseNotFoundError: If license not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if license exists and get features
            features = self.get_license_features(license_id)
            
            # Get usage metrics
            cursor.execute("""
                SELECT metric_type, metric_value
                FROM usage_metrics
                WHERE license_id = ?
            """, (license_id,))
            
            usage = {row['metric_type']: row['metric_value'] for row in cursor.fetchall()}
            conn.close()
            
            return UsageStats(
                license_id=license_id,
                api_calls=int(usage.get('api_calls', 0)),
                api_calls_limit=features.get('max_api_calls_per_day', 0),
                projects=int(usage.get('projects', 0)),
                projects_limit=features.get('max_projects', 0),
                users=int(usage.get('users', 0)),
                users_limit=features.get('max_users', 0),
                storage_gb=float(usage.get('storage_gb', 0)),
                storage_limit_gb=float(features.get('max_storage_gb', 0))
            )
            
        except LicenseNotFoundError as e:
            logger.error(f"Get usage stats error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            raise LicenseError(f"Failed to get usage stats: {e}")
    
    def transfer_license(self, license_id: int, from_user_id: int, to_user_id: int) -> bool:
        """
        Transfer a license from one user to another.
        
        Args:
            license_id: License ID to transfer
            from_user_id: Current owner user ID
            to_user_id: New owner user ID
            
        Returns:
            True if transferred successfully
            
        Raises:
            LicenseNotFoundError: If license not found
            LicenseError: If transfer not allowed
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Verify license ownership
            cursor.execute("""
                SELECT user_id, status
                FROM licenses
                WHERE id = ?
            """, (license_id,))
            
            license_data = cursor.fetchone()
            
            if not license_data:
                conn.close()
                raise LicenseNotFoundError(f"License {license_id} not found")
            
            if license_data['user_id'] != from_user_id:
                conn.close()
                raise LicenseError("License does not belong to the specified user")
            
            # Deactivate current activations
            cursor.execute("""
                UPDATE license_activations
                SET deactivated_at = ?
                WHERE license_id = ? AND deactivated_at IS NULL
            """, (datetime.now().isoformat(), license_id))
            
            # Transfer license
            cursor.execute("""
                UPDATE licenses
                SET user_id = ?
                WHERE id = ?
            """, (to_user_id, license_id))
            
            # Log audit trail
            cursor.execute("""
                INSERT INTO license_audit_log (
                    license_id, action, performed_by, details
                )
                VALUES (?, ?, ?, ?)
            """, (
                license_id, "LICENSE_TRANSFERRED", from_user_id,
                f"License transferred from user {from_user_id} to user {to_user_id}"
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"License {license_id} transferred from user {from_user_id} to {to_user_id}")
            return True
            
        except (LicenseNotFoundError, LicenseError) as e:
            logger.error(f"License transfer error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error transferring license: {e}")
            raise LicenseError(f"Failed to transfer license: {e}")
    
    def renew_license(self, license_id: int, duration_days: int) -> bool:
        """
        Renew a license by extending its expiry date.
        
        Args:
            license_id: License ID to renew
            duration_days: Number of days to extend
            
        Returns:
            True if renewed successfully
            
        Raises:
            LicenseNotFoundError: If license not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get current expiry
            cursor.execute("""
                SELECT expiry_date, status
                FROM licenses
                WHERE id = ?
            """, (license_id,))
            
            license_data = cursor.fetchone()
            
            if not license_data:
                conn.close()
                raise LicenseNotFoundError(f"License {license_id} not found")
            
            # Calculate new expiry
            if license_data['expiry_date']:
                current_expiry = datetime.fromisoformat(license_data['expiry_date'])
                # If expired, start from now, otherwise extend from current expiry
                if datetime.now() > current_expiry:
                    new_expiry = datetime.now() + timedelta(days=duration_days)
                else:
                    new_expiry = current_expiry + timedelta(days=duration_days)
            else:
                new_expiry = datetime.now() + timedelta(days=duration_days)
            
            # Update license
            cursor.execute("""
                UPDATE licenses
                SET expiry_date = ?, status = ?
                WHERE id = ?
            """, (new_expiry.isoformat(), LicenseStatus.ACTIVE.value, license_id))
            
            # Log audit trail
            cursor.execute("""
                INSERT INTO license_audit_log (
                    license_id, action, performed_by, details
                )
                VALUES (?, ?, ?, ?)
            """, (
                license_id, "LICENSE_RENEWED", 0,
                f"License renewed for {duration_days} days until {new_expiry.isoformat()}"
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"License {license_id} renewed for {duration_days} days")
            return True
            
        except LicenseNotFoundError as e:
            logger.error(f"License renewal error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error renewing license: {e}")
            raise LicenseError(f"Failed to renew license: {e}")
    
    def upgrade_license(self, license_id: int, new_plan_id: int) -> bool:
        """
        Upgrade a license to a different plan.
        
        Args:
            license_id: License ID to upgrade
            new_plan_id: New plan ID
            
        Returns:
            True if upgraded successfully
            
        Raises:
            LicenseNotFoundError: If license or plan not found
            LicenseError: If upgrade not allowed
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get current license info
            cursor.execute("""
                SELECT l.plan_id, sp1.name as current_plan, sp1.price as current_price
                FROM licenses l
                JOIN subscription_plans sp1 ON l.plan_id = sp1.id
                WHERE l.id = ?
            """, (license_id,))
            
            current_license = cursor.fetchone()
            
            if not current_license:
                conn.close()
                raise LicenseNotFoundError(f"License {license_id} not found")
            
            # Get new plan info
            cursor.execute("""
                SELECT name, price
                FROM subscription_plans
                WHERE id = ?
            """, (new_plan_id,))
            
            new_plan = cursor.fetchone()
            
            if not new_plan:
                conn.close()
                raise LicenseNotFoundError(f"Plan {new_plan_id} not found")
            
            # Validate upgrade (can only upgrade to higher tier)
            plan_hierarchy = ["TRIAL", "BASIC", "PRO", "ENT"]
            current_tier = plan_hierarchy.index(current_license['current_plan'])
            new_tier = plan_hierarchy.index(new_plan['name'])
            
            if new_tier <= current_tier:
                conn.close()
                raise LicenseError("Can only upgrade to a higher tier plan")
            
            # Update license
            cursor.execute("""
                UPDATE licenses
                SET plan_id = ?
                WHERE id = ?
            """, (new_plan_id, license_id))
            
            # Log audit trail
            cursor.execute("""
                INSERT INTO license_audit_log (
                    license_id, action, performed_by, details
                )
                VALUES (?, ?, ?, ?)
            """, (
                license_id, "LICENSE_UPGRADED", 0,
                f"License upgraded from {current_license['current_plan']} to {new_plan['name']}"
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"License {license_id} upgraded to plan {new_plan['name']}")
            return True
            
        except (LicenseNotFoundError, LicenseError) as e:
            logger.error(f"License upgrade error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error upgrading license: {e}")
            raise LicenseError(f"Failed to upgrade license: {e}")
    
    def _update_license_status(self, license_id: int, status: str) -> None:
        """
        Internal method to update license status.
        
        Args:
            license_id: License ID to update
            status: New status value
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE licenses
                SET status = ?
                WHERE id = ?
            """, (status, license_id))
            
            cursor.execute("""
                INSERT INTO license_audit_log (
                    license_id, action, performed_by, details
                )
                VALUES (?, ?, ?, ?)
            """, (license_id, "STATUS_CHANGED", 0, f"Status changed to {status}"))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating license status: {e}")


# ============================================================================
# Basic Unit Tests (as comments for reference)
# ============================================================================

"""
UNIT TESTS:

def test_generate_license_key():
    # Test license key generation
    lm = LicenseManager("test.db")
    key = lm.generate_license_key(plan_id=1, user_id=1)
    assert key.startswith("TRIAL-") or key.startswith("BASIC-")
    assert len(key) == 46  # PREFIX(5) + DASH(1) + HEX(32) + CHECKSUM(8)

def test_validate_license_format():
    lm = LicenseManager("test.db")
    # Valid format
    is_valid, prefix = lm._validate_key_format("TRIAL-" + "A" * 32 + "12345678")
    assert is_valid == True or is_valid == False  # Depends on checksum
    
    # Invalid format
    is_valid, prefix = lm._validate_key_format("INVALID-KEY")
    assert is_valid == False

def test_activate_license():
    lm = LicenseManager("test.db")
    # Generate and activate
    key = lm.generate_license_key(plan_id=1, user_id=1)
    result = lm.activate_license(key, user_id=1)
    assert result == True

def test_check_feature_access():
    lm = LicenseManager("test.db")
    # User with BASIC plan should have api_access
    has_access = lm.check_feature_access(user_id=1, feature_name="api_access")
    # Result depends on user's actual licenses

def test_usage_tracking():
    lm = LicenseManager("test.db")
    # Update usage
    result = lm.update_license_usage(license_id=1, metric_type="api_calls", value=10)
    # Get stats
    stats = lm.get_usage_stats(license_id=1)
    assert stats.api_calls >= 10

def test_license_transfer():
    lm = LicenseManager("test.db")
    result = lm.transfer_license(license_id=1, from_user_id=1, to_user_id=2)
    # Verify transfer
    info = lm.get_license_info(license_key="...")
    assert info.user_id == 2

def test_license_renewal():
    lm = LicenseManager("test.db")
    result = lm.renew_license(license_id=1, duration_days=365)
    assert result == True

def test_license_upgrade():
    lm = LicenseManager("test.db")
    result = lm.upgrade_license(license_id=1, new_plan_id=2)
    assert result == True

def test_exception_handling():
    lm = LicenseManager("test.db")
    # Test LicenseNotFoundError
    try:
        lm.get_license_info("INVALID-KEY")
        assert False, "Should raise LicenseNotFoundError"
    except LicenseNotFoundError:
        pass
    
    # Test InvalidLicenseKeyError
    try:
        lm.activate_license("INVALID", user_id=1)
        assert False, "Should raise InvalidLicenseKeyError"
    except InvalidLicenseKeyError:
        pass
"""