"""
PetroFlow Redis Rate Limiter
=============================

Distributed rate limiting implementation using Redis with advanced features:
- Token bucket algorithm for smooth rate limiting
- Sliding window counter for accurate tracking
- Multiple rate limit tiers (per-user, per-IP, per-endpoint)
- Fallback to in-memory storage when Redis unavailable
- Integration with existing rate_limiter.py
- Production-ready with comprehensive error handling

Features:
- Distributed rate limiting across multiple instances
- Token bucket algorithm with configurable refill rates
- Sliding window counter for precise rate limiting
- Multi-tier rate limiting (user, IP, endpoint, global)
- Automatic failover to in-memory storage
- Audit logging integration
- Performance optimized with Lua scripts

Author: Bob
Version: 1.0.0
"""

import logging
import time
import json
from typing import Optional, Dict, List, Tuple, Any, Union
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock
import hashlib

# Try to import Redis
try:
    import redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    RedisError = Exception
    RedisConnectionError = Exception

# Import audit logging
try:
    from core.audit_logging_service import AuditLogger, SessionContext
    AUDIT_LOGGING_AVAILABLE = True
except ImportError:
    AUDIT_LOGGING_AVAILABLE = False
    AuditLogger = None
    SessionContext = None

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
    def __init__(self, retry_after: int, tier: str = "default", message: str = "Rate limit exceeded"):
        self.retry_after = retry_after
        self.tier = tier
        super().__init__(f"{message} (tier: {tier}). Retry after {retry_after} seconds.")


class DistributedLockError(RateLimitError):
    """Raised when distributed lock cannot be acquired."""
    pass


# ============================================================================
# LUA SCRIPTS FOR ATOMIC OPERATIONS
# ============================================================================

# Token bucket algorithm with Lua script for atomic operations
TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local requested = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

-- Calculate tokens to add based on time elapsed
local elapsed = now - last_refill
local tokens_to_add = elapsed * refill_rate
tokens = math.min(capacity, tokens + tokens_to_add)

-- Check if we have enough tokens
if tokens >= requested then
    tokens = tokens - requested
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {1, tokens}
else
    -- Calculate retry after time
    local tokens_needed = requested - tokens
    local retry_after = math.ceil(tokens_needed / refill_rate)
    return {0, retry_after}
end
"""

# Sliding window counter with Lua script
SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

-- Remove old entries outside the window
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

-- Count current entries
local count = redis.call('ZCARD', key)

if count < limit then
    -- Add new entry
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, window)
    return {1, count + 1, limit - count - 1}
else
    -- Get oldest entry to calculate retry time
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = math.ceil((tonumber(oldest[2]) + window) - now)
    return {0, count, 0, retry_after}
end
"""


# ============================================================================
# IN-MEMORY FALLBACK STORAGE
# ============================================================================

class InMemoryRateLimitStorage:
    """
    In-memory storage for rate limiting when Redis is unavailable.
    Thread-safe implementation with token bucket and sliding window support.
    """
    
    def __init__(self):
        self.token_buckets: Dict[str, Dict[str, Any]] = {}
        self.sliding_windows: Dict[str, List[float]] = defaultdict(list)
        self.lock = Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        with self.lock:
            # Cleanup token buckets
            expired_buckets = [
                key for key, bucket in self.token_buckets.items()
                if bucket.get('expires_at', 0) < current_time
            ]
            for key in expired_buckets:
                del self.token_buckets[key]
            
            # Cleanup sliding windows
            expired_windows = [
                key for key, entries in self.sliding_windows.items()
                if not entries or max(entries) < current_time - 3600
            ]
            for key in expired_windows:
                del self.sliding_windows[key]
            
            self._last_cleanup = current_time
            logger.debug(f"Cleaned up {len(expired_buckets)} buckets and {len(expired_windows)} windows")
    
    def token_bucket_check(
        self,
        key: str,
        capacity: int,
        refill_rate: float,
        requested: int,
        now: float
    ) -> Tuple[bool, Union[int, float]]:
        """Check token bucket and consume tokens if available."""
        self._cleanup_expired()
        
        with self.lock:
            bucket = self.token_buckets.get(key, {
                'tokens': capacity,
                'last_refill': now,
                'expires_at': now + 3600
            })
            
            # Calculate tokens to add
            elapsed = now - bucket['last_refill']
            tokens_to_add = elapsed * refill_rate
            tokens = min(capacity, bucket['tokens'] + tokens_to_add)
            
            # Check if we have enough tokens
            if tokens >= requested:
                tokens -= requested
                self.token_buckets[key] = {
                    'tokens': tokens,
                    'last_refill': now,
                    'expires_at': now + 3600
                }
                return True, tokens
            else:
                # Calculate retry after
                tokens_needed = requested - tokens
                retry_after = tokens_needed / refill_rate
                return False, int(retry_after) + 1
    
    def sliding_window_check(
        self,
        key: str,
        window: int,
        limit: int,
        now: float
    ) -> Tuple[bool, int, int, int]:
        """Check sliding window and add entry if within limit."""
        self._cleanup_expired()
        
        with self.lock:
            entries = self.sliding_windows[key]
            
            # Remove old entries
            cutoff = now - window
            entries = [e for e in entries if e > cutoff]
            self.sliding_windows[key] = entries
            
            count = len(entries)
            
            if count < limit:
                entries.append(now)
                return True, count + 1, limit - count - 1, 0
            else:
                # Calculate retry after
                oldest = min(entries) if entries else now
                retry_after = int((oldest + window) - now) + 1
                return False, count, 0, retry_after
    
    def clear(self):
        """Clear all data."""
        with self.lock:
            self.token_buckets.clear()
            self.sliding_windows.clear()


# ============================================================================
# REDIS RATE LIMITER CLASS
# ============================================================================

class RedisRateLimiter:
    """
    Distributed Rate Limiter using Redis
    
    Provides advanced rate limiting with multiple algorithms and tiers:
    - Token bucket for smooth rate limiting
    - Sliding window for accurate counting
    - Multi-tier support (user, IP, endpoint, global)
    - Automatic failover to in-memory storage
    - Comprehensive audit logging
    
    Attributes:
        redis_client: Redis client instance
        fallback_storage: In-memory storage for failover
        use_redis: Whether Redis is currently available
        audit_logger: Audit logging instance
    """
    
    # Rate limit tier configurations
    TIER_CONFIGS = {
        'user': {
            'capacity': 1000,
            'refill_rate': 10.0,  # tokens per second
            'window': 60,
            'limit': 100
        },
        'ip': {
            'capacity': 500,
            'refill_rate': 5.0,
            'window': 60,
            'limit': 50
        },
        'endpoint': {
            'capacity': 2000,
            'refill_rate': 20.0,
            'window': 60,
            'limit': 200
        },
        'global': {
            'capacity': 10000,
            'refill_rate': 100.0,
            'window': 60,
            'limit': 1000
        }
    }
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        use_redis: bool = True,
        key_prefix: str = 'petroflow:ratelimit'
    ):
        """
        Initialize Redis Rate Limiter.
        
        Args:
            redis_url: Redis connection URL (overrides host/port/db)
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
            redis_password: Redis password
            use_redis: Whether to attempt Redis connection
            key_prefix: Prefix for all Redis keys
        """
        self.key_prefix = key_prefix
        self.redis_client = None
        self.use_redis = False
        self.fallback_storage = InMemoryRateLimitStorage()
        self.token_bucket_script = None
        self.sliding_window_script = None
        
        # Initialize audit logger
        if AUDIT_LOGGING_AVAILABLE:
            self.audit_logger = AuditLogger()
        else:
            self.audit_logger = None
        
        # Try to connect to Redis
        if use_redis and REDIS_AVAILABLE:
            try:
                if redis_url:
                    self.redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=2,
                        socket_timeout=2
                    )
                else:
                    self.redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        password=redis_password,
                        decode_responses=True,
                        socket_connect_timeout=2,
                        socket_timeout=2
                    )
                
                # Test connection
                self.redis_client.ping()
                
                # Register Lua scripts
                self.token_bucket_script = self.redis_client.register_script(TOKEN_BUCKET_SCRIPT)
                self.sliding_window_script = self.redis_client.register_script(SLIDING_WINDOW_SCRIPT)
                
                self.use_redis = True
                logger.info("Redis rate limiter initialized successfully")
                
                if self.audit_logger:
                    self.audit_logger.log_system_event(
                        action="REDIS_RATELIMIT_INIT",
                        details={"status": "success", "backend": "redis"}
                    )
                
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
                self.use_redis = False
                
                if self.audit_logger:
                    self.audit_logger.log_system_event(
                        action="REDIS_RATELIMIT_INIT",
                        details={"status": "fallback", "backend": "memory", "error": str(e)}
                    )
        else:
            logger.info("Redis rate limiter using in-memory storage")
            
            if self.audit_logger:
                self.audit_logger.log_system_event(
                    action="REDIS_RATELIMIT_INIT",
                    details={"status": "success", "backend": "memory"}
                )
    
    def _make_key(self, tier: str, identifier: str, action: str = '') -> str:
        """Create Redis key."""
        parts = [self.key_prefix, tier, identifier]
        if action:
            parts.append(action)
        return ':'.join(parts)
    
    def check_rate_limit_token_bucket(
        self,
        identifier: str,
        tier: str = 'user',
        action: str = '',
        capacity: Optional[int] = None,
        refill_rate: Optional[float] = None,
        requested: int = 1
    ) -> Tuple[bool, Union[int, float]]:
        """
        Check rate limit using token bucket algorithm.
        
        Args:
            identifier: User ID, IP address, or other identifier
            tier: Rate limit tier (user, ip, endpoint, global)
            action: Specific action being rate limited
            capacity: Token bucket capacity (overrides tier default)
            refill_rate: Tokens per second refill rate (overrides tier default)
            requested: Number of tokens requested
            
        Returns:
            Tuple of (allowed: bool, remaining_or_retry: Union[int, float])
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
            
        Example:
            >>> limiter = RedisRateLimiter()
            >>> allowed, remaining = limiter.check_rate_limit_token_bucket("user123", "user")
            >>> if not allowed:
            ...     print(f"Rate limited. Retry after {remaining} seconds")
        """
        try:
            # Get tier configuration
            # Refactored by Jhon Villegas
            config = self.TIER_CONFIGS.get(tier, self.TIER_CONFIGS['user'])
            capacity = capacity if capacity is not None else config['capacity']
            refill_rate = refill_rate if refill_rate is not None else config['refill_rate']
            
            key = self._make_key(tier, identifier, action)
            now = time.time()
            
            if self.use_redis and self.redis_client:
                try:
                    # Execute Lua script atomically
                    result = self.token_bucket_script(
                        keys=[key],
                        args=[capacity, refill_rate, requested, now]
                    )
                    
                    allowed = bool(result[0])
                    value = result[1]
                    
                    if not allowed:
                        # Log rate limit exceeded
                        if self.audit_logger:
                            self.audit_logger.log_security_event(
                                action="RATE_LIMIT_EXCEEDED",
                                details={
                                    "tier": tier,
                                    "identifier": identifier,
                                    "action": action,
                                    "algorithm": "token_bucket",
                                    "retry_after": value
                                }
                            )
                        
                        raise RateLimitExceededError(
                            retry_after=int(value),
                            tier=tier,
                            message=f"Token bucket rate limit exceeded"
                        )
                    
                    return True, value
                    
                except (RedisError, RedisConnectionError) as e:
                    logger.warning(f"Redis error, falling back to in-memory: {e}")
                    self.use_redis = False
                    # Fall through to in-memory
            
            # Use in-memory fallback
            allowed, value = self.fallback_storage.token_bucket_check(
                key, capacity, refill_rate, requested, now
            )
            
            if not allowed:
                if self.audit_logger:
                    self.audit_logger.log_security_event(
                        action="RATE_LIMIT_EXCEEDED",
                        details={
                            "tier": tier,
                            "identifier": identifier,
                            "action": action,
                            "algorithm": "token_bucket",
                            "retry_after": value,
                            "backend": "memory"
                        }
                    )
                
                raise RateLimitExceededError(
                    retry_after=int(value),
                    tier=tier,
                    message=f"Token bucket rate limit exceeded"
                )
            
            return True, value
            
        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"Error checking token bucket rate limit: {e}")
            # Fail open - allow request if error occurs
            return True, 0
    
    def check_rate_limit_sliding_window(
        self,
        identifier: str,
        tier: str = 'user',
        action: str = '',
        window: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit using sliding window counter.
        
        Args:
            identifier: User ID, IP address, or other identifier
            tier: Rate limit tier (user, ip, endpoint, global)
            action: Specific action being rate limited
            window: Time window in seconds (overrides tier default)
            limit: Maximum requests in window (overrides tier default)
            
        Returns:
            Tuple of (allowed: bool, current_count: int, remaining: int)
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
            
        Example:
            >>> limiter = RedisRateLimiter()
            >>> allowed, count, remaining = limiter.check_rate_limit_sliding_window("192.168.1.1", "ip")
            >>> print(f"Used {count} of {count + remaining} requests")
        """
        try:
            # Get tier configuration
            # Refactored by Jhon Villegas
            config = self.TIER_CONFIGS.get(tier, self.TIER_CONFIGS['user'])
            window = window if window is not None else config['window']
            limit = limit if limit is not None else config['limit']
            
            key = self._make_key(tier, identifier, action)
            now = time.time()
            
            if self.use_redis and self.redis_client:
                try:
                    # Execute Lua script atomically
                    result = self.sliding_window_script(
                        keys=[key],
                        args=[window, limit, now]
                    )
                    
                    allowed = bool(result[0])
                    count = int(result[1])
                    remaining = int(result[2]) if allowed else 0
                    retry_after = int(result[3]) if not allowed else 0
                    
                    if not allowed:
                        if self.audit_logger:
                            self.audit_logger.log_security_event(
                                action="RATE_LIMIT_EXCEEDED",
                                details={
                                    "tier": tier,
                                    "identifier": identifier,
                                    "action": action,
                                    "algorithm": "sliding_window",
                                    "count": count,
                                    "limit": limit,
                                    "retry_after": retry_after
                                }
                            )
                        
                        raise RateLimitExceededError(
                            retry_after=retry_after,
                            tier=tier,
                            message=f"Sliding window rate limit exceeded ({count}/{limit})"
                        )
                    
                    return True, count, remaining
                    
                except (RedisError, RedisConnectionError) as e:
                    logger.warning(f"Redis error, falling back to in-memory: {e}")
                    self.use_redis = False
                    # Fall through to in-memory
            
            # Use in-memory fallback
            allowed, count, remaining, retry_after = self.fallback_storage.sliding_window_check(
                key, window, limit, now
            )
            
            if not allowed:
                if self.audit_logger:
                    self.audit_logger.log_security_event(
                        action="RATE_LIMIT_EXCEEDED",
                        details={
                            "tier": tier,
                            "identifier": identifier,
                            "action": action,
                            "algorithm": "sliding_window",
                            "count": count,
                            "limit": limit,
                            "retry_after": retry_after,
                            "backend": "memory"
                        }
                    )
                
                raise RateLimitExceededError(
                    retry_after=retry_after,
                    tier=tier,
                    message=f"Sliding window rate limit exceeded ({count}/{limit})"
                )
            
            return True, count, remaining
            
        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"Error checking sliding window rate limit: {e}")
            # Fail open - allow request if error occurs
            return True, 0, 0
    
    def check_multi_tier(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        action: str = '',
        algorithm: str = 'token_bucket'
    ) -> Dict[str, Any]:
        """
        Check rate limits across multiple tiers.
        
        Args:
            user_id: User identifier
            ip_address: IP address
            endpoint: API endpoint
            action: Specific action
            algorithm: 'token_bucket' or 'sliding_window'
            
        Returns:
            Dictionary with tier results
            
        Raises:
            RateLimitExceededError: If any tier limit exceeded
            
        Example:
            >>> limiter = RedisRateLimiter()
            >>> result = limiter.check_multi_tier(
            ...     user_id="user123",
            ...     ip_address="192.168.1.1",
            ...     endpoint="/api/data"
            ... )
        """
        results = {}
        
        try:
            # Check user tier
            if user_id:
                if algorithm == 'token_bucket':
                    allowed, value = self.check_rate_limit_token_bucket(user_id, 'user', action)
                    results['user'] = {'allowed': allowed, 'remaining': value}
                else:
                    allowed, count, remaining = self.check_rate_limit_sliding_window(user_id, 'user', action)
                    results['user'] = {'allowed': allowed, 'count': count, 'remaining': remaining}
            
            # Check IP tier
            if ip_address:
                if algorithm == 'token_bucket':
                    allowed, value = self.check_rate_limit_token_bucket(ip_address, 'ip', action)
                    results['ip'] = {'allowed': allowed, 'remaining': value}
                else:
                    allowed, count, remaining = self.check_rate_limit_sliding_window(ip_address, 'ip', action)
                    results['ip'] = {'allowed': allowed, 'count': count, 'remaining': remaining}
            
            # Check endpoint tier
            if endpoint:
                if algorithm == 'token_bucket':
                    allowed, value = self.check_rate_limit_token_bucket(endpoint, 'endpoint', action)
                    results['endpoint'] = {'allowed': allowed, 'remaining': value}
                else:
                    allowed, count, remaining = self.check_rate_limit_sliding_window(endpoint, 'endpoint', action)
                    results['endpoint'] = {'allowed': allowed, 'count': count, 'remaining': remaining}
            
            # Check global tier
            if algorithm == 'token_bucket':
                allowed, value = self.check_rate_limit_token_bucket('global', 'global', action)
                results['global'] = {'allowed': allowed, 'remaining': value}
            else:
                allowed, count, remaining = self.check_rate_limit_sliding_window('global', 'global', action)
                results['global'] = {'allowed': allowed, 'count': count, 'remaining': remaining}
            
            return results
            
        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"Error checking multi-tier rate limits: {e}")
            return {}
    
    def reset_limit(self, identifier: str, tier: str = 'user', action: str = ''):
        """
        Reset rate limit for identifier.
        
        Args:
            identifier: User ID, IP address, or other identifier
            tier: Rate limit tier
            action: Specific action
            
        Example:
            >>> limiter = RedisRateLimiter()
            >>> limiter.reset_limit("user123", "user")
        """
        try:
            key = self._make_key(tier, identifier, action)
            
            if self.use_redis and self.redis_client:
                try:
                    self.redis_client.delete(key)
                except (RedisError, RedisConnectionError):
                    self.use_redis = False
            
            # Also clear from fallback storage
            if hasattr(self.fallback_storage, 'token_buckets'):
                self.fallback_storage.token_buckets.pop(key, None)
            if hasattr(self.fallback_storage, 'sliding_windows'):
                self.fallback_storage.sliding_windows.pop(key, None)
            
            logger.info(f"Reset rate limit for {tier}:{identifier}:{action}")
            
            if self.audit_logger:
                self.audit_logger.log_system_event(
                    action="RATE_LIMIT_RESET",
                    details={"tier": tier, "identifier": identifier, "action": action}
                )
            
        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}")
    
    def get_stats(self, identifier: str, tier: str = 'user', action: str = '') -> Dict[str, Any]:
        """
        Get rate limit statistics for identifier.
        
        Args:
            identifier: User ID, IP address, or other identifier
            tier: Rate limit tier
            action: Specific action
            
        Returns:
            Dictionary with statistics
            
        Example:
            >>> limiter = RedisRateLimiter()
            >>> stats = limiter.get_stats("user123", "user")
            >>> print(f"Tokens remaining: {stats.get('tokens', 0)}")
        """
        try:
            key = self._make_key(tier, identifier, action)
            stats = {}
            
            if self.use_redis and self.redis_client:
                try:
                    # Get token bucket data
                    bucket_data = self.redis_client.hgetall(key)
                    if bucket_data:
                        stats['tokens'] = float(bucket_data.get('tokens', 0))
                        stats['last_refill'] = float(bucket_data.get('last_refill', 0))
                    
                    # Get sliding window count
                    window_count = self.redis_client.zcard(key)
                    if window_count:
                        stats['window_count'] = window_count
                    
                    # Get TTL
                    ttl = self.redis_client.ttl(key)
                    if ttl > 0:
                        stats['ttl'] = ttl
                    
                except (RedisError, RedisConnectionError):
                    self.use_redis = False
            
            # Get from fallback storage if Redis unavailable
            if not stats:
                if key in self.fallback_storage.token_buckets:
                    bucket = self.fallback_storage.token_buckets[key]
                    stats['tokens'] = bucket.get('tokens', 0)
                    stats['last_refill'] = bucket.get('last_refill', 0)
                
                if key in self.fallback_storage.sliding_windows:
                    stats['window_count'] = len(self.fallback_storage.sliding_windows[key])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting rate limit stats: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of rate limiter.
        
        Returns:
            Dictionary with health status
            
        Example:
            >>> limiter = RedisRateLimiter()
            >>> health = limiter.health_check()
            >>> print(f"Backend: {health['backend']}")
        """
        health = {
            'backend': 'redis' if self.use_redis else 'memory',
            'redis_available': REDIS_AVAILABLE,
            'redis_connected': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.ping()
                health['redis_connected'] = True
                
                # Get Redis info
                info = self.redis_client.info('stats')
                health['redis_stats'] = {
                    'total_commands_processed': info.get('total_commands_processed', 0),
                    'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec', 0)
                }
            except Exception as e:
                health['redis_error'] = str(e)
                self.use_redis = False
        
        return health


# ============================================================================
# INTEGRATION WITH EXISTING RATE LIMITER
# ============================================================================

def create_rate_limiter(config: Optional[Dict[str, Any]] = None) -> RedisRateLimiter:
    """
    Factory function to create rate limiter instance.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        RedisRateLimiter instance
        
    Example:
        >>> config = {
        ...     'redis_url': 'redis://localhost:6379/0',
        ...     'use_redis': True
        ... }
        >>> limiter = create_rate_limiter(config)
    """
    config = config or {}
    return RedisRateLimiter(**config)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example usage
    limiter = RedisRateLimiter(redis_host='localhost', redis_port=6379)
    
    # Check token bucket rate limit
    try:
        allowed, remaining = limiter.check_rate_limit_token_bucket("user123", "user")
        print(f"Token bucket: Allowed={allowed}, Remaining={remaining}")
    except RateLimitExceededError as e:
        print(f"Rate limited: {e}")
    
    # Check sliding window rate limit
    try:
        allowed, count, remaining = limiter.check_rate_limit_sliding_window("192.168.1.1", "ip")
        print(f"Sliding window: Allowed={allowed}, Count={count}, Remaining={remaining}")
    except RateLimitExceededError as e:
        print(f"Rate limited: {e}")
    
    # Multi-tier check
    try:
        results = limiter.check_multi_tier(
            user_id="user123",
            ip_address="192.168.1.1",
            endpoint="/api/data"
        )
        print(f"Multi-tier results: {results}")
    except RateLimitExceededError as e:
        print(f"Rate limited: {e}")
    
    # Health check
    health = limiter.health_check()
    print(f"Health: {health}")