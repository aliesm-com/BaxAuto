from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import ViewerCannotMutate

from .models import StorageDestination
from .serializers import StorageDestinationSerializer


class StorageDestinationViewSet(viewsets.ModelViewSet):
    """CRUD for per-user storage targets (S3-compatible, SFTP, FTP)."""

    serializer_class = StorageDestinationSerializer
    permission_classes = [IsAuthenticated, ViewerCannotMutate]

    def get_queryset(self):
        return StorageDestination.objects.filter(user=self.request.user)
