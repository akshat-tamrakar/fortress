"""
Request and response serializers for authentication endpoints.

Handles validation of input data and serialization of responses.
"""

import re

from rest_framework import serializers


# =============================================================================
# Request Serializers
# =============================================================================


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration requests."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, min_length=12, write_only=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_password(self, value: str) -> str:
        """
        Validate password meets policy requirements:
        - Minimum 12 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        - At least one special character
        """
        errors = []

        if len(value) < 12:
            errors.append("Password must be at least 12 characters long")

        if not re.search(r"[A-Z]", value):
            errors.append("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", value):
            errors.append("Password must contain at least one lowercase letter")

        if not re.search(r"\d", value):
            errors.append("Password must contain at least one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            errors.append("Password must contain at least one special character")

        if errors:
            raise serializers.ValidationError(errors)

        return value

    def validate_phone(self, value: str) -> str:
        """Validate phone number format (E.164 format preferred)."""
        if not value:
            return value

        # Remove spaces and dashes for validation
        cleaned = re.sub(r"[\s\-()]", "", value)

        # Check for valid phone format (E.164 or common formats)
        if not re.match(r"^\+?[1-9]\d{6,14}$", cleaned):
            raise serializers.ValidationError(
                "Invalid phone number format. Use E.164 format (e.g., +12025551234)"
            )

        return value


class LoginSerializer(serializers.Serializer):
    """Serializer for login requests."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class MFAVerifySerializer(serializers.Serializer):
    """Serializer for MFA verification requests."""

    session_token = serializers.CharField(required=True)
    mfa_code = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_mfa_code(self, value: str) -> str:
        """Validate MFA code is numeric."""
        if not value.isdigit():
            raise serializers.ValidationError("MFA code must contain only digits")
        return value


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for token refresh requests."""

    refresh_token = serializers.CharField(required=True)


class VerifyEmailSerializer(serializers.Serializer):
    """Serializer for email verification requests."""

    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_code(self, value: str) -> str:
        """Validate verification code is numeric."""
        if not value.isdigit():
            raise serializers.ValidationError(
                "Verification code must contain only digits"
            )
        return value


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resend verification requests."""

    email = serializers.EmailField(required=True)


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password requests."""

    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset confirmation requests."""

    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=12, write_only=True)

    def validate_new_password(self, value: str) -> str:
        """Validate new password meets policy requirements."""
        # Reuse the same validation logic as RegisterSerializer
        errors = []

        if len(value) < 12:
            errors.append("Password must be at least 12 characters long")

        if not re.search(r"[A-Z]", value):
            errors.append("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", value):
            errors.append("Password must contain at least one lowercase letter")

        if not re.search(r"\d", value):
            errors.append("Password must contain at least one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            errors.append("Password must contain at least one special character")

        if errors:
            raise serializers.ValidationError(errors)

        return value


class NewPasswordRequiredSerializer(serializers.Serializer):
    """Serializer for new password required challenge."""

    session_token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=12, write_only=True)

    def validate_new_password(self, value: str) -> str:
        """Validate new password meets policy requirements."""
        errors = []

        if len(value) < 12:
            errors.append("Password must be at least 12 characters long")

        if not re.search(r"[A-Z]", value):
            errors.append("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", value):
            errors.append("Password must contain at least one lowercase letter")

        if not re.search(r"\d", value):
            errors.append("Password must contain at least one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            errors.append("Password must contain at least one special character")

        if errors:
            raise serializers.ValidationError(errors)

        return value


# =============================================================================
# Response Serializers
# =============================================================================


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token responses."""

    access_token = serializers.CharField()
    id_token = serializers.CharField()
    refresh_token = serializers.CharField(required=False, allow_null=True)
    expires_in = serializers.IntegerField()
    token_type = serializers.CharField(default="Bearer")


class MFAChallengeResponseSerializer(serializers.Serializer):
    """Serializer for MFA challenge responses."""

    challenge = serializers.CharField()
    session_token = serializers.CharField()


class NewPasswordChallengeResponseSerializer(serializers.Serializer):
    """Serializer for new password required challenge responses."""

    challenge = serializers.CharField()
    session_token = serializers.CharField()


class RegisterResponseSerializer(serializers.Serializer):
    """Serializer for registration responses."""

    user_id = serializers.UUIDField()
    email = serializers.EmailField()
    status = serializers.CharField()
    message = serializers.CharField()


class MessageResponseSerializer(serializers.Serializer):
    """Serializer for simple message responses."""

    message = serializers.CharField()
    status = serializers.CharField(required=False)
