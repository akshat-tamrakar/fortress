"""
Cache service for authorization decisions.

This module provides a Redis-based caching layer for authorization decisions,
implementing the caching requirements defined in the Authorization App design.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis-based cache service for authorization decisions.

    Provides methods for getting, setting, and invalidating cached
    authorization decisions with configurable TTL.

    Requirements:
        - 5.1: Cache authorization decisions in Redis with 60-second TTL
        - 5.2: Use cache key format: authz:{principal_id}:{action}:{resource_type}:{resource_id}
        - 5.4: Invalidate all cache entries for a user when attributes change
        - 5.5: Support full cache flush when policies are updated
    """

    def __init__(self) -> None:
        """Initialize Redis client with settings from Django configuration."""
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> redis.Redis:
        """
        Lazy initialization of Redis client.

        Returns:
            redis.Redis: Connected Redis client instance.
        """
        if self._redis is None:
            self._redis = redis.Redis(
                host=getattr(settings, "REDIS_HOST", "127.0.0.1"),
                port=getattr(settings, "REDIS_PORT", 6379),
                db=getattr(settings, "REDIS_DB", 0),
                decode_responses=True,
            )
        return self._redis

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached value by key.

        Args:
            key: The cache key to retrieve.

        Returns:
            The cached dictionary value if found and valid, None otherwise.
        """
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except redis.RedisError as e:
            logger.warning(f"Redis get error for key {key}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error for key {key}: {e}")
            return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> bool:
        """
        Set cached value with TTL.

        Args:
            key: The cache key to set.
            value: The dictionary value to cache.
            ttl: Time-to-live in seconds. Defaults to CACHE_TTL_AUTHORIZATION (60s).

        Returns:
            True if the value was successfully cached, False otherwise.
        """
        if ttl is None:
            ttl = getattr(settings, "CACHE_TTL_AUTHORIZATION", 60)

        try:
            self.redis.setex(key, ttl, json.dumps(value))
            return True
        except redis.RedisError as e:
            logger.warning(f"Redis set error for key {key}: {e}")
            return False
        except (TypeError, ValueError) as e:
            logger.warning(f"JSON encode error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete cached value by key.

        Args:
            key: The cache key to delete.

        Returns:
            True if the key was deleted (or didn't exist), False on error.
        """
        try:
            self.redis.delete(key)
            return True
        except redis.RedisError as e:
            logger.warning(f"Redis delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Uses SCAN to iterate through keys matching the pattern and deletes them
        in batches. This is used for cache invalidation when user attributes
        change or when policies are updated.

        Args:
            pattern: Redis glob-style pattern (e.g., "authz:user123:*").

        Returns:
            The number of keys deleted.
        """
        deleted_count = 0
        cursor = 0

        try:
            while True:
                cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted_count += self.redis.delete(*keys)
                if cursor == 0:
                    break
            return deleted_count
        except redis.RedisError as e:
            logger.warning(f"Redis delete_pattern error for pattern {pattern}: {e}")
            return deleted_count


# Singleton instance for use across the application
cache_service = CacheService()
