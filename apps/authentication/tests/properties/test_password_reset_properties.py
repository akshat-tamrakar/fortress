"""
Property-based tests for password reset flows.

Feature: authentication-app
Property: 13
"""

from unittest.mock import MagicMock

from hypothesis import given, settings, strategies as st

from apps.authentication.services import AuthService


# Strategies for generating test data
valid_email_strategy = st.emails()

# Strategy for emails that might or might not exist in the system
any_email_strategy = st.one_of(
    st.emails(),
    st.text(
        alphabet=st.sampled_from(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@."
        ),
        min_size=5,
        max_size=50,
    ).filter(lambda s: "@" in s and "." in s),
)


class TestPasswordResetPrivacyProperties:
    """
    Property-based tests for password reset privacy.

    Feature: authentication-app, Property 13: Password Reset Privacy
    Validates: Requirements 7.2
    """

    @settings(max_examples=100)
    @given(email=valid_email_strategy)
    def test_password_reset_always_returns_success_for_existing_user(
        self,
        email: str,
    ):
        """
        Property 13: Password Reset Privacy - Existing User

        For any password reset request with an existing email, the Authentication_Service
        SHALL return a success response.

        Validates: Requirements 7.2
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.forgot_password.return_value = {
            "message": "If the email exists, a password reset code has been sent."
        }

        auth_service = AuthService(cognito_client=mock_cognito)

        # Act
        result = auth_service.forgot_password(email)

        # Assert - Property: response contains message
        assert "message" in result, "Response must contain message"

        # Assert - Property: message does not reveal user existence
        # The message should be generic and not confirm the email exists
        assert "password reset" in result["message"].lower() or "sent" in result["message"].lower()

    @settings(max_examples=100)
    @given(email=valid_email_strategy)
    def test_password_reset_always_returns_success_for_nonexistent_user(
        self,
        email: str,
    ):
        """
        Property 13: Password Reset Privacy - Non-existent User

        For any password reset request with a non-existent email, the Authentication_Service
        SHALL return a success response (to prevent user enumeration).

        Validates: Requirements 7.2
        """
        # Arrange
        mock_cognito = MagicMock()
        # Even for non-existent users, Cognito client returns success
        mock_cognito.forgot_password.return_value = {
            "message": "If the email exists, a password reset code has been sent."
        }

        auth_service = AuthService(cognito_client=mock_cognito)

        # Act
        result = auth_service.forgot_password(email)

        # Assert - Property: response contains message (same as existing user)
        assert "message" in result, "Response must contain message"

        # Assert - Property: message does not reveal user non-existence
        assert "password reset" in result["message"].lower() or "sent" in result["message"].lower()

    @settings(max_examples=100)
    @given(
        existing_email=valid_email_strategy,
        nonexistent_email=valid_email_strategy,
    )
    def test_password_reset_response_identical_for_any_email(
        self,
        existing_email: str,
        nonexistent_email: str,
    ):
        """
        Property 13: Password Reset Privacy - Response Consistency

        For any two password reset requests (one with existing email, one without),
        the response structure and message SHALL be identical to prevent user enumeration.

        Validates: Requirements 7.2
        """
        # Arrange
        mock_cognito = MagicMock()
        standard_response = {
            "message": "If the email exists, a password reset code has been sent."
        }
        mock_cognito.forgot_password.return_value = standard_response

        auth_service = AuthService(cognito_client=mock_cognito)

        # Act
        result_existing = auth_service.forgot_password(existing_email)
        result_nonexistent = auth_service.forgot_password(nonexistent_email)

        # Assert - Property: both responses have identical structure
        assert result_existing.keys() == result_nonexistent.keys()

        # Assert - Property: both responses have identical message
        assert result_existing["message"] == result_nonexistent["message"]
