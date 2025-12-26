"""
Integration tests for Authorization API endpoints.

Tests the complete request-response cycle for authorization endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, MagicMock


@pytest.mark.integration
@pytest.mark.django_db
class TestAuthorizeAPI:
    """Integration tests for single authorization endpoint."""

    @patch("apps.authorization.views.authz_service")
    @patch("apps.authorization.authentication.IAMAuthentication.authenticate")
    def test_authorize_allow(self, mock_auth, mock_authz_service, api_client):
        """Test authorization check with ALLOW decision."""
        # Arrange
        mock_auth.return_value = (MagicMock(is_authenticated=True), None)
        mock_authz_service.authorize.return_value = {"decision": "ALLOW"}
        
        url = reverse("authorization:authorize")
        data = {
            "principal": {"id": "user-123", "type": "User"},
            "action": "User:read",
            "resource": {"type": "User", "id": "user-456"},
            "context": {},
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["decision"] == "ALLOW"
        mock_authz_service.authorize.assert_called_once()

    @patch("apps.authorization.views.authz_service")
    @patch("apps.authorization.authentication.IAMAuthentication.authenticate")
    def test_authorize_deny(self, mock_auth, mock_authz_service, api_client):
        """Test authorization check with DENY decision."""
        # Arrange
        mock_auth.return_value = (MagicMock(is_authenticated=True), None)
        mock_authz_service.authorize.return_value = {
            "decision": "DENY",
            "reasons": ["Insufficient permissions"],
        }
        
        url = reverse("authorization:authorize")
        data = {
            "principal": {"id": "user-123", "type": "User"},
            "action": "User:delete",
            "resource": {"type": "User", "id": "user-456"},
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["decision"] == "DENY"
        assert "reasons" in response.data

    @patch("apps.authorization.authentication.IAMAuthentication.authenticate")
    def test_authorize_validation_error(self, mock_auth, api_client):
        """Test authorization with invalid request data."""
        # Arrange
        mock_auth.return_value = (MagicMock(is_authenticated=True), None)
        url = reverse("authorization:authorize")
        data = {"invalid": "data"}  # Missing required fields

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_authorize_unauthorized(self, api_client):
        """Test authorization without authentication."""
        # Arrange
        url = reverse("authorization:authorize")
        data = {
            "principal": {"id": "user-123", "type": "User"},
            "action": "User:read",
            "resource": {"type": "User", "id": "user-456"},
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.django_db
class TestBatchAuthorizeAPI:
    """Integration tests for batch authorization endpoint."""

    @patch("apps.authorization.views.authz_service")
    @patch("apps.authorization.authentication.IAMAuthentication.authenticate")
    def test_batch_authorize_success(self, mock_auth, mock_authz_service, api_client):
        """Test batch authorization with all successful requests."""
        # Arrange
        mock_auth.return_value = (MagicMock(is_authenticated=True), None)
        mock_authz_service.batch_authorize.return_value = {
            "results": [
                {"decision": "ALLOW"},
                {"decision": "DENY", "reasons": ["Insufficient permissions"]},
            ]
        }
        
        url = reverse("authorization:batch-authorize")
        data = {
            "items": [
                {
                    "principal": {"id": "user-123", "type": "User"},
                    "action": "User:read",
                    "resource": {"type": "User", "id": "user-456"},
                },
                {
                    "principal": {"id": "user-123", "type": "User"},
                    "action": "User:delete",
                    "resource": {"type": "User", "id": "user-456"},
                },
            ]
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["decision"] == "ALLOW"
        assert response.data["results"][1]["decision"] == "DENY"

    @patch("apps.authorization.views.authz_service")
    @patch("apps.authorization.authentication.IAMAuthentication.authenticate")
    def test_batch_authorize_partial_failure(self, mock_auth, mock_authz_service, api_client):
        """Test batch authorization with partial failures."""
        # Arrange
        mock_auth.return_value = (MagicMock(is_authenticated=True), None)
        mock_authz_service.batch_authorize.return_value = {
            "results": [
                {"decision": "ALLOW"},
                {"error": {"code": "VALIDATION_FAILED", "message": "Invalid request"}},
            ]
        }
        
        url = reverse("authorization:batch-authorize")
        data = {
            "items": [
                {
                    "principal": {"id": "user-123", "type": "User"},
                    "action": "User:read",
                    "resource": {"type": "User", "id": "user-456"},
                },
                {
                    "principal": {"id": "user-123", "type": "User"},
                    "action": "User:write",
                    "resource": {"type": "User", "id": "user-456"},
                },
            ]
        }

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["decision"] == "ALLOW"
        assert "error" in response.data["results"][1]

    @patch("apps.authorization.authentication.IAMAuthentication.authenticate")
    def test_batch_authorize_exceeds_limit(self, mock_auth, api_client):
        """Test batch authorization with too many items."""
        # Arrange
        mock_auth.return_value = (MagicMock(is_authenticated=True), None)
        url = reverse("authorization:batch-authorize")
        # Create 31 items (exceeds limit of 30)
        items = [
            {
                "principal": {"id": f"user-{i}", "type": "User"},
                "action": "User:read",
                "resource": {"type": "User", "id": "user-456"},
            }
            for i in range(31)
        ]
        data = {"items": items}

        # Act
        response = api_client.post(url, data, format="json")

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
