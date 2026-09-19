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
        self.assertTrue(_has(cm.output, 'status=success', 'source=connection_test', 'prod'))


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

        def fake_upload(dest, local_path, filename):
            uploaded.append((dest.name, filename, Path(local_path).read_bytes()[:2]))
            return f'remote/{filename}'

        with TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                with patch('db_connections.services.dbs_backup', side_effect=fake_backup):
                    with patch('db_connections.services.upload_backup_file', side_effect=fake_upload):
                        path, filename = perform_backup(self.conn, initiated_by=self.user, compress=True)

        self.assertTrue(filename.endswith('.gz'))
        self.assertTrue(path.is_file())
        names = [n for n, _fn, _magic in uploaded]
        self.assertEqual(names, ['minio', 'sftp-offsite'])
        rec = BackupRecord.objects.get(status=BackupRecord.Status.SUCCESS)
        self.assertTrue(rec.compressed)
        self.assertEqual(len(rec.storage_uploads), 2)
        self.assertTrue(all(u['ok'] for u in rec.storage_uploads))

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
