"""URL configuration for the authorization app."""

from django.urls import path

from .views import AuthorizeView, BatchAuthorizeView

app_name = "authorization"

urlpatterns = [
    path("", AuthorizeView.as_view(), name="authorize"),
    path("batch", BatchAuthorizeView.as_view(), name="batch-authorize"),
]
