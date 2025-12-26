"""
Unit tests for AuthService.

Tests the authentication service orchestration layer with mocked CognitoClient.
"""

import pytest
from unittest.mock import MagicMock

from apps.authentication.services import AuthService


@pytest.mark.unit
class TestAuthServiceRegister:
    """Tests for AuthService.register method."""

    def test_register_success(self, auth_service, mock_cognito_client):
        """Test successful user registration."""
        # Arrange
        data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+12025551234",
        }
        expected_result = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "status": "UNCONFIRMED",
            "message": "User registered successfully. Please check your email for verification code.",
        }
        mock_cognito_client.sign_up.return_value = expected_result

        # Act
        result = auth_service.register(data)

        # Assert
        mock_cognito_client.sign_up.assert_called_once_with(
            email="test@example.com",
            password="SecurePass123!",
            attributes={
                "given_name": "John",
                "family_name": "Doe",
                "phone_number": "+12025551234",
                "custom:user_type": "end_user",
            },
        )
        assert result == expected_result

    def test_register_without_phone(self, auth_service, mock_cognito_client):
        """Test registration without phone number."""
        # Arrange
        data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
        }
        expected_result = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "status": "UNCONFIRMED",
            "message": "User registered successfully.",
        }
        mock_cognito_client.sign_up.return_value = expected_result

        # Act
        result = auth_service.register(data)

        # Assert
        mock_cognito_client.sign_up.assert_called_once()
        call_args = mock_cognito_client.sign_up.call_args
        assert "phone_number" not in call_args[1]["attributes"]
        assert result == expected_result


@pytest.mark.unit
class TestAuthServiceVerifyEmail:
    """Tests for AuthService.verify_email method."""

    def test_verify_email_success(self, auth_service, mock_cognito_client):
        """Test successful email verification."""
        # Arrange
        expected_result = {
            "status": "success",
            "message": "Email verified successfully",
        }
        mock_cognito_client.confirm_sign_up.return_value = expected_result

        # Act
        result = auth_service.verify_email("test@example.com", "123456")

        # Assert
        mock_cognito_client.confirm_sign_up.assert_called_once_with(
            "test@example.com", "123456"
        )
        assert result == expected_result


@pytest.mark.unit
class TestAuthServiceResendVerification:
    """Tests for AuthService.resend_verification method."""

    def test_resend_verification_success(self, auth_service, mock_cognito_client):
        """Test successful verification code resend."""
        # Arrange
        expected_result = {"message": "Verification code sent to test@example.com"}
        mock_cognito_client.resend_confirmation_code.return_value = expected_result

        # Act
        result = auth_service.resend_verification("test@example.com")

        # Assert
        mock_cognito_client.resend_confirmation_code.assert_called_once_with(
            "test@example.com"
        )
        assert result == expected_result


@pytest.mark.unit
class TestAuthServiceLogin:
    """Tests for AuthService.login method."""

    def test_login_success(self, auth_service, mock_cognito_client, valid_tokens):
        """Test successful login with tokens."""
        # Arrange
        data = {"email": "test@example.com", "password": "SecurePass123!"}
        mock_cognito_client.initiate_auth.return_value = {"tokens": valid_tokens}

        # Act
        result = auth_service.login(data)

        # Assert
        mock_cognito_client.initiate_auth.assert_called_once_with(
            email="test@example.com",
            password="SecurePass123!",
        )
        assert result == valid_tokens

    def test_login_mfa_required(self, auth_service, mock_cognito_client):
        """Test login when MFA is required."""
        # Arrange
        data = {"email": "test@example.com", "password": "SecurePass123!"}
        mock_cognito_client.initiate_auth.return_value = {
            "challenge": "MFA_REQUIRED",
            "session": "session-token-123",
        }

        # Act
        result = auth_service.login(data)

        # Assert
        assert result == {
            "challenge": "MFA_REQUIRED",
            "session_token": "session-token-123",
        }

    def test_login_new_password_required(self, auth_service, mock_cognito_client):
        """Test login when new password is required."""
        # Arrange
        data = {"email": "test@example.com", "password": "TempPass123!"}
        mock_cognito_client.initiate_auth.return_value = {
            "challenge": "NEW_PASSWORD_REQUIRED",
            "session": "session-token-456",
        }

        # Act
        result = auth_service.login(data)

        # Assert
        assert result == {
            "challenge": "NEW_PASSWORD_REQUIRED",
            "session_token": "session-token-456",
        }


@pytest.mark.unit
class TestAuthServiceVerifyMFA:
    """Tests for AuthService.verify_mfa method."""

    def test_verify_mfa_success(self, auth_service, mock_cognito_client, valid_tokens):
        """Test successful MFA verification."""
        # Arrange
        data = {"session_token": "session-123", "mfa_code": "123456"}
        mock_cognito_client.respond_to_auth_challenge.return_value = valid_tokens

        # Act
        result = auth_service.verify_mfa(data)

        # Assert
        mock_cognito_client.respond_to_auth_challenge.assert_called_once_with(
            session="session-123",
            mfa_code="123456",
            challenge_name="SOFTWARE_TOKEN_MFA",
        )
        assert result == valid_tokens


@pytest.mark.unit
class TestAuthServiceCompleteNewPassword:
    """Tests for AuthService.complete_new_password method."""

    def test_complete_new_password_success(
        self, auth_service, mock_cognito_client, valid_tokens
    ):
        """Test successful new password completion."""
        # Arrange
        data = {"session_token": "session-456", "new_password": "NewPass123!"}
        mock_cognito_client.respond_to_auth_challenge.return_value = valid_tokens

        # Act
        result = auth_service.complete_new_password(data)

        # Assert
        mock_cognito_client.respond_to_auth_challenge.assert_called_once_with(
            session="session-456",
            new_password="NewPass123!",
            challenge_name="NEW_PASSWORD_REQUIRED",
        )
        assert result == valid_tokens


@pytest.mark.unit
class TestAuthServiceRefreshToken:
    """Tests for AuthService.refresh_token method."""

    def test_refresh_token_success(
        self, auth_service, mock_cognito_client, valid_tokens
    ):
        """Test successful token refresh."""
        # Arrange
        data = {"refresh_token": "refresh-token-123"}
        mock_cognito_client.refresh_tokens.return_value = valid_tokens

        # Act
        result = auth_service.refresh_token(data)

        # Assert
        mock_cognito_client.refresh_tokens.assert_called_once_with("refresh-token-123")
        assert result == valid_tokens


@pytest.mark.unit
class TestAuthServiceLogout:
    """Tests for AuthService.logout method."""

    def test_logout_success(self, auth_service, mock_cognito_client):
        """Test successful logout."""
        # Arrange
        access_token = "access-token-123"

        # Act
        auth_service.logout(access_token)

        # Assert
        mock_cognito_client.global_sign_out.assert_called_once_with(access_token)


@pytest.mark.unit
class TestAuthServiceForgotPassword:
    """Tests for AuthService.forgot_password method."""

    def test_forgot_password_success(self, auth_service, mock_cognito_client):
        """Test successful password reset request."""
        # Arrange
        expected_result = {
            "message": "Password reset code sent to test@example.com",
        }
        mock_cognito_client.forgot_password.return_value = expected_result

        # Act
        result = auth_service.forgot_password("test@example.com")

        # Assert
        mock_cognito_client.forgot_password.assert_called_once_with("test@example.com")
        assert result == expected_result


@pytest.mark.unit
class TestAuthServiceResetPassword:
    """Tests for AuthService.reset_password method."""

    def test_reset_password_success(self, auth_service, mock_cognito_client):
        """Test successful password reset."""
        # Arrange
        expected_result = {"message": "Password reset successfully"}
        mock_cognito_client.confirm_forgot_password.return_value = expected_result

        # Act
        result = auth_service.reset_password(
            email="test@example.com",
            code="123456",
            new_password="NewSecurePass123!",
        )

        # Assert
        mock_cognito_client.confirm_forgot_password.assert_called_once_with(
            "test@example.com", "123456", "NewSecurePass123!"
        )
        assert result == expected_result


@pytest.mark.unit
class TestAuthServiceGetUserInfo:
    """Tests for AuthService.get_user_info method."""

    def test_get_user_info_success(self, auth_service, mock_cognito_client):
        """Test successful user info retrieval."""
        # Arrange
        expected_result = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "given_name": "John",
            "family_name": "Doe",
        }
        mock_cognito_client.get_user.return_value = expected_result

        # Act
        result = auth_service.get_user_info("access-token-123")

        # Assert
        mock_cognito_client.get_user.assert_called_once_with("access-token-123")
        assert result == expected_result
