"""
Property-based tests for token management flows.

Feature: authentication-app
Properties: 11, 12
"""

from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from apps.authentication.exceptions import TokenInvalidError
from apps.authentication.services import AuthService


# Strategy for JWT-like tokens
token_strategy = st.text(
    alphabet=st.sampled_from(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_."
    ),
    min_size=50,
    max_size=200,
)

expires_in_strategy = st.integers(min_value=300, max_value=86400)


class TestTokenRefreshProperties:
    """
    Property-based tests for token refresh behavior.

    Feature: authentication-app, Property 11: Token Refresh Behavior
    Validates: Requirements 5.1, 5.2, 5.3
    """

    @settings(max_examples=100)
    @given(
        refresh_token=token_strategy,
        new_access_token=token_strategy,
        new_id_token=token_strategy,
        expires_in=expires_in_strategy,
    )
    def test_valid_refresh_token_returns_new_tokens(
        self,
        refresh_token: str,
        new_access_token: str,
        new_id_token: str,
        expires_in: int,
    ):
        """
        Property 11: Token Refresh Behavior - Valid Refresh

        For any valid refresh token, the Authentication_Service SHALL return
        new `access_token` and `id_token`.

        Validates: Requirements 5.1
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.refresh_tokens.return_value = {
            "access_token": new_access_token,
            "id_token": new_id_token,
            "refresh_token": None,  # Cognito may not return new refresh token
            "expires_in": expires_in,
            "token_type": "Bearer",
        }

        auth_service = AuthService(cognito_client=mock_cognito)
        refresh_data = {"refresh_token": refresh_token}

        # Act
        result = auth_service.refresh_token(refresh_data)

        # Assert - Property: response contains new access_token
        assert "access_token" in result, "Response must contain access_token"
        assert result["access_token"] == new_access_token

        # Assert - Property: response contains new id_token
        assert "id_token" in result, "Response must contain id_token"
        assert result["id_token"] == new_id_token

        # Assert - Property: response contains expires_in
        assert "expires_in" in result, "Response must contain expires_in"
        assert result["expires_in"] == expires_in

    @settings(max_examples=100)
    @given(refresh_token=token_strategy)
    def test_invalid_refresh_token_returns_error(
        self,
        refresh_token: str,
    ):
        """
        Property 11: Token Refresh Behavior - Invalid Token

        For invalid or expired refresh tokens, the Authentication_Service
        SHALL return `TOKEN_INVALID` error.

        Validates: Requirements 5.2
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.refresh_tokens.side_effect = TokenInvalidError(
            "Token is invalid or malformed"
        )

        auth_service = AuthService(cognito_client=mock_cognito)
        refresh_data = {"refresh_token": refresh_token}

        # Act & Assert
        with pytest.raises(TokenInvalidError) as exc_info:
            auth_service.refresh_token(refresh_data)

        # Assert - Property: error code is TOKEN_INVALID
        assert exc_info.value.error_code == "TOKEN_INVALID"
        assert exc_info.value.status_code == 401

    @settings(max_examples=100)
    @given(refresh_token=token_strategy)
    def test_revoked_refresh_token_returns_error(
        self,
        refresh_token: str,
    ):
        """
        Property 11: Token Refresh Behavior - Revoked Token

        For revoked refresh tokens, the Authentication_Service
        SHALL return `TOKEN_INVALID` error.

        Validates: Requirements 5.3
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.refresh_tokens.side_effect = TokenInvalidError(
            "Refresh token has been revoked"
        )

        auth_service = AuthService(cognito_client=mock_cognito)
        refresh_data = {"refresh_token": refresh_token}

        # Act & Assert
        with pytest.raises(TokenInvalidError) as exc_info:
            auth_service.refresh_token(refresh_data)

        # Assert - Property: error code is TOKEN_INVALID
        assert exc_info.value.error_code == "TOKEN_INVALID"
        assert exc_info.value.status_code == 401


class TestLogoutProperties:
    """
    Property-based tests for logout behavior.

    Feature: authentication-app, Property 12: Logout Behavior
    Validates: Requirements 6.1, 6.2, 6.3
    """

    @settings(max_examples=100)
    @given(access_token=token_strategy)
    def test_valid_logout_revokes_tokens(
        self,
        access_token: str,
    ):
        """
        Property 12: Logout Behavior - Successful Logout

        For any logout request with a valid access token, the Authentication_Service
        SHALL revoke tokens and complete without error.

        Validates: Requirements 6.1, 6.2
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.global_sign_out.return_value = None

        auth_service = AuthService(cognito_client=mock_cognito)

        # Act - should not raise any exception
        auth_service.logout(access_token)

        # Assert - Property: global_sign_out was called with the access token
        mock_cognito.global_sign_out.assert_called_once_with(access_token)

    @settings(max_examples=100)
    @given(access_token=token_strategy)
    def test_invalid_token_logout_returns_error(
        self,
        access_token: str,
    ):
        """
        Property 12: Logout Behavior - Invalid Token

        For any logout request with an invalid access token, the Authentication_Service
        SHALL return `TOKEN_INVALID` error.

        Validates: Requirements 6.3
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.global_sign_out.side_effect = TokenInvalidError(
            "Token is invalid or malformed"
        )

        auth_service = AuthService(cognito_client=mock_cognito)

        # Act & Assert
        with pytest.raises(TokenInvalidError) as exc_info:
            auth_service.logout(access_token)

        # Assert - Property: error code is TOKEN_INVALID
        assert exc_info.value.error_code == "TOKEN_INVALID"
        assert exc_info.value.status_code == 401
