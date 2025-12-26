"""
Unit tests for AuthzService.

Tests the authorization service orchestration layer with mocked dependencies.
"""

import pytest
from unittest.mock import MagicMock

from apps.authorization.exceptions import AuthorizationError, AVPUnavailableError
from apps.authorization.services.authz_service import AuthzService


@pytest.fixture
def mock_avp_client():
    """Create a mock AVP client."""
    return MagicMock()


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    return MagicMock()


@pytest.fixture
def authz_service(mock_avp_client, mock_cache_service):
    """Create an AuthzService with mocked dependencies."""
    return AuthzService(
        avp_client=mock_avp_client,
        cache_service=mock_cache_service,
    )


@pytest.fixture
def valid_authz_request():
    """Valid authorization request data."""
    return {
        "principal": {"id": "user-123", "type": "User"},
        "action": "User:read",
        "resource": {"type": "User", "id": "user-456"},
        "context": {},
    }


@pytest.mark.unit
class TestAuthzServiceBuildCacheKey:
    """Tests for AuthzService._build_cache_key method."""

    def test_build_cache_key(self, authz_service, valid_authz_request):
        """Test cache key generation."""
        # Act
        cache_key = authz_service._build_cache_key(valid_authz_request)

        # Assert
        assert cache_key == "authz:user-123:User:read:User:user-456"

    def test_build_cache_key_with_numeric_ids(self, authz_service):
        """Test cache key generation with numeric IDs."""
        # Arrange
        data = {
            "principal": {"id": 123, "type": "User"},
            "action": "Document:write",
            "resource": {"type": "Document", "id": 456},
        }

        # Act
        cache_key = authz_service._build_cache_key(data)

        # Assert
        assert cache_key == "authz:123:Document:write:Document:456"


@pytest.mark.unit
class TestAuthzServiceAuthorize:
    """Tests for AuthzService.authorize method."""

    def test_authorize_cache_hit(
        self, authz_service, mock_avp_client, mock_cache_service, valid_authz_request
    ):
        """Test authorization with cache hit."""
        # Arrange
        cached_result = {"decision": "ALLOW"}
        mock_cache_service.get.return_value = cached_result

        # Act
        result = authz_service.authorize(valid_authz_request)

        # Assert
        mock_cache_service.get.assert_called_once()
        mock_avp_client.is_authorized.assert_not_called()
        assert result == cached_result

    def test_authorize_cache_miss_allow(
        self, authz_service, mock_avp_client, mock_cache_service, valid_authz_request
    ):
        """Test authorization with cache miss and ALLOW decision."""
        # Arrange
        mock_cache_service.get.return_value = None
        avp_result = {"decision": "ALLOW"}
        mock_avp_client.is_authorized.return_value = avp_result

        # Act
        result = authz_service.authorize(valid_authz_request)

        # Assert
        mock_cache_service.get.assert_called_once()
        mock_avp_client.is_authorized.assert_called_once_with(
            principal=valid_authz_request["principal"],
            action=valid_authz_request["action"],
            resource=valid_authz_request["resource"],
            context={},
        )
        mock_cache_service.set.assert_called_once()
        assert result == avp_result

    def test_authorize_cache_miss_deny(
        self, authz_service, mock_avp_client, mock_cache_service, valid_authz_request
    ):
        """Test authorization with cache miss and DENY decision."""
        # Arrange
        mock_cache_service.get.return_value = None
        avp_result = {"decision": "DENY", "reasons": ["Insufficient permissions"]}
        mock_avp_client.is_authorized.return_value = avp_result

        # Act
        result = authz_service.authorize(valid_authz_request)

        # Assert
        mock_avp_client.is_authorized.assert_called_once()
        mock_cache_service.set.assert_called_once()
        assert result == avp_result

    def test_authorize_avp_unavailable_fail_closed(
        self, authz_service, mock_avp_client, mock_cache_service, valid_authz_request
    ):
        """Test authorization fails closed when AVP is unavailable."""
        # Arrange
        mock_cache_service.get.return_value = None
        mock_avp_client.is_authorized.side_effect = AVPUnavailableError(
            "AVP service unavailable"
        )

        # Act
        result = authz_service.authorize(valid_authz_request)

        # Assert
        assert result["decision"] == "DENY"
        assert "Service unavailable" in result["reasons"]
        mock_cache_service.set.assert_called_once()

    def test_authorize_authz_error_fail_closed(
        self, authz_service, mock_avp_client, mock_cache_service, valid_authz_request
    ):
        """Test authorization fails closed on authorization error."""
        # Arrange
        mock_cache_service.get.return_value = None
        mock_avp_client.is_authorized.side_effect = AuthorizationError(
            "Authorization error"
        )

        # Act
        result = authz_service.authorize(valid_authz_request)

        # Assert
        assert result["decision"] == "DENY"
        assert "Authorization error" in result["reasons"]
        mock_cache_service.set.assert_called_once()

    def test_authorize_unexpected_error_fail_closed(
        self, authz_service, mock_avp_client, mock_cache_service, valid_authz_request
    ):
        """Test authorization fails closed on unexpected error."""
        # Arrange
        mock_cache_service.get.return_value = None
        mock_avp_client.is_authorized.side_effect = Exception("Unexpected error")

        # Act
        result = authz_service.authorize(valid_authz_request)

        # Assert
        assert result["decision"] == "DENY"
        assert "Authorization error" in result["reasons"]
        mock_cache_service.set.assert_called_once()


@pytest.mark.unit
class TestAuthzServiceBatchAuthorize:
    """Tests for AuthzService.batch_authorize method."""

    def test_batch_authorize_all_success(
        self, authz_service, mock_avp_client, mock_cache_service
    ):
        """Test batch authorization with all successful requests."""
        # Arrange
        mock_cache_service.get.return_value = None
        mock_avp_client.is_authorized.return_value = {"decision": "ALLOW"}

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
        result = authz_service.batch_authorize(data)

        # Assert
        assert len(result["results"]) == 2
        assert all(r["decision"] == "ALLOW" for r in result["results"])
        assert mock_avp_client.is_authorized.call_count == 2

    def test_batch_authorize_mixed_results(
        self, authz_service, mock_avp_client, mock_cache_service
    ):
        """Test batch authorization with mixed ALLOW/DENY results."""
        # Arrange
        mock_cache_service.get.return_value = None
        mock_avp_client.is_authorized.side_effect = [
            {"decision": "ALLOW"},
            {"decision": "DENY", "reasons": ["Insufficient permissions"]},
        ]

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
        result = authz_service.batch_authorize(data)

        # Assert
        assert len(result["results"]) == 2
        assert result["results"][0]["decision"] == "ALLOW"
        assert result["results"][1]["decision"] == "DENY"

    def test_batch_authorize_partial_failure(
        self, authz_service, mock_avp_client, mock_cache_service
    ):
        """Test batch authorization with partial failures."""
        # Arrange
        mock_cache_service.get.return_value = None
        mock_avp_client.is_authorized.side_effect = [
            {"decision": "ALLOW"},
            Exception("Unexpected error"),
        ]

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
        result = authz_service.batch_authorize(data)

        # Assert
        assert len(result["results"]) == 2
        assert result["results"][0]["decision"] == "ALLOW"
        assert result["results"][1]["decision"] == "DENY"


@pytest.mark.unit
class TestAuthzServiceInvalidateUserCache:
    """Tests for AuthzService.invalidate_user_cache method."""

    def test_invalidate_user_cache(self, authz_service, mock_cache_service):
        """Test cache invalidation for a user."""
        # Arrange
        mock_cache_service.delete_pattern.return_value = 5

        # Act
        deleted_count = authz_service.invalidate_user_cache("user-123")

        # Assert
        mock_cache_service.delete_pattern.assert_called_once_with("authz:user-123:*")
        assert deleted_count == 5


@pytest.mark.unit
class TestAuthzServiceFlushCache:
    """Tests for AuthzService.flush_cache method."""

    def test_flush_cache(self, authz_service, mock_cache_service):
        """Test complete cache flush."""
        # Arrange
        mock_cache_service.delete_pattern.return_value = 100

        # Act
        deleted_count = authz_service.flush_cache()

        # Assert
        mock_cache_service.delete_pattern.assert_called_once_with("authz:*")
        assert deleted_count == 100
