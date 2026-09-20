"""Reassign user-owned rows before hard-deleting a user account."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet

from db_connections.models import DatabaseConnection, DatabaseConnectionShare
from scheduler.models import ScheduledJob
from storage.models import StorageDestination

User = get_user_model()


def _unique_name(model, owner: User, base_name: str, *, exclude_pk: int | None = None) -> str:
    """Return ``base_name`` or a suffixed variant unused by ``owner`` on ``model``."""
    qs = model.objects.filter(user=owner, name=base_name)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if not qs.exists():
        return base_name

    suffix = 2
    while True:
        candidate = f'{base_name} ({suffix})'
        qs = model.objects.filter(user=owner, name=candidate)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.exists():
            return candidate
        suffix += 1


def owned_asset_counts(user: User) -> dict[str, int]:
    return {
        'database_connections': DatabaseConnection.objects.filter(user=user).count(),
        'storage_destinations': StorageDestination.objects.filter(user=user).count(),
        'scheduled_jobs': ScheduledJob.objects.filter(run_as=user).count(),
        'connection_shares_received': DatabaseConnectionShare.objects.filter(user=user).count(),
    }


@transaction.atomic
def transfer_user_owned_data(from_user: User, to_user: User) -> dict[str, int]:
    """
    Move CASCADE-owned assets from ``from_user`` to ``to_user``.

    After this, deleting ``from_user`` no longer wipes connections, backups
    (via connection), storage destinations, or scheduled jobs.
    """
    if from_user.pk == to_user.pk:
        raise ValueError('Cannot transfer ownership to the same user.')

    moved = {
        'database_connections': 0,
        'storage_destinations': 0,
        'scheduled_jobs': 0,
        'shares_removed_for_new_owner': 0,
    }

    connection_ids: list[int] = []
    for conn in DatabaseConnection.objects.filter(user=from_user).iterator():
        conn.name = _unique_name(DatabaseConnection, to_user, conn.name, exclude_pk=conn.pk)
        conn.user = to_user
        conn.save(update_fields=['user', 'name', 'updated_at'])
        connection_ids.append(conn.pk)
        moved['database_connections'] += 1

    if connection_ids:
        deleted, _ = DatabaseConnectionShare.objects.filter(
            connection_id__in=connection_ids,
            user=to_user,
        ).delete()
        moved['shares_removed_for_new_owner'] = deleted

    for dest in StorageDestination.objects.filter(user=from_user).iterator():
        dest.name = _unique_name(StorageDestination, to_user, dest.name, exclude_pk=dest.pk)
        dest.user = to_user
        dest.save(update_fields=['user', 'name', 'updated_at'])
        moved['storage_destinations'] += 1

    updated = ScheduledJob.objects.filter(run_as=from_user).update(run_as=to_user)
    moved['scheduled_jobs'] = updated

    return moved


@transaction.atomic
def transfer_and_delete_users(users: QuerySet | list[User], to_user: User) -> None:
    """Transfer owned data for each user, then delete them."""
    user_list = list(users)
    if not user_list:
        return
    if any(u.pk == to_user.pk for u in user_list):
        raise ValueError('Transfer target cannot be among the users being deleted.')

    for user in user_list:
        transfer_user_owned_data(user, to_user)

    User.objects.filter(pk__in=[u.pk for u in user_list]).delete()
