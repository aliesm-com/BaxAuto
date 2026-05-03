from django.apps import AppConfig


class DbConnectionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'db_connections'
    verbose_name = 'Database connections'
