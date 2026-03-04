#!/usr/bin/env bash
set -e

echo "[start] DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-smartwash.settings}"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-smartwash.settings}"
export CHECK_TABLE="${CHECK_TABLE:-lavagem_tipolavagem}"

db_state() {
  python - <<'PY'
import os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'smartwash.settings'))
import django
django.setup()
from django.db import connection
check = os.getenv('CHECK_TABLE', 'lavagem_tipolavagem')
with connection.cursor() as c:
    c.execute("SELECT to_regclass(%s)", [f"public.{check}"])
    has_check = c.fetchone()[0] is not None
    c.execute("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname='public' AND tablename LIKE 'lavagem_%'
        ORDER BY tablename
    """)
    tables = [r[0] for r in c.fetchall()]
print(json.dumps({"has_check": has_check, "count": len(tables), "tables": tables}))
PY
}

reset_lavagem_schema() {
  echo "[start] RESETTING schema for app 'lavagem' (dropping lavagem_* tables + clearing migration records)..."
  python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'smartwash.settings'))
import django
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname='public' AND tablename LIKE 'lavagem_%'
        ORDER BY tablename
    """)
    tables = [r[0] for r in c.fetchall()]
    for t in tables:
        c.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
    c.execute("DELETE FROM django_migrations WHERE app=%s;", ['lavagem'])
print(f"[reset] Dropped {len(tables)} table(s): {', '.join(tables) if tables else '(none)'}")
print("[reset] Cleared django_migrations for app 'lavagem'.")
PY
}

echo "[start] Inspecting DB schema for app 'lavagem'..."
STATE_JSON="$(db_state)"
echo "[start] DB state: ${STATE_JSON}"

export STATE_JSON
PARTIAL_BROKEN=$(python - <<'PY'
import os, json
s=json.loads(os.environ.get("STATE_JSON","{}") or "{}")
print("1" if (s.get("count",0)>0 and not s.get("has_check",False)) else "0")
PY
)

if [ "$PARTIAL_BROKEN" = "1" ]; then
  echo "[start] Detected partial lavagem schema (some tables exist but ${CHECK_TABLE} is missing). Resetting before migrate..."
  reset_lavagem_schema
fi

echo "[start] Running migrate (safe mode: --fake-initial)..."
set +e
python manage.py migrate --noinput --fake-initial
MIGRATE_STATUS=$?
set -e

if [ "$MIGRATE_STATUS" != "0" ]; then
  echo "[start] migrate failed (status=$MIGRATE_STATUS). Will reset lavagem schema and retry..."
  reset_lavagem_schema
  python manage.py migrate --noinput
fi

echo "[start] Verifying core table public.${CHECK_TABLE}..."
HAS_CHECK=$(python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'smartwash.settings'))
import django
django.setup()
from django.db import connection
table = os.getenv('CHECK_TABLE', 'lavagem_tipolavagem')
with connection.cursor() as c:
    c.execute("SELECT to_regclass(%s)", [f"public.{table}"])
    print("1" if c.fetchone()[0] else "0")
PY
)

if [ "$HAS_CHECK" != "1" ]; then
  echo "[start] ERROR: Table public.${CHECK_TABLE} is missing after migrations."
  echo "[start] This strongly suggests DATABASE_URL points to a different DB than the one your service uses."
  exit 1
fi

echo "[start] Seeding base data (idempotent)..."
python manage.py gerar_horarios || true
python manage.py init_admin || true

echo "[start] Starting gunicorn..."
exec gunicorn smartwash.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --threads 2 --timeout 120
