"""
AVP Client - Amazon Verified Permissions SDK abstraction.

This module provides a clean interface for interacting with Amazon Verified
Permissions (AVP) for authorization decisions. It encapsulates all AVP SDK
operations and translates AVP-specific exceptions to application error codes.
"""

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from django.conf import settings

from apps.authorization.exceptions import (
    AuthorizationError,
    AuthorizationValidationError,
    AVPUnavailableError,
    PolicyStoreNotFoundError,
)

logger = logging.getLogger(__name__)


class AVPClient:
    """
    Client for Amazon Verified Permissions (AVP) operations.
    
    Encapsulates all AVP SDK operations and provides a clean interface
    for authorization checks. Handles error translation from AVP-specific
    exceptions to application exceptions.
    """

    def __init__(self, policy_store_id: str | None = None, region: str | None = None):
        """
        Initialize AVP client with boto3.
        
        Args:
            policy_store_id: AVP policy store ID. Defaults to settings.AVP_POLICY_STORE_ID
            region: AWS region. Defaults to settings.AWS_REGION
        """
        self.policy_store_id = policy_store_id or settings.AVP_POLICY_STORE_ID
        self.region = region or settings.AWS_REGION
        self.client = boto3.client(
            "verifiedpermissions",
            region_name=self.region,
        )

    def is_authorized(
        self,
        principal: dict[str, Any],
        action: str,
        resource: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Check if a principal is authorized to perform an action on a resource.
        
        Args:
            principal: Principal entity with id, type, and optional attributes
            action: Action string (e.g., 'User:read')
            resource: Resource entity with type, id, and optional attributes
            context: Optional context for the authorization decision
            
        Returns:
            dict with 'decision' ('ALLOW' or 'DENY') and optional 'reasons'
            
        Raises:
            AVPUnavailableError: When AVP service is unavailable
            AuthorizationValidationError: When request validation fails
            PolicyStoreNotFoundError: When policy store is not found
            AuthorizationError: For other AVP errors
        """
        try:
            request_params = {
                "policyStoreId": self.policy_store_id,
                "principal": self._build_entity_reference(
                    principal["type"], str(principal["id"])
                ),
                "action": self._build_action_reference(action),
                "resource": self._build_entity_reference(
                    resource["type"], str(resource["id"])
                ),
            }

            # Add context if provided
            built_context = self._build_context(
                context or {}, principal.get("attributes", {})
            )
            if built_context:
                request_params["context"] = built_context

            response = self.client.is_authorized(**request_params)

            decision = response.get("decision", "DENY")
            determining_policies = response.get("determiningPolicies", [])
            
            # Extract reasons from determining policies for DENY decisions
            reasons = []
            if decision == "DENY":
                for policy in determining_policies:
                    policy_id = policy.get("policyId", "")
                    if policy_id:
                        reasons.append(f"Policy: {policy_id}")

            return {
                "decision": decision,
                "reasons": reasons,
            }

        except ClientError as e:
            raise self._translate_error(e)
        except BotoCoreError as e:
            logger.error(f"AVP BotoCoreError: {e}")
            raise AVPUnavailableError(
                message="Failed to connect to authorization service",
                details={"error": str(e)},
            )

    def _build_entity_reference(self, entity_type: str, entity_id: str) -> dict[str, Any]:
        """
        Build Cedar entity reference for principals and resources.
        
        Args:
            entity_type: Entity type (e.g., 'User', 'AdminUser')
            entity_id: Entity identifier (UUID string or 'self')
            
        Returns:
            dict with entityType and entityId in Cedar format
        """
        return {
            "entityType": f"Fortress::{entity_type}",
            "entityId": entity_id,
        }

    def _build_action_reference(self, action: str) -> dict[str, Any]:
        """
        Build Cedar action reference.
        
        Args:
            action: Action string (e.g., 'User:read', 'User:update')
            
        Returns:
            dict with actionType and actionId in Cedar format
        """
        return {
            "actionType": "Fortress::Action",
            "actionId": action,
        }

    def _build_context(
        self,
        context: dict[str, Any],
        principal_attributes: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Build context for AVP evaluation.
        
        Combines request context with principal attributes for ABAC evaluation.
        
        Args:
            context: Request context (e.g., request source, timestamp)
            principal_attributes: Attributes of the principal making the request
            
        Returns:
            dict with contextMap for AVP, or None if no context data
        """
        context_map = {**context}
        
        if principal_attributes:
            context_map["principalAttributes"] = principal_attributes

        if not context_map:
            return None

        return {"contextMap": self._convert_to_avp_context(context_map)}

    def _convert_to_avp_context(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert Python dict to AVP context format.
        
        AVP expects context values in a specific format with type annotations.
        
        Args:
            data: Python dictionary with context data
            
        Returns:
            dict formatted for AVP contextMap
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = {"string": value}
            elif isinstance(value, bool):
                result[key] = {"boolean": value}
            elif isinstance(value, int):
                result[key] = {"long": value}
            elif isinstance(value, list):
                result[key] = {"set": [self._convert_single_value(v) for v in value]}
            elif isinstance(value, dict):
                result[key] = {"record": self._convert_to_avp_context(value)}
            else:
                # Default to string representation
                result[key] = {"string": str(value)}
        return result

    def _convert_single_value(self, value: Any) -> dict[str, Any]:
        """Convert a single value to AVP format."""
        if isinstance(value, str):
            return {"string": value}
        elif isinstance(value, bool):
            return {"boolean": value}
        elif isinstance(value, int):
            return {"long": value}
        else:
            return {"string": str(value)}

    def _translate_error(self, error: ClientError) -> Exception:
        """
        Translate AVP ClientError to application exceptions.
        
        Maps AWS SDK exceptions to domain-specific exceptions with
        appropriate error codes and HTTP status codes.
        
        Args:
            error: boto3 ClientError from AVP operations
            
        Returns:
            Application-specific exception
        """
        error_code = error.response.get("Error", {}).get("Code", "")
        error_message = error.response.get("Error", {}).get("Message", str(error))

        logger.error(f"AVP error - Code: {error_code}, Message: {error_message}")

        # Service unavailability errors
        if error_code in ("ServiceException", "InternalServerException", "ServiceQuotaExceededException"):
            return AVPUnavailableError(
                message="Authorization service temporarily unavailable",
                details={"avp_error_code": error_code, "avp_message": error_message},
            )

        # Validation errors
        if error_code == "ValidationException":
            return AuthorizationValidationError(
                message="Invalid authorization request",
                details={"avp_error_code": error_code, "avp_message": error_message},
            )

        # Resource not found errors
        if error_code == "ResourceNotFoundException":
            return PolicyStoreNotFoundError(
                message="Policy store not found or not accessible",
                details={"avp_error_code": error_code, "avp_message": error_message},
            )

        # Access denied errors
        if error_code == "AccessDeniedException":
            return AVPUnavailableError(
                message="Access denied to authorization service",
                details={"avp_error_code": error_code, "avp_message": error_message},
            )

        # Throttling errors
        if error_code == "ThrottlingException":
            return AVPUnavailableError(
                message="Authorization service rate limit exceeded",
                details={"avp_error_code": error_code, "avp_message": error_message},
            )

        # Default to generic authorization error
        return AuthorizationError(
            message="Authorization service error",
            details={"avp_error_code": error_code, "avp_message": error_message},
        )


# Module-level singleton instance
avp_client = AVPClient()
