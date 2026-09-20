from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .fields import EncryptedTextField


class DatabaseConnection(models.Model):
    """Saved connection settings per user; supports several engines with shared + optional fields."""

    class Engine(models.TextChoices):
        MYSQL = 'mysql', 'MySQL'
        MARIADB = 'mariadb', 'MariaDB'
        POSTGRESQL = 'postgresql', 'PostgreSQL'
        REDIS = 'redis', 'Redis'
        RABBITMQ = 'rabbitmq', 'RabbitMQ'
        CLICKHOUSE = 'clickhouse', 'ClickHouse'
        SQLSERVER = 'sqlserver', 'Microsoft SQL Server'
        MONGODB = 'mongodb', 'MongoDB'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='database_connections',
    )
    name = models.CharField(
        max_length=255,
        help_text='Label shown in your list (unique per user).',
    )
    engine = models.CharField(max_length=32, choices=Engine.choices)

    host = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            'Database host. With SSH tunnel enabled, this is the address as seen from '
            'the SSH server (often 127.0.0.1).'
        ),
    )
    port = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Leave empty to use the default port for this engine on the client.',
    )

    database_name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Database/schema/bucket name where applicable. For Redis: logical DB index (e.g. 0).',
    )

    username = models.CharField(max_length=255, blank=True)
    password = EncryptedTextField(
        blank=True,
        help_text='Stored encrypted at rest. Prefer setting DB_CREDENTIALS_FERNET_KEY in production.',
    )

    virtual_host = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='RabbitMQ vhost (often /).',
    )

    connection_uri = models.TextField(
        blank=True,
        help_text='Optional full connection URI (common for MongoDB; can be extended for others).',
    )

    use_tls = models.BooleanField(
        default=False,
        help_text='TLS/SSL for the connection where the driver supports it.',
    )

    ssh_enabled = models.BooleanField(
        default=False,
        help_text='Open an SSH local port-forward before backup/test/restore.',
    )
    ssh_host = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='SSH bastion / server hostname (public address).',
    )
    ssh_port = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=22,
        help_text='SSH port (default 22).',
    )
    ssh_username = models.CharField(max_length=255, blank=True, default='')
    ssh_password = EncryptedTextField(
        blank=True,
        default='',
        help_text='SSH password (optional if a private key is set). Encrypted at rest.',
    )
    ssh_private_key = EncryptedTextField(
        blank=True,
        default='',
        help_text='PEM private key for SSH (preferred). Encrypted at rest.',
    )
    ssh_private_key_passphrase = EncryptedTextField(
        blank=True,
        default='',
        help_text='Passphrase for the SSH private key, if any. Encrypted at rest.',
    )
    ssh_host_key_fingerprint = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=(
            'Required when SSH is enabled. SHA256 fingerprint of the server host key '
            '(from: ssh-keyscan HOST | ssh-keygen -lf -).'
        ),
    )

    extra_options = models.JSONField(
        default=dict,
        blank=True,
        help_text='Engine-specific options (e.g. SQL Server ODBC driver name, Mongo authSource).',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='db_connections_unique_name_per_user',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.name} ({self.get_engine_display()})'

    def save(self, *args, **kwargs):
        if self.engine == self.Engine.RABBITMQ and self.virtual_host == '':
            self.virtual_host = '/'
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        uri = (self.connection_uri or '').strip()
        host = (self.host or '').strip()

        if self.ssh_enabled:
            errors: dict[str, str] = {}
            if not (self.ssh_host or '').strip():
                errors['ssh_host'] = 'SSH host is required when the tunnel is enabled.'
            if not (self.ssh_username or '').strip():
                errors['ssh_username'] = 'SSH username is required when the tunnel is enabled.'
            if not (self.ssh_host_key_fingerprint or '').strip():
                errors['ssh_host_key_fingerprint'] = (
                    'Host key fingerprint is required when the tunnel is enabled.'
                )
            has_key = bool((self.ssh_private_key or '').strip())
            has_pwd = bool((self.ssh_password or '').strip())
            if not has_key and not has_pwd:
                errors['ssh_private_key'] = 'Provide an SSH private key or SSH password.'
            if uri:
                errors['connection_uri'] = (
                    'Connection URI cannot be used with an SSH tunnel; use host/port '
                    '(as seen from the SSH server, e.g. 127.0.0.1).'
                )
            if not host:
                errors['host'] = (
                    'Database host is required with SSH tunnel '
                    '(usually 127.0.0.1 on the remote server).'
                )
            if errors:
                raise ValidationError(errors)

        if self.engine == self.Engine.MONGODB:
            if not uri and not host:
                raise ValidationError(
                    {'connection_uri': 'Provide a MongoDB URI or a host.'}
                )
        elif not host:
            raise ValidationError({'host': 'Host is required for this engine.'})


class DatabaseConnectionShare(models.Model):
    """Grant another user read-only or edit access to someone else's saved connection."""

    class Role(models.TextChoices):
        VIEWER = 'viewer', 'Viewer'
        EDITOR = 'editor', 'Editor'

    connection = models.ForeignKey(
        DatabaseConnection,
        on_delete=models.CASCADE,
        related_name='shares',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='database_connection_shares',
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.VIEWER)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('connection', 'user'),
                name='db_connections_share_unique_member',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.connection_id} → {self.user_id} ({self.role})'
