from __future__ import annotations

from django.db import connection, transaction
from django.utils import timezone

from .models import ScheduledJob
from .tasks import REGISTERED_SCHEDULER_TASKS


def run_due_scheduled_jobs(limit: int = 50) -> int:
    """
    Find enabled jobs with ``next_run`` in the past, enqueue their Django Task,
    then advance ``next_run``. Intended to be invoked periodically (cron/systemd/Kubernetes CronJob).

    Uses ``select_for_update`` when the database supports it so overlapping ticks contend safely.
    """
    now = timezone.now()
    base_qs = (
        ScheduledJob.objects.filter(enabled=True, next_run__lte=now)
        .order_by('next_run')
        .values_list('pk', flat=True)[:limit]
    )
    ids = list(base_qs)
    processed = 0

    for job_id in ids:
        with transaction.atomic():
            qs = ScheduledJob.objects.filter(pk=job_id)
            if connection.features.supports_select_for_update:
                qs = qs.select_for_update()
            job = qs.first()
            if job is None:
                continue
            if not job.enabled or job.next_run is None or job.next_run > timezone.now():
                continue

            task_obj = REGISTERED_SCHEDULER_TASKS.get(job.task_key)
            if task_obj is None:
                job.last_status = ScheduledJob.LastStatus.FAILED
                job.last_error = 'Unknown task_key.'
                after_fail = timezone.now()
                job.last_run = after_fail
                job.next_run = job.compute_next_run_after(after_fail)
                job.save()
                processed += 1
                continue

            kwargs = dict(job.payload or {})
            if job.task_key == 'backup_saved_connection':
                kwargs['owner_user_id'] = job.run_as_id

            try:
                task_obj.enqueue(**kwargs)
                job.last_status = ScheduledJob.LastStatus.SUCCESS
                job.last_error = ''
            except Exception as exc:
                job.last_status = ScheduledJob.LastStatus.FAILED
                job.last_error = str(exc)[:8000]

            after = timezone.now()
            job.last_run = after
            job.next_run = job.compute_next_run_after(after)
            job.save()
            processed += 1

    return processed
