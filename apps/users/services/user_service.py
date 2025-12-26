"""
User Management Service - Core business logic layer.

This service orchestrates user lifecycle management operations by:
- Interacting with AWS Cognito for user data operations
- Managing user attributes and status
- Providing clean abstractions for controllers
"""

import logging
from typing import Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

from apps.users.exceptions import (
    AuthorizationDeniedError,
    InvalidMFACodeError,
    MFAAlreadyEnabledError,
    TokenInvalidError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class UserService:
    """
    User Management Service for CRUD operations and lifecycle management.

    All user data is stored in AWS Cognito. This service abstracts Cognito
    operations and provides a clean interface for user management.
    """

    def __init__(self):
        """Initialize Cognito client with AWS SDK."""
        self.client = boto3.client(
            "cognito-idp",
            region_name=settings.AWS_REGION,
        )
        self.user_pool_id = settings.COGNITO_USER_POOL_ID

    def create_user(
        self,
        email: str,
        given_name: str,
        family_name: str,
        user_type: str = "end_user",
        phone_number: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new user (admin-initiated).

        User is created in FORCE_CHANGE_PASSWORD state and receives
        a temporary password via email.

        Args:
            email: User's email address (used as username)
            given_name: User's first name
            family_name: User's last name
            user_type: 'end_user' or 'admin'
            phone_number: Optional phone number in E.164 format

        Returns:
            dict with user details (user_id, email, status, etc.)

        Raises:
            UserAlreadyExistsError: If user with email already exists
            ValidationError: If input validation fails
        """
        try:
            user_attributes = [
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "given_name", "Value": given_name},
                {"Name": "family_name", "Value": family_name},
                {"Name": "custom:user_type", "Value": user_type},
            ]

            if phone_number:
                user_attributes.append({"Name": "phone_number", "Value": phone_number})

            response = self.client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=user_attributes,
                DesiredDeliveryMediums=["EMAIL"],
                MessageAction="SUPPRESS",  # We'll send custom email via notification service
            )

            user = response["User"]

            return self._format_user_response(user)

        except ClientError as e:
            self._handle_error(e)

    def get_user(self, user_id: str) -> dict[str, Any]:
        """
        Get user details by user ID.

        Args:
            user_id: User's Cognito sub (UUID)

        Returns:
            dict with user details

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        try:
            # List users with filter by sub attribute
            response = self.client.list_users(
                UserPoolId=self.user_pool_id,
                Filter=f'sub = "{user_id}"',
                Limit=1,
            )

            if not response.get("Users"):
                raise UserNotFoundError(f"User {user_id} not found")

            user = response["Users"][0]
            return self._format_user_response(user)

        except ClientError as e:
            self._handle_error(e)

    def list_users(
        self,
        limit: int = 60,
        pagination_token: str | None = None,
    ) -> dict[str, Any]:
        """
        List all users with pagination.

        Args:
            limit: Maximum number of users to return (1-60)
            pagination_token: Token for next page of results

        Returns:
            dict with 'users' list and optional 'next_token'
        """
        try:
            params = {
                "UserPoolId": self.user_pool_id,
                "Limit": min(limit, 60),
            }

            if pagination_token:
                params["PaginationToken"] = pagination_token

            response = self.client.list_users(**params)

            return {
                "users": [
                    self._format_user_response(user)
                    for user in response.get("Users", [])
                ],
                "next_token": response.get("PaginationToken"),
            }

        except ClientError as e:
            self._handle_error(e)

    def update_user(
        self,
        user_id: str,
        given_name: str | None = None,
        family_name: str | None = None,
        phone_number: str | None = None,
    ) -> dict[str, Any]:
        """
        Update user attributes.

        Note: Email and user_type are immutable.

        Args:
            user_id: User's Cognito sub (UUID)
            given_name: New first name (optional)
            family_name: New last name (optional)
            phone_number: New phone number (optional)

        Returns:
            dict with updated user details

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        # First, get the user's username (email)
        user = self.get_user(user_id)
        username = user["email"]

        try:
            user_attributes = []

            if given_name is not None:
                user_attributes.append({"Name": "given_name", "Value": given_name})
            if family_name is not None:
                user_attributes.append({"Name": "family_name", "Value": family_name})
            if phone_number is not None:
                user_attributes.append({"Name": "phone_number", "Value": phone_number})

            if user_attributes:
                self.client.admin_update_user_attributes(
                    UserPoolId=self.user_pool_id,
                    Username=username,
                    UserAttributes=user_attributes,
                )

            # Return updated user
            return self.get_user(user_id)

        except ClientError as e:
            self._handle_error(e)

    def delete_user(self, user_id: str) -> None:
        """
        Permanently delete a user from Cognito.

        ⚠️ This is a hard delete - user data cannot be recovered.
        All tokens are immediately invalidated.

        Args:
            user_id: User's Cognito sub (UUID)

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        # First, get the user's username (email)
        user = self.get_user(user_id)
        username = user["email"]

        try:
            self.client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=username,
            )

        except ClientError as e:
            self._handle_error(e)

    def disable_user(self, user_id: str) -> dict[str, Any]:
        """
        Disable a user account.

        Disabled users cannot authenticate. All active tokens remain
        valid but will be rejected when validated against user status.

        Args:
            user_id: User's Cognito sub (UUID)

        Returns:
            dict with updated user details

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        # First, get the user's username (email)
        user = self.get_user(user_id)
        username = user["email"]

        try:
            self.client.admin_disable_user(
                UserPoolId=self.user_pool_id,
                Username=username,
            )

            # Return updated user
            return self.get_user(user_id)

        except ClientError as e:
            self._handle_error(e)

    def enable_user(self, user_id: str) -> dict[str, Any]:
        """
        Enable a previously disabled user account.

        Args:
            user_id: User's Cognito sub (UUID)

        Returns:
            dict with updated user details

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        # First, get the user's username (email)
        user = self.get_user(user_id)
        username = user["email"]

        try:
            self.client.admin_enable_user(
                UserPoolId=self.user_pool_id,
                Username=username,
            )

            # Return updated user
            return self.get_user(user_id)

        except ClientError as e:
            self._handle_error(e)

    def setup_mfa(self, access_token: str) -> dict[str, Any]:
        """
        Setup TOTP MFA for a user.

        Returns a secret code that the user must enter into their
        authenticator app (Google Authenticator, Authy, etc.).

        Args:
            access_token: User's valid access token

        Returns:
            dict with 'secret_code' for authenticator app setup

        Raises:
            TokenInvalidError: If access token is invalid
            MFAAlreadyEnabledError: If MFA is already enabled
        """
        try:
            response = self.client.associate_software_token(
                AccessToken=access_token,
            )

            return {
                "secret_code": response["SecretCode"],
                "message": "Enter this code in your authenticator app, then verify with a TOTP code.",
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            if error_code == "InvalidParameterException":
                raise MFAAlreadyEnabledError("MFA is already enabled for this user")

            self._handle_error(e)

    def verify_mfa_setup(self, access_token: str, totp_code: str) -> dict[str, Any]:
        """
        Verify MFA setup with a TOTP code.

        Args:
            access_token: User's valid access token
            totp_code: 6-digit TOTP code from authenticator app

        Returns:
            dict with success message

        Raises:
            InvalidMFACodeError: If TOTP code is invalid
            TokenInvalidError: If access token is invalid
        """
        try:
            self.client.verify_software_token(
                AccessToken=access_token,
                UserCode=totp_code,
            )

            # Enable MFA for the user
            self.client.set_user_mfa_preference(
                AccessToken=access_token,
                SoftwareTokenMfaSettings={
                    "Enabled": True,
                    "PreferredMfa": True,
                },
            )

            return {"message": "MFA enabled successfully"}

        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            if error_code == "EnableSoftwareTokenMFAException":
                raise InvalidMFACodeError("Invalid TOTP code")

            self._handle_error(e)

    def get_user_by_token(self, access_token: str) -> dict[str, Any]:
        """
        Get user details from access token.

        Used for /me endpoints to get current user's profile.

        Args:
            access_token: User's valid access token

        Returns:
            dict with user details

        Raises:
            TokenInvalidError: If access token is invalid
        """
        try:
            response = self.client.get_user(AccessToken=access_token)

            # Build user dict from response
            attributes = {}
            for attr in response.get("UserAttributes", []):
                attributes[attr["Name"]] = attr["Value"]

            return {
                "user_id": attributes.get("sub"),
                "email": attributes.get("email"),
                "given_name": attributes.get("given_name"),
                "family_name": attributes.get("family_name"),
                "phone_number": attributes.get("phone_number"),
                "user_type": attributes.get("custom:user_type"),
                "email_verified": attributes.get("email_verified") == "true",
                "mfa_enabled": response.get("UserMFASettingList", []) != [],
            }

        except ClientError as e:
            self._handle_error(e)

    def _format_user_response(self, user: dict[str, Any]) -> dict[str, Any]:
        """
        Format Cognito user response into standardized user dict.

        Args:
            user: Raw Cognito user object

        Returns:
            dict with standardized user fields
        """
        # Extract attributes
        attributes = {}
        for attr in user.get("Attributes", []):
            attributes[attr["Name"]] = attr["Value"]

        # Determine status
        status = "Active"
        if not user.get("Enabled", True):
            status = "Disabled"
        elif user.get("UserStatus") == "UNCONFIRMED":
            status = "Unverified"
        elif user.get("UserStatus") == "FORCE_CHANGE_PASSWORD":
            status = "PasswordChangeRequired"

        return {
            "user_id": attributes.get("sub"),
            "email": attributes.get("email"),
            "given_name": attributes.get("given_name"),
            "family_name": attributes.get("family_name"),
            "phone_number": attributes.get("phone_number"),
            "user_type": attributes.get("custom:user_type"),
            "email_verified": attributes.get("email_verified") == "true",
            "status": status,
            "mfa_enabled": user.get("MFAOptions") is not None,
            "created_at": user.get("UserCreateDate").isoformat()
            if user.get("UserCreateDate")
            else None,
            "updated_at": user.get("UserLastModifiedDate").isoformat()
            if user.get("UserLastModifiedDate")
            else None,
        }

    def _handle_error(self, error: ClientError) -> None:
        """
        Translate Cognito errors to application exceptions.

        Args:
            error: Boto3 ClientError from Cognito

        Raises:
            Appropriate application exception
        """
        error_code = error.response["Error"]["Code"]
        error_message = error.response["Error"].get("Message", str(error))

        logger.warning(f"Cognito error: {error_code} - {error_message}")

        error_map = {
            "UserNotFoundException": UserNotFoundError,
            "UsernameExistsException": UserAlreadyExistsError,
            "InvalidParameterException": ValidationError,
            "NotAuthorizedException": TokenInvalidError,
            "TooManyRequestsException": ValidationError,
        }

        exception_class = error_map.get(error_code)

        if exception_class:
            raise exception_class(error_message)

        # Default to validation error
        raise ValidationError(error_message)


# Singleton instance for use across the application
user_service = UserService()
