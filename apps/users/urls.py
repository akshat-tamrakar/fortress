from django.urls import path

from .views import (
    MeView,
    MFASetupView,
    UserDetailView,
    UserDisableView,
    UserEnableView,
    UserListCreateView,
)

app_name = "users"

# Admin user management endpoints (mounted at /v1/users/)
urlpatterns = [
    path("", UserListCreateView.as_view(), name="user-list-create"),
    path("<uuid:user_id>", UserDetailView.as_view(), name="user-detail"),
    path("<uuid:user_id>/disable", UserDisableView.as_view(), name="user-disable"),
    path("<uuid:user_id>/enable", UserEnableView.as_view(), name="user-enable"),
]

# Self-service endpoints (mounted at /v1/me/)
me_urlpatterns = [
    path("", MeView.as_view(), name="me"),
    path("mfa/setup", MFASetupView.as_view(), name="mfa-setup"),
]
