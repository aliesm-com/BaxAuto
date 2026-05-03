from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from db_connections.fields import EncryptedTextField


class StorageDestination(models.Model):
    """User-scoped remote storage targets (S3-compatible, SFTP, FTP)."""

    class Kind(models.TextChoices):
        S3 = 's3', 'S3 / compatible'
        SFTP = 'sftp', 'SFTP'
        FTP = 'ftp', 'FTP'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='storage_destinations',
    )
    name = models.CharField(max_length=255, help_text='Unique label per user.')
    kind = models.CharField(max_length=16, choices=Kind.choices)

    host = models.CharField(max_length=255, blank=True, default='', help_text='SFTP/FTP hostname.')
    port = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Defaults: SFTP 22, FTP 21 when left empty.',
    )

    username = models.CharField(max_length=255, blank=True, default='', help_text='S3 access key ID or SSH/FTP user.')
    secret = EncryptedTextField(
        blank=True,
        default='',
        help_text='S3 secret key or SFTP/FTP password (encrypted at rest).',
    )

    bucket = models.CharField(max_length=255, blank=True, default='', help_text='S3 bucket name.')
    region = models.CharField(max_length=64, blank=True, default='', help_text='Optional AWS region.')
    endpoint_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Custom S3 endpoint (e.g. MinIO). Leave blank for default AWS.',
    )

    remote_path = models.CharField(
        max_length=512,
        blank=True,
        default='',
        help_text='Remote directory prefix for SFTP/FTP uploads.',
    )

    ftp_passive = models.BooleanField(default=True)
    ftp_use_tls = models.BooleanField(default=False, help_text='FTP over TLS (FTPS).')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='storage_dest_unique_name_per_user'),
        ]

    def __str__(self) -> str:
        return f'{self.name} ({self.get_kind_display()})'

    def clean(self):
        super().clean()
        kind = self.kind
        bucket = (self.bucket or '').strip()
        host = (self.host or '').strip()
        user = (self.username or '').strip()

        if kind == self.Kind.S3:
            if not bucket:
                raise ValidationError({'bucket': 'Bucket is required for S3.'})
            if not user:
                raise ValidationError({'username': 'Access key ID is required for S3.'})
            endpoint = (self.endpoint_url or '').strip()
            if endpoint and not (endpoint.startswith('http://') or endpoint.startswith('https://')):
                raise ValidationError({'endpoint_url': 'Endpoint must start with http:// or https://'})
        elif kind == self.Kind.SFTP:
            if not host:
                raise ValidationError({'host': 'Host is required for SFTP.'})
            if not user:
                raise ValidationError({'username': 'Username is required for SFTP.'})
        elif kind == self.Kind.FTP:
            if not host:
                raise ValidationError({'host': 'Host is required for FTP.'})
            if not user:
                raise ValidationError({'username': 'Username is required for FTP.'})
