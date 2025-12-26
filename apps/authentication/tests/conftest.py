"""
Pytest fixtures for authentication tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.authentication.services import AuthService, CognitoClient


@pytest.fixture
def mock_cognito_client():
    """Create a mock CognitoClient."""
    return MagicMock(spec=CognitoClient)


@pytest.fixture
def auth_service(mock_cognito_client):
    """Create an AuthService with mocked CognitoClient."""
    return AuthService(cognito_client=mock_cognito_client)


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 cognito-idp client."""
    with patch("boto3.client") as mock_client:
        mock_cognito = MagicMock()
        mock_client.return_value = mock_cognito
        yield mock_cognito


@pytest.fixture
def valid_registration_data():
    """Valid registration request data."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+12025551234",
    }


@pytest.fixture
def valid_login_data():
    """Valid login request data."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
    }


@pytest.fixture
def valid_tokens():
    """Valid token response data."""
    return {
        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
        "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJjdHkiOiJKV1QiLCJlbmMiOiJBMjU2R0NNIiwiYWxnIjoiUlNBLU9BRVAifQ...",
        "expires_in": 900,
        "token_type": "Bearer",
    }


@pytest.fixture
def mfa_challenge_response():
    """MFA challenge response data."""
    return {
        "challenge": "MFA_REQUIRED",
        "session_token": "AYABeC1234567890...",
    }
