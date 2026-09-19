#!/bin/sh
set -e

echo "BaxAuto API: waiting for database..."
sleep 3

echo "BaxAuto API: running migrations..."
python manage.py migrate --noinput

echo "BaxAuto API: collecting static files..."
python manage.py collectstatic --noinput --clear || true

echo "BaxAuto API: starting Django runserver..."
exec python manage.py runserver 0.0.0.0:8000
