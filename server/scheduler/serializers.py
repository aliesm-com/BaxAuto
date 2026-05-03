from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import ScheduledJob

User = get_user_model()

_SCHEDULE_ATTRS = frozenset({'schedule_kind', 'interval_seconds', 'crontab_expression'})


class ScheduledJobSerializer(serializers.ModelSerializer):
    run_as = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = ScheduledJob
        fields = (
            'id',
            'name',
            'enabled',
            'schedule_kind',
            'interval_seconds',
            'crontab_expression',
            'task_key',
            'payload',
            'run_as',
            'last_run',
            'next_run',
            'last_status',
            'last_error',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'last_run',
            'last_status',
            'last_error',
            'created_at',
            'updated_at',
        )

    def create(self, validated_data):
        job = ScheduledJob(**validated_data)
        job.full_clean()
        job.save()
        return job

    def update(self, instance, validated_data):
        touched_schedule = bool(_SCHEDULE_ATTRS & validated_data.keys())
        before = {k: getattr(instance, k) for k in _SCHEDULE_ATTRS}
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        after = {k: getattr(instance, k) for k in _SCHEDULE_ATTRS}
        if touched_schedule and before != after:
            instance.next_run = instance.compute_next_run_after(timezone.now())
        instance.save()
        return instance
