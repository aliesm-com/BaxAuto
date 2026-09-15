from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import ViewerCannotMutate
from baxconf.alertlog import log_alert

from .models import StorageDestination
from .serializers import StorageDestinationSerializer


class StorageDestinationViewSet(viewsets.ModelViewSet):
    """CRUD for per-user storage targets (S3-compatible, SFTP, FTP)."""

    serializer_class = StorageDestinationSerializer
    permission_classes = [IsAuthenticated, ViewerCannotMutate]

    def get_queryset(self):
        return StorageDestination.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save()
        dest = serializer.instance
        log_alert(
            f'Storage destination “{dest.name}” created ({dest.kind}).',
            status='success',
            source='storage',
            storage_id=dest.pk,
        )

    def perform_update(self, serializer):
        serializer.save()
        dest = serializer.instance
        log_alert(
            f'Storage destination “{dest.name}” updated ({dest.kind}).',
            status='success',
            source='storage',
            storage_id=dest.pk,
        )

    def perform_destroy(self, instance):
        name, pk, kind = instance.name, instance.pk, instance.kind
        super().perform_destroy(instance)
        log_alert(
            f'Storage destination “{name}” deleted ({kind}).',
            status='success',
            source='storage',
            storage_id=pk,
        )
