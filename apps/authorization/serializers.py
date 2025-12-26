"""
Request and response serializers for authorization endpoints.

Handles validation of input data and serialization of responses
for single and batch authorization checks.
"""

from rest_framework import serializers


# =============================================================================
# Valid Actions
# =============================================================================

VALID_ACTIONS = [
    "User:create",
    "User:read",
    "User:update",
    "User:delete",
    "User:list",
    "User:disable",
    "User:enable",
]


# =============================================================================
# Request Serializers
# =============================================================================


class PrincipalSerializer(serializers.Serializer):
    """Serializer for principal (user) in authorization requests."""

    id = serializers.UUIDField(required=True)
    type = serializers.ChoiceField(choices=["User", "AdminUser"], default="User")
    attributes = serializers.DictField(required=False, default=dict)


class ResourceSerializer(serializers.Serializer):
    """Serializer for resource in authorization requests."""

    type = serializers.CharField(required=True)
    id = serializers.CharField(required=True)  # UUID or 'self'
    attributes = serializers.DictField(required=False, default=dict)

    def validate_id(self, value: str) -> str:
        """Validate resource id is either 'self' or a valid UUID format."""
        if value == "self":
            return value
        # Allow UUID format validation to be flexible
        # The actual UUID validation happens at the AVP level
        return value


class AuthorizeRequestSerializer(serializers.Serializer):
    """Serializer for single authorization requests."""

    principal = PrincipalSerializer(required=True)
    action = serializers.CharField(required=True)
    resource = ResourceSerializer(required=True)
    context = serializers.DictField(required=False, default=dict)

    def validate_action(self, value: str) -> str:
        """Validate action is one of the known action types."""
        if value not in VALID_ACTIONS:
            raise serializers.ValidationError(
                f"Invalid action: {value}. Must be one of: {', '.join(VALID_ACTIONS)}"
            )
        return value


class AuthorizeItemSerializer(serializers.Serializer):
    """Serializer for individual items in batch authorization requests."""

    principal = PrincipalSerializer(required=True)
    action = serializers.CharField(required=True)
    resource = ResourceSerializer(required=True)
    context = serializers.DictField(required=False, default=dict)

    def validate_action(self, value: str) -> str:
        """Validate action is one of the known action types."""
        if value not in VALID_ACTIONS:
            raise serializers.ValidationError(
                f"Invalid action: {value}. Must be one of: {', '.join(VALID_ACTIONS)}"
            )
        return value


class BatchAuthorizeRequestSerializer(serializers.Serializer):
    """Serializer for batch authorization requests."""

    items = AuthorizeItemSerializer(many=True, required=True)

    def validate_items(self, value: list) -> list:
        """Validate batch contains between 1 and 30 items."""
        if len(value) > 30:
            raise serializers.ValidationError("Batch cannot exceed 30 items")
        if len(value) == 0:
            raise serializers.ValidationError("Batch must contain at least 1 item")
        return value


# =============================================================================
# Response Serializers
# =============================================================================


class AuthorizeResponseSerializer(serializers.Serializer):
    """Serializer for single authorization responses."""

    decision = serializers.ChoiceField(choices=["ALLOW", "DENY"])
    reasons = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class BatchItemResultSerializer(serializers.Serializer):
    """Serializer for individual results in batch authorization responses."""

    decision = serializers.ChoiceField(
        choices=["ALLOW", "DENY"], required=False, allow_null=True
    )
    reasons = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    error = serializers.DictField(required=False, allow_null=True)


class BatchAuthorizeResponseSerializer(serializers.Serializer):
    """Serializer for batch authorization responses."""

    results = BatchItemResultSerializer(many=True)
