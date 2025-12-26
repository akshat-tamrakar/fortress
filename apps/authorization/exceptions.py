"""
Authorization exceptions with standardized error codes.

Each exception maps to a specific HTTP status code and error code
for consistent API error responses.
"""

from typing import Any


class AuthorizationError(Exception):
    """Base authorization error."""

    error_code: str = "AUTHORIZATION_ERROR"
    status_code: int = 500
    retryable: bool = False
    retry_after: int | None = None

    def __init__(self, message: str = "", details: dict[str, Any] | None = None):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)

    @property
    def default_message(self) -> str:
        return "Authorization error occurred"


class AuthorizationDeniedError(AuthorizationError):
    """Authorization request was denied."""

    error_code = "AUTHORIZATION_DENIED"
    status_code = 403

    @property
    def default_message(self) -> str:
        return "Authorization denied"


class AVPUnavailableError(AuthorizationError):
    """Amazon Verified Permissions service is unavailable."""

    error_code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503
    retryable = True

    @property
    def default_message(self) -> str:
        return "Authorization service temporarily unavailable"


class AuthorizationValidationError(AuthorizationError):
    """Request validation failed."""

    error_code = "VALIDATION_FAILED"
    status_code = 422

    @property
    def default_message(self) -> str:
        return "Request validation failed"


class PolicyStoreNotFoundError(AuthorizationError):
    """AVP policy store not found."""

    error_code = "POLICY_STORE_NOT_FOUND"
    status_code = 500

    @property
    def default_message(self) -> str:
        return "Policy store configuration error"


class IAMAuthenticationError(AuthorizationError):
    """IAM authentication required or failed."""

    error_code = "AUTHENTICATION_REQUIRED"
    status_code = 401

    @property
    def default_message(self) -> str:
        return "IAM authentication required"


class RateLimitExceededError(AuthorizationError):
    """Too many authorization requests."""

    error_code = "RATE_LIMIT_EXCEEDED"
    status_code = 429
    retryable = True

    def __init__(
        self,
        message: str = "",
        details: dict[str, Any] | None = None,
        retry_after: int = 60,
    ):
        super().__init__(message, details)
        self.retry_after = retry_after

    @property
    def default_message(self) -> str:
        return "Too many requests, please try again later"
