from __future__ import annotations

from rest_framework import serializers

from .models import AlertEvent, AppSettings, BackupRecord, RestoreRecord
from .services import local_backup_available


class RestoreRecordSerializer(serializers.ModelSerializer):
    initiated_by_username = serializers.CharField(
        source='initiated_by.username',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = RestoreRecord
        fields = (
            'id',
            'backup',
            'connection',
            'initiated_by',
            'initiated_by_username',
            'status',
            'engine',
            'options',
            'error_message',
            'created_at',
            'finished_at',
        )
        read_only_fields = fields


class BackupRecordSerializer(serializers.ModelSerializer):
    connection_name = serializers.CharField(source='connection.name', read_only=True)
    restore_logs = RestoreRecordSerializer(many=True, read_only=True)
    local_available = serializers.SerializerMethodField()

    class Meta:
        model = BackupRecord
        fields = (
            'id',
            'connection',
            'connection_name',
            'initiated_by',
            'trigger',
            'scheduled_job',
            'status',
            'engine',
            'relative_media_path',
            'download_filename',
            'size_bytes',
            'compressed',
            'storage_uploads',
            'local_available',
            'error_message',
            'created_at',
            'finished_at',
            'restore_logs',
        )
        read_only_fields = fields

    def get_local_available(self, obj: BackupRecord) -> bool:
        return local_backup_available(obj)


class RestoreRequestSerializer(serializers.Serializer):
    """Optional kwargs forwarded to engine-specific ``restore`` implementations."""

    flush_before_restore = serializers.BooleanField(required=False)
    apply_schema = serializers.BooleanField(required=False)
    truncate_first = serializers.BooleanField(required=False)
    drop = serializers.BooleanField(required=False)
    storage_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='Download the artifact from this storage destination before restore. Omit for local MEDIA.',
    )


class AlertEventSerializer(serializers.ModelSerializer):
    webhook_status = serializers.SerializerMethodField()

    class Meta:
        model = AlertEvent
        fields = (
            'id',
            'status',
            'webhook_status',
            'source',
            'error',
            'description',
            'created_at',
        )
        read_only_fields = fields

    def get_webhook_status(self, obj: AlertEvent) -> str:
        return obj.webhook_status


class AppSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppSettings
        fields = ('keep_local_backups', 'updated_at')
        read_only_fields = ('updated_at',)
