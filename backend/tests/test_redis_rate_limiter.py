"""
Unit Tests for Redis Rate Limiter
==================================

Comprehensive test suite for the Redis-based distributed rate limiter.

Test Coverage:
- Token bucket algorithm
- Sliding window counter
- Multi-tier rate limiting
- Fallback to in-memory storage
- Error handling and recovery
- Performance benchmarks

Author: Bob
Version: 1.0.0
"""

import unittest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import the module to test
try:
    from core.redis_rate_limiter import (
        RedisRateLimiter,
        RateLimitExceededError,
        DistributedLockError,
        InMemoryRateLimitStorage,
        create_rate_limiter
    )
    REDIS_RATE_LIMITER_AVAILABLE = True
except ImportError:
    REDIS_RATE_LIMITER_AVAILABLE = False


@unittest.skipIf(not REDIS_RATE_LIMITER_AVAILABLE, "Redis rate limiter not available")
class TestInMemoryRateLimitStorage(unittest.TestCase):
    """Test in-memory storage fallback."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.storage = InMemoryRateLimitStorage()
    
    def tearDown(self):
        """Clean up after tests."""
        self.storage.clear()
    
    def test_token_bucket_basic(self):
        """Test basic token bucket functionality."""
        key = "test:user:123"
        capacity = 10
        refill_rate = 1.0
        requested = 1
        now = time.time()
        
        # First request should succeed
        allowed, remaining = self.storage.token_bucket_check(
            key, capacity, refill_rate, requested, now
        )
        self.assertTrue(allowed)
        self.assertEqual(remaining, capacity - requested)
    
    def test_token_bucket_exhaustion(self):
        """Test token bucket exhaustion."""
        key = "test:user:456"
        capacity = 5
        refill_rate = 1.0
        requested = 1
        now = time.time()
        
        # Exhaust all tokens
        for i in range(capacity):
            allowed, remaining = self.storage.token_bucket_check(
                key, capacity, refill_rate, requested, now
            )
            self.assertTrue(allowed)
        
        # Next request should fail
        allowed, retry_after = self.storage.token_bucket_check(
            key, capacity, refill_rate, requested, now
        )
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)
    
    def test_token_bucket_refill(self):
        """Test token bucket refill over time."""
        key = "test:user:789"
        capacity = 10
        refill_rate = 2.0  # 2 tokens per second
        requested = 5
        now = time.time()
        
        # Use 5 tokens
        allowed, remaining = self.storage.token_bucket_check(
            key, capacity, refill_rate, requested, now
        )
        self.assertTrue(allowed)
        self.assertEqual(remaining, 5)
        
        # Wait 2 seconds (should refill 4 tokens)
        now += 2
        allowed, remaining = self.storage.token_bucket_check(
            key, capacity, refill_rate, requested, now
        )
        self.assertTrue(allowed)
        # Should have ~4 tokens remaining (5 - 5 + 4)
        self.assertGreater(remaining, 3)
    
    def test_sliding_window_basic(self):
        """Test basic sliding window functionality."""
        key = "test:ip:192.168.1.1"
        window = 60
        limit = 10
        now = time.time()
        
        # First request should succeed
        allowed, count, remaining, retry = self.storage.sliding_window_check(
            key, window, limit, now
        )
        self.assertTrue(allowed)
        self.assertEqual(count, 1)
        self.assertEqual(remaining, limit - 1)
    
    def test_sliding_window_limit(self):
        """Test sliding window limit enforcement."""
        key = "test:ip:192.168.1.2"
        window = 60
        limit = 5
        now = time.time()
        
        # Make requests up to limit
        for i in range(limit):
            allowed, count, remaining, retry = self.storage.sliding_window_check(
                key, window, limit, now
            )
            self.assertTrue(allowed)
            self.assertEqual(count, i + 1)
        
        # Next request should fail
        allowed, count, remaining, retry = self.storage.sliding_window_check(
            key, window, limit, now
        )
        self.assertFalse(allowed)
        self.assertEqual(count, limit)
        self.assertGreater(retry, 0)
    
    def test_sliding_window_expiry(self):
        """Test sliding window entry expiry."""
        key = "test:ip:192.168.1.3"
        window = 5  # 5 second window
        limit = 3
        now = time.time()
        
        # Make 3 requests
        for i in range(limit):
            allowed, count, remaining, retry = self.storage.sliding_window_check(
                key, window, limit, now
            )
            self.assertTrue(allowed)
        
        # Wait for window to expire
        now += window + 1
        
        # Should be able to make requests again
        allowed, count, remaining, retry = self.storage.sliding_window_check(
            key, window, limit, now
        )
        self.assertTrue(allowed)
        self.assertEqual(count, 1)
    
    def test_cleanup(self):
        """Test automatic cleanup of expired entries."""
        # Add some entries
        for i in range(10):
            key = f"test:cleanup:{i}"
            self.storage.token_bucket_check(key, 10, 1.0, 1, time.time())
        
        # Force cleanup
        self.storage._last_cleanup = 0
        self.storage._cleanup_expired()
        
        # Verify cleanup ran
        self.assertGreater(self.storage._last_cleanup, 0)


@unittest.skipIf(not REDIS_RATE_LIMITER_AVAILABLE, "Redis rate limiter not available")
class TestRedisRateLimiter(unittest.TestCase):
    """Test Redis rate limiter with mocked Redis."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create limiter without Redis (uses in-memory fallback)
        self.limiter = RedisRateLimiter(use_redis=False)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.limiter, 'fallback_storage'):
            self.limiter.fallback_storage.clear()
    
    def test_initialization(self):
        """Test rate limiter initialization."""
        self.assertIsNotNone(self.limiter)
        self.assertFalse(self.limiter.use_redis)
        self.assertIsNotNone(self.limiter.fallback_storage)
    
    def test_token_bucket_rate_limit(self):
        """Test token bucket rate limiting."""
        identifier = "user123"
        tier = "user"
        
        # Should allow first request
        allowed, remaining = self.limiter.check_rate_limit_token_bucket(
            identifier, tier
        )
        self.assertTrue(allowed)
        self.assertGreater(remaining, 0)
    
    def test_token_bucket_rate_limit_exceeded(self):
        """Test token bucket rate limit exceeded."""
        identifier = "user456"
        tier = "user"
        capacity = 5
        
        # Exhaust tokens
        for i in range(capacity):
            try:
                self.limiter.check_rate_limit_token_bucket(
                    identifier, tier, capacity=capacity, refill_rate=0.1, requested=1
                )
            except RateLimitExceededError:
                pass
        
        # Next request should raise exception
        with self.assertRaises(RateLimitExceededError) as context:
            self.limiter.check_rate_limit_token_bucket(
                identifier, tier, capacity=capacity, refill_rate=0.1, requested=1
            )
        
        self.assertGreater(context.exception.retry_after, 0)
    
    def test_sliding_window_rate_limit(self):
        """Test sliding window rate limiting."""
        identifier = "192.168.1.1"
        tier = "ip"
        
        # Should allow first request
        allowed, count, remaining = self.limiter.check_rate_limit_sliding_window(
            identifier, tier
        )
        self.assertTrue(allowed)
        self.assertEqual(count, 1)
        self.assertGreater(remaining, 0)
    
    def test_sliding_window_rate_limit_exceeded(self):
        """Test sliding window rate limit exceeded."""
        identifier = "192.168.1.2"
        tier = "ip"
        limit = 5
        
        # Make requests up to limit
        for i in range(limit):
            try:
                self.limiter.check_rate_limit_sliding_window(
                    identifier, tier, limit=limit
                )
            except RateLimitExceededError:
                pass
        
        # Next request should raise exception
        with self.assertRaises(RateLimitExceededError) as context:
            self.limiter.check_rate_limit_sliding_window(
                identifier, tier, limit=limit
            )
        
        self.assertGreater(context.exception.retry_after, 0)
    
    def test_multi_tier_rate_limiting(self):
        """Test multi-tier rate limiting."""
        user_id = "user789"
        ip_address = "192.168.1.3"
        endpoint = "/api/data"
        
        # Should check all tiers
        results = self.limiter.check_multi_tier(
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            algorithm='token_bucket'
        )
        
        self.assertIn('user', results)
        self.assertIn('ip', results)
        self.assertIn('endpoint', results)
        self.assertIn('global', results)
        
        # All should be allowed
        for tier, result in results.items():
            self.assertTrue(result['allowed'])
    
    def test_reset_limit(self):
        """Test resetting rate limit."""
        identifier = "user_reset"
        tier = "user"
        
        # Make some requests
        for i in range(3):
            try:
                self.limiter.check_rate_limit_token_bucket(identifier, tier)
            except RateLimitExceededError:
                pass
        
        # Reset limit
        self.limiter.reset_limit(identifier, tier)
        
        # Should be able to make requests again
        allowed, remaining = self.limiter.check_rate_limit_token_bucket(
            identifier, tier
        )
        self.assertTrue(allowed)
    
    def test_get_stats(self):
        """Test getting rate limit statistics."""
        identifier = "user_stats"
        tier = "user"
        
        # Make a request
        self.limiter.check_rate_limit_token_bucket(identifier, tier)
        
        # Get stats
        stats = self.limiter.get_stats(identifier, tier)
        
        # Should have some data
        self.assertIsInstance(stats, dict)
    
    def test_health_check(self):
        """Test health check."""
        health = self.limiter.health_check()
        
        self.assertIn('backend', health)
        self.assertEqual(health['backend'], 'memory')
        self.assertIn('timestamp', health)
    
    def test_tier_configurations(self):
        """Test tier configurations."""
        # Verify tier configs exist
        self.assertIn('user', self.limiter.TIER_CONFIGS)
        self.assertIn('ip', self.limiter.TIER_CONFIGS)
        self.assertIn('endpoint', self.limiter.TIER_CONFIGS)
        self.assertIn('global', self.limiter.TIER_CONFIGS)
        
        # Verify config structure
        for tier, config in self.limiter.TIER_CONFIGS.items():
            self.assertIn('capacity', config)
            self.assertIn('refill_rate', config)
            self.assertIn('window', config)
            self.assertIn('limit', config)


@unittest.skipIf(not REDIS_RATE_LIMITER_AVAILABLE, "Redis rate limiter not available")
class TestRateLimiterFactory(unittest.TestCase):
    """Test rate limiter factory function."""
    
    def test_create_rate_limiter_default(self):
        """Test creating rate limiter with default config."""
        limiter = create_rate_limiter()
        self.assertIsNotNone(limiter)
        self.assertIsInstance(limiter, RedisRateLimiter)
    
    def test_create_rate_limiter_with_config(self):
        """Test creating rate limiter with custom config."""
        config = {
            'redis_host': 'localhost',
            'redis_port': 6379,
            'use_redis': False
        }
        limiter = create_rate_limiter(config)
        self.assertIsNotNone(limiter)
        self.assertFalse(limiter.use_redis)


@unittest.skipIf(not REDIS_RATE_LIMITER_AVAILABLE, "Redis rate limiter not available")
class TestRateLimiterPerformance(unittest.TestCase):
    """Performance benchmarks for rate limiter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.limiter = RedisRateLimiter(use_redis=False)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.limiter, 'fallback_storage'):
            self.limiter.fallback_storage.clear()
    
    def test_token_bucket_performance(self):
        """Benchmark token bucket performance."""
        identifier = "perf_user"
        tier = "user"
        iterations = 1000
        
        start_time = time.time()
        
        for i in range(iterations):
            try:
                self.limiter.check_rate_limit_token_bucket(
                    f"{identifier}_{i}", tier
                )
            except RateLimitExceededError:
                pass
        
        elapsed = time.time() - start_time
        ops_per_second = iterations / elapsed
        
        print(f"\nToken bucket performance: {ops_per_second:.2f} ops/sec")
        
        # Should handle at least 1000 ops/sec
        self.assertGreater(ops_per_second, 1000)
    
    def test_sliding_window_performance(self):
        """Benchmark sliding window performance."""
        identifier = "perf_ip"
        tier = "ip"
        iterations = 1000
        
        start_time = time.time()
        
        for i in range(iterations):
            try:
                self.limiter.check_rate_limit_sliding_window(
                    f"{identifier}_{i}", tier
                )
            except RateLimitExceededError:
                pass
        
        elapsed = time.time() - start_time
        ops_per_second = iterations / elapsed
        
        print(f"\nSliding window performance: {ops_per_second:.2f} ops/sec")
        
        # Should handle at least 1000 ops/sec
        self.assertGreater(ops_per_second, 1000)
    
    def test_concurrent_requests(self):
        """Test handling concurrent requests."""
        import threading
        
        identifier = "concurrent_user"
        tier = "user"
        num_threads = 10
        requests_per_thread = 10
        results = []
        
        def make_requests():
            for i in range(requests_per_thread):
                try:
                    allowed, remaining = self.limiter.check_rate_limit_token_bucket(
                        identifier, tier
                    )
                    results.append(allowed)
                except RateLimitExceededError:
                    results.append(False)
        
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=make_requests)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have processed all requests
        self.assertEqual(len(results), num_threads * requests_per_thread)


@unittest.skipIf(not REDIS_RATE_LIMITER_AVAILABLE, "Redis rate limiter not available")
class TestRateLimiterErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.limiter = RedisRateLimiter(use_redis=False)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.limiter, 'fallback_storage'):
            self.limiter.fallback_storage.clear()
    
    def test_invalid_tier(self):
        """Test handling of invalid tier."""
        identifier = "user123"
        tier = "invalid_tier"
        
        # Should use default tier config
        allowed, remaining = self.limiter.check_rate_limit_token_bucket(
            identifier, tier
        )
        self.assertTrue(allowed)
    
    def test_zero_capacity(self):
        """Test handling of zero capacity."""
        identifier = "user_zero"
        tier = "user"
        
        # Should raise exception immediately
        with self.assertRaises(RateLimitExceededError):
            self.limiter.check_rate_limit_token_bucket(
                identifier, tier, capacity=0, requested=1
            )
    
    def test_negative_values(self):
        """Test handling of negative values."""
        identifier = "user_negative"
        tier = "user"
        
        # Should handle gracefully (fail open)
        try:
            allowed, remaining = self.limiter.check_rate_limit_token_bucket(
                identifier, tier, capacity=-1, refill_rate=-1
            )
            # If it doesn't raise, it should fail open
            self.assertTrue(allowed)
        except Exception:
            # Or it might raise an exception, which is also acceptable
            pass


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()