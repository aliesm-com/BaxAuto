"""Aggregated dashboard metrics for the authenticated user."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backups.models import BackupRecord
from backups.services import backup_artifact_bytes_on_disk_or_record, total_success_backup_storage_bytes
from db_connections.access import connections_visible_q
from db_connections.models import DatabaseConnection
from scheduler.models import ScheduledJob


def _day_bounds(d):
    """Start (inclusive) and end (exclusive) aware datetimes for calendar date ``d`` in the active timezone."""
    start = timezone.make_aware(datetime.combine(d, datetime.min.time()))
    return start, start + timedelta(days=1)


def _serialize_backup_row(b: BackupRecord) -> dict:
    eff_bytes = backup_artifact_bytes_on_disk_or_record(
        relative_media_path=b.relative_media_path,
        size_bytes=b.size_bytes,
    )
    return {
        'id': b.id,
        'connection': b.connection_id,
        'connection_name': b.connection.name,
        'engine': b.engine,
        'created_at': b.created_at.isoformat(),
        'finished_at': b.finished_at.isoformat() if b.finished_at else None,
        'size_bytes': eff_bytes,
    }


class OverviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        user = request.user
        today = timezone.localdate()

        conn_qs = DatabaseConnection.objects.filter(connections_visible_q(user)).distinct()
        backup_qs = (
            BackupRecord.objects.filter(
                Q(connection__user=user) | Q(connection__shares__user=user),
            )
            .distinct()
            .select_related('connection')
        )

        agg = backup_qs.aggregate(
            total=Count('id'),
            success_count=Count('id', filter=Q(status=BackupRecord.Status.SUCCESS)),
            failed_count=Count('id', filter=Q(status=BackupRecord.Status.FAILED)),
            in_progress_count=Count('id', filter=Q(status=BackupRecord.Status.IN_PROGRESS)),
        )

        used_bytes = total_success_backup_storage_bytes(backup_qs)

        quota = int(getattr(settings, 'OVERVIEW_STORAGE_QUOTA_BYTES', 1024**4))
        storage_pct = min(100, round((used_bytes / quota) * 100)) if quota > 0 else 0

        last_success = (
            backup_qs.filter(status=BackupRecord.Status.SUCCESS).order_by('-created_at').select_related('connection').first()
        )

        recent_success = list(
            backup_qs.filter(status=BackupRecord.Status.SUCCESS)
            .order_by('-created_at')[:5]
            .select_related('connection'),
        )

        activity_week: list[dict] = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            start, end = _day_bounds(d)
            cnt = backup_qs.filter(
                status=BackupRecord.Status.SUCCESS,
                created_at__gte=start,
                created_at__lt=end,
            ).count()
            activity_week.append(
                {
                    'date': d.isoformat(),
                    'weekday': d.strftime('%a'),
                    'success_count': cnt,
                },
            )

        prev_week_counts: list[int] = []
        for i in range(13, 6, -1):
            d = today - timedelta(days=i)
            start, end = _day_bounds(d)
            prev_week_counts.append(
                backup_qs.filter(
                    status=BackupRecord.Status.SUCCESS,
                    created_at__gte=start,
                    created_at__lt=end,
                ).count(),
            )

        this_week_total = sum(x['success_count'] for x in activity_week)
        prev_week_total = sum(prev_week_counts)

        if prev_week_total > 0:
            trend_percent = round((this_week_total - prev_week_total) / prev_week_total * 100)
            trend_new = False
        elif this_week_total > 0:
            trend_percent = None
            trend_new = True
        else:
            trend_percent = None
            trend_new = False

        sparkline = [x['success_count'] for x in activity_week]

        is_admin = bool(user.is_superuser or getattr(user, 'is_admin', False))
        scheduler_payload: dict
        if is_admin:
            sj = ScheduledJob.objects.all()
            enabled = sj.filter(enabled=True).count()
            failed = sj.filter(enabled=True, last_status=ScheduledJob.LastStatus.FAILED).count()
            scheduler_payload = {
                'visible': True,
                'enabled_jobs': enabled,
                'failed_jobs': failed,
                'status': 'issues' if failed else 'ok',
            }
        else:
            scheduler_payload = {'visible': False, 'enabled_jobs': 0, 'failed_jobs': 0, 'status': 'unknown'}

        payload = {
            'generated_at': timezone.now().isoformat(),
            'connections': {'count': conn_qs.count()},
            'backups': {
                'total': agg['total'] or 0,
                'success': agg['success_count'] or 0,
                'failed': agg['failed_count'] or 0,
                'in_progress': agg['in_progress_count'] or 0,
            },
            'storage': {
                'used_bytes': used_bytes,
                'quota_bytes': quota,
                'quota_percent': storage_pct,
            },
            'last_success': _serialize_backup_row(last_success) if last_success else None,
            'recent_success': [_serialize_backup_row(b) for b in recent_success],
            'activity_week': activity_week,
            'trend_percent': trend_percent,
            'trend_new': trend_new,
            'sparkline': sparkline,
            'health': {
                'scheduler': scheduler_payload,
                'workers_configured': settings.OVERVIEW_WORKERS_COUNT,
            },
        }
        return Response(payload)
