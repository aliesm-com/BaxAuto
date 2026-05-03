from __future__ import annotations

from rest_framework import serializers

from .models import BackupRecord, RestoreRecord


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

    class Meta:
        model = BackupRecord
        fields = (
            'id',
            'connection',
            'connection_name',
            'initiated_by',
            'trigger',
            'status',
            'engine',
            'relative_media_path',
            'download_filename',
            'size_bytes',
            'error_message',
            'created_at',
            'finished_at',
            'restore_logs',
        )
        read_only_fields = fields


class RestoreRequestSerializer(serializers.Serializer):
    """Optional kwargs forwarded to engine-specific ``restore`` implementations."""

    flush_before_restore = serializers.BooleanField(required=False)
    apply_schema = serializers.BooleanField(required=False)
    truncate_first = serializers.BooleanField(required=False)
    drop = serializers.BooleanField(required=False)
