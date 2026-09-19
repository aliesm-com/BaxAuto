from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from scheduler.models import ScheduledJob
from scheduler.services import run_due_scheduled_jobs

User = get_user_model()


def _has(records: list[str], *needles: str) -> bool:
    return any(all(n in line for n in needles) for line in records)


class SchedulerOperationLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('dana', password='secret12xx', is_admin=True)

    def test_noop_job_success_logs(self):
        job = ScheduledJob(
            name='heartbeat',
            enabled=True,
            schedule_kind=ScheduledJob.ScheduleKind.INTERVAL,
            interval_seconds=60,
            task_key='noop',
            run_as=self.user,
            next_run=timezone.now(),
        )
        job.save()
        with self.assertLogs('baxauto.alert', level='INFO') as cm:
            processed = run_due_scheduled_jobs()
        self.assertEqual(processed, 1)
        job.refresh_from_db()
        self.assertEqual(job.last_status, ScheduledJob.LastStatus.SUCCESS)
        self.assertTrue(_has(cm.output, 'status=success', 'source=schedule', 'heartbeat'))

    def test_unknown_task_failure_logs(self):
        job = ScheduledJob(
            name='broken',
            enabled=True,
            schedule_kind=ScheduledJob.ScheduleKind.INTERVAL,
            interval_seconds=60,
            task_key='noop',
            run_as=self.user,
            next_run=timezone.now(),
        )
        job.save()
        ScheduledJob.objects.filter(pk=job.pk).update(task_key='does_not_exist')
        with self.assertLogs('baxauto.alert', level='ERROR') as cm:
            processed = run_due_scheduled_jobs()
        self.assertEqual(processed, 1)
        job.refresh_from_db()
        self.assertEqual(job.last_status, ScheduledJob.LastStatus.FAILED)
        self.assertTrue(_has(cm.output, 'status=error', 'source=schedule', 'Unknown task_key'))
