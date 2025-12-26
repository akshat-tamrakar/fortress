"""
AWS Cognito client abstraction.

Encapsulates all Cognito SDK operations and translates Cognito-specific
exceptions to application exceptions.
"""

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

from ..exceptions import (
    AccountLockedError,
    DependencyUnavailableError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidMFACodeError,
    InvalidVerificationCodeError,
    PasswordTooWeakError,
    SessionExpiredError,
    TokenInvalidError,
    UserAlreadyExistsError,
    UserDisabledError,
    UserNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class CognitoClient:
    """
    Client for AWS Cognito operations.

    Abstracts all Cognito SDK calls and provides consistent error handling.
    """

    def __init__(self):
        self.client = boto3.client(
            "cognito-idp",
            region_name=settings.AWS_REGION,
        )
        self.user_pool_id = settings.COGNITO_USER_POOL_ID
        self.client_id = settings.COGNITO_CLIENT_ID

    def sign_up(
        self,
        email: str,
        password: str,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a new user in Cognito.

        Args:
            email: User's email address (used as username)
            password: User's password
            attributes: Additional user attributes (given_name, family_name, etc.)

        Returns:
            dict with user_id, email, status, and message
        """
        try:
            user_attributes = [
                {"Name": "email", "Value": email},
            ]

            for key, value in attributes.items():
                if value:  # Only add non-empty attributes
                    user_attributes.append({"Name": key, "Value": str(value)})

            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=email,
                Password=password,
                UserAttributes=user_attributes,
            )

            return {
                "user_id": response["UserSub"],
                "email": email,
                "status": "UNCONFIRMED",
                "message": "Verification email sent. Please check your inbox.",
            }

        except ClientError as e:
            self._handle_error(e)

    def confirm_sign_up(self, email: str, code: str) -> dict[str, Any]:
        """
        Confirm user registration with verification code.

        Args:
            email: User's email address
            code: Verification code from email

        Returns:
            dict with status and message
        """
        try:
            self.client.confirm_sign_up(
                ClientId=self.client_id,
                Username=email,
                ConfirmationCode=code,
            )

            return {
                "status": "CONFIRMED",
                "message": "Email verified successfully. You can now log in.",
            }

        except ClientError as e:
            self._handle_error(e)

    def resend_confirmation_code(self, email: str) -> dict[str, Any]:
        """
        Resend verification email.

        Args:
            email: User's email address

        Returns:
            dict with message
        """
        try:
            self.client.resend_confirmation_code(
                ClientId=self.client_id,
                Username=email,
            )

            return {"message": "Verification email sent. Please check your inbox."}

        except ClientError as e:
            self._handle_error(e)

    def initiate_auth(self, email: str, password: str) -> dict[str, Any]:
        """
        Authenticate user with email and password.

        Args:
            email: User's email address
            password: User's password

        Returns:
            dict with either:
            - tokens (access_token, id_token, refresh_token, expires_in, token_type)
            - challenge (MFA_REQUIRED or NEW_PASSWORD_REQUIRED) with session
        """
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": email,
                    "PASSWORD": password,
                },
            )

            # Check for challenges
            if "ChallengeName" in response:
                challenge_name = response["ChallengeName"]

                if challenge_name == "SOFTWARE_TOKEN_MFA":
                    return {
                        "challenge": "MFA_REQUIRED",
                        "session": response["Session"],
                    }

                if challenge_name == "NEW_PASSWORD_REQUIRED":
                    return {
                        "challenge": "NEW_PASSWORD_REQUIRED",
                        "session": response["Session"],
                    }

                # Unknown challenge
                logger.warning(f"Unknown Cognito challenge: {challenge_name}")
                raise ValidationError(
                    f"Unexpected authentication challenge: {challenge_name}"
                )

            # Successful authentication
            return {"tokens": self._extract_tokens(response["AuthenticationResult"])}

        except ClientError as e:
            self._handle_error(e)

    def respond_to_auth_challenge(
        self,
        session: str,
        mfa_code: str | None = None,
        new_password: str | None = None,
        challenge_name: str = "SOFTWARE_TOKEN_MFA",
    ) -> dict[str, Any]:
        """
        Respond to authentication challenge (MFA or new password).

        Args:
            session: Session token from initiate_auth
            mfa_code: TOTP code (for MFA challenge)
            new_password: New password (for NEW_PASSWORD_REQUIRED challenge)
            challenge_name: Type of challenge

        Returns:
            dict with tokens
        """
        try:
            challenge_responses = {}

            if challenge_name == "SOFTWARE_TOKEN_MFA" and mfa_code:
                challenge_responses["SOFTWARE_TOKEN_MFA_CODE"] = mfa_code
            elif challenge_name == "NEW_PASSWORD_REQUIRED" and new_password:
                challenge_responses["NEW_PASSWORD"] = new_password

            response = self.client.respond_to_auth_challenge(
                ClientId=self.client_id,
                ChallengeName=challenge_name,
                Session=session,
                ChallengeResponses=challenge_responses,
            )

            return self._extract_tokens(response["AuthenticationResult"])

        except ClientError as e:
            self._handle_error(e)

    def refresh_tokens(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            dict with new tokens (access_token, id_token, expires_in, token_type)
        """
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={
                    "REFRESH_TOKEN": refresh_token,
                },
            )

            return self._extract_tokens(response["AuthenticationResult"])

        except ClientError as e:
            self._handle_error(e)

    def global_sign_out(self, access_token: str) -> None:
        """
        Revoke all tokens for user (global sign out).

        Args:
            access_token: Valid access token
        """
        try:
            self.client.global_sign_out(AccessToken=access_token)

        except ClientError as e:
            self._handle_error(e)

    def forgot_password(self, email: str) -> dict[str, Any]:
        """
        Initiate password reset flow.

        Note: Always returns success to prevent user enumeration.

        Args:
            email: User's email address

        Returns:
            dict with message
        """
        try:
            self.client.forgot_password(
                ClientId=self.client_id,
                Username=email,
            )

            return {
                "message": "If the email exists, a password reset code has been sent."
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            # Don't reveal if user exists
            if error_code in ("UserNotFoundException", "InvalidParameterException"):
                return {
                    "message": "If the email exists, a password reset code has been sent."
                }

            self._handle_error(e)

    def confirm_forgot_password(
        self,
        email: str,
        code: str,
        new_password: str,
    ) -> dict[str, Any]:
        """
        Confirm password reset with code and new password.

        Args:
            email: User's email address
            code: Reset code from email
            new_password: New password

        Returns:
            dict with message
        """
        try:
            self.client.confirm_forgot_password(
                ClientId=self.client_id,
                Username=email,
                ConfirmationCode=code,
                Password=new_password,
            )

            return {"message": "Password reset successfully. You can now log in."}

        except ClientError as e:
            self._handle_error(e)

    def get_user(self, access_token: str) -> dict[str, Any]:
        """
        Get user details from access token.

        Args:
            access_token: Valid access token

        Returns:
            dict with user attributes
        """
        try:
            response = self.client.get_user(AccessToken=access_token)

            attributes = {}
            for attr in response.get("UserAttributes", []):
                attributes[attr["Name"]] = attr["Value"]

            return {
                "username": response["Username"],
                "attributes": attributes,
            }

        except ClientError as e:
            self._handle_error(e)

    def _extract_tokens(self, auth_result: dict[str, Any]) -> dict[str, Any]:
        """Extract tokens from Cognito authentication result."""
        return {
            "access_token": auth_result["AccessToken"],
            "id_token": auth_result["IdToken"],
            "refresh_token": auth_result.get("RefreshToken"),
            "expires_in": auth_result["ExpiresIn"],
            "token_type": auth_result.get("TokenType", "Bearer"),
        }

    def _handle_error(self, error: ClientError) -> None:
        """
        Translate Cognito errors to application exceptions.

        Args:
            error: Boto3 ClientError from Cognito

        Raises:
            Appropriate AuthenticationError subclass
        """
        error_code = error.response["Error"]["Code"]
        error_message = error.response["Error"].get("Message", str(error))

        logger.warning(f"Cognito error: {error_code} - {error_message}")

        error_map = {
            "UsernameExistsException": UserAlreadyExistsError,
            "UserNotFoundException": UserNotFoundError,
            "NotAuthorizedException": InvalidCredentialsError,
            "UserNotConfirmedException": EmailNotVerifiedError,
            "CodeMismatchException": InvalidVerificationCodeError,
            "ExpiredCodeException": InvalidVerificationCodeError,
            "InvalidPasswordException": PasswordTooWeakError,
            "InvalidParameterException": ValidationError,
            "TooManyRequestsException": AccountLockedError,
            "LimitExceededException": AccountLockedError,
            "PasswordResetRequiredException": InvalidCredentialsError,
            "UserDisabledException": UserDisabledError,
        }

        # MFA-specific errors
        if error_code == "NotAuthorizedException":
            if "Invalid session" in error_message:
                raise SessionExpiredError(error_message)
            if "Invalid code" in error_message or "Code mismatch" in error_message:
                raise InvalidMFACodeError(error_message)

        # Token-specific errors
        if error_code == "NotAuthorizedException":
            if "Access Token" in error_message or "token" in error_message.lower():
                raise TokenInvalidError(error_message)

        exception_class = error_map.get(error_code)

        if exception_class:
            raise exception_class(error_message)

        # Service unavailable errors
        if error_code in ("ServiceUnavailable", "InternalErrorException"):
            raise DependencyUnavailableError(error_message)

        # Default to generic error
        raise InvalidCredentialsError(error_message)
