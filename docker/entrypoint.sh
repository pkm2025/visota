#!/bin/bash
set -e

echo "=== Visota Docker Entrypoint ==="

# Wait for MariaDB
echo "Waiting for database..."
for i in $(seq 1 30); do
    python -c "
import MySQLdb, os
MySQLdb.connect(
    host=os.environ.get('DB_HOST', 'db'),
    port=int(os.environ.get('DB_PORT', '3306')),
    user=os.environ.get('DB_USER', 'visota'),
    passwd=os.environ.get('DB_PASSWORD', ''),
    db=os.environ.get('DB_NAME', 'visota'),
)
" 2>/dev/null && break
    echo "  DB not ready (attempt $i/30)... retrying in 2s"
    sleep 2
done
echo "✓ Database ready"

# Migrate
echo "Running migrations..."
python manage.py migrate --noinput
python manage.py createcachetable 2>/dev/null || true

# Seed
echo "Seeding permissions..."
python manage.py seed_permissions 2>/dev/null || true

echo "Ensuring TT133 chart of accounts for all companies..."
python manage.py ensure_tt133_charts 2>/dev/null || true

# Collect static (WhiteNoise — compressed)
echo "Collecting static files (WhiteNoise compressed)..."
python manage.py collectstatic --noinput --clear

# Create superuser (web only — skip for worker)
if [ "${VISOTA_ROLE:-web}" = "web" ]; then
    echo "Ensuring superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username='admin',
        email=os.environ.get('SUPERUSER_EMAIL', 'admin@visota.net'),
        password=os.environ.get('SUPERUSER_PASSWORD', 'admin'),
    )
    print('  Created superuser: admin')
else:
    print('  Superuser exists')
" 2>/dev/null
fi

echo "=== Starting: $* ==="
# Validate uvicorn env vars (defense against tampered .env)
for v in UVICORN_WORKERS; do
  val="${!v:-}"
  if [ -n "$val" ] && ! [[ "$val" =~ ^[0-9]+$ ]]; then
    echo "FATAL: $v='$val' is not numeric. Refusing to start." >&2
    exit 1
  fi
done
exec "$@"
