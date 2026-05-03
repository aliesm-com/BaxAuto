from rest_framework import permissions

SAFE = permissions.SAFE_METHODS


def user_can_mutate_app_data(user) -> bool:
    """Unsafe API calls allowed unless the account is viewer-only."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, 'is_admin', False) or getattr(user, 'is_editor', False):
        return True
    return not getattr(user, 'is_viewer', False)


class IsSuperuser(permissions.BasePermission):
    """Only Django superusers."""

    message = 'Superuser privileges required.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_superuser)


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


class ViewerCannotMutate(permissions.BasePermission):
    """
    Authenticated reads allowed.

    POST/PATCH/PUT/DELETE require editor, app admin, or superuser; plain users may mutate.
    Viewer-only accounts (``is_viewer`` without editor/admin/superuser) are read-only.
    """

    message = 'Write operations require editor or admin privileges.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE:
            return True
        return user_can_mutate_app_data(request.user)


class ScheduledJobAccessPermission(permissions.BasePermission):
    """Any authenticated user may read schedules; writes restricted to app admins."""

    message = 'Managing schedules requires admin privileges.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE:
            return True
        return bool(request.user.is_superuser or getattr(request.user, 'is_admin', False))
