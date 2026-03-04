import os
import django
from django.db import connection
from django.core.management import call_command

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartwash.settings")
django.setup()

def main():
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
    missing = "agendamento_tipolavagem" not in tables
    if not missing:
        return

    # If table missing but migrations marked as applied, reset migration records for agendamento
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM django_migrations WHERE app=%s LIMIT 1", ["agendamento"])
        has_mig = cursor.fetchone() is not None

    if has_mig:
        print("[ensure_db] agendamento_tipolavagem missing but django_migrations has agendamento; resetting migration records...")
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM django_migrations WHERE app=%s", ["agendamento"])

    print("[ensure_db] Running migrate to recreate missing tables...")
    call_command("migrate", interactive=False, verbosity=1)

if __name__ == "__main__":
    main()
