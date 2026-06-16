# 06. Deployment & Vận hành

> Hướng dẫn triển khai PMKetoan từ development đến production. **Không Docker** — deployment trực tiếp lên VPS bằng systemd.

## 1. Stack vận hành

| Layer | Tool | Phiên bản |
|-------|------|----------|
| OS | Ubuntu Server LTS | 22.04 hoặc 24.04 |
| Web server (reverse proxy) | Nginx | 1.24+ |
| Application server (WSGI) | Gunicorn | 22+ |
| Background workers | django-q2 cluster | 2.0+ |
| Database | MariaDB | 11.4 LTS |
| Cache | Django DB cache (MariaDB) | – |
| Process manager | systemd | built-in Ubuntu |
| Log rotation | logrotate | built-in |
| Backup | mariadb-backup + restic | – |
| Monitoring | Sentry + Prometheus node_exporter | – |
| SSL certificates | certbot (Let's Encrypt) | – |

## 2. Cài đặt development environment

### 2.1. Yêu cầu hệ thống (dev)

- Python 3.12+
- MariaDB 11.4 (hoặc chạy trên localhost qua apt)
- Node.js 20+ (chỉ để install vendor assets)
- Make, git, build-essential

### 2.2. Setup Ubuntu 24.04 (dev)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3.12 python3.12-venv python3.12-dev \
    build-essential default-libmysqlclient-dev \
    libxml2-dev libxslt1-dev libjpeg-dev libfreetype6-dev libffi-dev \
    pkg-config \
    mariadb-server mariadb-client \
    nginx \
    git curl vim

# Install Node.js 20 (cho vendor assets)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Start services
sudo systemctl enable --now mariadb
sudo systemctl enable --now nginx
```

### 2.3. Setup project

```bash
# Clone repo
git clone <repo-url> pmketoan
cd pmketoan

# Create virtualenv với uv (nhanh hơn pip/poetry)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12
source .venv/bin/activate

# Install Python deps
uv pip install -r requirements/base.txt
uv pip install -r requirements/dev.txt

# Or with pyproject.toml
# uv sync

# Setup environment
cp .env.example .env
# Edit .env with your local config

# Create database
sudo mysql -e "CREATE DATABASE pmketoan CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER 'pmketoan'@'localhost' IDENTIFIED BY 'devpass';"
sudo mysql -e "GRANT ALL PRIVILEGES ON pmketoan.* TO 'pmketoan'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# Install vendor assets
make install-vendor

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load initial data (chart of accounts TT133, currencies, etc)
python manage.py load_initial_data

# Run dev server
python manage.py runserver

# In another terminal, run django-q2 cluster
python manage.py qcluster
```

## 3. Production deployment trên VPS

### 3.1. Server provisioning (Ubuntu 24.04)

```bash
# SSH vào server fresh
ssh root@your-server-ip

# Create deploy user
adduser pmketoan
usermod -aG sudo pmketoan
# Set passwordless sudo cho một số lệnh cụ thể nếu cần

# Update system
apt update && apt upgrade -y

# Install packages
apt install -y \
    python3.12 python3.12-venv python3.12-dev \
    build-essential default-libmysqlclient-dev \
    libxml2-dev libxslt1-dev libjpeg-dev libfreetype6-dev libffi-dev \
    pkg-config \
    mariadb-server mariadb-client \
    nginx \
    certbot python3-certbot-nginx \
    git curl vim ufw fail2ban

# Configure firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# Secure MariaDB
mysql_secure_installation

# Configure MariaDB
# (see section 3.4)

# Harden SSH (optional but recommended)
# - Disable root login
# - Disable password auth
# - Use SSH keys
```

### 3.2. Application setup

```bash
# Switch to deploy user
su - pmketoan

# Clone repo
cd /home/pmketoan
git clone <repo-url> app
cd app

# Create virtualenv
python3.12 -m venv .venv
source .venv/bin/activate

# Install deps
pip install --upgrade pip
pip install -r requirements/prod.txt

# Or with uv
# curl -LsSf https://astral.sh/uv/install.sh | sh
# uv venv --python 3.12
# uv pip install -r requirements/prod.txt

# Configure environment
cp .env.example .env
vim .env  # set SECRET_KEY, DATABASE_URL, etc.

# Create database (run as root)
sudo mysql -e "CREATE DATABASE pmketoan_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER 'pmketoan'@'localhost' IDENTIFIED BY '<strong-password>';"
sudo mysql -e "GRANT ALL PRIVILEGES ON pmketoan_prod.* TO 'pmketoan'@'localhost';"

# Migrations
python manage.py migrate

# Collect static
python manage.py collectstatic --noinput

# Load initial data
python manage.py load_initial_data

# Create superuser
python manage.py createsuperuser

# Test run
python manage.py check --deploy
```

### 3.3. systemd units

#### `/etc/systemd/system/pmketoan-web.service`

```ini
[Unit]
Description=PMKetoan Gunicorn Web Server
After=network.target mariadb.service

[Service]
Type=notify
User=pmketoan
Group=www-data
WorkingDirectory=/home/pmketoan/app
Environment="PATH=/home/pmketoan/app/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.prod"
EnvironmentFile=/home/pmketoan/app/.env
ExecStart=/home/pmketoan/app/.venv/bin/gunicorn \
    --workers 4 \
    --threads 2 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/pmketoan/gunicorn-access.log \
    --error-logfile /var/log/pmketoan/gunicorn-error.log \
    --timeout 120 \
    --graceful-timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5s

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/var/log/pmketoan /home/pmketoan/app/staticfiles /home/pmketoan/app/media
RestrictSUIDSGID=true
RemoveIPC=true

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/pmketoan-qcluster.service`

```ini
[Unit]
Description=PMKetoan django-q2 Cluster (background workers)
After=network.target mariadb.service pmketoan-web.service

[Service]
Type=simple
User=pmketoan
Group=www-data
WorkingDirectory=/home/pmketoan/app
Environment="PATH=/home/pmketoan/app/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.prod"
EnvironmentFile=/home/pmketoan/app/.env
ExecStart=/home/pmketoan/app/.venv/bin/python manage.py qcluster
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure
RestartSec=10s

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/var/log/pmketoan /home/pmketoan/app/media

[Install]
WantedBy=multi-user.target
```

#### Kích hoạt services

```bash
sudo mkdir -p /var/log/pmketoan
sudo chown pmketoan:www-data /var/log/pmketoan

sudo systemctl daemon-reload
sudo systemctl enable --now pmketoan-web
sudo systemctl enable --now pmketoan-qcluster

# Check status
sudo systemctl status pmketoan-web
sudo systemctl status pmketoan-qcluster

# View logs
sudo journalctl -u pmketoan-web -f
sudo journalctl -u pmketoan-qcluster -f
```

### 3.4. MariaDB configuration

`/etc/mysql/mariadb.conf.d/50-server.cnf`:

```ini
[mysqld]
# Basic
user = mysql
pid-file = /var/run/mysqld/mysqld.pid
socket = /var/run/mysqld/mysqld.sock
port = 3306
basedir = /usr
datadir = /var/lib/mysql
tmpdir = /tmp

# Charset
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# InnoDB (adjust to ~60-70% of total RAM)
innodb_buffer_pool_size = 8G
innodb_buffer_pool_instances = 8
innodb_log_file_size = 1G
innodb_log_buffer_size = 64M
innodb_flush_log_at_trx_commit = 1
innodb_flush_method = O_DIRECT
innodb_file_per_table = 1
innodb_stats_persistent = 1
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# Connection
max_connections = 200
max_user_connections = 150

# Query cache (OFF — QC không hiệu quả với workload nặng)
query_cache_type = 0
query_cache_size = 0

# Logging
log_error = /var/log/mysql/error.log
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1
log_queries_not_using_indexes = 1

# Binary log (cho replication + PITR)
server_id = 1
log_bin = /var/lib/mysql/mysql-bin
binlog_format = ROW
expire_logs_days = 7
max_binlog_size = 100M

# Safety
sql_mode = STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION
default_storage_engine = InnoDB

# Performance
innodb_io_capacity = 2000
innodb_io_capacity_max = 4000
innodb_flush_neighbors = 0

# MariaDB-specific
optimizerswitch = 'index_merge=on'
```

Sau khi sửa, restart:

```bash
sudo systemctl restart mariadb
```

### 3.5. Nginx configuration

`/etc/nginx/sites-available/pmketoan.conf`:

```nginx
server {
    listen 80;
    server_name pmketoan.example.com;
    
    # Redirect to HTTPS (after certbot setup)
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pmketoan.example.com;
    
    # SSL (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/pmketoan.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pmketoan.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # SSL stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    client_max_body_size 50M;
    
    # Static files (served by Nginx, not Django)
    location /static/ {
        alias /home/pmketoan/app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    location /media/ {
        alias /home/pmketoan/app/media/;
        expires 30d;
        access_log off;
    }
    
    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
    
    # Login endpoint (strict rate limit)
    location /auth/login/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/proxy_params.conf;
    }
    
    # API (moderate rate limit)
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/proxy_params.conf;
    }
    
    # Main app
    location / {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/proxy_params.conf;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
    
    # Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;
}
```

`/etc/nginx/snippets/proxy_params.conf`:

```nginx
proxy_set_header Host $http_host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_redirect off;
proxy_connect_timeout 60s;
```

Kích hoạt:

```bash
sudo ln -s /etc/nginx/sites-available/pmketoan.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d pmketoan.example.com -d www.pmketoan.example.com
```

### 3.6. Django settings (prod)

`config/settings/prod.py`:

```python
import os
from .base import *

DEBUG = False
ALLOWED_HOSTS = os.environ['ALLOWED_HOSTS'].split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'CONN_MAX_AGE': 60,  # Persistent connections
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}

# Cache (Django DB cache — không cần Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
        'TIMEOUT': 3600,
        'OPTIONS': {'MAX_ENTRIES': 100000},
    },
    'local': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'per-process',
    },
}

# Session: cached_db (DB persistent + cache for speed)
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# django-q2 configuration
Q_CLUSTER = {
    'name': 'PMKetoan',
    'workers': 4,
    'recycle': 500,           # Recycle worker sau 500 tasks
    'timeout': 600,           # Per-task timeout 10 phút
    'retry': 720,             # Retry sau 12 phút
    'queue_limit': 1000,      # Max tasks in queue
    'bulk': 5,                # Process 5 tasks mỗi batch
    'orm': 'default',         # Dùng default DB làm broker
    'sync': False,            # Async mode
    'cpu_affinity': 2,        # Pin workers to CPU cores
    'label': 'Django Q2',
    'catch_up': True,         # Run missed schedules
    'max_attempts': 3,        # Max retries per task
}

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Static files
STATIC_ROOT = '/home/pmketoan/app/staticfiles/'
MEDIA_ROOT = '/home/pmketoan/app/media/'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/pmketoan/django.log',
            'maxBytes': 1024*1024*100,  # 100 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Sentry
if SENTRY_DSN := os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
```

### 3.7. Log rotation

`/etc/logrotate.d/pmketoan`:

```
/var/log/pmketoan/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 pmketoan www-data
    sharedscripts
    postrotate
        systemctl reload pmketoan-web > /dev/null 2>&1 || true
    endscript
}
```

## 4. CI/CD Pipeline

### 4.1. GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mariadb:
        image: mariadb:11.4
        env:
          MYSQL_ROOT_PASSWORD: rootpass
          MYSQL_DATABASE: test_pmketoan
        ports: ['3306:3306']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install uv && uv venv && uv pip install -r requirements/dev.txt
      - run: ruff check apps/
      - run: black --check apps/
      - run: mypy apps/
      - run: pytest --cov=apps

  deploy:
    needs: test
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd /home/pmketoan/app
            git pull origin main
            source .venv/bin/activate
            pip install -r requirements/prod.txt
            python manage.py migrate
            python manage.py collectstatic --noinput
            sudo systemctl restart pmketoan-web
            sudo systemctl restart pmketoan-qcluster
            # Health check
            sleep 5
            curl -f https://pmketoan.example.com/health/ || \
              (echo "Health check failed"; exit 1)
```

### 4.2. Manual deploy script

`scripts/deploy.sh` (chạy trên server):

```bash
#!/bin/bash
set -euo pipefail

cd /home/pmketoan/app
source .venv/bin/activate

echo "==> Pulling latest code..."
git pull origin main

echo "==> Installing dependencies..."
pip install -r requirements/prod.txt

echo "==> Running migrations..."
python manage.py migrate

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Restarting services..."
sudo systemctl restart pmketoan-web
sudo systemctl restart pmketoan-qcluster

echo "==> Health check..."
sleep 5
if curl -fsS https://pmketoan.example.com/health/ > /dev/null; then
    echo "✓ Deployment successful"
else
    echo "✗ Health check failed — rolling back"
    sudo systemctl stop pmketoan-web
    git revert HEAD --no-edit
    git push origin main
    sudo systemctl start pmketoan-web
    exit 1
fi
```

## 5. Rollback

### 5.1. Code rollback

```bash
cd /home/pmketoan/app

# Xem 5 commit gần nhất
git log --oneline -5

# Rollback về commit trước (giữ lịch sử)
git revert HEAD --no-edit
git push origin main

# Hoặc reset cứng (cẩn thận!)
# git reset --hard <commit-hash>
# git push --force  # không khuyến nghị trên main

# Deploy lại
./scripts/deploy.sh
```

### 5.2. Database rollback

**Chỉ khi migration gây lỗi nghiêm trọng**:

```bash
# Rollback migration
python manage.py migrate <app_name> <previous_migration>

# Restore từ backup nếu cần
sudo systemctl stop pmketoan-web pmketoan-qcluster
mariadb-backup --copy-back --target-dir=/backup/mysql/full/20260616_020000
sudo chown -R mysql:mysql /var/lib/mysql
sudo systemctl start mariadb
sudo systemctl start pmketoan-web pmketoan-qcluster
```

## 6. Health checks

```python
# apps/core/views/health.py
from django.http import JsonResponse
from django.db import connections


def health_check(request):
    """Lightweight health check (for load balancer / monitoring)"""
    return JsonResponse({'status': 'ok'})


def health_detailed(request):
    """Detailed health check"""
    checks = {
        'database': check_database(),
        'cache': check_cache(),
        'qcluster': check_qcluster(),
        'disk_space': check_disk_space(),
    }
    
    all_ok = all(c.get('status') == 'ok' for c in checks.values())
    return JsonResponse({
        'status': 'ok' if all_ok else 'degraded',
        'checks': checks,
    }, status=200 if all_ok else 503)


def check_qcluster():
    """Check if django-q2 cluster is responsive"""
    from django_q.models import Task
    from datetime import timedelta
    from django.utils import timezone
    
    # Check if there's a stuck task
    stuck = Task.objects.filter(
        success=None,
        started__lt=timezone.now() - timedelta(minutes=30),
    ).count()
    
    if stuck > 5:
        return {'status': 'error', 'error': f'{stuck} stuck tasks'}
    return {'status': 'ok'}
```

## 7. Monitoring

### 7.1. Process monitoring

```bash
# Quick check
sudo systemctl status pmketoan-web pmketoan-qcluster

# Resource usage
sudo systemctl status pmketoan-web -l | grep -E "(Memory|CPU)"

# Live logs
sudo journalctl -u pmketoan-web -f
sudo journalctl -u pmketoan-qcluster -f
```

### 7.2. django-q2 monitoring

```bash
# Truy cập admin Django → Django Q2 → Tasks/Schedules/Failed
# Hoặc query DB:
mysql> SELECT COUNT(*) FROM django_q2_task WHERE success IS NULL;  -- Pending
mysql> SELECT COUNT(*) FROM django_q2_task WHERE success = 1;       -- Success
mysql> SELECT COUNT(*) FROM django_q2_task WHERE success = 0;       -- Failed

# Recent failed tasks
mysql> SELECT id, name, func, started, stopped 
       FROM django_q2_task 
       WHERE success = 0 
       ORDER BY started DESC LIMIT 10;
```

### 7.3. Sentry error tracking

Tự động capture exceptions. Configure ở `SENTRY_DSN` env var.

### 7.4. Prometheus + Grafana (optional)

```ini
# /etc/systemd/system/node_exporter.service
[Service]
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Grafana trên server riêng, query Prometheus + MariaDB exporter.

## 8. Backup & Recovery

### 8.1. Backup strategy

| Type | Frequency | Retention |
|------|----------|-----------|
| Full DB backup (mariadb-backup) | Daily 02:00 | 30 ngày |
| Incremental (binlog) | Hourly | 7 ngày |
| Static files (rsync) | Daily | 90 ngày |
| Media files | Daily | 90 ngày |
| Code (git) | Push | Forever |

### 8.2. Backup script

`/home/pmketoan/scripts/backup_db.sh`:

```bash
#!/bin/bash
set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backup/mysql
mkdir -p $BACKUP_DIR

# Full backup with mariadb-backup
sudo mariadb-backup --backup \
    --target-dir=$BACKUP_DIR/$DATE \
    --user=root --password=$MYSQL_ROOT_PASSWORD \
    --compress --compress-threads=4

# Keep 7 daily, 4 weekly, 12 monthly
find $BACKUP_DIR -mtime +7 -delete

# Upload to offsite (S3)
if [ -n "$S3_BUCKET" ]; then
    aws s3 sync $BACKUP_DIR/$DATE s3://$S3_BUCKET/backup/full/$DATE \
        --storage-class STANDARD_IA
fi

# Verify backup
mariadb-backup --prepare --target-dir=$BACKUP_DIR/$DATE 2>&1 | grep -q "completed OK!"

echo "✓ Backup $DATE completed"
```

### 8.3. Crontab

```
# /var/spool/cron/crontabs/root
0 2 * * * /home/pmketoan/scripts/backup_db.sh >> /var/log/pmketoan/backup.log 2>&1
0 * * * * /home/pmketoan/scripts/backup_binlog.sh >> /var/log/pmketoan/backup.log 2>&1
0 3 * * * /home/pmketoan/scripts/backup_media.sh >> /var/log/pmketoan/backup.log 2>&1
```

### 8.4. RPO/RTO targets

- **RPO** (Recovery Point Objective): ≤ 1 giờ
- **RTO** (Recovery Time Objective): ≤ 4 giờ

### 8.5. Restore procedure

```bash
# Stop services
sudo systemctl stop pmketoan-web pmketoan-qcluster

# Restore latest backup
sudo rm -rf /var/lib/mysql/*
sudo mariadb-backup --copy-back \
    --target-dir=/backup/mysql/20260616_020000

# Fix permissions
sudo chown -R mysql:mysql /var/lib/mysql

# Start MariaDB
sudo systemctl start mariadb

# Verify
mysql -e "SHOW DATABASES;"

# Restart app
sudo systemctl start pmketoan-web pmketoan-qcluster

# Health check
curl https://pmketoan.example.com/health/
```

### 8.6. DR test (quarterly)

- Restore DB to staging server
- Verify integrity
- Simulate failover
- Document gaps and improve plan

## 9. SSL renewal

```bash
# Certbot auto-renewals
sudo certbot renew --dry-run  # Test

# Crontab (auto-renew trước 30 ngày hết hạn)
0 12 * * * /usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
```

## 10. Security hardening checklist

- [ ] UFW firewall enabled
- [ ] SSH root login disabled
- [ ] SSH password auth disabled (key only)
- [ ] fail2ban installed và configured
- [ ] MariaDB root password strong
- [ ] App user (`pmketoan`) limited permissions
- [ ] App env file (`/home/pmketoan/app/.env`) chmod 600
- [ ] Nginx security headers (HSTS, X-Frame-Options, etc.)
- [ ] HTTPS enforced, auto-renew
- [ ] Sentry monitoring configured
- [ ] Audit log enabled
- [ ] Backup encryption (restic + age hoặc GPG)

## 11. Update process

### 11.1. Regular update (no downtime)

```bash
./scripts/deploy.sh
# → git pull → migrate → collectstatic → restart pmketoan-web → restart pmketoan-qcluster
```

### 11.2. Major update (with downtime)

```bash
# Schedule maintenance window
# Notify users 24h ahead

# Maintenance mode
echo "Maintenance" > /home/pmketoan/app/templates/503.html
# (Nginx serve static maintenance page)

sudo systemctl stop pmketoan-web pmketoan-qcluster

# Deploy
./scripts/deploy.sh

# Test thoroughly
curl https://pmketoan.example.com/health/

# Bring back
sudo systemctl start pmketoan-web pmketoan-qcluster
```

---

**Tiếp theo**: [Tài liệu API →](../06-tai-lieu-api/01-api-conventions.md)
