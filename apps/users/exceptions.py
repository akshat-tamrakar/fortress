"""
Users app exceptions with standardized error codes.

Each exception maps to a specific HTTP status code and error code
for consistent API error responses.
"""

from typing import Any


class UsersError(Exception):
    """Base users error."""

    error_code: str = "USERS_ERROR"
    status_code: int = 500
    retryable: bool = False
    retry_after: int | None = None

    def __init__(self, message: str = "", details: dict[str, Any] | None = None):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)

    @property
    def default_message(self) -> str:
        return "Users service error occurred"


class UserNotFoundError(UsersError):
    """User does not exist."""

    error_code = "USER_NOT_FOUND"
    status_code = 404

    @property
    def default_message(self) -> str:
        return "User not found"


class UserAlreadyExistsError(UsersError):
    """User with this email already exists."""

    error_code = "USER_ALREADY_EXISTS"
    status_code = 409

    @property
    def default_message(self) -> str:
        return "User with this email already exists"


class AuthorizationDeniedError(UsersError):
    """User is not authorized to perform this action."""

    error_code = "AUTHORIZATION_DENIED"
    status_code = 403

    @property
    def default_message(self) -> str:
        return "Not authorized to perform this action"


class ValidationError(UsersError):
    """Request validation failed."""

    error_code = "VALIDATION_FAILED"
    status_code = 422

    @property
    def default_message(self) -> str:
        return "Request validation failed"


class InvalidMFACodeError(UsersError):
    """MFA code is invalid or expired."""

    error_code = "INVALID_MFA_CODE"
    status_code = 400

    @property
    def default_message(self) -> str:
        return "Invalid or expired MFA code"


class MFAAlreadyEnabledError(UsersError):
    """MFA is already enabled for this user."""

    error_code = "MFA_ALREADY_ENABLED"
    status_code = 409

    @property
    def default_message(self) -> str:
        return "MFA is already enabled for this user"


class TokenInvalidError(UsersError):
    """Token is malformed or invalid."""

    error_code = "TOKEN_INVALID"
    status_code = 401

    @property
    def default_message(self) -> str:
        return "Token is invalid or malformed"


class RateLimitExceededError(UsersError):
    """Too many requests."""

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
