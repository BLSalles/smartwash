#!/usr/bin/env bash
set -e

echo "[start] DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-smartwash.settings}"

# ---------------------------------------------------------------------------
# Render without shell access + shared Postgres:
# Some deployments end up with an inconsistent DB state:
#  - migrations marked as applied but tables missing  -> "relation does not exist"
#  - tables exist but migrations not aligned          -> "relation ... already exists"
#
# This script makes the service self-healing:
#  1) Try migrate with --fake-initial (safe when tables already exist)
#  2) Verify core table exists
#  3) If migrate fails OR core table missing, we RESET ONLY the 'lavagem' schema:
#       - drop tables named lavagem_* (does not touch SmartBarber agendamento_*)
#       - delete django_migrations rows where app='lavagem'
#       - run migrate again
#
# NOTE: Reset will delete data from the SmartWash app (lavagem_* tables).
# ---------------------------------------------------------------------------

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-smartwash.settings}"
export CHECK_TABLE="${CHECK_TABLE:-lavagem_tipolavagem}"

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

reset_lavagem_schema() {
  echo "[start] RESETTING schema for app 'lavagem' (dropping lavagem_* tables + clearing migration records)..."
  python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'smartwash.settings'))
import django
django.setup()
from django.db import connection, transaction

with connection.cursor() as c:
    # Drop all tables that start with 'lavagem_' in public schema
    c.execute("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename LIKE 'lavagem_%'
        ORDER BY tablename;
    """)
    tables = [r[0] for r in c.fetchall()]

    # Drop tables (CASCADE to remove FKs, indexes, constraints)
    for t in tables:
        c.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')

    # Clear migration records only for this app
    c.execute("DELETE FROM django_migrations WHERE app = %s;", ['lavagem'])

print(f"[reset] Dropped {len(tables)} table(s): {', '.join(tables) if tables else '(none)'}")
print("[reset] Cleared django_migrations for app 'lavagem'.")
PY
}

echo "[start] Running migrate (safe mode: --fake-initial)..."
set +e
python manage.py migrate --noinput --fake-initial
MIGRATE_STATUS=$?
set -e

if [ "$MIGRATE_STATUS" != "0" ]; then
  echo "[start] migrate failed (status=$MIGRATE_STATUS). Will reset lavagem schema and retry."
  reset_lavagem_schema
  python manage.py migrate --noinput
fi

# Ensure core table exists
if [ "$(table_exists)" = "0" ]; then
  echo "[start] Missing table public.${CHECK_TABLE}. Will reset lavagem schema and retry."
  reset_lavagem_schema
  python manage.py migrate --noinput
  if [ "$(table_exists)" = "0" ]; then
    echo "[start] ERROR: Table public.${CHECK_TABLE} still missing after reset."
    echo "[start] This usually means DATABASE_URL is pointing to a different database than the one your site is using."
    exit 1
  fi
fi

echo "[start] Seeding base data (idempotent)..."
python manage.py gerar_horarios || true
python manage.py init_admin || true

echo "[start] Starting gunicorn..."
exec gunicorn smartwash.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --threads 2 --timeout 120
