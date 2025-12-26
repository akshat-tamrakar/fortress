"""
URL configuration for fortress project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from apps.users.urls import me_urlpatterns
from fortress.views import health_check

urlpatterns = [
    # Health check endpoint (no authentication required)
    path("health", health_check, name="health"),
    path("admin/", admin.site.urls),
    # Django REST Framework authentication URLs (for browsable API)
    path("api-auth/", include("rest_framework.urls")),
    # API v1 endpoints
    path("v1/auth/", include(("apps.authentication.urls", "authentication"), namespace="auth")),
    path("v1/authorize/", include(("apps.authorization.urls", "authorization"), namespace="authorization")),
    path("v1/users/", include("apps.users.urls")),
    path("v1/me/", include(me_urlpatterns)),
]
