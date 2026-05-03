from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dbs.base import BackupRestoreError

from .models import DatabaseConnection
from .serializers import DatabaseConnectionSerializer
from .services import perform_backup, test_saved_connection


class DatabaseConnectionViewSet(viewsets.ModelViewSet):
    """Saved DB targets for this user: CRUD, test connectivity, download logical backup."""

    serializer_class = DatabaseConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DatabaseConnection.objects.filter(user=self.request.user)

    @extend_schema(request=None, responses={200: dict})
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        conn = self.get_object()
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
        try:
            path, filename = perform_backup(conn)
        except BackupRestoreError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return FileResponse(path.open('rb'), as_attachment=True, filename=filename)
