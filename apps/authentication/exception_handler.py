"""
Custom exception handler for standardized API error responses.

Converts exceptions to the format:
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": {},
        "request_id": "uuid"
    },
    "retry": {
        "retryable": false,
        "retry_after_seconds": null
    }
}
"""

import uuid
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .exceptions import AuthenticationError
from apps.authorization.exceptions import AuthorizationError


def custom_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """
    Convert exceptions to standardized error responses.

    Handles:
    - AuthenticationError subclasses (our domain exceptions)
    - AuthorizationError subclasses (authorization domain exceptions)
    - DRF validation errors
    - Other DRF exceptions
    """
    request_id = str(uuid.uuid4())

    # Handle our custom authentication exceptions
    if isinstance(exc, AuthenticationError):
        return Response(
            {
                "error": {
                    "code": exc.error_code,
                    "message": str(exc),
                    "details": exc.details,
                    "request_id": request_id,
                },
                "retry": {
                    "retryable": exc.retryable,
                    "retry_after_seconds": exc.retry_after,
                },
            },
            status=exc.status_code,
        )

    # Handle our custom authorization exceptions
    if isinstance(exc, AuthorizationError):
        return Response(
            {
                "error": {
                    "code": exc.error_code,
                    "message": str(exc),
                    "details": exc.details,
                    "request_id": request_id,
                },
                "retry": {
                    "retryable": exc.retryable,
                    "retry_after_seconds": exc.retry_after,
                },
            },
            status=exc.status_code,
        )

    # Let DRF handle its own exceptions first
    response = drf_exception_handler(exc, context)

    if response is not None:
        # Transform DRF response to our format
        error_code = _get_error_code_from_status(response.status_code)
        error_message = _get_error_message(response.data)
        error_details = _get_error_details(response.data)

        return Response(
            {
                "error": {
                    "code": error_code,
                    "message": error_message,
                    "details": error_details,
                    "request_id": request_id,
                },
                "retry": {
                    "retryable": response.status_code >= 500,
                    "retry_after_seconds": None,
                },
            },
            status=response.status_code,
        )

    # Return None for unhandled exceptions (will result in 500)
    return None


def _get_error_code_from_status(status_code: int) -> str:
    """Map HTTP status code to error code."""
    status_map = {
        status.HTTP_400_BAD_REQUEST: "VALIDATION_FAILED",
        status.HTTP_401_UNAUTHORIZED: "AUTHENTICATION_REQUIRED",
        status.HTTP_403_FORBIDDEN: "AUTHORIZATION_DENIED",
        status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_FAILED",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMIT_EXCEEDED",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    return status_map.get(status_code, "UNKNOWN_ERROR")


def _get_error_message(data: Any) -> str:
    """Extract human-readable message from DRF error data."""
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        if "non_field_errors" in data:
            errors = data["non_field_errors"]
            return str(errors[0]) if errors else "Validation failed"
        # Get first field error
        for field, errors in data.items():
            if isinstance(errors, list) and errors:
                return f"{field}: {errors[0]}"
            if isinstance(errors, str):
                return f"{field}: {errors}"
        return "Request validation failed"
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data) if data else "An error occurred"


def _get_error_details(data: Any) -> dict[str, Any]:
    """Extract detailed error information from DRF error data."""
    if isinstance(data, dict):
        # Remove 'detail' as it's already in message
        details = {k: v for k, v in data.items() if k != "detail"}
        return details if details else {}
    if isinstance(data, list):
        return {"errors": data}
    return {}
