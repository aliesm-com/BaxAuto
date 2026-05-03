from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import ScheduledJobAccessPermission

from .models import ScheduledJob
from .serializers import ScheduledJobSerializer


class ScheduledJobViewSet(viewsets.ModelViewSet):
    """CRUD for :class:`~scheduler.models.ScheduledJob`; reads for any user, writes for app admins."""

    queryset = ScheduledJob.objects.all()
    serializer_class = ScheduledJobSerializer
    permission_classes = [IsAuthenticated, ScheduledJobAccessPermission]
