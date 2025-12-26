"""
Integration tests for Authentication API endpoints.

Tests the complete request-response cycle for authentication endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, MagicMock


@pytest.mark.integration
@pytest.mark.django_db
class TestRegisterAPI:
    """Integration tests for user registration endpoint."""

    @patch("apps.authentication.views.get_auth_service")
    def test_register_success(self, mock_get_service, api_client):
        """Test successful user registration."""
        # Arrange
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.register.return_value = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "status": "UNCONFIRMED",
            "message": "User registered successfully",
        }

        url = reverse("auth:register")
        data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "test@example.com"
        mock_service.register.assert_called_once()

    @patch("apps.authentication.views.get_auth_service")
    def test_register_validation_error(self, mock_get_service, api_client):
        """Test registration with invalid data."""
        # Arrange
        url = reverse("auth:register")
        data = {"email": "invalid-email"}  # Missing required fields

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.django_db
class TestLoginAPI:
    """Integration tests for login endpoint."""

    @patch("apps.authentication.views.get_auth_service")
    def test_login_success(self, mock_get_service, api_client, valid_access_token):
        """Test successful login."""
        # Arrange
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.login.return_value = {
            "access_token": valid_access_token,
            "id_token": "id-token",
            "refresh_token": "refresh-token",
            "expires_in": 900,
            "token_type": "Bearer",
        }

        url = reverse("auth:login")
        data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data
        mock_service.login.assert_called_once()

    @patch("apps.authentication.views.get_auth_service")
    def test_login_mfa_required(self, mock_get_service, api_client):
        """Test login when MFA is required."""
        # Arrange
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.login.return_value = {
            "challenge": "MFA_REQUIRED",
            "session_token": "session-token-123",
        }

        url = reverse("auth:login")
        data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["challenge"] == "MFA_REQUIRED"
        assert "session_token" in response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestVerifyEmailAPI:
    """Integration tests for email verification endpoint."""

    @patch("apps.authentication.views.get_auth_service")
    def test_verify_email_success(self, mock_get_service, api_client):
        """Test successful email verification."""
        # Arrange
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.verify_email.return_value = {
            "status": "success",
            "message": "Email verified successfully",
        }

        url = reverse("auth:verify-email")
        data = {
            "email": "test@example.com",
            "code": "123456",
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"


@pytest.mark.integration
@pytest.mark.django_db
class TestPasswordResetAPI:
    """Integration tests for password reset endpoints."""

    @patch("apps.authentication.views.get_auth_service")
    def test_forgot_password_success(self, mock_get_service, api_client):
        """Test successful password reset request."""
        # Arrange
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.forgot_password.return_value = {
            "message": "Password reset code sent",
        }

        url = reverse("auth:forgot-password")
        data = {"email": "test@example.com"}

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    @patch("apps.authentication.views.get_auth_service")
    def test_reset_password_success(self, mock_get_service, api_client):
        """Test successful password reset."""
        # Arrange
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.reset_password.return_value = {
            "message": "Password reset successfully",
        }

        url = reverse("auth:reset-password")
        data = {
            "email": "test@example.com",
            "code": "123456",
            "new_password": "NewSecurePass123!",
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestTokenRefreshAPI:
    """Integration tests for token refresh endpoint."""

    @patch("apps.authentication.views.get_auth_service")
    def test_refresh_token_success(
        self, mock_get_service, api_client, valid_access_token
    ):
        """Test successful token refresh."""
        # Arrange
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.refresh_token.return_value = {
            "access_token": valid_access_token,
            "id_token": "new-id-token",
            "expires_in": 900,
            "token_type": "Bearer",
        }

        url = reverse("auth:token-refresh")
        data = {"refresh_token": "refresh-token-123"}

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestLogoutAPI:
    """Integration tests for logout endpoint."""

    @patch("apps.authentication.backends.CognitoJWTAuthentication.authenticate")
    @patch("apps.authentication.views.get_auth_service")
    def test_logout_success(
        self, mock_get_service, mock_authenticate, api_client, valid_access_token
    ):
        """Test successful logout."""
        # Arrange
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.logout.return_value = None

        # Mock authentication to return a user
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_authenticate.return_value = (mock_user, None)

        url = reverse("auth:logout")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {valid_access_token}")

        # Act
        response = api_client.post(url, format="json")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.integration
@pytest.mark.django_db
class TestMFAVerifyAPI:
    """Integration tests for MFA verification endpoint."""

    @patch("apps.authentication.views.get_auth_service")
    def test_mfa_verify_success(self, mock_get_service, api_client, valid_access_token):
        """Test successful MFA verification."""
        # Arrange
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.verify_mfa.return_value = {
            "access_token": valid_access_token,
            "id_token": "id-token",
            "refresh_token": "refresh-token",
            "expires_in": 900,
            "token_type": "Bearer",
        }

        url = reverse("auth:mfa-verify")
        data = {
            "session_token": "session-token-123",
            "mfa_code": "123456",
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data
