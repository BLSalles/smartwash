#!/usr/bin/env bash
set -e

echo "[start] DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-smartwash.settings}"

echo "[start] Running migrate (safe for shared DB)..."
python manage.py migrate --noinput --fake-initial

echo "[start] Seeding base data (idempotent)..."
python manage.py gerar_horarios || true
python manage.py init_admin || true

echo "[start] Starting gunicorn..."
exec gunicorn smartwash.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --timeout 120
