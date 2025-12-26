"""
Views for the authorization app.

Provides REST API endpoints for authorization checks using
Amazon Verified Permissions (AVP) with IAM authentication.

Requirements:
    - 1.1: Single authorization check endpoint
    - 2.1: Batch authorization check endpoint
    - 3.1: IAM authentication for all endpoints
"""

import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authorization.authentication import IAMAuthentication
from apps.authorization.serializers import (
    AuthorizeRequestSerializer,
    AuthorizeResponseSerializer,
    BatchAuthorizeRequestSerializer,
    BatchAuthorizeResponseSerializer,
)
from apps.authorization.services.authz_service import authz_service


logger = logging.getLogger(__name__)


class AuthorizeView(APIView):
    """
    POST /v1/authorize - Single authorization check.
    
    Evaluates whether a principal can perform an action on a resource
    using Amazon Verified Permissions policies.
    
    Request body:
        {
            "principal": {"id": "uuid", "type": "User", "attributes": {}},
            "action": "User:read",
            "resource": {"type": "User", "id": "uuid", "attributes": {}},
            "context": {}
        }
    
    Response:
        {
            "decision": "ALLOW" | "DENY",
            "reasons": []  // Only present for DENY
        }
    
    Requirements:
        - 1.1: Evaluate authorization requests against AVP policies
        - 1.2, 1.3: Return proper decision format
        - 3.1: Require IAM authentication
    """

    authentication_classes = [IAMAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        """Handle single authorization check request."""
        # Validate request data
        serializer = AuthorizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Perform authorization check
        result = authz_service.authorize(serializer.validated_data)
        
        # Serialize and return response
        response_serializer = AuthorizeResponseSerializer(result)
        return Response(response_serializer.data)


class BatchAuthorizeView(APIView):
    """
    POST /v1/authorize/batch - Batch authorization check.
    
    Evaluates multiple authorization decisions in a single request.
    Results are returned in the same order as input items.
    
    Request body:
        {
            "items": [
                {
                    "principal": {"id": "uuid", "type": "User", "attributes": {}},
                    "action": "User:read",
                    "resource": {"type": "User", "id": "uuid", "attributes": {}},
                    "context": {}
                },
                ...
            ]
        }
    
    Response:
        {
            "results": [
                {"decision": "ALLOW" | "DENY", "reasons": []},
                {"error": {"code": "...", "message": "..."}}  // For failed items
            ]
        }
    
    Requirements:
        - 2.1: Process batch authorization requests
        - 2.2: Support up to 30 items per batch
        - 2.4: Return results in same order as input
        - 3.1: Require IAM authentication
    """

    authentication_classes = [IAMAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        """Handle batch authorization check request."""
        # Validate request data
        serializer = BatchAuthorizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Perform batch authorization check
        result = authz_service.batch_authorize(serializer.validated_data)
        
        # Serialize and return response
        response_serializer = BatchAuthorizeResponseSerializer(result)
        return Response(response_serializer.data)
