"""
Authentication API views.

REST API endpoints for authentication operations.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    MFAChallengeResponseSerializer,
    MFAVerifySerializer,
    MessageResponseSerializer,
    NewPasswordChallengeResponseSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    ResetPasswordSerializer,
    TokenRefreshSerializer,
    TokenResponseSerializer,
    VerifyEmailSerializer,
)
from .services import get_auth_service


class RegisterView(APIView):
    """
    POST /v1/auth/register

    Register a new user account.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_service = get_auth_service()
        result = auth_service.register(serializer.validated_data)

        response_serializer = RegisterResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    """
    POST /v1/auth/verify-email

    Verify email address with OTP code.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_service = get_auth_service()
        result = auth_service.verify_email(
            email=serializer.validated_data["email"],
            code=serializer.validated_data["code"],
        )

        response_serializer = MessageResponseSerializer(result)
        return Response(response_serializer.data)


class ResendVerificationView(APIView):
    """
    POST /v1/auth/resend-verification

    Resend email verification code.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_service = get_auth_service()
        result = auth_service.resend_verification(
            email=serializer.validated_data["email"],
        )

        response_serializer = MessageResponseSerializer(result)
        return Response(response_serializer.data)


class LoginView(APIView):
    """
    POST /v1/auth/login

    Authenticate user with email and password.
    Returns tokens or MFA challenge.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_service = get_auth_service()
        result = auth_service.login(serializer.validated_data)

        # Check if MFA is required
        if result.get("challenge") == "MFA_REQUIRED":
            response_serializer = MFAChallengeResponseSerializer(result)
            return Response(response_serializer.data)

        # Check if new password is required
        if result.get("challenge") == "NEW_PASSWORD_REQUIRED":
            response_serializer = NewPasswordChallengeResponseSerializer(result)
            return Response(response_serializer.data)

        # Successful login - return tokens
        response_serializer = TokenResponseSerializer(result)
        return Response(response_serializer.data)


class MFAVerifyView(APIView):
    """
    POST /v1/auth/mfa/verify

    Complete MFA verification with TOTP code.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_service = get_auth_service()
        result = auth_service.verify_mfa(serializer.validated_data)

        response_serializer = TokenResponseSerializer(result)
        return Response(response_serializer.data)


class TokenRefreshView(APIView):
    """
    POST /v1/auth/token/refresh

    Refresh access token using refresh token.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_service = get_auth_service()
        result = auth_service.refresh_token(serializer.validated_data)

        response_serializer = TokenResponseSerializer(result)
        return Response(response_serializer.data)


class LogoutView(APIView):
    """
    POST /v1/auth/logout

    Logout user and revoke all tokens.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        # Get access token from Authorization header
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        access_token = auth_header.replace("Bearer ", "") if auth_header else ""

        if not access_token:
            # Try to get from request data as fallback
            access_token = request.data.get("access_token", "")

        auth_service = get_auth_service()
        auth_service.logout(access_token)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ForgotPasswordView(APIView):
    """
    POST /v1/auth/password/forgot

    Request password reset code.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_service = get_auth_service()
        result = auth_service.forgot_password(
            email=serializer.validated_data["email"],
        )

        response_serializer = MessageResponseSerializer(result)
        return Response(response_serializer.data)


class ResetPasswordView(APIView):
    """
    POST /v1/auth/password/reset

    Reset password with code and new password.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_service = get_auth_service()
        result = auth_service.reset_password(
            email=serializer.validated_data["email"],
            code=serializer.validated_data["code"],
            new_password=serializer.validated_data["new_password"],
        )

        response_serializer = MessageResponseSerializer(result)
        return Response(response_serializer.data)
