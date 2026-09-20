from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from .access import connection_access_role
from .models import DatabaseConnection, DatabaseConnectionShare
from .ssh_tunnel import normalize_fingerprint

User = get_user_model()


class DatabaseConnectionSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
    )
    ssh_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
    )
    ssh_private_key = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'base_template': 'textarea.html'},
    )
    ssh_private_key_passphrase = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
    )
    ssh_private_key_set = serializers.SerializerMethodField()
    ssh_password_set = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source='user.username', read_only=True)
    access_role = serializers.SerializerMethodField()

    class Meta:
        model = DatabaseConnection
        fields = [
            'id',
            'user',
            'owner_username',
            'access_role',
            'name',
            'engine',
            'host',
            'port',
            'database_name',
            'username',
            'password',
            'virtual_host',
            'connection_uri',
            'use_tls',
            'ssh_enabled',
            'ssh_host',
            'ssh_port',
            'ssh_username',
            'ssh_password',
            'ssh_password_set',
            'ssh_private_key',
            'ssh_private_key_set',
            'ssh_private_key_passphrase',
            'ssh_host_key_fingerprint',
            'extra_options',
            'created_at',
            'updated_at',
        ]
        read_only_fields = (
            'user',
            'owner_username',
            'access_role',
            'ssh_password_set',
            'ssh_private_key_set',
            'created_at',
            'updated_at',
        )

    def get_access_role(self, obj: DatabaseConnection) -> str | None:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        return connection_access_role(request.user, obj)

    def get_ssh_private_key_set(self, obj: DatabaseConnection) -> bool:
        return bool((obj.ssh_private_key or '').strip())

    def get_ssh_password_set(self, obj: DatabaseConnection) -> bool:
        return bool((obj.ssh_password or '').strip())

    def validate_name(self, value: str) -> str:
        name = (value or '').strip()
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return name
        qs = DatabaseConnection.objects.filter(user=request.user, name=name)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'You already have a connection with this name. Choose a different display name.'
            )
        return name

    def validate_ssh_host_key_fingerprint(self, value: str) -> str:
        return normalize_fingerprint(value)

    def validate(self, attrs):
        instance = self.instance
        ssh_enabled = attrs.get(
            'ssh_enabled',
            instance.ssh_enabled if instance is not None else False,
        )
        if not ssh_enabled:
            return attrs

        def merged_str(field: str) -> str:
            if field in attrs:
                val = attrs.get(field)
                return '' if val is None else str(val).strip()
            if instance is not None:
                return str(getattr(instance, field, None) or '').strip()
            return ''

        def secret_present(field: str) -> bool:
            if field in attrs:
                return bool((attrs.get(field) or '').strip())
            if instance is not None:
                return bool((getattr(instance, field, None) or '').strip())
            return False

        errors: dict[str, str] = {}
        if not merged_str('ssh_host'):
            errors['ssh_host'] = 'Required when SSH tunnel is enabled.'
        if not merged_str('ssh_username'):
            errors['ssh_username'] = 'Required when SSH tunnel is enabled.'
        if not merged_str('ssh_host_key_fingerprint'):
            errors['ssh_host_key_fingerprint'] = 'Required when SSH tunnel is enabled.'

        host = merged_str('host')
        uri = merged_str('connection_uri')
        if uri:
            errors['connection_uri'] = (
                'Cannot use a connection URI with SSH tunnel; use host/port '
                '(e.g. 127.0.0.1 as seen from the SSH server).'
            )
        if not host:
            errors['host'] = 'Database host is required with SSH tunnel (often 127.0.0.1).'

        if not secret_present('ssh_private_key') and not secret_present('ssh_password'):
            errors['ssh_private_key'] = 'Provide an SSH private key or SSH password.'

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        pwd = validated_data.pop('password', '')
        ssh_password = validated_data.pop('ssh_password', '')
        ssh_private_key = validated_data.pop('ssh_private_key', '')
        ssh_passphrase = validated_data.pop('ssh_private_key_passphrase', '')
        validated_data['user'] = self.context['request'].user
        try:
            return DatabaseConnection.objects.create(
                password=pwd,
                ssh_password=ssh_password,
                ssh_private_key=ssh_private_key,
                ssh_private_key_passphrase=ssh_passphrase,
                **validated_data,
            )
        except IntegrityError as e:
            raise serializers.ValidationError(
                {'name': 'You already have a connection with this name. Choose a different display name.'}
            ) from e

    def update(self, instance, validated_data):
        pwd = validated_data.pop('password', None)
        ssh_password = validated_data.pop('ssh_password', None)
        ssh_private_key = validated_data.pop('ssh_private_key', None)
        ssh_passphrase = validated_data.pop('ssh_private_key_passphrase', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if pwd is not None:
            instance.password = pwd
        if ssh_password is not None:
            instance.ssh_password = ssh_password
        if ssh_private_key is not None:
            instance.ssh_private_key = ssh_private_key
        if ssh_passphrase is not None:
            instance.ssh_private_key_passphrase = ssh_passphrase
        try:
            instance.save()
        except IntegrityError as e:
            raise serializers.ValidationError(
                {'name': 'You already have a connection with this name. Choose a different display name.'}
            ) from e
        return instance


class ConnectionShareReadSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = DatabaseConnectionShare
        fields = ['user', 'username', 'role']


class ConnectionShareWriteSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    role = serializers.ChoiceField(choices=DatabaseConnectionShare.Role.choices, default=DatabaseConnectionShare.Role.VIEWER)


class BackupRequestSerializer(serializers.Serializer):
    compress = serializers.BooleanField(required=False, default=False)
