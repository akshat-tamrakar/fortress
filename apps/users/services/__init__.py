"""
User services module.

Exports the user service singleton for use across the application.
"""

from apps.users.services.user_service import user_service

__all__ = ["user_service"]
