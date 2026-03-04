import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartwash.settings")

# Safety net: if Render is starting Gunicorn directly (ignoring start.sh),
# ensure migrations are applied once at boot.
# Uses a Postgres advisory lock so multiple workers don't race.

def _maybe_run_migrations():
    if os.environ.get("DISABLE_AUTO_MIGRATE") == "1":
        return

    # Only attempt if we're likely running in a hosted environment
    if not (os.environ.get("RENDER") or os.environ.get("DATABASE_URL") or os.environ.get("DJANGO_AUTO_MIGRATE") == "1"):
        return

    try:
        from django.db import connection
        from django.core.management import call_command

        # Acquire advisory lock on Postgres; if not Postgres, just try migrate
        acquired = True
        try:
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_try_advisory_lock(987654321)")
                    acquired = bool(cursor.fetchone()[0])
        except Exception:
            acquired = True

        if not acquired:
            return

        try:
            call_command("migrate", interactive=False, verbosity=1)
        finally:
            try:
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT pg_advisory_unlock(987654321)")
            except Exception:
                pass

    except Exception:
        # Never block app boot because of auto-migration issues.
        return


_maybe_run_migrations()

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
