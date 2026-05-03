from __future__ import annotations

from django.db.models import Q
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import ViewerCannotMutate
from db_connections.access import connection_access_role

from .services import perform_restore, resolved_backup_file
from dbs.base import BackupRestoreError

from .models import BackupRecord, RestoreRecord
from .serializers import (
    BackupRecordSerializer,
    RestoreRecordSerializer,
    RestoreRequestSerializer,
)


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
            return Response(
                {'detail': 'Backup did not complete successfully.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            path = resolved_backup_file(backup)
        except BackupRestoreError as e:
            return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)
        if not path.is_file():
            return Response({'detail': 'Backup file missing on disk.'}, status=status.HTTP_404_NOT_FOUND)
        name = backup.download_filename or path.name
        return FileResponse(path.open('rb'), as_attachment=True, filename=name)

    @extend_schema(request=RestoreRequestSerializer, responses={201: RestoreRecordSerializer})
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        backup = self.get_object()
        if connection_access_role(request.user, backup.connection) == 'viewer':
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
