from rest_framework import permissions


class IsAppAdmin(permissions.BasePermission):
    """Superusers or users with ``is_admin`` (app-level)."""

    message = 'Admin privileges required.'

    def has_permission(self, request, view):
        u = request.user
        return bool(
            u
            and u.is_authenticated
            and (u.is_superuser or getattr(u, 'is_admin', False))
        )
