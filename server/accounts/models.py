from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """App-level roles (separate from Django ``is_staff`` / ``is_superuser``)."""

    is_viewer = models.BooleanField(
        default=False,
        help_text='Read-oriented access when enforced by API permissions.',
    )
    is_editor = models.BooleanField(
        default=False,
        help_text='Create/update access when enforced by API permissions.',
    )
    is_admin = models.BooleanField(
        default=False,
        help_text='Manage users and scheduler jobs via API (with superuser).',
    )

    phone_number = models.CharField(max_length=32, blank=True, null=True)
    country_code = models.CharField(max_length=8, blank=True, null=True)
