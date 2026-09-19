from __future__ import annotations

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from baxconf.alertlog import log_alert, log_http_alert

from .permissions import IsAppAdmin, IsSuperuser
from .serializers import (
    AdminUserSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    MeProfileUpdateSerializer,
    UserPublicSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            username = request.data.get('username') or 'unknown'
            log_alert(
                f'User “{username}” signed in.',
                status='success',
                source='login',
            )
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserPublicSerializer})
    def get(self, request):
        return Response(UserPublicSerializer(request.user).data)

    @extend_schema(request=MeProfileUpdateSerializer, responses={200: UserPublicSerializer})
    def patch(self, request):
        ser = MeProfileUpdateSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        log_alert(
            f'Profile updated for “{request.user.username}”.',
            status='success',
            source='profile',
            user_id=request.user.pk,
        )
        return Response(UserPublicSerializer(request.user).data)


class LoginAsView(APIView):
    """Issue JWTs for another user (superuser only). Adds ``imp`` claim for auditing."""

    permission_classes = [IsAuthenticated, IsSuperuser]

    @extend_schema(
        request={'application/json': {'type': 'object', 'properties': {'user_id': {'type': 'integer'}}}},
        responses={200: dict},
    )
    def post(self, request):
        raw_id = request.data.get('user_id')
        try:
            uid = int(raw_id)
        except (TypeError, ValueError):
            log_http_alert(
                'user_id is required and must be an integer.',
                http_status=status.HTTP_400_BAD_REQUEST,
                source='login_as',
            )
            return Response({'detail': 'user_id is required and must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
        target = get_object_or_404(User.objects.filter(is_active=True), pk=uid)
        if target.pk == request.user.pk:
            log_http_alert(
                'Already authenticated as this user.',
                http_status=status.HTTP_400_BAD_REQUEST,
                source='login_as',
                user_id=uid,
            )
            return Response({'detail': 'Already authenticated as this user.'}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(target)
        refresh['imp'] = request.user.pk
        access = refresh.access_token
        access['imp'] = request.user.pk

        log_alert(
            f'User “{request.user.username}” signed in as “{target.username}”.',
            status='success',
            source='login_as',
            user_id=target.pk,
            impersonator_id=request.user.pk,
        )
        return Response(
            {
                'access': str(access),
                'refresh': str(refresh),
                'user': UserPublicSerializer(target).data,
                'impersonator_id': request.user.pk,
                'impersonator_username': request.user.username,
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses={204: None})
    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        if not request.user.check_password(ser.validated_data['old_password']):
            log_http_alert(
                'Current password is incorrect.',
                http_status=status.HTTP_400_BAD_REQUEST,
                source='change_password',
                user_id=request.user.pk,
            )
            return Response(
                {'old_password': ['Current password is incorrect.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(ser.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        log_alert(
            f'Password changed for “{request.user.username}”.',
            status='success',
            source='change_password',
            user_id=request.user.pk,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserViewSet(viewsets.ModelViewSet):
    """List/create/update/delete users (superuser or ``is_admin``)."""

    queryset = User.objects.all().order_by('username')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAppAdmin]

    def perform_create(self, serializer):
        serializer.save()
        user = serializer.instance
        log_alert(
            f'User “{user.username}” created.',
            status='success',
            source='user',
            user_id=user.pk,
        )

    def perform_destroy(self, instance):
        if instance.is_superuser:
            raise PermissionDenied('Superuser accounts cannot be deleted from this API.')
        username, pk = instance.username, instance.pk
        super().perform_destroy(instance)
        log_alert(
            f'User “{username}” deleted.',
            status='success',
            source='user',
            user_id=pk,
        )

    def perform_update(self, serializer):
        if serializer.instance.is_superuser:
            raise PermissionDenied('Superuser accounts cannot be modified from this API.')
        super().perform_update(serializer)
        user = serializer.instance
        log_alert(
            f'User “{user.username}” updated.',
            status='success',
            source='user',
            user_id=user.pk,
        )
