#!/bin/bash
set -euo pipefail

echo "Waiting for database..."
python3 - <<'PY'
import os, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
for i in range(60):
    try:
        django.setup()
        from django.db import connection
        connection.ensure_connection()
        print("DB ready")
        break
    except Exception as e:
        print(f"DB not ready ({e}), retry {i+1}/60")
        time.sleep(2)
else:
    raise SystemExit("Database unavailable")
PY

python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput || true

if [ "${SVDB_BOOTSTRAP:-0}" = "1" ]; then
  python3 manage.py bootstrap_svdb || true
fi

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
