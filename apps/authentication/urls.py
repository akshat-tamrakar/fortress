from django.urls import path

from .views import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MFAVerifyView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    TokenRefreshView,
    VerifyEmailView,
)

app_name = "authentication"

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("verify-email", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification", ResendVerificationView.as_view(), name="resend-verification"),
    path("login", LoginView.as_view(), name="login"),
    path("mfa/verify", MFAVerifyView.as_view(), name="mfa-verify"),
    path("token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("password/forgot", ForgotPasswordView.as_view(), name="forgot-password"),
    path("password/reset", ResetPasswordView.as_view(), name="reset-password"),
]
