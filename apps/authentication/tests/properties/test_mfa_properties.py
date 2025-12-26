"""
Property-based tests for MFA flows.

Feature: authentication-app
Properties: 9, 10
"""

from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from apps.authentication.exceptions import InvalidMFACodeError, SessionExpiredError
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

# Strategy for session tokens
session_token_strategy = st.text(
    alphabet=st.sampled_from(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    ),
    min_size=20,
    max_size=100,
)

# Strategy for 6-digit MFA codes
mfa_code_strategy = st.text(
    alphabet=st.sampled_from("0123456789"),
    min_size=6,
    max_size=6,
)

# Strategy for JWT-like tokens
token_strategy = st.text(
    alphabet=st.sampled_from(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_."
    ),
    min_size=50,
    max_size=200,
)

expires_in_strategy = st.integers(min_value=300, max_value=86400)


class TestMFAChallengeFlowProperties:
    """
    Property-based tests for MFA challenge flow.

    Feature: authentication-app, Property 9: MFA Challenge Flow
    Validates: Requirements 3.5, 4.1
    """

    @settings(max_examples=100)
    @given(
        email=valid_email_strategy,
        password=valid_password_strategy,
        session_token=session_token_strategy,
    )
    def test_mfa_enabled_user_receives_challenge(
        self,
        email: str,
        password: str,
        session_token: str,
    ):
        """
        Property 9: MFA Challenge Flow - Challenge Response

        For any login attempt by a user with MFA enabled, the response SHALL
        contain `challenge: 'MFA_REQUIRED'` and a `session_token`.

        Validates: Requirements 3.5
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.return_value = {
            "challenge": "MFA_REQUIRED",
            "session": session_token,
        }

        auth_service = AuthService(cognito_client=mock_cognito)
        login_data = {"email": email, "password": password}

        # Act
        result = auth_service.login(login_data)

        # Assert - Property: response contains MFA challenge
        assert "challenge" in result, "Response must contain challenge field"
        assert result["challenge"] == "MFA_REQUIRED"

        # Assert - Property: response contains session_token
        assert "session_token" in result, "Response must contain session_token"
        assert result["session_token"] == session_token

    @settings(max_examples=100)
    @given(
        session_token=session_token_strategy,
        mfa_code=mfa_code_strategy,
        access_token=token_strategy,
        id_token=token_strategy,
        refresh_token=token_strategy,
        expires_in=expires_in_strategy,
    )
    def test_valid_mfa_code_returns_tokens(
        self,
        session_token: str,
        mfa_code: str,
        access_token: str,
        id_token: str,
        refresh_token: str,
        expires_in: int,
    ):
        """
        Property 9: MFA Challenge Flow - Token Response

        For any MFA verification with valid TOTP code, the response SHALL
        return complete token set.

        Validates: Requirements 4.1
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.respond_to_auth_challenge.return_value = {
            "access_token": access_token,
            "id_token": id_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "token_type": "Bearer",
        }

        auth_service = AuthService(cognito_client=mock_cognito)
        mfa_data = {"session_token": session_token, "mfa_code": mfa_code}

        # Act
        result = auth_service.verify_mfa(mfa_data)

        # Assert - Property: response contains all required token fields
        assert "access_token" in result, "Response must contain access_token"
        assert "id_token" in result, "Response must contain id_token"
        assert "refresh_token" in result, "Response must contain refresh_token"
        assert "expires_in" in result, "Response must contain expires_in"
        assert "token_type" in result, "Response must contain token_type"

        # Assert - Property: token values match
        assert result["access_token"] == access_token
        assert result["id_token"] == id_token
        assert result["refresh_token"] == refresh_token


class TestMFAErrorHandlingProperties:
    """
    Property-based tests for MFA error handling.

    Feature: authentication-app, Property 10: MFA Error Handling
    Validates: Requirements 4.2, 4.3
    """

    @settings(max_examples=100)
    @given(
        session_token=session_token_strategy,
        mfa_code=mfa_code_strategy,
    )
    def test_invalid_mfa_code_returns_correct_error(
        self,
        session_token: str,
        mfa_code: str,
    ):
        """
        Property 10: MFA Error Handling - Invalid Code

        For any MFA verification attempt with invalid TOTP codes,
        the error SHALL be INVALID_MFA_CODE.

        Validates: Requirements 4.2
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.respond_to_auth_challenge.side_effect = InvalidMFACodeError(
            "Invalid or expired MFA code"
        )

        auth_service = AuthService(cognito_client=mock_cognito)
        mfa_data = {"session_token": session_token, "mfa_code": mfa_code}

        # Act & Assert
        with pytest.raises(InvalidMFACodeError) as exc_info:
            auth_service.verify_mfa(mfa_data)

        # Assert - Property: error code is INVALID_MFA_CODE
        assert exc_info.value.error_code == "INVALID_MFA_CODE"
        assert exc_info.value.status_code == 401

    @settings(max_examples=100)
    @given(
        session_token=session_token_strategy,
        mfa_code=mfa_code_strategy,
    )
    def test_expired_session_returns_correct_error(
        self,
        session_token: str,
        mfa_code: str,
    ):
        """
        Property 10: MFA Error Handling - Expired Session

        For any MFA verification attempt with expired session tokens,
        the error SHALL be SESSION_EXPIRED.

        Validates: Requirements 4.3
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.respond_to_auth_challenge.side_effect = SessionExpiredError(
            "Session has expired"
        )

        auth_service = AuthService(cognito_client=mock_cognito)
        mfa_data = {"session_token": session_token, "mfa_code": mfa_code}

        # Act & Assert
        with pytest.raises(SessionExpiredError) as exc_info:
            auth_service.verify_mfa(mfa_data)

        # Assert - Property: error code is SESSION_EXPIRED
        assert exc_info.value.error_code == "SESSION_EXPIRED"
        assert exc_info.value.status_code == 401
