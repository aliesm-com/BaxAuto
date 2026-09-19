from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers

from .models import ScheduledJob

User = get_user_model()

_SCHEDULE_ATTRS = frozenset({'schedule_kind', 'interval_seconds', 'crontab_expression'})


def _django_validation_to_drf(exc: DjangoValidationError) -> serializers.ValidationError:
    if hasattr(exc, 'message_dict') and exc.message_dict:
        return serializers.ValidationError(exc.message_dict)
    if hasattr(exc, 'messages'):
        return serializers.ValidationError(list(exc.messages))
    return serializers.ValidationError(str(exc))


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
        try:
            job.full_clean()
            job.save()
        except DjangoValidationError as e:
            raise _django_validation_to_drf(e) from e
        except IntegrityError as e:
            if 'name' in str(e).lower() or 'unique' in str(e).lower():
                raise serializers.ValidationError(
                    {'name': 'A schedule with this name already exists.'}
                ) from e
            raise
        return job

    def update(self, instance, validated_data):
        touched_schedule = bool(_SCHEDULE_ATTRS & validated_data.keys())
        before = {k: getattr(instance, k) for k in _SCHEDULE_ATTRS}
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        try:
            instance.full_clean()
            after = {k: getattr(instance, k) for k in _SCHEDULE_ATTRS}
            if touched_schedule and before != after:
                instance.next_run = instance.compute_next_run_after(timezone.now())
            instance.save()
        except DjangoValidationError as e:
            raise _django_validation_to_drf(e) from e
        except IntegrityError as e:
            if 'name' in str(e).lower() or 'unique' in str(e).lower():
                raise serializers.ValidationError(
                    {'name': 'A schedule with this name already exists.'}
                ) from e
            raise
        return instance
