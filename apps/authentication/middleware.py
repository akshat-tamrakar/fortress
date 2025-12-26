"""
Authentication and authorization middleware.

Provides user status checking and authorization enforcement.
"""

import logging

from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status

from apps.authentication.backends import CognitoUser
from apps.authorization.services.avp_client import avp_client
from apps.authorization.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class UserStatusMiddleware:
    """
    Middleware to check if authenticated user is enabled.
    
    Checks user status on every authenticated request to ensure
    disabled users cannot access the API even with valid tokens.
    
    Uses Redis cache (30-second TTL) to minimize Cognito API calls.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check user status before processing request
        if hasattr(request, "user") and isinstance(request.user, CognitoUser):
            if not self._is_user_enabled(request.user.user_id):
                return JsonResponse(
                    {
                        "error": {
                            "code": "USER_DISABLED",
                            "message": "User account is disabled",
                            "details": {},
                        },
                        "retry": {
                            "retryable": False,
                            "retry_after_seconds": None,
                        },
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        response = self.get_response(request)
        return response

    def _is_user_enabled(self, user_id: str) -> bool:
        """
        Check if user is enabled (with caching).
        
        Args:
            user_id: User's Cognito sub (UUID)
            
        Returns:
            True if user is enabled, False otherwise
        """
        # Try cache first
        cache_key = f"user_status:{user_id}"
        cached_status = cache.get(cache_key)
        
        if cached_status is not None:
            return cached_status == "enabled"
        
        # Cache miss - query Cognito
        try:
            from apps.users.services.user_service import user_service
            
            user = user_service.get_user(user_id)
            is_enabled = user.get("status") not in ("Disabled",)
            
            # Cache the result (30 seconds)
            cache.set(
                cache_key,
                "enabled" if is_enabled else "disabled",
                timeout=30,
            )
            
            return is_enabled
            
        except Exception as e:
            logger.error(f"Error checking user status: {e}")
            # Fail-closed: deny access if we can't verify status
            return False


class AuthorizationMiddleware:
    """
    Middleware to enforce authorization using Amazon Verified Permissions.
    
    Checks authorization for protected endpoints before allowing access.
    Uses Redis cache (60-second TTL) for authorization decisions.
    
    NOTE: This is a basic implementation. For production, you should:
    1. Define which endpoints require authorization
    2. Map HTTP methods to actions
    3. Extract resource information from URL paths
    4. Handle different resource types
    """

    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define protected endpoints that require authorization
        # Format: (path_pattern, methods, action, resource_type)
        self.protected_endpoints = [
            # User management (admin only)
            (r"^/v1/users/?$", ["GET", "POST"], "User:list", "User"),
            (r"^/v1/users/[^/]+/?$", ["GET", "PUT", "DELETE"], "User:read", "User"),
            (r"^/v1/users/[^/]+/disable/?$", ["POST"], "User:disable", "User"),
            (r"^/v1/users/[^/]+/enable/?$", ["POST"], "User:enable", "User"),
        ]

    def __call__(self, request):
        # Check authorization for authenticated requests
        if hasattr(request, "user") and isinstance(request.user, CognitoUser):
            # Check if this endpoint requires authorization
            authz_required, action, resource_type = self._requires_authorization(
                request.path, request.method
            )
            
            if authz_required:
                # Extract resource ID from path if present
                resource_id = self._extract_resource_id(request.path)
                
                # Check authorization
                if not self._is_authorized(
                    request.user, action, resource_type, resource_id
                ):
                    return JsonResponse(
                        {
                            "error": {
                                "code": "AUTHORIZATION_DENIED",
                                "message": "Not authorized to perform this action",
                                "details": {},
                            },
                            "retry": {
                                "retryable": False,
                                "retry_after_seconds": None,
                            },
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

        response = self.get_response(request)
        return response

    def _requires_authorization(
        self, path: str, method: str
    ) -> tuple[bool, str, str]:
        """
        Check if endpoint requires authorization.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            Tuple of (requires_authz, action, resource_type)
        """
        import re
        
        for pattern, methods, action, resource_type in self.protected_endpoints:
            if re.match(pattern, path) and method in methods:
                return (True, action, resource_type)
        
        return (False, "", "")

    def _extract_resource_id(self, path: str) -> str:
        """
        Extract resource ID from URL path.
        
        Args:
            path: Request path
            
        Returns:
            Resource ID or "self" if not found
        """
        import re
        
        # Match UUID pattern in path
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        match = re.search(uuid_pattern, path, re.IGNORECASE)
        
        if match:
            return match.group(0)
        
        return "self"

    def _is_authorized(
        self,
        user: CognitoUser,
        action: str,
        resource_type: str,
        resource_id: str,
    ) -> bool:
        """
        Check if user is authorized to perform action (with caching).
        
        Args:
            user: Authenticated CognitoUser
            action: Action to perform (e.g., 'User:read')
            resource_type: Type of resource (e.g., 'User')
            resource_id: Resource identifier
            
        Returns:
            True if authorized, False otherwise
        """
        # Build cache key
        cache_key = f"authz:{user.user_id}:{action}:{resource_type}:{resource_id}"
        
        # Try cache first
        cached_decision = cache_service.get(cache_key)
        if cached_decision is not None:
            return cached_decision.get("decision") == "ALLOW"
        
        # Cache miss - query AVP
        try:
            # Build principal
            principal = {
                "type": "User",
                "id": user.user_id,
                "attributes": {
                    "user_type": user.user_type,
                    "email": user.email,
                },
            }
            
            # Build resource
            resource = {
                "type": resource_type,
                "id": resource_id,
            }
            
            # Check authorization
            result = avp_client.is_authorized(
                principal=principal,
                action=action,
                resource=resource,
            )
            
            # Cache the decision (60 seconds)
            cache_service.set(cache_key, result, ttl=60)
            
            return result.get("decision") == "ALLOW"
            
        except Exception as e:
            logger.error(f"Authorization error: {e}")
            # Fail-closed: deny access if authorization check fails
            return False
