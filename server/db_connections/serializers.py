from django.contrib.auth import get_user_model
from rest_framework import serializers

from .access import connection_access_role
from .models import DatabaseConnection, DatabaseConnectionShare

User = get_user_model()


class DatabaseConnectionSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
    )
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
            'extra_options',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('user', 'owner_username', 'access_role', 'created_at', 'updated_at')

    def get_access_role(self, obj: DatabaseConnection) -> str | None:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        return connection_access_role(request.user, obj)


class ConnectionShareReadSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = DatabaseConnectionShare
        fields = ['user', 'username', 'role']


class ConnectionShareWriteSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))
    role = serializers.ChoiceField(choices=DatabaseConnectionShare.Role.choices, default=DatabaseConnectionShare.Role.VIEWER)

    def create(self, validated_data):
        pwd = validated_data.pop('password', '')
        validated_data['user'] = self.context['request'].user
        return DatabaseConnection.objects.create(password=pwd, **validated_data)

    def update(self, instance, validated_data):
        pwd = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if pwd is not None:
            instance.password = pwd
        instance.save()
        return instance
