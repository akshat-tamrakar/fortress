"""
Authorization Service - Orchestration layer for authorization decisions.

This module provides the main orchestration layer for authorization checks,
combining AVP client operations with caching for optimal performance.
It implements fail-closed behavior for security.
"""

import logging
from typing import Any

from rest_framework.exceptions import ValidationError

from apps.authorization.exceptions import (
    AuthorizationError,
    AVPUnavailableError,
)
from apps.authorization.services.avp_client import AVPClient
from apps.authorization.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class AuthzService:
    """
    Authorization service orchestration layer.
    
    Coordinates authorization checks between AVP and the cache layer,
    implementing fail-closed behavior for security.
    
    Requirements:
        - 1.1: Evaluate authorization requests against AVP policies
        - 2.1: Process batch authorization requests
        - 5.2: Use cache key format: authz:{principal_id}:{action}:{resource_type}:{resource_id}
        - 5.3: Return cached decisions without calling AVP when available
        - 6.1, 6.2: Fail-closed behavior on AVP errors
    """

    def __init__(
        self,
        avp_client: AVPClient | None = None,
        cache_service: CacheService | None = None,
    ):
        """
        Initialize AuthzService with dependencies.
        
        Args:
            avp_client: AVP client instance. Uses default singleton if not provided.
            cache_service: Cache service instance. Uses default singleton if not provided.
        """
        from apps.authorization.services.avp_client import avp_client as default_avp
        from apps.authorization.services.cache_service import cache_service as default_cache
        
        self.avp = avp_client or default_avp
        self.cache = cache_service or default_cache

    def _build_cache_key(self, data: dict[str, Any]) -> str:
        """
        Build cache key from authorization request data.
        
        Format: authz:{principal_id}:{action}:{resource_type}:{resource_id}
        
        Args:
            data: Authorization request data with principal, action, and resource.
            
        Returns:
            Cache key string following the required format.
            
        Requirements:
            - 5.2: Cache key format specification
        """
        principal_id = str(data["principal"]["id"])
        action = data["action"]
        resource_type = data["resource"]["type"]
        resource_id = str(data["resource"]["id"])
        return f"authz:{principal_id}:{action}:{resource_type}:{resource_id}"

    def authorize(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Perform single authorization check with caching.
        
        Checks cache first, then calls AVP if no cached decision exists.
        Implements fail-closed behavior: returns DENY on any error.
        
        Args:
            data: Authorization request with principal, action, resource, and optional context.
            
        Returns:
            dict with 'decision' ('ALLOW' or 'DENY') and optional 'reasons'.
            
        Requirements:
            - 1.1: Evaluate authorization requests
            - 5.3: Return cached decisions when available
            - 6.1, 6.2: Fail-closed on errors
        """
        cache_key = self._build_cache_key(data)

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for key: {cache_key}")
            return cached

        # Call AVP
        try:
            result = self.avp.is_authorized(
                principal=data["principal"],
                action=data["action"],
                resource=data["resource"],
                context=data.get("context", {}),
            )
        except AVPUnavailableError as e:
            # Fail closed - log and return DENY
            logger.error(f"AVP unavailable, failing closed: {e}")
            result = {"decision": "DENY", "reasons": ["Service unavailable"]}
        except AuthorizationError as e:
            # Fail closed on any authorization error
            logger.error(f"Authorization error, failing closed: {e}")
            result = {"decision": "DENY", "reasons": ["Authorization error"]}
        except Exception as e:
            # Fail closed on any unexpected error
            logger.error(f"Unexpected error during authorization, failing closed: {e}")
            result = {"decision": "DENY", "reasons": ["Authorization error"]}

        # Cache result (even DENY results to prevent repeated AVP calls)
        self.cache.set(cache_key, result)
        return result

    def batch_authorize(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Perform batch authorization check.
        
        Processes each item individually, handling partial failures.
        Results are returned in the same order as input items.
        
        Args:
            data: Batch request with 'items' list of authorization requests.
            
        Returns:
            dict with 'results' list containing individual decisions or errors.
            
        Requirements:
            - 2.1: Process batch authorization requests
            - 2.4: Return results in same order as input
            - 2.5: Handle partial failures
        """
        results = []
        for item in data["items"]:
            try:
                result = self.authorize(item)
                results.append(result)
            except ValidationError as e:
                # Include validation error for this item
                results.append({
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": str(e.detail) if hasattr(e, "detail") else str(e),
                    }
                })
            except Exception as e:
                # Fail closed for unexpected errors
                logger.error(f"Unexpected error in batch item: {e}")
                results.append({
                    "decision": "DENY",
                    "reasons": ["Authorization error"],
                })
        return {"results": results}

    def invalidate_user_cache(self, user_id: str) -> int:
        """
        Invalidate all cache entries for a specific user.
        
        Used when user attributes change to ensure fresh authorization decisions.
        
        Args:
            user_id: The user ID whose cache entries should be invalidated.
            
        Returns:
            Number of cache entries deleted.
            
        Requirements:
            - 5.4: Invalidate cache when user attributes change
        """
        pattern = f"authz:{user_id}:*"
        deleted = self.cache.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} cache entries for user {user_id}")
        return deleted

    def flush_cache(self) -> int:
        """
        Flush entire authorization cache.
        
        Used when policies are updated to ensure all decisions are re-evaluated.
        
        Returns:
            Number of cache entries deleted.
            
        Requirements:
            - 5.5: Support full cache flush when policies are updated
        """
        pattern = "authz:*"
        deleted = self.cache.delete_pattern(pattern)
        logger.info(f"Flushed {deleted} authorization cache entries")
        return deleted


# Module-level singleton instance
authz_service = AuthzService()
