from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from backups.models import BackupRecord
from backups.stale import sweep_stale_in_progress
from db_connections.models import DatabaseConnection
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


class StaleInProgressSweepTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('erin', password='secret12xx')
        self.conn = DatabaseConnection.objects.create(
            user=self.user,
            name='shop',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='127.0.0.1',
        )

    def test_removes_backup_older_than_one_hour_and_alerts(self):
        stale = BackupRecord.objects.create(
            connection=self.conn,
            initiated_by=self.user,
            status=BackupRecord.Status.IN_PROGRESS,
            engine=self.conn.engine,
        )
        fresh = BackupRecord.objects.create(
            connection=self.conn,
            initiated_by=self.user,
            status=BackupRecord.Status.IN_PROGRESS,
            engine=self.conn.engine,
        )
        BackupRecord.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(hours=1, minutes=5),
        )
        with self.assertLogs('baxauto.alert', level='WARNING') as cm:
            removed = sweep_stale_in_progress()
        self.assertEqual(removed, 1)
        self.assertFalse(BackupRecord.objects.filter(pk=stale.pk).exists())
        self.assertTrue(BackupRecord.objects.filter(pk=fresh.pk).exists())
        self.assertTrue(_has(cm.output, 'status=warning', 'source=backup', 'Stale in-progress'))

    def test_scheduler_tick_sweeps_before_running_jobs(self):
        BackupRecord.objects.create(
            connection=self.conn,
            initiated_by=self.user,
            status=BackupRecord.Status.IN_PROGRESS,
            engine=self.conn.engine,
        )
        BackupRecord.objects.all().update(created_at=timezone.now() - timedelta(hours=2))
        job = ScheduledJob(
            name='noop-after-sweep',
            enabled=True,
            schedule_kind=ScheduledJob.ScheduleKind.INTERVAL,
            interval_seconds=60,
            task_key='noop',
            run_as=self.user,
            next_run=timezone.now(),
        )
        job.save()
        with self.assertLogs('baxauto.alert', level='WARNING'):
            run_due_scheduled_jobs()
        self.assertEqual(BackupRecord.objects.count(), 0)
