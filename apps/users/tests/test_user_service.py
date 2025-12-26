"""
Unit tests for UserService.

Tests the user management service with mocked Cognito client.
"""

import pytest
from datetime import datetime
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch

from apps.users.exceptions import (
    InvalidMFACodeError,
    MFAAlreadyEnabledError,
    TokenInvalidError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from apps.users.services.user_service import UserService


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 Cognito client."""
    with patch("boto3.client") as mock_client:
        mock_cognito = MagicMock()
        mock_client.return_value = mock_cognito
        yield mock_cognito


@pytest.fixture
def user_service(mock_boto3_client):
    """Create a UserService with mocked boto3 client."""
    return UserService()


@pytest.fixture
def cognito_user_response():
    """Sample Cognito user response."""
    return {
        "Username": "test@example.com",
        "Enabled": True,
        "UserStatus": "CONFIRMED",
        "UserCreateDate": datetime(2024, 1, 1, 12, 0, 0),
        "UserLastModifiedDate": datetime(2024, 1, 2, 12, 0, 0),
        "Attributes": [
            {"Name": "sub", "Value": "123e4567-e89b-12d3-a456-426614174000"},
            {"Name": "email", "Value": "test@example.com"},
            {"Name": "given_name", "Value": "John"},
            {"Name": "family_name", "Value": "Doe"},
            {"Name": "email_verified", "Value": "true"},
            {"Name": "custom:user_type", "Value": "end_user"},
        ],
    }


@pytest.mark.unit
class TestUserServiceCreateUser:
    """Tests for UserService.create_user method."""

    def test_create_user_success(self, user_service, mock_boto3_client, cognito_user_response):
        """Test successful user creation."""
        # Arrange
        mock_boto3_client.admin_create_user.return_value = {"User": cognito_user_response}

        # Act
        result = user_service.create_user(
            email="test@example.com",
            given_name="John",
            family_name="Doe",
            user_type="end_user",
            phone_number="+12025551234",
        )

        # Assert
        mock_boto3_client.admin_create_user.assert_called_once()
        assert result["email"] == "test@example.com"
        assert result["given_name"] == "John"
        assert result["family_name"] == "Doe"

    def test_create_user_without_phone(self, user_service, mock_boto3_client, cognito_user_response):
        """Test user creation without phone number."""
        # Arrange
        mock_boto3_client.admin_create_user.return_value = {"User": cognito_user_response}

        # Act
        result = user_service.create_user(
            email="test@example.com",
            given_name="John",
            family_name="Doe",
        )

        # Assert
        call_args = mock_boto3_client.admin_create_user.call_args
        user_attributes = call_args[1]["UserAttributes"]
        phone_attrs = [attr for attr in user_attributes if attr["Name"] == "phone_number"]
        assert len(phone_attrs) == 0

    def test_create_user_already_exists(self, user_service, mock_boto3_client):
        """Test user creation when user already exists."""
        # Arrange
        error_response = {"Error": {"Code": "UsernameExistsException", "Message": "User already exists"}}
        mock_boto3_client.admin_create_user.side_effect = ClientError(
            error_response, "AdminCreateUser"
        )

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError):
            user_service.create_user(
                email="test@example.com",
                given_name="John",
                family_name="Doe",
            )


@pytest.mark.unit
class TestUserServiceGetUser:
    """Tests for UserService.get_user method."""

    def test_get_user_success(self, user_service, mock_boto3_client, cognito_user_response):
        """Test successful user retrieval."""
        # Arrange
        mock_boto3_client.list_users.return_value = {"Users": [cognito_user_response]}

        # Act
        result = user_service.get_user("123e4567-e89b-12d3-a456-426614174000")

        # Assert
        mock_boto3_client.list_users.assert_called_once()
        assert result["user_id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert result["email"] == "test@example.com"

    def test_get_user_not_found(self, user_service, mock_boto3_client):
        """Test user retrieval when user doesn't exist."""
        # Arrange
        mock_boto3_client.list_users.return_value = {"Users": []}

        # Act & Assert
        with pytest.raises(UserNotFoundError):
            user_service.get_user("nonexistent-id")


@pytest.mark.unit
class TestUserServiceListUsers:
    """Tests for UserService.list_users method."""

    def test_list_users_success(self, user_service, mock_boto3_client, cognito_user_response):
        """Test successful user listing."""
        # Arrange
        mock_boto3_client.list_users.return_value = {
            "Users": [cognito_user_response],
            "PaginationToken": "next-token",
        }

        # Act
        result = user_service.list_users(limit=10)

        # Assert
        mock_boto3_client.list_users.assert_called_once_with(
            UserPoolId=user_service.user_pool_id, Limit=10
        )
        assert len(result["users"]) == 1
        assert result["next_token"] == "next-token"

    def test_list_users_with_pagination(self, user_service, mock_boto3_client):
        """Test user listing with pagination token."""
        # Arrange
        mock_boto3_client.list_users.return_value = {"Users": []}

        # Act
        user_service.list_users(limit=20, pagination_token="token-123")

        # Assert
        mock_boto3_client.list_users.assert_called_once_with(
            UserPoolId=user_service.user_pool_id,
            Limit=20,
            PaginationToken="token-123",
        )


@pytest.mark.unit
class TestUserServiceUpdateUser:
    """Tests for UserService.update_user method."""

    def test_update_user_success(self, user_service, mock_boto3_client, cognito_user_response):
        """Test successful user update."""
        # Arrange
        mock_boto3_client.list_users.return_value = {"Users": [cognito_user_response]}
        mock_boto3_client.admin_update_user_attributes.return_value = {}

        # Act
        result = user_service.update_user(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            given_name="Jane",
            phone_number="+12025559999",
        )

        # Assert
        mock_boto3_client.admin_update_user_attributes.assert_called_once()
        call_args = mock_boto3_client.admin_update_user_attributes.call_args
        assert call_args[1]["Username"] == "test@example.com"

    def test_update_user_not_found(self, user_service, mock_boto3_client):
        """Test user update when user doesn't exist."""
        # Arrange
        mock_boto3_client.list_users.return_value = {"Users": []}

        # Act & Assert
        with pytest.raises(UserNotFoundError):
            user_service.update_user(user_id="nonexistent-id", given_name="Jane")


@pytest.mark.unit
class TestUserServiceDeleteUser:
    """Tests for UserService.delete_user method."""

    def test_delete_user_success(self, user_service, mock_boto3_client, cognito_user_response):
        """Test successful user deletion."""
        # Arrange
        mock_boto3_client.list_users.return_value = {"Users": [cognito_user_response]}
        mock_boto3_client.admin_delete_user.return_value = {}

        # Act
        user_service.delete_user("123e4567-e89b-12d3-a456-426614174000")

        # Assert
        mock_boto3_client.admin_delete_user.assert_called_once_with(
            UserPoolId=user_service.user_pool_id,
            Username="test@example.com",
        )


@pytest.mark.unit
class TestUserServiceDisableUser:
    """Tests for UserService.disable_user method."""

    def test_disable_user_success(self, user_service, mock_boto3_client, cognito_user_response):
        """Test successful user disabling."""
        # Arrange
        mock_boto3_client.list_users.return_value = {"Users": [cognito_user_response]}
        mock_boto3_client.admin_disable_user.return_value = {}

        # Act
        result = user_service.disable_user("123e4567-e89b-12d3-a456-426614174000")

        # Assert
        mock_boto3_client.admin_disable_user.assert_called_once_with(
            UserPoolId=user_service.user_pool_id,
            Username="test@example.com",
        )


@pytest.mark.unit
class TestUserServiceEnableUser:
    """Tests for UserService.enable_user method."""

    def test_enable_user_success(self, user_service, mock_boto3_client, cognito_user_response):
        """Test successful user enabling."""
        # Arrange
        mock_boto3_client.list_users.return_value = {"Users": [cognito_user_response]}
        mock_boto3_client.admin_enable_user.return_value = {}

        # Act
        result = user_service.enable_user("123e4567-e89b-12d3-a456-426614174000")

        # Assert
        mock_boto3_client.admin_enable_user.assert_called_once_with(
            UserPoolId=user_service.user_pool_id,
            Username="test@example.com",
        )


@pytest.mark.unit
class TestUserServiceSetupMFA:
    """Tests for UserService.setup_mfa method."""

    def test_setup_mfa_success(self, user_service, mock_boto3_client):
        """Test successful MFA setup initiation."""
        # Arrange
        mock_boto3_client.associate_software_token.return_value = {
            "SecretCode": "SECRET123ABC"
        }

        # Act
        result = user_service.setup_mfa("access-token-123")

        # Assert
        mock_boto3_client.associate_software_token.assert_called_once_with(
            AccessToken="access-token-123"
        )
        assert result["secret_code"] == "SECRET123ABC"

    def test_setup_mfa_already_enabled(self, user_service, mock_boto3_client):
        """Test MFA setup when MFA is already enabled."""
        # Arrange
        error_response = {
            "Error": {"Code": "InvalidParameterException", "Message": "MFA already enabled"}
        }
        mock_boto3_client.associate_software_token.side_effect = ClientError(
            error_response, "AssociateSoftwareToken"
        )

        # Act & Assert
        with pytest.raises(MFAAlreadyEnabledError):
            user_service.setup_mfa("access-token-123")


@pytest.mark.unit
class TestUserServiceVerifyMFASetup:
    """Tests for UserService.verify_mfa_setup method."""

    def test_verify_mfa_setup_success(self, user_service, mock_boto3_client):
        """Test successful MFA verification."""
        # Arrange
        mock_boto3_client.verify_software_token.return_value = {}
        mock_boto3_client.set_user_mfa_preference.return_value = {}

        # Act
        result = user_service.verify_mfa_setup("access-token-123", "123456")

        # Assert
        mock_boto3_client.verify_software_token.assert_called_once_with(
            AccessToken="access-token-123",
            UserCode="123456",
        )
        mock_boto3_client.set_user_mfa_preference.assert_called_once()

    def test_verify_mfa_setup_invalid_code(self, user_service, mock_boto3_client):
        """Test MFA verification with invalid code."""
        # Arrange
        error_response = {
            "Error": {"Code": "EnableSoftwareTokenMFAException", "Message": "Invalid code"}
        }
        mock_boto3_client.verify_software_token.side_effect = ClientError(
            error_response, "VerifySoftwareToken"
        )

        # Act & Assert
        with pytest.raises(InvalidMFACodeError):
            user_service.verify_mfa_setup("access-token-123", "invalid")


@pytest.mark.unit
class TestUserServiceGetUserByToken:
    """Tests for UserService.get_user_by_token method."""

    def test_get_user_by_token_success(self, user_service, mock_boto3_client):
        """Test successful user retrieval by token."""
        # Arrange
        mock_boto3_client.get_user.return_value = {
            "UserAttributes": [
                {"Name": "sub", "Value": "123e4567-e89b-12d3-a456-426614174000"},
                {"Name": "email", "Value": "test@example.com"},
                {"Name": "given_name", "Value": "John"},
                {"Name": "family_name", "Value": "Doe"},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "custom:user_type", "Value": "end_user"},
            ],
            "UserMFASettingList": ["SOFTWARE_TOKEN_MFA"],
        }

        # Act
        result = user_service.get_user_by_token("access-token-123")

        # Assert
        mock_boto3_client.get_user.assert_called_once_with(AccessToken="access-token-123")
        assert result["user_id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert result["email"] == "test@example.com"
        assert result["mfa_enabled"] is True

    def test_get_user_by_token_invalid_token(self, user_service, mock_boto3_client):
        """Test user retrieval with invalid token."""
        # Arrange
        error_response = {
            "Error": {"Code": "NotAuthorizedException", "Message": "Invalid token"}
        }
        mock_boto3_client.get_user.side_effect = ClientError(
            error_response, "GetUser"
        )

        # Act & Assert
        with pytest.raises(TokenInvalidError):
            user_service.get_user_by_token("invalid-token")


@pytest.mark.unit
class TestUserServiceFormatUserResponse:
    """Tests for UserService._format_user_response method."""

    def test_format_active_user(self, user_service):
        """Test formatting an active user."""
        # Arrange
        user = {
            "Enabled": True,
            "UserStatus": "CONFIRMED",
            "UserCreateDate": datetime(2024, 1, 1, 12, 0, 0),
            "Attributes": [
                {"Name": "sub", "Value": "user-123"},
                {"Name": "email", "Value": "test@example.com"},
                {"Name": "given_name", "Value": "John"},
                {"Name": "family_name", "Value": "Doe"},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "custom:user_type", "Value": "end_user"},
            ],
        }

        # Act
        result = user_service._format_user_response(user)

        # Assert
        assert result["status"] == "Active"
        assert result["email_verified"] is True

    def test_format_disabled_user(self, user_service):
        """Test formatting a disabled user."""
        # Arrange
        user = {
            "Enabled": False,
            "UserStatus": "CONFIRMED",
            "Attributes": [
                {"Name": "sub", "Value": "user-123"},
                {"Name": "email", "Value": "test@example.com"},
            ],
        }

        # Act
        result = user_service._format_user_response(user)

        # Assert
        assert result["status"] == "Disabled"

    def test_format_unconfirmed_user(self, user_service):
        """Test formatting an unconfirmed user."""
        # Arrange
        user = {
            "Enabled": True,
            "UserStatus": "UNCONFIRMED",
            "Attributes": [
                {"Name": "sub", "Value": "user-123"},
                {"Name": "email", "Value": "test@example.com"},
            ],
        }

        # Act
        result = user_service._format_user_response(user)

        # Assert
        assert result["status"] == "Unverified"
