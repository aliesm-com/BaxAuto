from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from baxconf.alertlog import log_alert, log_http_alert

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
