"""
User management API views.

Provides REST endpoints for user CRUD operations, account management,
and self-service profile operations.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.exceptions import (
    AuthorizationDeniedError,
    InvalidMFACodeError,
    MFAAlreadyEnabledError,
    RateLimitExceededError,
    TokenInvalidError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from apps.users.serializers import (
    MFASetupRequestSerializer,
    MFASetupResponseSerializer,
    UserCreateSerializer,
    UserListResponseSerializer,
    UserResponseSerializer,
    UserUpdateSerializer,
)
from apps.users.services.user_service import user_service

logger = logging.getLogger(__name__)


class UserListCreateView(APIView):
    """
    GET /v1/users - List users (admin only)
    POST /v1/users - Create user (admin only)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        List all users with pagination.

        Query Parameters:
            - limit: Maximum number of users to return (default: 60, max: 60)
            - next_token: Pagination token from previous response
        """
        try:
            # TODO: Add authorization check - only admins can list users
            # For now, proceeding without authorization check

            limit = int(request.query_params.get("limit", 60))
            limit = min(limit, 60)  # Cap at 60
            next_token = request.query_params.get("next_token")

            result = user_service.list_users(
                limit=limit,
                pagination_token=next_token,
            )

            serializer = UserListResponseSerializer(result)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception("Unexpected error listing users")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """
        Create a new user (admin-initiated).

        Request Body:
            - email: User's email address (required)
            - given_name: User's first name (required)
            - family_name: User's last name (required)
            - user_type: 'end_user' or 'admin' (optional, default: 'end_user')
            - phone_number: Phone number in E.164 format (optional)
        """
        try:
            # TODO: Add authorization check - only admins can create users
            # For now, proceeding without authorization check

            serializer = UserCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        "error": {
                            "code": "VALIDATION_FAILED",
                            "message": "Request validation failed",
                            "details": serializer.errors,
                        }
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            user = user_service.create_user(**serializer.validated_data)

            response_serializer = UserResponseSerializer(user)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED,
            )

        except UserAlreadyExistsError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except ValidationError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception("Unexpected error creating user")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserDetailView(APIView):
    """
    GET /v1/users/{id} - Get user by ID
    PUT /v1/users/{id} - Update user
    DELETE /v1/users/{id} - Delete user (hard delete)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        """Get user details by user ID."""
        try:
            # TODO: Add authorization check
            # - Admins can view any user
            # - Users can view their own profile
            # For now, proceeding without authorization check

            user = user_service.get_user(str(user_id))

            serializer = UserResponseSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except UserNotFoundError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception(f"Unexpected error getting user {user_id}")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, user_id):
        """
        Update user attributes.

        Request Body:
            - given_name: User's first name (optional)
            - family_name: User's last name (optional)
            - phone_number: Phone number (optional)
        """
        try:
            # TODO: Add authorization check
            # - Admins can update any user
            # - Users can update their own profile (limited fields)
            # For now, proceeding without authorization check

            serializer = UserUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        "error": {
                            "code": "VALIDATION_FAILED",
                            "message": "Request validation failed",
                            "details": serializer.errors,
                        }
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            user = user_service.update_user(str(user_id), **serializer.validated_data)

            response_serializer = UserResponseSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except UserNotFoundError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except ValidationError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception(f"Unexpected error updating user {user_id}")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, user_id):
        """
        Permanently delete a user.

        ⚠️ WARNING: This is a hard delete. User data cannot be recovered.
        """
        try:
            # TODO: Add authorization check - only admins can delete users
            # For now, proceeding without authorization check

            user_service.delete_user(str(user_id))

            return Response(
                {"message": "User deleted successfully"},
                status=status.HTTP_200_OK,
            )

        except UserNotFoundError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception(f"Unexpected error deleting user {user_id}")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserDisableView(APIView):
    """POST /v1/users/{id}/disable - Disable user account"""

    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """Disable a user account."""
        try:
            # TODO: Add authorization check - only admins can disable users
            # For now, proceeding without authorization check

            user = user_service.disable_user(str(user_id))

            serializer = UserResponseSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except UserNotFoundError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception(f"Unexpected error disabling user {user_id}")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserEnableView(APIView):
    """POST /v1/users/{id}/enable - Enable user account"""

    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """Enable a previously disabled user account."""
        try:
            # TODO: Add authorization check - only admins can enable users
            # For now, proceeding without authorization check

            user = user_service.enable_user(str(user_id))

            serializer = UserResponseSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except UserNotFoundError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception(f"Unexpected error enabling user {user_id}")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MeView(APIView):
    """
    GET /v1/me - Get own profile
    PUT /v1/me - Update own profile
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's profile."""
        try:
            # Extract access token from Authorization header
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if not auth_header.startswith("Bearer "):
                return Response(
                    {
                        "error": {
                            "code": "AUTHENTICATION_REQUIRED",
                            "message": "Valid access token required",
                            "details": {},
                        }
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            access_token = auth_header.split(" ")[1]
            user = user_service.get_user_by_token(access_token)

            serializer = UserResponseSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except TokenInvalidError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception("Unexpected error getting user profile")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request):
        """Update current user's profile."""
        try:
            # Extract access token from Authorization header
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if not auth_header.startswith("Bearer "):
                return Response(
                    {
                        "error": {
                            "code": "AUTHENTICATION_REQUIRED",
                            "message": "Valid access token required",
                            "details": {},
                        }
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            access_token = auth_header.split(" ")[1]
            current_user = user_service.get_user_by_token(access_token)

            serializer = UserUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        "error": {
                            "code": "VALIDATION_FAILED",
                            "message": "Request validation failed",
                            "details": serializer.errors,
                        }
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            user = user_service.update_user(
                current_user["user_id"],
                **serializer.validated_data,
            )

            response_serializer = UserResponseSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except TokenInvalidError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except ValidationError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception("Unexpected error updating user profile")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MFASetupView(APIView):
    """POST /v1/me/mfa/setup - Setup or verify MFA"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Setup TOTP MFA for current user.

        Two-step process:
        1. Without totp_code: Returns secret_code for authenticator app
        2. With totp_code: Verifies and enables MFA
        """
        try:
            # Extract access token from Authorization header
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if not auth_header.startswith("Bearer "):
                return Response(
                    {
                        "error": {
                            "code": "AUTHENTICATION_REQUIRED",
                            "message": "Valid access token required",
                            "details": {},
                        }
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            access_token = auth_header.split(" ")[1]

            serializer = MFASetupRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        "error": {
                            "code": "VALIDATION_FAILED",
                            "message": "Request validation failed",
                            "details": serializer.errors,
                        }
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            totp_code = serializer.validated_data.get("totp_code")

            if totp_code:
                # Step 2: Verify MFA setup
                result = user_service.verify_mfa_setup(access_token, totp_code)
            else:
                # Step 1: Initiate MFA setup
                result = user_service.setup_mfa(access_token)

            response_serializer = MFASetupResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except InvalidMFACodeError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except MFAAlreadyEnabledError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except TokenInvalidError as e:
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    }
                },
                status=e.status_code,
            )
        except Exception as e:
            logger.exception("Unexpected error setting up MFA")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
