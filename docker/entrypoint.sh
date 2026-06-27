#!/bin/bash
set -e

echo "=== Visota Docker Entrypoint ==="

# Wait for MariaDB
echo "Waiting for database..."
while ! python -c "
import MySQLdb
import os
try:
    MySQLdb.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=int(os.environ.get('DB_PORT', '3306')),
        user=os.environ.get('DB_USER', 'visota'),
        passwd=os.environ.get('DB_PASSWORD', ''),
        db=os.environ.get('DB_NAME', 'visota'),
    )
except Exception as e:
    print(f'  DB not ready: {e}')
    exit(1)
" 2>/dev/null; do
    sleep 2
done
echo "✓ Database ready"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Seed permissions
echo "Seeding permissions..."
python manage.py seed_permissions --reset 2>/dev/null || python manage.py seed_permissions 2>/dev/null || true

# Collect static
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if not exists
echo "Ensuring superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
import os
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

echo "=== Starting Gunicorn ==="
exec gunicorn \
    --bind 0.0.0.0:8900 \
    --workers ${GUNICORN_WORKERS:-4} \
    --threads ${GUNICORN_THREADS:-2} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile - \
    config.wsgi:application
