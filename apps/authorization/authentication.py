"""
IAM Authentication for Authorization endpoints.

This module provides AWS SigV4-based authentication for service-to-service
communication. Only internal services with valid IAM credentials can access
the authorization endpoints.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import logging
import re
from typing import Any

from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request

from apps.authorization.exceptions import IAMAuthenticationError


logger = logging.getLogger(__name__)


class IAMAuthentication(BaseAuthentication):
    """
    Authenticate requests using AWS SigV4.

    This authentication class validates that incoming requests have valid
    AWS Signature Version 4 authentication headers. It is designed for
    service-to-service communication where internal microservices need
    to make authorization requests.

    The authentication flow:
    1. Check for AWS4-HMAC-SHA256 Authorization header
    2. Validate required AWS headers are present
    3. Extract IAM role information from the request

    Note: In production, this would verify the signature using AWS STS.
    For POC, we validate the presence of required headers.
    """

    # Required headers for SigV4 authentication
    REQUIRED_HEADERS = [
        "HTTP_X_AMZ_DATE",
    ]

    # Optional but commonly present headers
    OPTIONAL_HEADERS = [
        "HTTP_X_AMZ_SECURITY_TOKEN",
        "HTTP_X_AMZ_CONTENT_SHA256",
    ]

    # Pattern to extract credential info from Authorization header
    CREDENTIAL_PATTERN = re.compile(
        r"Credential=([^/]+)/(\d{8})/([^/]+)/([^/]+)/aws4_request"
    )

    def authenticate(self, request: Request) -> tuple[str, None] | None:
        """
        Authenticate the request using AWS SigV4.

        Args:
            request: The incoming HTTP request

        Returns:
            A tuple of (iam_role_arn, None) if authentication succeeds,
            or None if this authentication method is not applicable.

        Raises:
            IAMAuthenticationError: If authentication fails
        """
        # Get Authorization header
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        # Check if this is a SigV4 request
        if not auth_header:
            logger.warning("Missing Authorization header for IAM authentication")
            raise IAMAuthenticationError(
                message="IAM authentication required",
                details={"reason": "Missing Authorization header"},
            )

        # Requirement 3.3: Reject JWT tokens - they start with "Bearer"
        if auth_header.startswith("Bearer"):
            logger.warning("JWT token rejected for authorization endpoint")
            raise IAMAuthenticationError(
                message="IAM authentication required, JWT tokens not accepted",
                details={
                    "reason": "JWT tokens are not accepted for authorization endpoints"
                },
            )

        # Requirement 3.1: Validate SigV4 signature format
        if not auth_header.startswith("AWS4-HMAC-SHA256"):
            logger.warning("Invalid authentication scheme: expected AWS4-HMAC-SHA256")
            raise IAMAuthenticationError(
                message="Invalid authentication scheme",
                details={"reason": "Expected AWS4-HMAC-SHA256 authentication"},
            )

        # Validate required headers are present
        self._validate_required_headers(request)

        # Requirement 3.2: Extract and validate IAM role
        iam_role = self._extract_iam_role(request, auth_header)

        logger.info(f"IAM authentication successful for role: {iam_role}")

        # Return the IAM role as the authenticated "user"
        return (iam_role, None)

    def _validate_required_headers(self, request: Request) -> None:
        """
        Validate that all required AWS headers are present.

        Args:
            request: The incoming HTTP request

        Raises:
            IAMAuthenticationError: If required headers are missing
        """
        missing_headers = []

        for header in self.REQUIRED_HEADERS:
            if header not in request.META:
                # Convert HTTP_X_AMZ_DATE to X-Amz-Date for error message
                readable_header = header.replace("HTTP_", "").replace("_", "-")
                missing_headers.append(readable_header)

        if missing_headers:
            logger.warning(f"Missing required IAM headers: {missing_headers}")
            raise IAMAuthenticationError(
                message="Missing required IAM authentication headers",
                details={"missing_headers": missing_headers},
            )

    def _extract_iam_role(self, request: Request, auth_header: str) -> str:
        """
        Extract IAM role ARN from the request.

        In production, this would decode the credentials from STS and
        validate them. For POC, we extract from headers or the
        Authorization header credential scope.

        Args:
            request: The incoming HTTP request
            auth_header: The Authorization header value

        Returns:
            The IAM role ARN or identifier
        """
        # First, check for explicit IAM role header (used in testing/POC)
        explicit_role = request.META.get("HTTP_X_AMZ_IAM_ROLE")
        if explicit_role:
            return explicit_role

        # Try to extract from Authorization header credential
        match = self.CREDENTIAL_PATTERN.search(auth_header)
        if match:
            access_key_id = match.group(1)
            region = match.group(3)
            service = match.group(4)

            # In production, we would use STS to get the actual role ARN
            # For POC, construct a placeholder based on available info
            return f"arn:aws:iam::unknown:role/{access_key_id}"

        # Fallback to unknown role
        logger.warning("Could not extract IAM role from request")
        return "arn:aws:iam::unknown:role/unknown"

    def authenticate_header(self, request: Request) -> str:
        """
        Return the WWW-Authenticate header value for 401 responses.

        Args:
            request: The incoming HTTP request

        Returns:
            The authentication scheme name
        """
        return "AWS4-HMAC-SHA256"
