from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    """Subset exposed on login and ``GET /me/``."""

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_superuser',
            'is_viewer',
            'is_editor',
            'is_admin',
            'phone_number',
            'country_code',
        )
        read_only_fields = fields


class MeProfileUpdateSerializer(serializers.ModelSerializer):
    """Editable profile fields for ``PATCH /me/`` (not roles)."""

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'country_code')


class AdminUserSerializer(serializers.ModelSerializer):
    """Create/update users (admin API). Password optional on update."""

    password = serializers.CharField(write_only=True, required=False, min_length=8)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
            'is_superuser',
            'is_viewer',
            'is_editor',
            'is_admin',
            'phone_number',
            'country_code',
            'password',
        )
        read_only_fields = ('id', 'is_staff', 'is_superuser')

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'Required when creating a user.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        validate_password(password, user=user)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password is not None:
            validate_password(password, user=instance)
            instance.set_password(password)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        validate_password(value, user=self.context['request'].user)
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_superuser'] = bool(user.is_superuser)
        token['is_viewer'] = bool(user.is_viewer)
        token['is_editor'] = bool(user.is_editor)
        token['is_admin'] = bool(user.is_admin)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserPublicSerializer(self.user).data
        return data
