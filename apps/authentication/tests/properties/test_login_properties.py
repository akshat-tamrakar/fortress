"""
Property-based tests for login flows.

Feature: authentication-app
Properties: 7, 8
"""

from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from apps.authentication.exceptions import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
    UserDisabledError,
)
from apps.authentication.services import AuthService


# Strategies for generating test data
valid_email_strategy = st.emails()

valid_password_strategy = st.text(
    alphabet=st.sampled_from(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*"
    ),
    min_size=12,
    max_size=50,
).filter(
    lambda p: (
        any(c.isupper() for c in p)
        and any(c.islower() for c in p)
        and any(c.isdigit() for c in p)
        and any(c in "!@#$%^&*" for c in p)
    )
)

# Strategy for generating valid JWT-like tokens
token_strategy = st.text(
    alphabet=st.sampled_from(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_."
    ),
    min_size=50,
    max_size=200,
)

# Strategy for expires_in (positive integers representing seconds)
expires_in_strategy = st.integers(min_value=300, max_value=86400)


class TestLoginTokenResponseProperties:
    """
    Property-based tests for login token response structure.

    Feature: authentication-app, Property 7: Login Token Response Structure
    Validates: Requirements 3.1
    """

    @settings(max_examples=100)
    @given(
        email=valid_email_strategy,
        password=valid_password_strategy,
        access_token=token_strategy,
        id_token=token_strategy,
        refresh_token=token_strategy,
        expires_in=expires_in_strategy,
    )
    def test_successful_login_returns_complete_token_response(
        self,
        email: str,
        password: str,
        access_token: str,
        id_token: str,
        refresh_token: str,
        expires_in: int,
    ):
        """
        Property 7: Login Token Response Structure

        For any successful login (valid credentials, confirmed user, enabled account,
        no MFA), the response SHALL contain `access_token`, `id_token`, `refresh_token`,
        `expires_in`, and `token_type` fields.

        Validates: Requirements 3.1
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.return_value = {
            "tokens": {
                "access_token": access_token,
                "id_token": id_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in,
                "token_type": "Bearer",
            }
        }

        auth_service = AuthService(cognito_client=mock_cognito)
        login_data = {"email": email, "password": password}

        # Act
        result = auth_service.login(login_data)

        # Assert - Property: response contains all required token fields
        assert "access_token" in result, "Response must contain access_token"
        assert "id_token" in result, "Response must contain id_token"
        assert "refresh_token" in result, "Response must contain refresh_token"
        assert "expires_in" in result, "Response must contain expires_in"
        assert "token_type" in result, "Response must contain token_type"

        # Assert - Property: token values match what Cognito returned
        assert result["access_token"] == access_token
        assert result["id_token"] == id_token
        assert result["refresh_token"] == refresh_token
        assert result["expires_in"] == expires_in
        assert result["token_type"] == "Bearer"


class TestLoginErrorMappingProperties:
    """
    Property-based tests for login error mapping.

    Feature: authentication-app, Property 8: Login Error Mapping
    Validates: Requirements 3.2, 3.3, 3.4
    """

    @settings(max_examples=100)
    @given(
        email=valid_email_strategy,
        password=valid_password_strategy,
    )
    def test_invalid_credentials_returns_correct_error(
        self,
        email: str,
        password: str,
    ):
        """
        Property 8: Login Error Mapping - Invalid Credentials

        For any login attempt with invalid credentials, the error response
        SHALL correctly map to INVALID_CREDENTIALS error.

        Validates: Requirements 3.2
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.side_effect = InvalidCredentialsError(
            "Invalid email or password"
        )

        auth_service = AuthService(cognito_client=mock_cognito)
        login_data = {"email": email, "password": password}

        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.login(login_data)

        # Assert - Property: error code is INVALID_CREDENTIALS
        assert exc_info.value.error_code == "INVALID_CREDENTIALS"
        assert exc_info.value.status_code == 401

    @settings(max_examples=100)
    @given(
        email=valid_email_strategy,
        password=valid_password_strategy,
    )
    def test_disabled_account_returns_correct_error(
        self,
        email: str,
        password: str,
    ):
        """
        Property 8: Login Error Mapping - Disabled Account

        For any login attempt with a disabled account, the error response
        SHALL correctly map to USER_DISABLED error.

        Validates: Requirements 3.3
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.side_effect = UserDisabledError(
            "User account is disabled"
        )

        auth_service = AuthService(cognito_client=mock_cognito)
        login_data = {"email": email, "password": password}

        # Act & Assert
        with pytest.raises(UserDisabledError) as exc_info:
            auth_service.login(login_data)

        # Assert - Property: error code is USER_DISABLED
        assert exc_info.value.error_code == "USER_DISABLED"
        assert exc_info.value.status_code == 403

    @settings(max_examples=100)
    @given(
        email=valid_email_strategy,
        password=valid_password_strategy,
    )
    def test_unverified_email_returns_correct_error(
        self,
        email: str,
        password: str,
    ):
        """
        Property 8: Login Error Mapping - Unverified Email

        For any login attempt with an unverified email, the error response
        SHALL correctly map to EMAIL_NOT_VERIFIED error.

        Validates: Requirements 3.4
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.side_effect = EmailNotVerifiedError(
            "Email address not verified"
        )

        auth_service = AuthService(cognito_client=mock_cognito)
        login_data = {"email": email, "password": password}

        # Act & Assert
        with pytest.raises(EmailNotVerifiedError) as exc_info:
            auth_service.login(login_data)

        # Assert - Property: error code is EMAIL_NOT_VERIFIED
        assert exc_info.value.error_code == "EMAIL_NOT_VERIFIED"
        assert exc_info.value.status_code == 403
