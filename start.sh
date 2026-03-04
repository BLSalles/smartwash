#!/usr/bin/env bash
set -e

echo "[start] DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-smartwash.settings}"

echo "[start] Ensuring DB schema..."
python ensure_db.py

echo "[start] Running migrate..."
python manage.py migrate --noinput

echo "[start] Seeding base data (idempotent)..."
python manage.py gerar_horarios
python manage.py init_admin

echo "[start] Starting gunicorn..."
exec gunicorn smartwash.wsgi:application --bind 0.0.0.0:${PORT:-8000}
