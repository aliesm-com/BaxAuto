from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import ScheduledJobAccessPermission
from baxconf.alertlog import log_alert

from .models import ScheduledJob
from .serializers import ScheduledJobSerializer


class ScheduledJobViewSet(viewsets.ModelViewSet):
    """CRUD for :class:`~scheduler.models.ScheduledJob`; reads for any user, writes for app admins."""

    queryset = ScheduledJob.objects.all()
    serializer_class = ScheduledJobSerializer
    permission_classes = [IsAuthenticated, ScheduledJobAccessPermission]

    def perform_create(self, serializer):
        serializer.save()
        job = serializer.instance
        log_alert(
            f'Schedule “{job.name}” created ({job.task_key}).',
            status='success',
            source='schedule',
            job_id=job.pk,
            task_key=job.task_key,
        )

    def perform_update(self, serializer):
        serializer.save()
        job = serializer.instance
        log_alert(
            f'Schedule “{job.name}” updated ({job.task_key}).',
            status='success',
            source='schedule',
            job_id=job.pk,
            task_key=job.task_key,
        )

    def perform_destroy(self, instance):
        name, pk, task_key = instance.name, instance.pk, instance.task_key
        super().perform_destroy(instance)
        log_alert(
            f'Schedule “{name}” deleted ({task_key}).',
            status='success',
            source='schedule',
            job_id=pk,
            task_key=task_key,
        )
