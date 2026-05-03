"""Single DRF router for ``/api/*`` (avoids registering format suffix converters twice)."""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from backups.views import BackupRecordViewSet, RestoreRecordViewSet
from db_connections.views import DatabaseConnectionViewSet
from scheduler.views import ScheduledJobViewSet

router = SimpleRouter()
router.register('db-connections', DatabaseConnectionViewSet, basename='db-connection')
router.register('backup-records', BackupRecordViewSet, basename='backup-record')
router.register('restore-records', RestoreRecordViewSet, basename='restore-record')
router.register('scheduled-jobs', ScheduledJobViewSet, basename='scheduled-job')

urlpatterns = [
    path('', include(router.urls)),
]
