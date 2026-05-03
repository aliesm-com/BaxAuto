from django.db import IntegrityError
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import ViewerCannotMutate
from dbs.base import BackupRestoreError

from .access import connection_access_role, connections_visible_q
from .models import DatabaseConnection, DatabaseConnectionShare
from .serializers import (
    ConnectionShareReadSerializer,
    ConnectionShareWriteSerializer,
    DatabaseConnectionSerializer,
)
from .services import perform_backup, test_saved_connection


class DatabaseConnectionViewSet(viewsets.ModelViewSet):
    """Saved DB connections: owner CRUD; shared users see list/detail per share role."""

    serializer_class = DatabaseConnectionSerializer
    permission_classes = [IsAuthenticated, ViewerCannotMutate]

    def get_queryset(self):
        u = self.request.user
        return (
            DatabaseConnection.objects.filter(connections_visible_q(u))
            .distinct()
            .select_related('user')
        )

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.pk:
            raise PermissionDenied('Only the connection owner can delete it.')
        super().perform_destroy(instance)

    def perform_update(self, serializer):
        role = connection_access_role(self.request.user, serializer.instance)
        if role not in ('owner', 'editor'):
            raise PermissionDenied('You do not have permission to edit this connection.')
        serializer.save()

    def _require_not_viewer_share(self, connection):
        role = connection_access_role(self.request.user, connection)
        if role == 'viewer':
            raise PermissionDenied('Viewers cannot run backups or connection tests.')

    @extend_schema(request=None, responses={200: dict})
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        conn = self.get_object()
        self._require_not_viewer_share(conn)
        try:
            test_saved_connection(conn)
        except BackupRestoreError as e:
            return Response({'ok': False, 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'ok': False, 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True})

    @extend_schema(request=None, responses={200: None})
    @action(detail=True, methods=['post'])
    def backup(self, request, pk=None):
        conn = self.get_object()
        self._require_not_viewer_share(conn)
        try:
            path, filename = perform_backup(conn, initiated_by=request.user)
        except BackupRestoreError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return FileResponse(path.open('rb'), as_attachment=True, filename=filename)

    @extend_schema(responses={200: ConnectionShareReadSerializer(many=True)})
    @action(detail=True, methods=['get', 'post'], url_path='shares')
    def shares(self, request, pk=None):
        conn = self.get_object()
        if conn.user_id != request.user.pk:
            raise PermissionDenied('Only the owner can manage shares.')

        if request.method == 'GET':
            rows = conn.shares.select_related('user').order_by('user__username')
            return Response(ConnectionShareReadSerializer(rows, many=True).data)

        ser = ConnectionShareWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        target = ser.validated_data['user']
        role = ser.validated_data['role']
        if target.pk == conn.user_id:
            raise ValidationError({'user': 'Cannot share with the owner (already has full access).'})
        try:
            share, created = DatabaseConnectionShare.objects.update_or_create(
                connection=conn,
                user=target,
                defaults={'role': role},
            )
        except IntegrityError as e:
            raise ValidationError(str(e)) from e
        st = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(ConnectionShareReadSerializer(share).data, status=st)

    @extend_schema(responses={204: None})
    @action(detail=True, methods=['delete'], url_path=r'shares/(?P<member_id>[0-9]+)')
    def shares_destroy(self, request, pk=None, member_id=None):
        conn = self.get_object()
        if conn.user_id != request.user.pk:
            raise PermissionDenied('Only the owner can manage shares.')
        deleted, _ = DatabaseConnectionShare.objects.filter(connection=conn, user_id=int(member_id)).delete()
        if not deleted:
            return Response({'detail': 'Share not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
