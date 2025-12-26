"""
Custom authentication backend for JWT token validation.

Validates AWS Cognito JWT tokens and checks user status.
"""

import logging
from typing import Any

import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from jwt import PyJWKClient
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from apps.authentication.exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    UserDisabledError,
)
from apps.users.services.user_service import user_service

logger = logging.getLogger(__name__)


class CognitoUser:
    """
    Lightweight user object for Cognito-authenticated users.

    Does not use Django's User model since all user data is in Cognito.
    """

    def __init__(
        self, user_id: str, email: str, user_type: str, claims: dict[str, Any]
    ):
        self.user_id = user_id
        self.email = email
        self.user_type = user_type
        self.claims = claims
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def __str__(self):
        return f"CognitoUser({self.email})"


class CognitoJWTAuthentication(authentication.BaseAuthentication):
    """
    JWT authentication backend for AWS Cognito tokens.

    Validates the JWT token signature, expiration, and issuer.
    Does NOT check user status - that's done by the UserStatusMiddleware.
    """

    def __init__(self):
        """Initialize JWKS client for token validation."""
        self.user_pool_id = settings.COGNITO_USER_POOL_ID
        self.region = settings.AWS_REGION

        # JWKS endpoint for token validation
        self.jwks_url = (
            f"https://cognito-idp.{self.region}.amazonaws.com/"
            f"{self.user_pool_id}/.well-known/jwks.json"
        )

        # Initialize JWKS client (caches keys)
        self.jwks_client = PyJWKClient(self.jwks_url)

    def authenticate(self, request):
        """
        Authenticate the request using JWT token from Authorization header.

        Args:
            request: Django request object

        Returns:
            Tuple of (user, token) if authentication succeeds, None otherwise

        Raises:
            AuthenticationFailed: If token is invalid or expired
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header:
            # No authentication provided - return None to try next backend
            return None

        if not auth_header.startswith("Bearer "):
            raise AuthenticationFailed("Invalid authentication header format")

        token = auth_header.split(" ")[1]

        try:
            # Validate and decode token
            user = self._validate_token(token)

            # Store token in request for later use (e.g., for user status check)
            request.cognito_token = token

            return (user, token)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationFailed("Authentication failed")

    def _validate_token(self, token: str) -> CognitoUser:
        """
        Validate JWT token and extract user information.

        Args:
            token: JWT token string

        Returns:
            CognitoUser object

        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        # Get signing key from JWKS
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)

        # Expected issuer
        expected_issuer = (
            f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
        )

        # Decode and validate token
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=expected_issuer,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
            },
        )

        # Extract user information from claims
        user_id = claims.get("sub")
        email = claims.get("email")
        user_type = claims.get("custom:user_type", "end_user")

        if not user_id or not email:
            raise jwt.InvalidTokenError("Token missing required claims")

        return CognitoUser(
            user_id=user_id,
            email=email,
            user_type=user_type,
            claims=claims,
        )

    def authenticate_header(self, request):
        """
        Return string to use as WWW-Authenticate header in 401 response.
        """
        return "Bearer"
