from __future__ import annotations

from django.db.models import Q
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import ViewerCannotMutate
from baxconf.alertlog import log_alert, log_http_alert
from db_connections.access import connection_access_role

from .services import perform_restore, resolved_backup_file
from dbs.base import BackupRestoreError

from .models import BackupRecord, RestoreRecord
from .serializers import (
    BackupRecordSerializer,
    RestoreRecordSerializer,
    RestoreRequestSerializer,
)
from .stale import cancel_in_progress_backup, cancel_in_progress_restore


class BackupRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """List backup history, download artifacts, and trigger restores."""

    serializer_class = BackupRecordSerializer
    permission_classes = [IsAuthenticated, ViewerCannotMutate]

    def get_queryset(self):
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
        try:
            path = resolved_backup_file(backup)
        except BackupRestoreError as e:
            log_http_alert(
                str(e),
                http_status=status.HTTP_404_NOT_FOUND,
                source='backup_download',
                backup_id=backup.pk,
            )
            return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)
        if not path.is_file():
            log_http_alert(
                'Backup file missing on disk.',
                http_status=status.HTTP_404_NOT_FOUND,
                source='backup_download',
                backup_id=backup.pk,
            )
            return Response({'detail': 'Backup file missing on disk.'}, status=status.HTTP_404_NOT_FOUND)
        name = backup.download_filename or path.name
        log_alert(
            f'Downloaded backup #{backup.pk} ({name}).',
            status='success',
            source='backup_download',
            backup_id=backup.pk,
            connection_id=backup.connection_id,
        )
        return FileResponse(path.open('rb'), as_attachment=True, filename=name)

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
        kw = {k: v for k, v in ser.validated_data.items()}
        try:
            rr = perform_restore(backup=backup, initiated_by=request.user, restore_kwargs=kw)
        except BackupRestoreError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RestoreRecordSerializer(rr).data, status=status.HTTP_201_CREATED)


class RestoreRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """Restore attempt history for the current user's connections."""

    serializer_class = RestoreRecordSerializer
    permission_classes = [IsAuthenticated, ViewerCannotMutate]

    def get_queryset(self):
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
