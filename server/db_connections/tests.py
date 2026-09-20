from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from backups.models import BackupRecord
from backups.services import perform_restore
from db_connections.models import DatabaseConnection
from db_connections.services import perform_backup
from dbs.base import BackupRestoreError

User = get_user_model()


def _has(records: list[str], *needles: str) -> bool:
    return any(all(n in line for n in needles) for line in records)


class ConnectionOperationLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('bob', password='secret12xx')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_connection_success_logs(self):
        with self.assertLogs('baxauto.alert', level='INFO') as cm:
            res = self.client.post(
                '/api/db-connections/',
                {'name': 'prod', 'engine': 'postgresql', 'host': '127.0.0.1', 'port': 5432},
                format='json',
            )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(_has(cm.output, 'status=success', 'source=connection', 'prod'))

    def test_connection_test_failure_logs(self):
        conn = DatabaseConnection.objects.create(
            user=self.user,
            name='prod',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='127.0.0.1',
            port=1,
        )
        with patch('db_connections.services.dbs_test', side_effect=BackupRestoreError('refused')):
            with self.assertLogs('baxauto.alert', level='ERROR') as cm:
                res = self.client.post(f'/api/db-connections/{conn.pk}/test_connection/')
        self.assertEqual(res.status_code, 400)
        self.assertTrue(_has(cm.output, 'status=error', 'source=connection_test', 'refused'))

    def test_connection_test_success_logs(self):
        conn = DatabaseConnection.objects.create(
            user=self.user,
            name='prod',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='127.0.0.1',
        )
        with patch('db_connections.services.dbs_test', return_value=None):
            with self.assertLogs('baxauto.alert', level='INFO') as cm:
                res = self.client.post(f'/api/db-connections/{conn.pk}/test_connection/')
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body['ok'])
        self.assertTrue(body['ssh']['ok'])
        self.assertFalse(body['ssh']['enabled'])
        self.assertTrue(body['database']['ok'])
        self.assertTrue(_has(cm.output, 'status=success', 'source=connection_test', 'prod'))

    def test_connection_test_reports_ssh_and_db(self):
        from contextlib import contextmanager

        conn = DatabaseConnection.objects.create(
            user=self.user,
            name='via-ssh',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='127.0.0.1',
            port=5432,
            ssh_enabled=True,
            ssh_host='bastion.example',
            ssh_username='deploy',
            ssh_password='secret',
            ssh_host_key_fingerprint='SHA256:abcdef',
        )

        @contextmanager
        def fake_forwards(**_kwargs):
            yield [55432]

        with patch('db_connections.services.ssh_local_forwards', fake_forwards):
            with patch('db_connections.services.dbs_test', return_value=None):
                res = self.client.post(f'/api/db-connections/{conn.pk}/test_connection/')
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body['ok'])
        self.assertTrue(body['ssh']['enabled'])
        self.assertTrue(body['ssh']['ok'])
        self.assertIn('55432', body['ssh']['detail'])
        self.assertTrue(body['database']['ok'])


class BackupRestoreLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('cara', password='secret12xx')
        self.conn = DatabaseConnection.objects.create(
            user=self.user,
            name='shop',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='127.0.0.1',
            port=5432,
        )

    def test_backup_success_logs(self):
        def fake_backup(_engine, _params, dest, **_kwargs):
            path = Path(dest)
            path.write_bytes(b'dump-bytes')
            return path

        with TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                with patch('db_connections.services.dbs_backup', side_effect=fake_backup):
                    with self.assertLogs('baxauto.alert', level='INFO') as cm:
                        perform_backup(self.conn, initiated_by=self.user)
        self.assertTrue(_has(cm.output, 'status=success', 'source=backup', 'shop', 'completed'))
        self.assertEqual(BackupRecord.objects.filter(status=BackupRecord.Status.SUCCESS).count(), 1)

    def test_backup_failure_logs(self):
        with TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                with patch('db_connections.services.dbs_backup', side_effect=BackupRestoreError('pg_dump missing')):
                    with self.assertLogs('baxauto.alert', level='ERROR') as cm:
                        with self.assertRaises(BackupRestoreError):
                            perform_backup(self.conn, initiated_by=self.user)
        self.assertTrue(_has(cm.output, 'status=error', 'source=backup', 'pg_dump missing'))
        self.assertEqual(BackupRecord.objects.filter(status=BackupRecord.Status.FAILED).count(), 1)

    def test_restore_success_logs(self):
        with TemporaryDirectory() as tmp:
            media = Path(tmp)
            artifact = media / 'db_exports' / 'x.dump'
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b'dump-bytes')
            backup = BackupRecord.objects.create(
                connection=self.conn,
                initiated_by=self.user,
                status=BackupRecord.Status.SUCCESS,
                engine=self.conn.engine,
                relative_media_path='db_exports/x.dump',
                download_filename='x.dump',
                size_bytes=10,
            )
            with override_settings(MEDIA_ROOT=tmp):
                with patch('backups.services.dbs_restore', return_value=None):
                    with self.assertLogs('baxauto.alert', level='INFO') as cm:
                        perform_restore(backup=backup, initiated_by=self.user, restore_kwargs={})
        self.assertTrue(_has(cm.output, 'status=success', 'source=restore', 'completed'))

    def test_backup_gzip_and_uploads_to_all_destinations(self):
        from storage.models import StorageDestination

        StorageDestination.objects.create(
            user=self.user,
            name='minio',
            kind=StorageDestination.Kind.S3,
            bucket='backups',
            username='ak',
            secret='sk',
        )
        StorageDestination.objects.create(
            user=self.user,
            name='sftp-offsite',
            kind=StorageDestination.Kind.SFTP,
            host='sftp.example.com',
            username='bax',
            secret='pw',
            remote_path='/dumps',
        )
        other = User.objects.create_user('other', password='secret12xx')
        StorageDestination.objects.create(
            user=other,
            name='not-mine',
            kind=StorageDestination.Kind.S3,
            bucket='other',
            username='ak',
            secret='sk',
        )

        def fake_backup(_engine, _params, dest, **_kwargs):
            path = Path(dest)
            path.write_bytes(b'dump-bytes-here')
            return path

        uploaded = []

        def fake_upload(dest, local_path, remote_relative):
            uploaded.append((dest.name, remote_relative, Path(local_path).read_bytes()[:2]))
            return f'remote/{remote_relative}'

        with TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                with patch('db_connections.services.dbs_backup', side_effect=fake_backup):
                    with patch('db_connections.services.upload_backup_file', side_effect=fake_upload):
                        path, filename = perform_backup(self.conn, initiated_by=self.user, compress=True)

            self.assertTrue(filename.endswith('.gz'))
            self.assertTrue(path.is_file())
            self.assertIn('/manual/', str(path).replace('\\', '/'))
            names = [n for n, _rel, _magic in uploaded]
            self.assertEqual(names, ['minio', 'sftp-offsite'])
            for _n, rel, _magic in uploaded:
                self.assertIn('/manual/', rel.replace('\\', '/'))
                self.assertTrue(rel.endswith('.gz'))
            rec = BackupRecord.objects.get(status=BackupRecord.Status.SUCCESS)
            self.assertTrue(rec.compressed)
            self.assertEqual(len(rec.storage_uploads), 2)
            self.assertTrue(all(u['ok'] for u in rec.storage_uploads))
            self.assertIn('/manual/', rec.relative_media_path)

    def test_restore_gzipped_dump(self):
        import gzip

        with TemporaryDirectory() as tmp:
            media = Path(tmp)
            artifact = media / 'db_exports' / 'x.dump.gz'
            artifact.parent.mkdir(parents=True)
            with gzip.open(artifact, 'wb') as fh:
                fh.write(b'dump-bytes')
            backup = BackupRecord.objects.create(
                connection=self.conn,
                initiated_by=self.user,
                status=BackupRecord.Status.SUCCESS,
                engine=self.conn.engine,
                relative_media_path='db_exports/x.dump.gz',
                download_filename='x.dump.gz',
                size_bytes=10,
                compressed=True,
            )
            seen: dict[str, bytes] = {}

            def fake_restore(*_args, **kwargs):
                seen['bytes'] = Path(kwargs['src']).read_bytes()

            with override_settings(MEDIA_ROOT=tmp):
                with patch('backups.services.dbs_restore', side_effect=fake_restore):
                    with self.assertLogs('baxauto.alert', level='INFO'):
                        perform_restore(backup=backup, initiated_by=self.user, restore_kwargs={})
            self.assertEqual(seen['bytes'], b'dump-bytes')


class SshTunnelHelperTests(TestCase):
    def test_normalize_fingerprint(self):
        from db_connections.ssh_tunnel import fingerprints_match, normalize_fingerprint

        self.assertEqual(
            normalize_fingerprint('AbCdEf'),
            'SHA256:AbCdEf',
        )
        self.assertTrue(fingerprints_match('SHA256:abc', 'abc'))

    def test_tunneled_params_rewrites_host_port(self):
        from contextlib import contextmanager

        from db_connections.services import tunneled_connection_params

        user = User.objects.create_user('sshuser', password='secret12xx')
        conn = DatabaseConnection.objects.create(
            user=user,
            name='tunneled-pg',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='127.0.0.1',
            port=5432,
            ssh_enabled=True,
            ssh_host='bastion.example',
            ssh_port=22,
            ssh_username='deploy',
            ssh_private_key='-----BEGIN OPENSSH PRIVATE KEY-----\nfake\n-----END OPENSSH PRIVATE KEY-----',
            ssh_host_key_fingerprint='SHA256:testhostkeyfingerprintvalue',
        )

        @contextmanager
        def fake_forwards(**_kwargs):
            yield [55432]

        with patch('db_connections.services.ssh_local_forwards', fake_forwards):
            with tunneled_connection_params(conn) as params:
                self.assertEqual(params['host'], '127.0.0.1')
                self.assertEqual(params['port'], 55432)

    def test_clickhouse_forwards_http_port(self):
        from contextlib import contextmanager

        from db_connections.services import tunneled_connection_params

        user = User.objects.create_user('chuser', password='secret12xx')
        conn = DatabaseConnection.objects.create(
            user=user,
            name='tunneled-ch',
            engine=DatabaseConnection.Engine.CLICKHOUSE,
            host='127.0.0.1',
            port=9000,
            extra_options={'http_port': 8123},
            ssh_enabled=True,
            ssh_host='bastion.example',
            ssh_username='deploy',
            ssh_password='secret',
            ssh_host_key_fingerprint='SHA256:abcdef',
        )

        seen: dict = {}

        @contextmanager
        def fake_forwards(**kwargs):
            seen['remotes'] = kwargs['remotes']
            yield [19000, 18123]

        with patch('db_connections.services.ssh_local_forwards', fake_forwards):
            with tunneled_connection_params(conn) as params:
                self.assertEqual(params['port'], 19000)
                self.assertEqual(params['extra_options']['http_port'], 18123)
        self.assertEqual(seen['remotes'], [('127.0.0.1', 9000), ('127.0.0.1', 8123)])

    def test_test_connection_uses_tunnel(self):
        from db_connections.services import test_saved_connection

        user = User.objects.create_user('probe', password='secret12xx')
        conn = DatabaseConnection.objects.create(
            user=user,
            name='probe-pg',
            engine=DatabaseConnection.Engine.POSTGRESQL,
            host='10.0.0.5',
            port=5432,
            ssh_enabled=True,
            ssh_host='bastion.example',
            ssh_username='deploy',
            ssh_password='secret',
            ssh_host_key_fingerprint='SHA256:abcdef',
        )

        from contextlib import contextmanager

        @contextmanager
        def fake_forwards(**_kwargs):
            yield [12345]

        captured: dict = {}

        def fake_test(_engine, params):
            captured.update(params)

        with patch('db_connections.services.ssh_local_forwards', fake_forwards):
            with patch('db_connections.services.dbs_test', side_effect=fake_test):
                test_saved_connection(conn)
        self.assertEqual(captured['host'], '127.0.0.1')
        self.assertEqual(captured['port'], 12345)


class SshTunnelApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('apiowner', password='secret12xx')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_requires_fingerprint_when_ssh_enabled(self):
        res = self.client.post(
            '/api/db-connections/',
            {
                'name': 'ssh-pg',
                'engine': 'postgresql',
                'host': '127.0.0.1',
                'port': 5432,
                'ssh_enabled': True,
                'ssh_host': 'bastion.example',
                'ssh_username': 'deploy',
                'ssh_private_key': '-----BEGIN OPENSSH PRIVATE KEY-----\nx\n-----END-----',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('ssh_host_key_fingerprint', res.json())

    def test_create_ssh_connection_ok(self):
        res = self.client.post(
            '/api/db-connections/',
            {
                'name': 'ssh-pg',
                'engine': 'postgresql',
                'host': '127.0.0.1',
                'port': 5432,
                'ssh_enabled': True,
                'ssh_host': 'bastion.example',
                'ssh_port': 22,
                'ssh_username': 'deploy',
                'ssh_private_key': '-----BEGIN OPENSSH PRIVATE KEY-----\nx\n-----END-----',
                'ssh_host_key_fingerprint': 'abcdef123',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()
        self.assertTrue(body['ssh_enabled'])
        self.assertTrue(body['ssh_private_key_set'])
        self.assertNotIn('ssh_private_key', body)
        self.assertEqual(body['ssh_host_key_fingerprint'], 'SHA256:abcdef123')
        conn = DatabaseConnection.objects.get(pk=body['id'])
        self.assertTrue(conn.ssh_private_key.startswith('-----BEGIN'))
