#!/bin/bash
set -euo pipefail

echo "=== Visota Deploy Script ==="
cd /opt/visota/app

# Pull latest
git pull origin main

# Virtual env
source .venv/bin/activate
pip install -r requirements.txt

# Migrate
python manage.py migrate --noinput

# Seed permissions (idempotent)
python manage.py seed_permissions

# Ensure TT133 chart of accounts for all companies (idempotent, back-fills
# companies that were created before the signup-flow fix).
python manage.py ensure_tt133_charts

# Collect static
python manage.py collectstatic --noinput --clear

# Compile messages (if i18n)
python manage.py compilemessages 2>/dev/null || true

# Restart services
sudo systemctl reload visota
sudo systemctl restart visota-worker

# Health check
sleep 3
curl -fs http://localhost:8903/health/ | grep -q ok && echo "✓ Deploy successful" || echo "✗ Health check failed"

echo "=== Done ==="
