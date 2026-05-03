"""Django 6 background tasks used by :mod:`scheduler` job definitions."""

from __future__ import annotations

from django.tasks import task
from django.tasks.base import Task

from backups.models import BackupRecord
from db_connections.models import DatabaseConnection
from db_connections.services import perform_backup

TASK_KEY_CHOICES: tuple[tuple[str, str], ...] = (
    ('noop', 'No-op (log only)'),
    ('backup_saved_connection', 'Backup one saved DB connection'),
)


@task
def noop_task() -> str:
    """Cheap heartbeat task for validating the scheduler wiring."""
    return 'ok'


@task
def backup_saved_connection(connection_id: int, owner_user_id: int) -> str:
    """
    Run :func:`db_connections.services.perform_backup` for a connection row.

    ``owner_user_id`` must match ``DatabaseConnection.user_id`` so scheduled backups
    stay scoped to that user's saved connections.
    """
    conn = DatabaseConnection.objects.get(pk=connection_id, user_id=owner_user_id)
    path, _name = perform_backup(conn, trigger=BackupRecord.Trigger.SCHEDULED)
    return str(path)


REGISTERED_SCHEDULER_TASKS: dict[str, Task] = {
    'noop': noop_task,
    'backup_saved_connection': backup_saved_connection,
}
