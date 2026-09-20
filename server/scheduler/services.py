from __future__ import annotations

from typing import Any

from django.db import connection, connections, transaction
from django.tasks.base import Task, TaskResultStatus
from django.utils import timezone

from backups.stale import STALE_IN_PROGRESS_AFTER, sweep_stale_in_progress

from .models import ScheduledJob
from .tasks import REGISTERED_SCHEDULER_TASKS


def run_due_scheduled_jobs(limit: int = 50) -> int:
    """
    Find enabled jobs with ``next_run`` in the past, enqueue their Django Task,
    then record ``last_run`` / ``last_status``.

    The job row is claimed (``next_run`` advanced) in a short transaction so
    overlapping ticks skip it. The task itself runs *outside* that transaction —
    ImmediateBackend runs backups synchronously and must not hold a SQLite lock
    for the duration of ``pg_dump``.
    """
    sweep_stale_in_progress()

    now = timezone.now()
    ids = list(
        ScheduledJob.objects.filter(enabled=True, next_run__lte=now)
        .order_by('next_run')
        .values_list('pk', flat=True)[:limit]
    )
    processed = 0

    for job_id in ids:
        claimed = _claim_due_job(job_id)
        if claimed is None:
            continue
        _job, kwargs, task_obj = claimed
        if task_obj is None:
            processed += 1
            continue

        connections.close_all()
        try:
            result = task_obj.enqueue(**kwargs)
        except Exception as exc:
            _finish_job(job_id, success=False, error=str(exc)[:8000])
        else:
            if getattr(result, 'status', None) == TaskResultStatus.FAILED:
                _finish_job(job_id, success=False, error=_task_error_text(result))
            else:
                _finish_job(job_id, success=True, error='')
        processed += 1

    return processed


def _claim_due_job(job_id: int) -> tuple[ScheduledJob, dict[str, Any], Task | None] | None:
    with transaction.atomic():
        qs = ScheduledJob.objects.filter(pk=job_id)
        if getattr(connection.features, 'has_select_for_update', False):
            qs = qs.select_for_update()
        job = qs.first()
        if job is None or not job.enabled or job.next_run is None or job.next_run > timezone.now():
            return None

        claimed_at = timezone.now()
        task_obj = REGISTERED_SCHEDULER_TASKS.get(job.task_key)
        if task_obj is None:
            job.last_status = ScheduledJob.LastStatus.FAILED
            job.last_error = 'Unknown task_key.'
            job.last_run = claimed_at
            job.next_run = job.compute_next_run_after(claimed_at)
            job.save()
            from baxconf.alertlog import log_alert

            log_alert(
                f'Scheduled job “{job.name}” failed: {job.last_error}',
                status='error',
                source='schedule',
                job_id=job.pk,
                task_key=job.task_key,
            )
            return job, {}, None

        kwargs: dict[str, Any] = dict(job.payload or {})
        if job.task_key == 'backup_saved_connection':
            from backups.models import BackupRecord

            cid = kwargs.get('connection_id') or (job.payload or {}).get('connection_id')
            kwargs = {
                'connection_id': cid,
                'owner_user_id': job.run_as_id,
                'compress': bool((job.payload or {}).get('compress', False)),
                'schedule_job_id': job.pk,
                'schedule_job_name': job.name,
            }
            if cid and BackupRecord.objects.filter(
                connection_id=cid,
                status=BackupRecord.Status.IN_PROGRESS,
            ).exists():
                # Still running (sweep already cleared rows older than 1h).
                return None

        # Hold the row so overlapping ticks skip it. The user's interval/cron is
        # applied when the run finishes, not at claim time.
        job.next_run = claimed_at + STALE_IN_PROGRESS_AFTER
        job.save(update_fields=['next_run', 'updated_at'])
        return job, kwargs, task_obj


def _finish_job(job_id: int, *, success: bool, error: str) -> None:
    after = timezone.now()
    with transaction.atomic():
        qs = ScheduledJob.objects.filter(pk=job_id)
        if getattr(connection.features, 'has_select_for_update', False):
            qs = qs.select_for_update()
        job = qs.first()
        if job is None:
            return
        job.last_run = after
        if success:
            job.last_status = ScheduledJob.LastStatus.SUCCESS
            job.last_error = ''
        else:
            job.last_status = ScheduledJob.LastStatus.FAILED
            job.last_error = error[-8000:]
        job.next_run = job.compute_next_run_after(after)
        job.save(update_fields=['last_run', 'last_status', 'last_error', 'next_run', 'updated_at'])
        from baxconf.alertlog import log_alert

        if success:
            log_alert(
                f'Scheduled job “{job.name}” completed.',
                status='success',
                source='schedule',
                job_id=job.pk,
                task_key=job.task_key,
            )
        else:
            log_alert(
                f'Scheduled job “{job.name}” failed: {job.last_error or "Task failed."}',
                status='error',
                source='schedule',
                job_id=job.pk,
                task_key=job.task_key,
            )


def _task_error_text(result: Any) -> str:
    errors = getattr(result, 'errors', None) or []
    if errors:
        last = errors[-1]
        err = getattr(last, 'traceback', None) or getattr(last, 'exception_class_path', '')
        if err:
            return str(err)[-8000:]
    return 'Task failed.'
