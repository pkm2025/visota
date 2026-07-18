# T6 — Deployment & DevOps

> Hướng dẫn deploy production, monitoring, CI/CD.

## 1. Yêu cầu hệ thống

### Production minimum

| Resource | Spec |
|----------|------|
| CPU | 8 cores |
| RAM | 32 GB |
| Disk | 500 GB SSD (cho DB + media + backup 6 tháng) |
| OS | Ubuntu 22.04 LTS / Debian 12 |
| Network | 100 Mbps up/down |

### Khuyến nghị (≥ 50 users)

| Resource | Spec |
|----------|------|
| CPU | 16 cores |
| RAM | 64 GB |
| Disk | 1 TB NVMe SSD |

## 2. Stack部署

```
┌──────────────────────────────────────┐
│   Nginx (reverse proxy + TLS)        │
└────────────────┬─────────────────────┘
                 │
   ┌─────────────┴──────────────┐
   │                            │
   ▼                            ▼
┌─────────┐                ┌─────────┐
│ Gunicorn│  ...           │ Gunicorn│
│  (8-16  │                │  workers│
│ workers)│                │         │
└────┬────┘                └────┬────┘
     │                          │
     └──────────┬───────────────┘
                │
                ▼
        ┌──────────────┐
        │  MariaDB 11.4│
        │  (primary)   │
        └──────┬───────┘
               │ (replicate)
               ▼
        ┌──────────────┐
        │  MariaDB     │
        │  (replica)   │
        └──────────────┘
```

## 3. Cài đặt step-by-step

### 3.1. OS prep

```bash
# Ubuntu 22.04
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
                    mariadb-server libmariadb-dev \
                    nginx redis-server \
                    build-essential libxml2-dev libxslt1-dev \
                    libpango-1.0-0 libpangoft2-1.0-0 \
                    supervisor git

# Create app user
sudo useradd -r -s /bin/bash -d /opt/pmketoan -m pmketoan
```

### 3.2. MariaDB

```bash
sudo mysql_secure_installation

# Create DB + user
sudo mysql <<EOF
CREATE DATABASE pmketoan_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'pmk'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD';
GRANT ALL ON pmketoan_prod.* TO 'pmk'@'localhost';
FLUSH PRIVILEGES;
EOF
```

`/etc/mysql/mariadb.conf.d/99-pmk.cnf`:

```ini
[mariadb]
character_set_server = utf8mb4
collation_server = utf8mb4_unicode_ci
max_connections = 200
innodb_buffer_pool_size = 16G
innodb_log_file_size = 1G
innodb_flush_log_at_trx_commit = 2
query_cache_type = OFF  # off in 10.6+
log_bin = mysql-bin
binlog_format = ROW
expire_logs_days = 7
```

Restart: `sudo systemctl restart mariadb`

### 3.3. App

```bash
sudo -iu pmketoan

cd /opt/pmketoan
git clone https://github.com/pkm/pmketoan.git repo
cd repo

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn psycopg2-binary  # if PostgreSQL
```

### 3.4. Environment

`/etc/pmketoan/env` (root:root 600):

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=your-django-secret-50-chars
ALLOWED_HOSTS=erp.pkm.vn,staging.pkm.vn
DATABASE_URL=mysql://pmk:STRONG_PASSWORD@localhost/pmketoan_prod
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@pkm.vn
EMAIL_HOST_PASSWORD=app-specific-password
DEFAULT_FROM_EMAIL="Visota ERP <noreply@visota.net>"
AXES_FAILURE_LIMIT=5
AXES_COOLOFF_TIME=1  # 1 hour
SENTRY_DSN=https://xxx@sentry.io/123
```

### 3.5. Initial setup

```bash
source /etc/pmketoan/env
cd /opt/pmketoan/repo

# Migrate
python manage.py migrate

# Seed demo data (only for staging/dev)
python manage.py seed_demo
python manage.py seed_permissions
python manage.py load_tt133

# Collect static
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser

# Test
python manage.py check --deploy
```

### 3.6. Gunicorn systemd

`/etc/systemd/system/pmketoan.service`:

```ini
[Unit]
Description=Visota ERP Gunicorn
After=network.target mariadb.service

[Service]
Type=notify
User=pmketoan
Group=www-data
WorkingDirectory=/opt/pmketoan/repo
EnvironmentFile=/etc/pmketoan/env
ExecStart=/opt/pmketoan/repo/.venv/bin/gunicorn \
    --workers 12 \
    --threads 4 \
    --bind 127.0.0.1:8900 \
    --access-logfile /var/log/pmketoan/gunicorn.access.log \
    --error-logfile /var/log/pmketoan/gunicorn.error.log \
    --timeout 120 \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pmketoan
sudo systemctl status pmketoan
```

### 3.7. django-q2 worker

`/etc/systemd/system/pmketoan-worker.service`:

```ini
[Unit]
Description=Visota ERP django-q2 worker
After=network.target mariadb.service

[Service]
Type=simple
User=pmketoan
Group=www-data
WorkingDirectory=/opt/pmketoan/repo
EnvironmentFile=/etc/pmketoan/env
ExecStart=/opt/pmketoan/repo/.venv/bin/python manage.py qcluster
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now pmketoan-worker
```

### 3.8. Nginx

`/etc/nginx/sites-available/pmketoan`:

```nginx
upstream pmketoan {
    server 127.0.0.1:8900;
}

server {
    listen 80;
    server_name erp.pkm.vn;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name erp.pkm.vn;

    # TLS (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/erp.pkm.vn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/erp.pkm.vn/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 50M;

    # Static
    location /static/ {
        alias /opt/pmketoan/repo/static_collected/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media (private — served via X-Accel-Redirect)
    location /media/ {
        internal;
        alias /var/lib/pmketoan/media/;
    }

    # App
    location / {
        proxy_pass http://pmketoan;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Health check
    location /health/ {
        proxy_pass http://pmketoan;
        access_log off;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/pmketoan /etc/nginx/sites-enabled/
sudo certbot --nginx -d erp.pkm.vn
sudo nginx -t && sudo systemctl reload nginx
```

## 4. CI/CD

### GitHub Actions

`.github/workflows/deploy.yml`:

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-django factory-boy
      - run: pytest tests/ --cov=apps --cov-report=xml
      - uses: codecov/codecov-action@v3

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to prod
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /opt/pmketoan/repo
            git pull origin main
            source .venv/bin/activate
            pip install -r requirements.txt
            python manage.py migrate --noinput
            python manage.py collectstatic --noinput
            python manage.py seed_permissions
            python manage.py compilemessages
            sudo systemctl restart pmketoan pmketoan-worker
            curl -fs http://localhost:8900/health/ | grep -q ok
```

## 5. Monitoring

### Sentry (error tracking)

```bash
pip install sentry-sdk
```

`config/settings/prod.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

SENTRY_DSN = env('SENTRY_DSN')
sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False,  # don't send tax code / ID numbers
)
```

### Prometheus + Grafana

`/etc/prometheus/conf.d/pmketoan.yml`:

```yaml
- job_name: pmketoan
  static_configs:
    - targets: ['localhost:8900']
  metrics_path: /metrics
```

Add `django-prometheus` for DB/cache/view metrics.

### Log aggregation

- Filebeat → Elasticsearch hoặc
- Loki + Promtail

### Uptime monitoring

- UptimeRobot (free, 5min check)
- Pingdom (paid, 1min)

## 6. Health checks

`/health/` endpoint:

```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "storage": "ok",
    "queue": "ok"
  },
  "version": "3.0.0",
  "uptime_seconds": 86400
}
```

## 7. Backup

Xem chi tiết: [A5-backup-restore](../admin-guide/05-backup-restore.md).

```cron
0 2 * * * /opt/pmketoan/scripts/backup_db.sh
0 3 * * 0 /opt/pmketoan/scripts/backup_db.sh --weekly
*/15 * * * * /opt/pmketoan/scripts/check_backup.sh
```

## 8. Update (zero-downtime)

```bash
# Pull
cd /opt/pmketoan/repo
git fetch --tags
git checkout v3.1.0

# Install deps
source .venv/bin/activate
pip install -r requirements.txt

# Migrate (most are non-blocking)
python manage.py migrate

# Compile messages
python manage.py compilemessages

# Pre-warm cache
python manage.py warmup_cache

# Reload (zero-downtime via systemd ExecReload)
sudo systemctl reload pmketoan

# Restart worker (kills running tasks — schedule during low-traffic)
sudo systemctl restart pmketoan-worker

# Verify
curl -fs http://localhost:8900/health/
python manage.py test_selenium_smoke
```

## 9. Rollback

```bash
# If update broke something:
cd /opt/pmketoan/repo
git checkout v3.0.0
pip install -r requirements.txt
python manage.py migrate  # reverse migrations if any
sudo systemctl restart pmketoan pmketoan-worker

# If DB migration is irreversible:
# Restore from last backup (see A5-backup-restore)
```

## 10. Security checklist

- [ ] TLS 1.2+ only (no SSLv3, TLS 1.0, 1.1)
- [ ] HSTS header (`max-age=63072000`)
- [ ] CSP header (allow only same-origin)
- [ ] X-Frame-Options: DENY (prevent clickjacking)
- [ ] X-Content-Type-Options: nosniff
- [ ] Strong SECRET_KEY (50+ random chars)
- [ ] SECURE_COOKIE for session/csrf
- [ ] Axes brute-force protection enabled
- [ ] DB user limited (only pmketoan_prod DB)
- [ ] Firewall: only 80/443 open externally
- [ ] SSH key-only (no password)
- [ ] fail2ban for SSH
- [ ] AppArmor profile for pmketoan
- [ ] Audit log rotated
- [ ] Backup encrypted

Run check:

```bash
python manage.py check --deploy
```

## 11. Scaling checklist

When traffic grows:
- [ ] Add read replica + route reads
- [ ] Move cache to Redis
- [ ] Add second app server + LB
- [ ] Move media to S3
- [ ] CDN for static files
- [ ] Search via Elasticsearch (replace LIKE queries)

---

Tài liệu liên quan:
- [T1-architecture](01-architecture.md) — Tổng quan kiến trúc
- [A5-backup-restore](../admin-guide/05-backup-restore.md) — Backup chi tiết
- [05-security](05-security.md) — Bảo mật chuyên sâu
