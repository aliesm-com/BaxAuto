from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from backups.models import BackupRecord
from baxconf.alertlog import log_alert, log_http_alert
from db_connections.models import DatabaseConnection
from scheduler.models import ScheduledJob
from storage.models import StorageDestination

from .ownership import transfer_and_delete_users, transfer_user_owned_data

User = get_user_model()


def _has(records: list[str], *needles: str) -> bool:
    return any(all(n in line for n in needles) for line in records)


class LogAlertHelperTests(TestCase):
    def test_success_uses_info(self):
        with self.assertLogs('baxauto.alert', level='INFO') as cm:
            log_alert('Backup finished.', status='success', source='backup', backup_id=9)
        self.assertTrue(_has(cm.output, 'INFO', 'status=success', 'source=backup', 'backup_id=9', 'Backup finished.'))

    def test_error_uses_error(self):
        with self.assertLogs('baxauto.alert', level='ERROR') as cm:
            log_alert('Backup failed: boom', status='error', source='backup')
        self.assertTrue(_has(cm.output, 'ERROR', 'status=error', 'Backup failed: boom'))

    def test_warning_uses_warning(self):
        with self.assertLogs('baxauto.alert', level='WARNING') as cm:
            log_alert('missing file', status='warning', source='backup_download')
        self.assertTrue(_has(cm.output, 'WARNING', 'status=warning', 'missing file'))

    def test_http_404_is_warning(self):
        with self.assertLogs('baxauto.alert', level='WARNING') as cm:
            log_http_alert('Share not found.', http_status=404, source='connection_share')
        self.assertTrue(_has(cm.output, 'WARNING', 'status=warning', 'http_status=404'))

    def test_http_400_is_error(self):
        with self.assertLogs('baxauto.alert', level='ERROR') as cm:
            log_http_alert('bad request', http_status=400, source='restore')
        self.assertTrue(_has(cm.output, 'ERROR', 'status=error', 'http_status=400'))

    def test_error_is_persisted(self):
        from backups.models import AlertEvent

        log_alert('Backup failed: boom', status='error', source='backup', error='boom')
        row = AlertEvent.objects.get()
        self.assertEqual(row.status, AlertEvent.Status.ERROR)
        self.assertEqual(row.webhook_status, 'down')
        self.assertEqual(row.error, 'boom')
        self.assertEqual(row.description, 'Backup failed: boom')

    def test_warning_webhook_status_is_degraded(self):
        from backups.models import AlertEvent

        log_alert('partial upload', status='warning', source='backup', error='storage upload failed')
        row = AlertEvent.objects.get()
        self.assertEqual(row.webhook_status, 'degraded')
        self.assertEqual(row.error, 'storage upload failed')


class AuthOperationLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='secret12xx')
        self.client = APIClient()

    def test_login_success_logs(self):
        with self.assertLogs('baxauto.alert', level='INFO') as cm:
            res = self.client.post(
                '/api/auth/login/',
                {'username': 'alice', 'password': 'secret12xx'},
                format='json',
            )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(_has(cm.output, 'status=success', 'source=login', 'alice'))

    def test_login_failure_logs(self):
        with self.assertLogs('baxauto.alert', level='WARNING') as cm:
            res = self.client.post(
                '/api/auth/login/',
                {'username': 'alice', 'password': 'wrong-password'},
                format='json',
            )
        self.assertEqual(res.status_code, 401)
        self.assertTrue(any('status=warning' in line or 'status=error' in line for line in cm.output))

    def test_profile_update_success_logs(self):
        self.client.force_authenticate(self.user)
        with self.assertLogs('baxauto.alert', level='INFO') as cm:
            res = self.client.patch('/api/auth/me/', {'first_name': 'Ali'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(_has(cm.output, 'status=success', 'source=profile', 'alice'))


class UserOwnershipTransferTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='secret12xx')
        self.heir = User.objects.create_user('heir', password='secret12xx')
        self.conn = DatabaseConnection.objects.create(
            user=self.owner,
            name='Alizade Postgres',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='127.0.0.1',
            port=5432,
        )
        self.backup = BackupRecord.objects.create(
            connection=self.conn,
            initiated_by=self.owner,
            engine=DatabaseConnection.Engine.POSTGRESQL,
            status=BackupRecord.Status.SUCCESS,
        )
        self.storage = StorageDestination.objects.create(
            user=self.owner,
            name='Alizade Storage',
            kind=StorageDestination.Kind.S3,
            username='key',
            bucket='bucket',
        )
        self.job = ScheduledJob(
            name='Alizade-daily',
            enabled=True,
            schedule_kind=ScheduledJob.ScheduleKind.INTERVAL,
            interval_seconds=86400,
            task_key='noop',
            run_as=self.owner,
            next_run=timezone.now(),
        )
        self.job.save()

    def test_transfer_keeps_related_rows(self):
        transfer_user_owned_data(self.owner, self.heir)
        self.conn.refresh_from_db()
        self.storage.refresh_from_db()
        self.job.refresh_from_db()
        self.backup.refresh_from_db()

        self.assertEqual(self.conn.user_id, self.heir.pk)
        self.assertEqual(self.storage.user_id, self.heir.pk)
        self.assertEqual(self.job.run_as_id, self.heir.pk)
        self.assertEqual(self.backup.connection_id, self.conn.pk)

    def test_transfer_and_delete_preserves_backups(self):
        backup_id = self.backup.pk
        conn_id = self.conn.pk
        transfer_and_delete_users([self.owner], self.heir)

        self.assertFalse(User.objects.filter(pk=self.owner.pk).exists())
        self.assertTrue(DatabaseConnection.objects.filter(pk=conn_id, user=self.heir).exists())
        self.assertTrue(BackupRecord.objects.filter(pk=backup_id).exists())
        self.assertTrue(StorageDestination.objects.filter(pk=self.storage.pk, user=self.heir).exists())
        self.assertTrue(ScheduledJob.objects.filter(pk=self.job.pk, run_as=self.heir).exists())

    def test_name_collision_renames(self):
        DatabaseConnection.objects.create(
            user=self.heir,
            name='Alizade Postgres',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='127.0.0.1',
        )
        transfer_user_owned_data(self.owner, self.heir)
        self.conn.refresh_from_db()
        self.assertEqual(self.conn.name, 'Alizade Postgres (2)')
        self.assertEqual(self.conn.user_id, self.heir.pk)


class AdminUserDeleteApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            'boss', password='secret12xx', is_admin=True, is_staff=True
        )
        self.owner = User.objects.create_user('owner', password='secret12xx')
        self.heir = User.objects.create_user('heir', password='secret12xx')
        self.conn = DatabaseConnection.objects.create(
            user=self.owner,
            name='db',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='127.0.0.1',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_delete_requires_transfer_to(self):
        res = self.client.delete(f'/api/auth/users/{self.owner.pk}/')
        self.assertEqual(res.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.owner.pk).exists())

    def test_delete_with_transfer_keeps_connection(self):
        res = self.client.delete(
            f'/api/auth/users/{self.owner.pk}/',
            {'transfer_to': self.heir.pk},
            format='json',
        )
        self.assertEqual(res.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.owner.pk).exists())
        self.conn.refresh_from_db()
        self.assertEqual(self.conn.user_id, self.heir.pk)
