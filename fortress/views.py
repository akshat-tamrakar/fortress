"""
Health check views for Fortress application.
"""

from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods


@never_cache
@require_http_methods(["GET", "HEAD"])
def health_check(request):
    """
    Health check endpoint for container orchestration and load balancers.
    
    Returns:
        JsonResponse: Simple OK response indicating the service is healthy
    """
    return JsonResponse({"status": "ok"}, status=200)
