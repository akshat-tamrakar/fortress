"""
Property-based tests for registration flows.

Feature: authentication-app
Properties: 3, 4
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st

from apps.authentication.exceptions import UserAlreadyExistsError
from apps.authentication.services import AuthService


# Strategies for generating valid registration data
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

valid_name_strategy = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"),
    min_size=1,
    max_size=50,
)


@pytest.fixture
def mock_cognito_client():
    """Create a mock CognitoClient for testing."""
    return MagicMock()


class TestRegistrationProperties:
    """
    Property-based tests for user registration.

    Feature: authentication-app, Property 3: Registration Creates Unconfirmed User
    Validates: Requirements 1.1
    """

    @settings(max_examples=100)
    @given(
        email=valid_email_strategy,
        password=valid_password_strategy,
        first_name=valid_name_strategy,
        last_name=valid_name_strategy,
    )
    def test_registration_creates_unconfirmed_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ):
        """
        Property 3: Registration Creates Unconfirmed User

        For any valid registration request (valid email, valid password,
        non-empty first/last name), the Authentication_Service SHALL return
        a response with status `UNCONFIRMED` and a valid UUID user_id.

        Validates: Requirements 1.1
        """
        # Arrange
        mock_cognito = MagicMock()
        generated_user_id = str(uuid4())

        mock_cognito.sign_up.return_value = {
            "user_id": generated_user_id,
            "email": email,
            "status": "UNCONFIRMED",
            "message": "Verification email sent. Please check your inbox.",
        }

        auth_service = AuthService(cognito_client=mock_cognito)

        registration_data = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        }

        # Act
        result = auth_service.register(registration_data)

        # Assert - Property: status must be UNCONFIRMED
        assert result["status"] == "UNCONFIRMED", (
            f"Expected status 'UNCONFIRMED', got '{result['status']}'"
        )

        # Assert - Property: user_id must be a valid UUID string
        assert "user_id" in result, "Response must contain user_id"
        assert result["user_id"] == generated_user_id

        # Assert - Property: email in response matches input
        assert result["email"] == email

        # Verify cognito was called with correct attributes
        mock_cognito.sign_up.assert_called_once()
        call_args = mock_cognito.sign_up.call_args
        assert call_args.kwargs["email"] == email
        assert call_args.kwargs["password"] == password
        assert call_args.kwargs["attributes"]["given_name"] == first_name
        assert call_args.kwargs["attributes"]["family_name"] == last_name


class TestDuplicateEmailProperties:
    """
    Property-based tests for duplicate email detection.

    Feature: authentication-app, Property 4: Duplicate Email Detection
    Validates: Requirements 1.4
    """

    @settings(max_examples=100)
    @given(
        email=valid_email_strategy,
        password=valid_password_strategy,
        first_name=valid_name_strategy,
        last_name=valid_name_strategy,
    )
    def test_duplicate_email_returns_user_already_exists_error(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ):
        """
        Property 4: Duplicate Email Detection

        For any email that has already been registered, attempting to register
        again with the same email SHALL return a `USER_ALREADY_EXISTS` error
        with HTTP status 409.

        Validates: Requirements 1.4
        """
        # Arrange
        mock_cognito = MagicMock()
        mock_cognito.sign_up.side_effect = UserAlreadyExistsError(
            "User with this email already exists"
        )

        auth_service = AuthService(cognito_client=mock_cognito)

        registration_data = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        }

        # Act & Assert - Property: duplicate email raises UserAlreadyExistsError
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            auth_service.register(registration_data)

        # Assert - Property: error code is USER_ALREADY_EXISTS
        assert exc_info.value.error_code == "USER_ALREADY_EXISTS"

        # Assert - Property: status code is 409
        assert exc_info.value.status_code == 409
