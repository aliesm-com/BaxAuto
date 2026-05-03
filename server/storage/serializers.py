from rest_framework import serializers

from .models import StorageDestination


class StorageDestinationSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = StorageDestination
        fields = [
            'id',
            'user',
            'name',
            'kind',
            'host',
            'port',
            'username',
            'secret',
            'bucket',
            'region',
            'endpoint_url',
            'remote_path',
            'ftp_passive',
            'ftp_use_tls',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('user', 'created_at', 'updated_at')

    def validate(self, attrs):
        instance = self.instance
        kind = attrs.get('kind', getattr(instance, 'kind', None) if instance else None)

        creating = instance is None
        if creating and kind:
            secret_val = (attrs.get('secret') or '').strip()
            if kind == StorageDestination.Kind.S3 and not secret_val:
                raise serializers.ValidationError({'secret': 'Secret access key is required for S3.'})
            if kind in (StorageDestination.Kind.SFTP, StorageDestination.Kind.FTP) and not secret_val:
                raise serializers.ValidationError({'secret': 'Password is required for SFTP/FTP.'})

        return attrs

    def create(self, validated_data):
        pwd = validated_data.pop('secret', '') or ''
        validated_data['user'] = self.context['request'].user
        instance = StorageDestination(secret=pwd, **validated_data)
        instance.full_clean()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        pwd = validated_data.pop('secret', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if pwd is not None and pwd.strip():
            instance.secret = pwd
        instance.full_clean()
        instance.save()
        return instance
