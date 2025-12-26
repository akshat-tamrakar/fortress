"""
Health check endpoints for monitoring and load balancers.
"""

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.db import connection
import redis


def health_check(request):
    """
    Basic health check endpoint.
    Returns 200 if the service is running.
    """
    return JsonResponse({"status": "healthy", "service": "fortress"})


def readiness_check(request):
    """
    Readiness check endpoint.
    Verifies critical dependencies (database, cache) are accessible.
    """
    checks = {
        "status": "ready",
        "checks": {
            "database": "unknown",
            "cache": "unknown",
        },
    }

    # Check database connectivity
    try:
        connection.ensure_connection()
        checks["checks"]["database"] = "healthy"
    except Exception as e:
        checks["checks"]["database"] = f"unhealthy: {str(e)}"
        checks["status"] = "not_ready"

    # Check Redis/cache connectivity
    try:
        cache.set("health_check", "ok", timeout=10)
        value = cache.get("health_check")
        if value == "ok":
            checks["checks"]["cache"] = "healthy"
        else:
            checks["checks"]["cache"] = "unhealthy: cache read failed"
            checks["status"] = "not_ready"
    except Exception as e:
        checks["checks"]["cache"] = f"unhealthy: {str(e)}"
        checks["status"] = "not_ready"

    status_code = 200 if checks["status"] == "ready" else 503
    return JsonResponse(checks, status=status_code)


def liveness_check(request):
    """
    Liveness check endpoint.
    Simple check to verify the application process is alive.
    """
    return JsonResponse({"status": "alive", "service": "fortress"})
