"""
Custom exception handler for users app.

Provides consistent error response formatting for all user management
endpoints following the standardized error format defined in API specs.
"""

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.users.exceptions import UsersError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats errors consistently.
    
    Handles both UsersError exceptions and Django REST Framework exceptions,
    returning a standardized error response format.
    
    Args:
        exc: The exception instance
        context: Dict with 'view' and 'request' keys
        
    Returns:
        Response with standardized error format
    """
    # Handle custom UsersError exceptions
    if isinstance(exc, UsersError):
        error_response = {
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
            "retry": {
                "retryable": exc.retryable,
                "retry_after_seconds": exc.retry_after,
            },
        }

        return Response(error_response, status=exc.status_code)

    # Fall back to default DRF exception handler for other exceptions
    response = exception_handler(exc, context)

    if response is not None:
        # Wrap DRF error responses in our standardized format
        error_data = response.data

        # Extract error message
        if isinstance(error_data, dict):
            if "detail" in error_data:
                message = error_data["detail"]
            else:
                message = str(error_data)
        else:
            message = str(error_data)

        error_response = {
            "error": {
                "code": "VALIDATION_FAILED" if response.status_code == 400 else "ERROR",
                "message": message,
                "details": error_data if isinstance(error_data, dict) else {},
            },
            "retry": {
                "retryable": False,
                "retry_after_seconds": None,
            },
        }

        response.data = error_response

    return response
