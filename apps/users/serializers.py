"""
User management serializers for request validation and response formatting.
"""

from rest_framework import serializers


class UserCreateSerializer(serializers.Serializer):
    """Serializer for creating a new user (admin-initiated)."""

    email = serializers.EmailField(
        required=True,
        max_length=255,
        help_text="User's email address (used as username)",
    )
    given_name = serializers.CharField(
        required=True,
        max_length=255,
        help_text="User's first name",
    )
    family_name = serializers.CharField(
        required=True,
        max_length=255,
        help_text="User's last name",
    )
    user_type = serializers.ChoiceField(
        choices=["end_user", "admin"],
        default="end_user",
        help_text="Type of user account",
    )
    phone_number = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=20,
        help_text="Phone number in E.164 format (e.g., +1234567890)",
    )


class UserUpdateSerializer(serializers.Serializer):
    """Serializer for updating user attributes."""

    given_name = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=255,
        help_text="User's first name",
    )
    family_name = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=255,
        help_text="User's last name",
    )
    phone_number = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=20,
        help_text="Phone number in E.164 format",
    )


class UserResponseSerializer(serializers.Serializer):
    """Serializer for user response data."""

    user_id = serializers.CharField(
        help_text="User's unique identifier (Cognito sub)",
    )
    email = serializers.EmailField(
        help_text="User's email address",
    )
    given_name = serializers.CharField(
        help_text="User's first name",
    )
    family_name = serializers.CharField(
        help_text="User's last name",
    )
    phone_number = serializers.CharField(
        allow_null=True,
        help_text="User's phone number",
    )
    user_type = serializers.CharField(
        help_text="User type (end_user or admin)",
    )
    email_verified = serializers.BooleanField(
        help_text="Whether email is verified",
    )
    status = serializers.CharField(
        help_text="User status (Active, Disabled, Unverified, PasswordChangeRequired)",
    )
    mfa_enabled = serializers.BooleanField(
        help_text="Whether MFA is enabled",
    )
    created_at = serializers.CharField(
        allow_null=True,
        help_text="User creation timestamp",
    )
    updated_at = serializers.CharField(
        allow_null=True,
        help_text="Last update timestamp",
    )


class UserListResponseSerializer(serializers.Serializer):
    """Serializer for paginated user list response."""

    users = UserResponseSerializer(many=True)
    next_token = serializers.CharField(
        allow_null=True,
        help_text="Pagination token for next page",
    )


class MFASetupRequestSerializer(serializers.Serializer):
    """Serializer for MFA setup request."""

    totp_code = serializers.CharField(
        required=False,
        min_length=6,
        max_length=6,
        help_text="6-digit TOTP code from authenticator app (for verification step)",
    )


class MFASetupResponseSerializer(serializers.Serializer):
    """Serializer for MFA setup response."""

    secret_code = serializers.CharField(
        required=False,
        help_text="Secret code to enter in authenticator app",
    )
    message = serializers.CharField(
        help_text="Response message",
    )
