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

    host = models.CharField(max_length=255, blank=True)
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

        if self.engine == self.Engine.MONGODB:
            if not uri and not host:
                raise ValidationError(
                    {'connection_uri': 'Provide a MongoDB URI or a host.'}
                )
        elif not host:
            raise ValidationError({'host': 'Host is required for this engine.'})
