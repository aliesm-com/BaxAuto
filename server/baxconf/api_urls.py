"""Single DRF router for ``/api/*`` (avoids registering format suffix converters twice)."""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from backups.views import BackupRecordViewSet, RestoreRecordViewSet
from db_connections.views import DatabaseConnectionViewSet
from overview.views import OverviewView
from scheduler.views import ScheduledJobViewSet
from storage.views import StorageDestinationViewSet

router = SimpleRouter()
router.register('db-connections', DatabaseConnectionViewSet, basename='db-connection')
router.register('backup-records', BackupRecordViewSet, basename='backup-record')
router.register('restore-records', RestoreRecordViewSet, basename='restore-record')
router.register('scheduled-jobs', ScheduledJobViewSet, basename='scheduled-job')
router.register('storage-destinations', StorageDestinationViewSet, basename='storage-destination')

urlpatterns = [
    path('overview/', OverviewView.as_view(), name='overview'),
    path('', include(router.urls)),
]
