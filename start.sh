#!/usr/bin/env bash
set -e

echo "[start] DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-smartwash.settings}"

# ---------------------------------------------------------------------------
# Render + shared Postgres safety:
# If the database has an inconsistent migration history (e.g. tables missing
# but migrations marked as applied), Django may say "No migrations to apply"
# and the app will crash with "relation does not exist".
#
# Since you don't have shell access on Render, we auto-heal on boot:
#   1) run migrate normally with --fake-initial
#   2) verify that core tables exist
#   3) if missing, reset ONLY the app migration records (FAKE to zero)
#      and re-run migrate with --fake-initial to (re)create missing tables.
# ---------------------------------------------------------------------------

table_exists() {
  python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'smartwash.settings'))
import django
django.setup()
from django.db import connection

table = os.getenv('CHECK_TABLE', 'lavagem_tipolavagem')
with connection.cursor() as cursor:
    cursor.execute("SELECT to_regclass(%s)", [f"public.{table}"])
    exists = cursor.fetchone()[0]
print('1' if exists else '0')
PY
}

echo "[start] Running migrate (safe for shared DB)..."
python manage.py migrate --noinput --fake-initial

# Verify expected tables exist; if not, heal inconsistent migration history.
export CHECK_TABLE=lavagem_tipolavagem
if [ "$(table_exists)" = "0" ]; then
  echo "[start] Detected missing table public.${CHECK_TABLE}. Healing migration history for app 'lavagem'..."
  # Reset only the app migration records (does NOT drop tables)
  python manage.py migrate lavagem zero --fake --noinput || true
  # Re-apply, creating missing tables and faking those already present
  python manage.py migrate lavagem --noinput --fake-initial

  if [ "$(table_exists)" = "0" ]; then
    echo "[start] ERROR: Table public.${CHECK_TABLE} still missing after healing."
    echo "[start] Check that DATABASE_URL points to the correct Postgres instance for this service."
    exit 1
  fi
fi

echo "[start] Seeding base data (idempotent)..."
python manage.py gerar_horarios || true
python manage.py init_admin || true

echo "[start] Starting gunicorn..."
exec gunicorn smartwash.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --timeout 120
