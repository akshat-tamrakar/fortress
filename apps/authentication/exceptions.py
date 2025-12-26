"""
Authentication exceptions with standardized error codes.

Each exception maps to a specific HTTP status code and error code
for consistent API error responses.
"""

from typing import Any


class AuthenticationError(Exception):
    """Base authentication error."""

    error_code: str = "AUTHENTICATION_ERROR"
    status_code: int = 401
    retryable: bool = False
    retry_after: int | None = None

    def __init__(self, message: str = "", details: dict[str, Any] | None = None):
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)

    @property
    def default_message(self) -> str:
        return "Authentication error occurred"


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password."""

    error_code = "INVALID_CREDENTIALS"
    status_code = 401

    @property
    def default_message(self) -> str:
        return "Invalid email or password"


class TokenExpiredError(AuthenticationError):
    """Access token has expired."""

    error_code = "TOKEN_EXPIRED"
    status_code = 401

    @property
    def default_message(self) -> str:
        return "Access token has expired"


class TokenInvalidError(AuthenticationError):
    """Token is malformed or invalid."""

    error_code = "TOKEN_INVALID"
    status_code = 401

    @property
    def default_message(self) -> str:
        return "Token is invalid or malformed"


class MFARequiredError(AuthenticationError):
    """MFA verification is required."""

    error_code = "MFA_REQUIRED"
    status_code = 401

    @property
    def default_message(self) -> str:
        return "MFA verification required"


class InvalidMFACodeError(AuthenticationError):
    """MFA code is invalid or expired."""

    error_code = "INVALID_MFA_CODE"
    status_code = 401

    @property
    def default_message(self) -> str:
        return "Invalid or expired MFA code"


class SessionExpiredError(AuthenticationError):
    """Session token has expired."""

    error_code = "SESSION_EXPIRED"
    status_code = 401

    @property
    def default_message(self) -> str:
        return "Session has expired"


class UserDisabledError(AuthenticationError):
    """User account is disabled."""

    error_code = "USER_DISABLED"
    status_code = 403

    @property
    def default_message(self) -> str:
        return "User account is disabled"


class EmailNotVerifiedError(AuthenticationError):
    """User email is not verified."""

    error_code = "EMAIL_NOT_VERIFIED"
    status_code = 403

    @property
    def default_message(self) -> str:
        return "Email address not verified"


class UserNotFoundError(AuthenticationError):
    """User does not exist."""

    error_code = "USER_NOT_FOUND"
    status_code = 404

    @property
    def default_message(self) -> str:
        return "User not found"


class UserAlreadyExistsError(AuthenticationError):
    """User with this email already exists."""

    error_code = "USER_ALREADY_EXISTS"
    status_code = 409

    @property
    def default_message(self) -> str:
        return "User with this email already exists"


class InvalidVerificationCodeError(AuthenticationError):
    """Verification code is invalid or expired."""

    error_code = "INVALID_VERIFICATION_CODE"
    status_code = 400

    @property
    def default_message(self) -> str:
        return "Invalid or expired verification code"


class PasswordTooWeakError(AuthenticationError):
    """Password does not meet policy requirements."""

    error_code = "PASSWORD_TOO_WEAK"
    status_code = 422

    @property
    def default_message(self) -> str:
        return "Password does not meet security requirements"


class ValidationError(AuthenticationError):
    """Request validation failed."""

    error_code = "VALIDATION_FAILED"
    status_code = 422

    @property
    def default_message(self) -> str:
        return "Request validation failed"


class RateLimitExceededError(AuthenticationError):
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


class AccountLockedError(AuthenticationError):
    """Account locked due to too many failed attempts."""

    error_code = "ACCOUNT_LOCKED"
    status_code = 429
    retryable = True

    def __init__(
        self,
        message: str = "",
        details: dict[str, Any] | None = None,
        retry_after: int = 300,
    ):
        super().__init__(message, details)
        self.retry_after = retry_after

    @property
    def default_message(self) -> str:
        return "Account temporarily locked due to too many failed attempts"


class DependencyUnavailableError(AuthenticationError):
    """External dependency (Cognito/AVP) is unavailable."""

    error_code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503
    retryable = True

    @property
    def default_message(self) -> str:
        return "Service temporarily unavailable"
