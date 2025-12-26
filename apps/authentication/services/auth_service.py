"""
Authentication service orchestration layer.

Coordinates authentication flows and delegates to CognitoClient.
"""

from typing import Any

from .cognito_client import CognitoClient


class AuthService:
    """
    Service layer for authentication operations.

    Orchestrates authentication flows and provides a clean interface
    for views to interact with.
    """

    def __init__(self, cognito_client: CognitoClient | None = None):
        self.cognito = cognito_client or CognitoClient()

    def register(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Register a new user.

        Args:
            data: Registration data with email, password, first_name, last_name, phone

        Returns:
            dict with user_id, email, status, message
        """
        attributes = {
            "given_name": data["first_name"],
            "family_name": data["last_name"],
            "custom:user_type": "end_user",
        }

        if data.get("phone"):
            attributes["phone_number"] = data["phone"]

        return self.cognito.sign_up(
            email=data["email"],
            password=data["password"],
            attributes=attributes,
        )

    def verify_email(self, email: str, code: str) -> dict[str, Any]:
        """
        Verify user email with OTP code.

        Args:
            email: User's email address
            code: Verification code from email

        Returns:
            dict with status and message
        """
        return self.cognito.confirm_sign_up(email, code)

    def resend_verification(self, email: str) -> dict[str, Any]:
        """
        Resend verification email.

        Args:
            email: User's email address

        Returns:
            dict with message
        """
        return self.cognito.resend_confirmation_code(email)

    def login(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Authenticate user.

        Args:
            data: Login data with email and password

        Returns:
            dict with either:
            - tokens (for successful auth)
            - challenge and session_token (for MFA or password change)
        """
        result = self.cognito.initiate_auth(
            email=data["email"],
            password=data["password"],
        )

        # Handle MFA challenge
        if result.get("challenge") == "MFA_REQUIRED":
            return {
                "challenge": "MFA_REQUIRED",
                "session_token": result["session"],
            }

        # Handle new password required challenge
        if result.get("challenge") == "NEW_PASSWORD_REQUIRED":
            return {
                "challenge": "NEW_PASSWORD_REQUIRED",
                "session_token": result["session"],
            }

        # Successful authentication
        return result["tokens"]

    def verify_mfa(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Complete MFA verification.

        Args:
            data: MFA data with session_token and mfa_code

        Returns:
            dict with tokens
        """
        return self.cognito.respond_to_auth_challenge(
            session=data["session_token"],
            mfa_code=data["mfa_code"],
            challenge_name="SOFTWARE_TOKEN_MFA",
        )

    def complete_new_password(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Complete new password required challenge.

        Args:
            data: Data with session_token and new_password

        Returns:
            dict with tokens
        """
        return self.cognito.respond_to_auth_challenge(
            session=data["session_token"],
            new_password=data["new_password"],
            challenge_name="NEW_PASSWORD_REQUIRED",
        )

    def refresh_token(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Refresh access token.

        Args:
            data: Data with refresh_token

        Returns:
            dict with new tokens
        """
        return self.cognito.refresh_tokens(data["refresh_token"])

    def logout(self, access_token: str) -> None:
        """
        Logout user (revoke all tokens).

        Args:
            access_token: User's access token
        """
        self.cognito.global_sign_out(access_token)

    def forgot_password(self, email: str) -> dict[str, Any]:
        """
        Initiate password reset.

        Args:
            email: User's email address

        Returns:
            dict with message
        """
        return self.cognito.forgot_password(email)

    def reset_password(
        self,
        email: str,
        code: str,
        new_password: str,
    ) -> dict[str, Any]:
        """
        Complete password reset.

        Args:
            email: User's email address
            code: Reset code from email
            new_password: New password

        Returns:
            dict with message
        """
        return self.cognito.confirm_forgot_password(email, code, new_password)

    def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information from access token.

        Args:
            access_token: User's access token

        Returns:
            dict with user attributes
        """
        return self.cognito.get_user(access_token)


# Singleton instance for dependency injection
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Get or create the AuthService singleton."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
