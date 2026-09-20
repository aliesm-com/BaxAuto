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
def backup_saved_connection(
    connection_id: int,
    owner_user_id: int,
    compress: bool = False,
    schedule_job_id: int | None = None,
    schedule_job_name: str = '',
) -> str:
    """
    Run :func:`db_connections.services.perform_backup` for a connection row.

    ``owner_user_id`` must match ``DatabaseConnection.user_id`` so scheduled backups
    stay scoped to that user's saved connections. After success, applies the schedule's
    retention policy (if any).
    """
    conn = DatabaseConnection.objects.get(pk=connection_id, user_id=owner_user_id)
    path, _name, purge_local = perform_backup(
        conn,
        trigger=BackupRecord.Trigger.SCHEDULED,
        compress=bool(compress),
        schedule_job_id=schedule_job_id,
        schedule_job_name=schedule_job_name or '',
    )
    if purge_local:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    if schedule_job_id:
        from scheduler.models import ScheduledJob

        from backups.retention import prune_schedule_backups

        retention = (
            ScheduledJob.objects.filter(pk=schedule_job_id)
            .values_list('retention_days', flat=True)
            .first()
        )
        prune_schedule_backups(schedule_job_id, retention_days=retention)
    return str(path)


REGISTERED_SCHEDULER_TASKS: dict[str, Task] = {
    'noop': noop_task,
    'backup_saved_connection': backup_saved_connection,
}
