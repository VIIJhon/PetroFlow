"""
Rate Limiter Service
====================

Provides protection against brute force attacks and API abuse.

Features:
- Rate limiting by IP address and user ID
- Temporary blocking after failed attempts
- IP whitelist/blacklist management
- Configurable rate limits and time windows
- Redis support with in-memory fallback
- Comprehensive logging of suspicious activity

Dependencies:
- redis (optional): For distributed rate limiting
- sqlite3: For persistent storage

Author: Bob
Version: 1.0.0
"""

import logging
import time
import sqlite3
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from threading import Lock
import json

# Try to import Redis, fallback to in-memory if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class RateLimitError(Exception):
    """Base exception for rate limiting errors."""
    pass


class RateLimitExceededError(RateLimitError):
    """Raised when rate limit is exceeded."""
    def __init__(self, retry_after: int, message: str = "Rate limit exceeded"):
        self.retry_after = retry_after
        super().__init__(f"{message}. Retry after {retry_after} seconds.")


class IPBlockedError(RateLimitError):
    """Raised when IP is blocked."""
    def __init__(self, reason: str = "IP address is blocked"):
        super().__init__(reason)


# ============================================================================
# IN-MEMORY STORAGE (FALLBACK)
# ============================================================================

class InMemoryStorage:
    """
    In-memory storage for rate limiting when Redis is not available.
    Thread-safe implementation with automatic cleanup.
    """
    
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.lock = Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        with self.lock:
            keys_to_delete = []
            for key, value in self.data.items():
                if 'expires_at' in value and value['expires_at'] < current_time:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.data[key]
            
            self._last_cleanup = current_time
            logger.debug(f"Cleaned up {len(keys_to_delete)} expired entries")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        self._cleanup_expired()
        with self.lock:
            entry = self.data.get(key)
            if entry and entry.get('expires_at', float('inf')) > time.time():
                return entry.get('value')
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value with TTL."""
        with self.lock:
            self.data[key] = {
                'value': value,
                'expires_at': time.time() + ttl
            }
    
    def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        with self.lock:
            entry = self.data.get(key, {'value': 0})
            entry['value'] = entry.get('value', 0) + amount
            self.data[key] = entry
            return entry['value']
    
    def delete(self, key: str):
        """Delete key."""
        with self.lock:
            if key in self.data:
                del self.data[key]
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self.get(key) is not None


# ============================================================================
# RATE LIMITER CLASS
# ============================================================================

class RateLimiter:
    """
    Rate Limiter Service
    
    Provides comprehensive rate limiting and brute force protection:
    - Per-IP and per-user rate limiting
    - Configurable time windows and limits
    - Automatic blocking after threshold
    - IP whitelist/blacklist
    - Suspicious activity logging
    - Redis support with in-memory fallback
    
    Attributes:
        db_path (str): Path to SQLite database
        redis_client: Redis client (optional)
        storage: Storage backend (Redis or in-memory)
    """
    
    # Default rate limit configurations
    DEFAULT_LIMITS = {
        'login': {'requests': 5, 'window': 300, 'block_duration': 900},  # 5 attempts per 5 min
        'api': {'requests': 100, 'window': 60, 'block_duration': 300},   # 100 requests per minute
        'password_reset': {'requests': 3, 'window': 3600, 'block_duration': 3600},  # 3 per hour
        'registration': {'requests': 3, 'window': 3600, 'block_duration': 3600},  # 3 per hour
    }
    
    def __init__(
        self,
        db_path: str = "petroflow.db",
        redis_url: Optional[str] = None,
        use_redis: bool = True
    ):
        """
        Initialize Rate Limiter.
        
        Args:
            db_path: Path to SQLite database
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            use_redis: Whether to attempt Redis connection
        """
        self.db_path = Path(db_path)
        self.redis_client = None
        self.storage = None
        
        # Try to connect to Redis
        if use_redis and REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                self.redis_client.ping()
                self.storage = self.redis_client
                logger.info("Rate limiter using Redis storage")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory storage.")
                self.storage = InMemoryStorage()
        else:
            self.storage = InMemoryStorage()
            logger.info("Rate limiter using in-memory storage")
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables for persistent IP lists."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # IP whitelist/blacklist table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_access_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address VARCHAR(45) NOT NULL UNIQUE,
                    list_type VARCHAR(20) NOT NULL,  -- 'whitelist' or 'blacklist'
                    reason TEXT,
                    added_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (added_by) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ip_access_list_ip 
                ON ip_access_list(ip_address)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ip_access_list_type 
                ON ip_access_list(list_type)
            """)
            
            conn.commit()
            conn.close()
            logger.debug("Rate limiter database tables initialized")
            
        except Exception as e:
            logger.error(f"Error initializing rate limiter database: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _make_key(self, identifier: str, action: str) -> str:
        """Create storage key."""
        return f"ratelimit:{action}:{identifier}"
    
    def _make_block_key(self, identifier: str, action: str) -> str:
        """Create block key."""
        return f"blocked:{action}:{identifier}"
    
    def check_rate_limit(
        self,
        identifier: str,
        action: str = 'api',
        custom_limit: Optional[Dict[str, int]] = None
    ) -> Tuple[bool, int]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: IP address or user ID
            action: Action type (login, api, password_reset, etc.)
            custom_limit: Custom limit configuration
            
        Returns:
            Tuple of (allowed: bool, retry_after: int)
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
            IPBlockedError: If IP is blocked
            
        Example:
            >>> limiter = RateLimiter()
            >>> allowed, retry = limiter.check_rate_limit("192.168.1.1", "login")
            >>> if not allowed:
            ...     print(f"Rate limited. Retry after {retry} seconds")
        """
        try:
            # Check if blocked
            block_key = self._make_block_key(identifier, action)
            if self._is_blocked(block_key):
                ttl = self._get_ttl(block_key)
                raise IPBlockedError(
                    f"Access blocked for {action}. Retry after {ttl} seconds."
                )
            
            # Get rate limit configuration
            limit_config = custom_limit or self.DEFAULT_LIMITS.get(
                action,
                self.DEFAULT_LIMITS['api']
            )
            
            key = self._make_key(identifier, action)
            current_count = self._get_count(key)
            
            # Check if limit exceeded
            if current_count >= limit_config['requests']:
                # Block if threshold reached
                self._block(
                    block_key,
                    limit_config['block_duration']
                )
                
                # Log suspicious activity
                self._log_suspicious_activity(
                    identifier,
                    action,
                    current_count,
                    "Rate limit exceeded"
                )
                
                raise RateLimitExceededError(
                    retry_after=limit_config['block_duration'],
                    message=f"Rate limit exceeded for {action}"
                )
            
            # Increment counter
            self._increment(key, limit_config['window'])
            
            return True, 0
            
        except (RateLimitExceededError, IPBlockedError):
            raise
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Fail open - allow request if error occurs
            return True, 0
    
    def record_failed_attempt(
        self,
        identifier: str,
        action: str = 'login',
        reason: str = "Failed attempt"
    ):
        """
        Record a failed attempt (e.g., failed login).
        
        Args:
            identifier: IP address or user ID
            action: Action type
            reason: Failure reason
            
        Example:
            >>> limiter = RateLimiter()
            >>> limiter.record_failed_attempt("192.168.1.1", "login", "Invalid password")
        """
        try:
            key = self._make_key(identifier, f"{action}_failed")
            limit_config = self.DEFAULT_LIMITS.get(action, self.DEFAULT_LIMITS['login'])
            
            count = self._increment(key, limit_config['window'])
            
            # Log the attempt
            self._log_suspicious_activity(
                identifier,
                action,
                count,
                reason
            )
            
            # Block if threshold exceeded
            if count >= limit_config['requests']:
                block_key = self._make_block_key(identifier, action)
                self._block(block_key, limit_config['block_duration'])
                
                logger.warning(
                    f"Blocked {identifier} for {action} after {count} failed attempts"
                )
            
        except Exception as e:
            logger.error(f"Error recording failed attempt: {e}")
    
    def reset_limit(self, identifier: str, action: str = 'api'):
        """
        Reset rate limit for identifier.
        
        Args:
            identifier: IP address or user ID
            action: Action type
            
        Example:
            >>> limiter = RateLimiter()
            >>> limiter.reset_limit("192.168.1.1", "login")
        """
        try:
            key = self._make_key(identifier, action)
            self._delete(key)
            
            # Also remove block if exists
            block_key = self._make_block_key(identifier, action)
            self._delete(block_key)
            
            logger.info(f"Reset rate limit for {identifier}:{action}")
            
        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}")
    
    def add_to_whitelist(
        self,
        ip_address: str,
        reason: str = "Trusted IP",
        added_by: Optional[int] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Add IP to whitelist.
        
        Args:
            ip_address: IP address to whitelist
            reason: Reason for whitelisting
            added_by: User ID who added the IP
            expires_at: Expiration datetime
            
        Returns:
            True if successful
            
        Example:
            >>> limiter = RateLimiter()
            >>> limiter.add_to_whitelist("192.168.1.100", "Office IP")
            True
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO ip_access_list 
                (ip_address, list_type, reason, added_by, expires_at)
                VALUES (?, 'whitelist', ?, ?, ?)
            """, (ip_address, reason, added_by, expires_at))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added {ip_address} to whitelist: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding to whitelist: {e}")
            return False
    
    def add_to_blacklist(
        self,
        ip_address: str,
        reason: str = "Suspicious activity",
        added_by: Optional[int] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Add IP to blacklist.
        
        Args:
            ip_address: IP address to blacklist
            reason: Reason for blacklisting
            added_by: User ID who added the IP
            expires_at: Expiration datetime
            
        Returns:
            True if successful
            
        Example:
            >>> limiter = RateLimiter()
            >>> limiter.add_to_blacklist("10.0.0.1", "Brute force attack")
            True
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO ip_access_list 
                (ip_address, list_type, reason, added_by, expires_at)
                VALUES (?, 'blacklist', ?, ?, ?)
            """, (ip_address, reason, added_by, expires_at))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"Added {ip_address} to blacklist: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding to blacklist: {e}")
            return False
    
    def remove_from_list(self, ip_address: str, list_type: str = 'blacklist') -> bool:
        """
        Remove IP from whitelist or blacklist.
        
        Args:
            ip_address: IP address to remove
            list_type: 'whitelist' or 'blacklist'
            
        Returns:
            True if successful
            
        Example:
            >>> limiter = RateLimiter()
            >>> limiter.remove_from_list("10.0.0.1", "blacklist")
            True
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM ip_access_list 
                WHERE ip_address = ? AND list_type = ?
            """, (ip_address, list_type))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Removed {ip_address} from {list_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing from list: {e}")
            return False
    
    def is_whitelisted(self, ip_address: str) -> bool:
        """
        Check if IP is whitelisted.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if whitelisted
            
        Example:
            >>> limiter = RateLimiter()
            >>> limiter.is_whitelisted("192.168.1.100")
            False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM ip_access_list 
                WHERE ip_address = ? 
                AND list_type = 'whitelist'
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, (ip_address,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking whitelist: {e}")
            return False
    
    def is_blacklisted(self, ip_address: str) -> bool:
        """
        Check if IP is blacklisted.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if blacklisted
            
        Example:
            >>> limiter = RateLimiter()
            >>> limiter.is_blacklisted("10.0.0.1")
            False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM ip_access_list 
                WHERE ip_address = ? 
                AND list_type = 'blacklist'
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, (ip_address,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking blacklist: {e}")
            return False
    
    def get_access_lists(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all whitelist and blacklist entries.
        
        Returns:
            Dictionary with 'whitelist' and 'blacklist' keys
            
        Example:
            >>> limiter = RateLimiter()
            >>> lists = limiter.get_access_lists()
            >>> print(lists['whitelist'])
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT ip_address, list_type, reason, created_at, expires_at
                FROM ip_access_list
                WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
                ORDER BY list_type, created_at DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            result = {'whitelist': [], 'blacklist': []}
            for row in rows:
                entry = {
                    'ip_address': row['ip_address'],
                    'reason': row['reason'],
                    'created_at': row['created_at'],
                    'expires_at': row['expires_at']
                }
                result[row['list_type']].append(entry)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting access lists: {e}")
            return {'whitelist': [], 'blacklist': []}
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _get_count(self, key: str) -> int:
        """Get current count for key."""
        try:
            if isinstance(self.storage, InMemoryStorage):
                value = self.storage.get(key)
                return int(value) if value else 0
            else:
                value = self.storage.get(key)
                return int(value) if value else 0
        except Exception:
            return 0
    
    def _increment(self, key: str, ttl: int) -> int:
        """Increment counter with TTL."""
        try:
            if isinstance(self.storage, InMemoryStorage):
                count = self.storage.incr(key)
                self.storage.set(key, count, ttl)
                return count
            else:
                pipe = self.storage.pipeline()
                pipe.incr(key)
                pipe.expire(key, ttl)
                result = pipe.execute()
                return result[0]
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
            return 0
    
    def _delete(self, key: str):
        """Delete key."""
        try:
            if isinstance(self.storage, InMemoryStorage):
                self.storage.delete(key)
            else:
                self.storage.delete(key)
        except Exception as e:
            logger.error(f"Error deleting key: {e}")
    
    def _is_blocked(self, key: str) -> bool:
        """Check if identifier is blocked."""
        try:
            if isinstance(self.storage, InMemoryStorage):
                return self.storage.exists(key)
            else:
                return self.storage.exists(key) == 1
        except Exception:
            return False
    
    def _block(self, key: str, duration: int):
        """Block identifier for duration."""
        try:
            if isinstance(self.storage, InMemoryStorage):
                self.storage.set(key, "blocked", duration)
            else:
                self.storage.setex(key, duration, "blocked")
        except Exception as e:
            logger.error(f"Error blocking: {e}")
    
    def _get_ttl(self, key: str) -> int:
        """Get TTL for key."""
        try:
            if isinstance(self.storage, InMemoryStorage):
                entry = self.storage.data.get(key)
                if entry and 'expires_at' in entry:
                    return max(0, int(entry['expires_at'] - time.time()))
                return 0
            else:
                ttl = self.storage.ttl(key)
                return max(0, ttl)
        except Exception:
            return 0
    
    def _log_suspicious_activity(
        self,
        identifier: str,
        action: str,
        count: int,
        reason: str
    ):
        """Log suspicious activity to database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if login_attempts table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='login_attempts'
            """)
            
            if cursor.fetchone():
                cursor.execute("""
                    INSERT INTO login_attempts 
                    (email, ip_address, success, failure_reason, attempted_at)
                    VALUES (?, ?, 0, ?, CURRENT_TIMESTAMP)
                """, (identifier, identifier, f"{reason} (count: {count})"))
                
                conn.commit()
            
            conn.close()
            
            logger.warning(
                f"Suspicious activity: {identifier} - {action} - "
                f"{reason} (count: {count})"
            )
            
        except Exception as e:
            logger.error(f"Error logging suspicious activity: {e}")


# ============================================================================
# UNIT TESTS (as comments for reference)
# ============================================================================

"""
Unit Tests for RateLimiter

import unittest
import tempfile
import os
import time

class TestRateLimiter(unittest.TestCase):
    
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.limiter = RateLimiter(db_path=self.db_path, use_redis=False)
    
    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_rate_limit_within_limit(self):
        # Should allow requests within limit
        for i in range(5):
            allowed, retry = self.limiter.check_rate_limit("192.168.1.1", "login")
            self.assertTrue(allowed)
    
    def test_rate_limit_exceeded(self):
        # Exceed rate limit
        for i in range(5):
            self.limiter.check_rate_limit("192.168.1.2", "login")
        
        # Next request should be blocked
        with self.assertRaises(RateLimitExceededError):
            self.limiter.check_rate_limit("192.168.1.2", "login")
    
    def test_failed_attempts_blocking(self):
        # Record multiple failed attempts
        for i in range(5):
            self.limiter.record_failed_attempt("192.168.1.3", "login")
        
        # Should be blocked
        with self.assertRaises(IPBlockedError):
            self.limiter.check_rate_limit("192.168.1.3", "login")
    
    def test_whitelist(self):
        ip = "192.168.1.100"
        self.limiter.add_to_whitelist(ip, "Test IP")
        self.assertTrue(self.limiter.is_whitelisted(ip))
        self.assertFalse(self.limiter.is_blacklisted(ip))
    
    def test_blacklist(self):
        ip = "10.0.0.1"
        self.limiter.add_to_blacklist(ip, "Malicious IP")
        self.assertTrue(self.limiter.is_blacklisted(ip))
        self.assertFalse(self.limiter.is_whitelisted(ip))
    
    def test_reset_limit(self):
        # Exceed limit
        for i in range(5):
            self.limiter.check_rate_limit("192.168.1.4", "login")
        
        # Reset
        self.limiter.reset_limit("192.168.1.4", "login")
        
        # Should work again
        allowed, retry = self.limiter.check_rate_limit("192.168.1.4", "login")
        self.assertTrue(allowed)

if __name__ == '__main__':
    unittest.main()
"""