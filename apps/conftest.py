"""
Shared pytest fixtures for all apps.

Provides common fixtures for testing across the entire project.
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient, APIRequestFactory
from unittest.mock import MagicMock


@pytest.fixture
def api_client():
    """Create a DRF API client."""
    return APIClient()


@pytest.fixture
def api_factory():
    """Create a DRF API request factory."""
    return APIRequestFactory()


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock()
    user.is_authenticated = True
    user.id = "123e4567-e89b-12d3-a456-426614174000"
    user.email = "test@example.com"
    return user


@pytest.fixture
def anonymous_user():
    """Create an anonymous user."""
    return AnonymousUser()


@pytest.fixture
def valid_access_token():
    """Sample valid access token."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.POstGetfAytaZS82wHcjoTyoqhMyxXiWdR7Nn7A29DNSl0EiXLdwJ6xC6AfgZWF1bOsS_TuYI3OG85AmiExREkrS6tDfTQ2B3WXlrr-wp5AokiRbz3_oB4OxG-W9KcEEbDRcZc0nH3L7LzYptiy1PtAylQGxHTWZXtGz4ht0bAecBgmpdgXMguEIcoqPJ1n3pIWk_dUZegpqx0Lka21H6XxUTxiy8OcaarA8zdnPUnV6AmNP3ecFawIFYdvJB_cm-GvpCSbr8G5AuuqZonnicigDg9obOEQzxLCjvKZ1YdRuLvMfvRBiZ_s7SfFZT9xCnpwt2DLp_Wqz8CGF3oPkAA"


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "given_name": "John",
        "family_name": "Doe",
        "phone_number": "+12025551234",
        "user_type": "end_user",
        "email_verified": True,
        "status": "Active",
        "mfa_enabled": False,
    }


@pytest.fixture
def sample_admin_data():
    """Sample admin user data for testing."""
    return {
        "user_id": "admin-123",
        "email": "admin@example.com",
        "given_name": "Admin",
        "family_name": "User",
        "user_type": "admin",
        "email_verified": True,
        "status": "Active",
        "mfa_enabled": True,
    }
