from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAppAdmin

from .models import ScheduledJob
from .serializers import ScheduledJobSerializer


class ScheduledJobViewSet(viewsets.ModelViewSet):
    """CRUD for :class:`~scheduler.models.ScheduledJob` (app admins only)."""

    queryset = ScheduledJob.objects.all()
    serializer_class = ScheduledJobSerializer
    permission_classes = [IsAuthenticated, IsAppAdmin]
