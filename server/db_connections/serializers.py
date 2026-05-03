from rest_framework import serializers

from .models import DatabaseConnection


class DatabaseConnectionSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = DatabaseConnection
        fields = [
            'id',
            'user',
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
        read_only_fields = ('user', 'created_at', 'updated_at')

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
