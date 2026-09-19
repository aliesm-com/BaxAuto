#!/bin/sh
set -e

echo "BaxAuto API: waiting for database..."
sleep 3

echo "BaxAuto API: running migrations..."
python manage.py migrate --noinput

echo "BaxAuto API: collecting static files..."
python manage.py collectstatic --noinput --clear

echo "BaxAuto API: starting Gunicorn..."
exec gunicorn baxconf.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --threads 2 \
    --timeout 1800 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
