"""
Integration tests for User Management API endpoints.

Tests the complete request-response cycle for user management endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, MagicMock


@pytest.mark.integration
@pytest.mark.django_db
class TestUserListCreateAPI:
    """Integration tests for user list and create endpoints."""

    @patch("apps.users.views.user_service")
    def test_list_users_success(self, mock_user_service, api_client, sample_user_data):
        """Test successful user listing."""
        # Arrange
        mock_user_service.list_users.return_value = {
            "users": [sample_user_data],
            "next_token": None,
        }

        url = reverse("users:user-list-create")
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))

        # Act
        response = api_client.get(url)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["users"]) == 1
        mock_user_service.list_users.assert_called_once()

    @patch("apps.users.views.user_service")
    def test_create_user_success(self, mock_user_service, api_client, sample_user_data):
        """Test successful user creation."""
        # Arrange
        mock_user_service.create_user.return_value = sample_user_data

        url = reverse("users:user-list-create")
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))
        data = {
            "email": "newuser@example.com",
            "given_name": "New",
            "family_name": "User",
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == sample_user_data["email"]


@pytest.mark.integration
@pytest.mark.django_db
class TestUserDetailAPI:
    """Integration tests for user detail endpoints."""

    @patch("apps.users.views.user_service")
    def test_get_user_success(self, mock_user_service, api_client, sample_user_data):
        """Test successful user retrieval."""
        # Arrange
        mock_user_service.get_user.return_value = sample_user_data

        url = reverse(
            "users:user-detail",
            kwargs={"user_id": "123e4567-e89b-12d3-a456-426614174000"},
        )
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))

        # Act
        response = api_client.get(url)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_id"] == sample_user_data["user_id"]

    @patch("apps.users.views.user_service")
    def test_update_user_success(self, mock_user_service, api_client, sample_user_data):
        """Test successful user update."""
        # Arrange
        updated_data = sample_user_data.copy()
        updated_data["given_name"] = "Jane"
        mock_user_service.update_user.return_value = updated_data

        url = reverse(
            "users:user-detail",
            kwargs={"user_id": "123e4567-e89b-12d3-a456-426614174000"},
        )
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))
        data = {"given_name": "Jane"}

        # Act
        response = api_client.put(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["given_name"] == "Jane"

    @patch("apps.users.views.user_service")
    def test_delete_user_success(self, mock_user_service, api_client):
        """Test successful user deletion."""
        # Arrange
        mock_user_service.delete_user.return_value = None

        url = reverse(
            "users:user-detail",
            kwargs={"user_id": "123e4567-e89b-12d3-a456-426614174000"},
        )
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))

        # Act
        response = api_client.delete(url)

        # Assert
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.django_db
class TestUserDisableEnableAPI:
    """Integration tests for user disable/enable endpoints."""

    @patch("apps.users.views.user_service")
    def test_disable_user_success(
        self, mock_user_service, api_client, sample_user_data
    ):
        """Test successful user disabling."""
        # Arrange
        disabled_data = sample_user_data.copy()
        disabled_data["status"] = "Disabled"
        mock_user_service.disable_user.return_value = disabled_data

        url = reverse(
            "users:user-disable",
            kwargs={"user_id": "123e4567-e89b-12d3-a456-426614174000"},
        )
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))

        # Act
        response = api_client.post(url)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "Disabled"

    @patch("apps.users.views.user_service")
    def test_enable_user_success(self, mock_user_service, api_client, sample_user_data):
        """Test successful user enabling."""
        # Arrange
        mock_user_service.enable_user.return_value = sample_user_data

        url = reverse(
            "users:user-enable",
            kwargs={"user_id": "123e4567-e89b-12d3-a456-426614174000"},
        )
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))

        # Act
        response = api_client.post(url)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "Active"


@pytest.mark.integration
@pytest.mark.django_db
class TestMeAPI:
    """Integration tests for /me endpoints."""

    @patch("apps.users.views.user_service")
    def test_get_me_success(
        self, mock_user_service, api_client, sample_user_data, valid_access_token
    ):
        """Test successful profile retrieval."""
        # Arrange
        mock_user_service.get_user_by_token.return_value = sample_user_data

        url = reverse("users:me")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {valid_access_token}")
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))

        # Act
        response = api_client.get(url)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == sample_user_data["email"]

    @patch("apps.users.views.user_service")
    def test_update_me_success(
        self, mock_user_service, api_client, sample_user_data, valid_access_token
    ):
        """Test successful profile update."""
        # Arrange
        updated_data = sample_user_data.copy()
        updated_data["given_name"] = "Jane"
        mock_user_service.get_user_by_token.return_value = sample_user_data
        mock_user_service.update_user.return_value = updated_data

        url = reverse("users:me")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {valid_access_token}")
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))
        data = {"given_name": "Jane"}

        # Act
        response = api_client.put(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["given_name"] == "Jane"


@pytest.mark.integration
@pytest.mark.django_db
class TestMFASetupAPI:
    """Integration tests for MFA setup endpoint."""

    @patch("apps.users.views.user_service")
    def test_mfa_setup_initiate(
        self, mock_user_service, api_client, valid_access_token
    ):
        """Test MFA setup initiation."""
        # Arrange
        mock_user_service.setup_mfa.return_value = {
            "secret_code": "SECRET123ABC",
            "message": "Enter this code in your authenticator app",
        }

        url = reverse("users:mfa-setup")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {valid_access_token}")
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))

        # Act
        response = api_client.post(url, {}, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "secret_code" in response.data

    @patch("apps.users.views.user_service")
    def test_mfa_setup_verify(self, mock_user_service, api_client, valid_access_token):
        """Test MFA setup verification."""
        # Arrange
        mock_user_service.verify_mfa_setup.return_value = {
            "message": "MFA enabled successfully",
        }

        url = reverse("users:mfa-setup")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {valid_access_token}")
        api_client.force_authenticate(user=MagicMock(is_authenticated=True))
        data = {"totp_code": "123456"}

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
