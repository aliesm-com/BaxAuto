from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import ViewerCannotMutate

from .models import StorageDestination
from .probe import StorageProbeError, test_destination
from .serializers import StorageDestinationSerializer


class StorageDestinationViewSet(viewsets.ModelViewSet):
    """CRUD for per-user storage targets (S3-compatible, SFTP, FTP)."""

    serializer_class = StorageDestinationSerializer
    permission_classes = [IsAuthenticated, ViewerCannotMutate]

    def get_queryset(self):
        return StorageDestination.objects.filter(user=self.request.user)

    @extend_schema(request=None, responses={200: dict})
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        dest = self.get_object()
        try:
            test_destination(dest)
        except StorageProbeError as e:
            return Response({'ok': False, 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'ok': False, 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True})
