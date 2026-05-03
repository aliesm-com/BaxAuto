#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

try:
    from django.core.management import execute_from_command_line
except ImportError as exc:
    _django_exc = exc
else:
    _django_exc = None


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baxconf.settings')
    if _django_exc is not None:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            'available on your PYTHONPATH environment variable? Did you '
            'forget to activate a virtual environment?'
        ) from _django_exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
