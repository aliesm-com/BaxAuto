from __future__ import annotations

from pathlib import Path

from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAppAdmin, ViewerCannotMutate
from baxconf.alertlog import log_alert, log_http_alert
from db_connections.access import connection_access_role
from dbs.base import BackupRestoreError
from storage.models import StorageDestination
from storage.transfer import StorageTransferError, download_backup_file

from .models import AppSettings, BackupRecord, RestoreRecord
from .serializers import (
    AppSettingsSerializer,
    BackupRecordSerializer,
    RestoreRecordSerializer,
    RestoreRequestSerializer,
)
from .services import (
    UnlinkingFile,
    local_backup_available,
    perform_restore,
    remote_relative_for_upload,
    resolved_backup_file,
    successful_storage_uploads,
)
from .stale import cancel_in_progress_backup, cancel_in_progress_restore


def _parse_storage_id(raw) -> int | None | object:
    """
    Parse storage_id query/body value.

    Returns None for local, int for remote, or a sentinel False when invalid.
    """
    if raw is None or raw == '' or str(raw).lower() == 'local':
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return False


class AppSettingsView(APIView):
    """Singleton app settings (keep local backups after remote upload)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: AppSettingsSerializer})
    def get(self, request):
        ser = AppSettingsSerializer(AppSettings.load())
        return Response(ser.data)

    @extend_schema(request=AppSettingsSerializer, responses={200: AppSettingsSerializer})
    def patch(self, request):
        if not IsAppAdmin().has_permission(request, self):
            raise PermissionDenied('Admin privileges required to change app settings.')
        obj = AppSettings.load()
        ser = AppSettingsSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class BackupRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """List backup history, download artifacts, and trigger restores."""

    serializer_class = BackupRecordSerializer
    permission_classes = [IsAuthenticated, ViewerCannotMutate]

    def get_queryset(self):
        from django.db.models import Q

        u = self.request.user
        return (
            BackupRecord.objects.filter(Q(connection__user=u) | Q(connection__shares__user=u))
            .distinct()
            .select_related('connection')
            .prefetch_related('restore_logs')
        )

    @extend_schema(request=None, responses={200: None})
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        backup = self.get_object()
        if backup.status != BackupRecord.Status.SUCCESS:
            log_http_alert(
                'Backup did not complete successfully.',
                http_status=status.HTTP_400_BAD_REQUEST,
                source='backup_download',
                backup_id=backup.pk,
            )
            return Response(
                {'detail': 'Backup did not complete successfully.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        storage_raw = request.query_params.get('storage_id')
        storage_id = _parse_storage_id(storage_raw)
        if storage_id is False:
            return Response(
                {'detail': 'Invalid storage_id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = backup.download_filename or f'backup-{backup.pk}'

        if storage_id is None:
            if not local_backup_available(backup):
                remotes = successful_storage_uploads(backup)
                if remotes:
                    log_http_alert(
                        'Local backup file is not available; pick a storage destination.',
                        http_status=status.HTTP_404_NOT_FOUND,
                        source='backup_download',
                        backup_id=backup.pk,
                    )
                    return Response(
                        {
                            'detail': 'Local backup file is not available. Pass storage_id to download from remote storage.',
                            'storage_uploads': remotes,
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )
                log_http_alert(
                    'Backup file missing on disk.',
                    http_status=status.HTTP_404_NOT_FOUND,
                    source='backup_download',
                    backup_id=backup.pk,
                )
                return Response({'detail': 'Backup file missing on disk.'}, status=status.HTTP_404_NOT_FOUND)
            try:
                path = resolved_backup_file(backup)
            except BackupRestoreError as e:
                return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)
            log_alert(
                f'Downloaded backup #{backup.pk} ({name}) from local storage.',
                status='success',
                source='backup_download',
                backup_id=backup.pk,
                connection_id=backup.connection_id,
            )
            return FileResponse(path.open('rb'), as_attachment=True, filename=name)

        uploads = {u['id']: u for u in successful_storage_uploads(backup)}
        entry = uploads.get(storage_id)
        if entry is None:
            return Response(
                {'detail': f'Storage destination #{storage_id} has no successful upload for this backup.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            dest = StorageDestination.objects.get(pk=storage_id)
        except StorageDestination.DoesNotExist:
            return Response(
                {'detail': f'Storage destination #{storage_id} no longer exists.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        import tempfile

        remote_rel = remote_relative_for_upload(backup, entry)
        suffix = Path(name).suffix or '.bin'
        tmp = tempfile.NamedTemporaryFile(prefix=f'bax-dl-{backup.pk}-', suffix=suffix, delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        try:
            download_backup_file(dest, remote_rel, tmp_path)
        except (StorageTransferError, OSError, BackupRestoreError) as e:
            tmp_path.unlink(missing_ok=True)
            log_http_alert(
                str(e),
                http_status=status.HTTP_502_BAD_GATEWAY,
                source='backup_download',
                backup_id=backup.pk,
            )
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        log_alert(
            f'Downloaded backup #{backup.pk} ({name}) from storage “{dest.name}”.',
            status='success',
            source='backup_download',
            backup_id=backup.pk,
            connection_id=backup.connection_id,
        )
        return FileResponse(UnlinkingFile(tmp_path), as_attachment=True, filename=name)

    @extend_schema(request=None, responses={204: None, 400: dict})
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Stop an in-progress backup and remove it from the list."""
        backup = self.get_object()
        role = connection_access_role(request.user, backup.connection)
        if role == 'viewer':
            raise PermissionDenied('Viewers cannot cancel backups on shared connections.')
        try:
            cancel_in_progress_backup(
                backup,
                reason='Cancelled from the panel.',
                cancelled_by=request.user,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=RestoreRequestSerializer, responses={201: RestoreRecordSerializer})
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        backup = self.get_object()
        if connection_access_role(request.user, backup.connection) == 'viewer':
            log_http_alert(
                'Viewers cannot run restores on shared connections.',
                http_status=status.HTTP_403_FORBIDDEN,
                source='restore',
                backup_id=backup.pk,
            )
            return Response(
                {'detail': 'Viewers cannot run restores on shared connections.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = RestoreRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        storage_id = data.pop('storage_id', None)
        try:
            rr = perform_restore(
                backup=backup,
                initiated_by=request.user,
                restore_kwargs=data,
                storage_id=storage_id,
            )
        except BackupRestoreError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RestoreRecordSerializer(rr).data, status=status.HTTP_201_CREATED)


class RestoreRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """Restore attempt history for the current user's connections."""

    serializer_class = RestoreRecordSerializer
    permission_classes = [IsAuthenticated, ViewerCannotMutate]

    def get_queryset(self):
        from django.db.models import Q

        u = self.request.user
        return (
            RestoreRecord.objects.filter(Q(connection__user=u) | Q(connection__shares__user=u))
            .distinct()
            .select_related('backup', 'connection', 'initiated_by')
        )

    @extend_schema(request=None, responses={204: None, 400: dict})
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Stop an in-progress restore and remove it from the list."""
        restore = self.get_object()
        role = connection_access_role(request.user, restore.connection)
        if role == 'viewer':
            raise PermissionDenied('Viewers cannot cancel restores on shared connections.')
        try:
            cancel_in_progress_restore(
                restore,
                reason='Cancelled from the panel.',
                cancelled_by=request.user,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
