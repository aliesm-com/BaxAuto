"""Who can see or change a :class:`~db_connections.models.DatabaseConnection`."""

from __future__ import annotations

from django.db.models import Q

from .models import DatabaseConnection, DatabaseConnectionShare


def connections_visible_q(user):
    """Q object for connections owned by or shared with ``user``."""
    return Q(user=user) | Q(shares__user=user)


def connection_access_role(user, connection: DatabaseConnection) -> str | None:
    """
    Return ``owner``, ``editor``, ``viewer``, or ``None`` if no access.

    Call only for connections the user is allowed to see (e.g. from scoped queryset).
    """
    if connection.user_id == user.pk:
        return 'owner'
    share = (
        DatabaseConnectionShare.objects.filter(connection_id=connection.pk, user=user)
        .values_list('role', flat=True)
        .first()
    )
    return share
