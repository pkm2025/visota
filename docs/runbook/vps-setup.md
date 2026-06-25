# Hướng dẫn deploy Visota lên VPS

> Từ VPS trống → visota.net chạy production
> Thời gian ước tính: 30-45 phút

## 0. Yêu cầu VPS

| Spec | Tối thiểu | Khuyến nghị |
|------|----------|-------------|
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| RAM | 2 GB | 4 GB |
| CPU | 1 core | 2 cores |
| Disk | 20 GB SSD | 50 GB SSD |
| Python | 3.12 | 3.12 |
| DB | MariaDB 11.4 | MariaDB 11.4 |
| Web | Nginx | Nginx |

## 1. Cài đặt hệ thống

```bash
# Update OS
sudo apt update && sudo apt upgrade -y

# Cài đặt dependencies
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
    mariadb-server libmariadb-dev \
    nginx supervisor \
    build-essential libxml2-dev libxslt1-dev \
    libpango-1.0-0 libpangoft2-1.0-0 \
    libffi-dev libcairo2 \
    git curl certbot python3-certbot-nginx
```

## 2. Tạo user + thư mục

```bash
# Tạo user visota
sudo useradd -r -s /bin/bash -d /opt/visota -m visota

# Tạo thư mục
sudo mkdir -p /opt/visota/app /opt/visota/staticfiles /opt/visota/media /var/log/visota
sudo chown -R visota:visota /opt/visota /var/log/visota

# Thêm visota vào www-data (cho Nginx đọc static)
sudo usermod -aG visota www-data
```

## 3. Clone code

```bash
sudo -iu visota
cd /opt/visota/app
git clone https://github.com/pkm2025/visota.git .
```

## 4. Virtualenv + dependencies

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

## 5. Cấu hình MariaDB

```bash
# Secure installation
sudo mysql_secure_installation

# Tạo database + user
sudo mysql <<EOF
CREATE DATABASE visota CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'visota'@'localhost' IDENTIFIED BY 'ĐẶT_MẬT_KHẨU_MẠNH';
GRANT ALL PRIVILEGES ON visota.* TO 'visota'@'localhost';
FLUSH PRIVILEGES;
EOF
```

Tối ưu MariaDB:

```bash
sudo tee /etc/mysql/mariadb.conf.d/99-visota.cnf <<EOF
[mariadb]
character_set_server = utf8mb4
collation_server = utf8mb4_unicode_ci
max_connections = 100
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
log_bin = mysql-bin
expire_logs_days = 7
EOF

sudo systemctl restart mariadb
```

## 6. Tạo file .env

```bash
sudo tee /opt/visota/.env <<EOF
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
ALLOWED_HOSTS=visota.net,www.visota.net
DB_NAME=visota
DB_USER=visota
DB_PASSWORD=ĐẶT_MẬT_KHẨU_MẠNH
DB_HOST=127.0.0.1
DB_PORT=3306
STATIC_ROOT=/opt/visota/staticfiles/
MEDIA_ROOT=/opt/visota/media/
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@visota.net
EMAIL_HOST_PASSWORD=your-app-password
LOG_FILE=/var/log/visota/django.log
SENTRY_DSN=
EOF

sudo chown visota:visota /opt/visota/.env
sudo chmod 600 /opt/visota/.env
```

## 7. Khởi tạo Django

```bash
sudo -iu visota
cd /opt/visota/app
source .venv/bin/activate

# Migrate
python manage.py migrate

# Seed dữ liệu cơ bản
python manage.py seed_permissions
python manage.py load_tt133

# Tạo superuser
python manage.py createsuperuser

# Collect static
python manage.py collectstatic --noinput

# Test
python manage.py check --deploy
```

## 8. Cấu hình Gunicorn (systemd)

```bash
sudo tee /etc/systemd/system/visota.service <<EOF
[Unit]
Description=Visota Gunicorn
After=network.target mariadb.service

[Service]
Type=notify
User=visota
Group=www-data
WorkingDirectory=/opt/visota/app
EnvironmentFile=/opt/visota/.env
ExecStart=/opt/visota/app/.venv/bin/gunicorn \
    --workers 8 \
    --threads 4 \
    --bind 127.0.0.1:8900 \
    --access-logfile /var/log/visota/gunicorn-access.log \
    --error-logfile /var/log/visota/gunicorn-error.log \
    --timeout 120 \
    config.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

## 9. Cấu hình django-q2 worker

```bash
sudo tee /etc/systemd/system/visota-worker.service <<EOF
[Unit]
Description=Visota django-q2 Worker
After=network.target mariadb.service visota.service

[Service]
Type=simple
User=visota
Group=www-data
WorkingDirectory=/opt/visota/app
EnvironmentFile=/opt/visota/.env
ExecStart=/opt/visota/app/.venv/bin/python manage.py qcluster
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

## 10. Cấu hình Nginx

```bash
sudo tee /etc/nginx/sites-available/visota <<EOF
upstream visota {
    server 127.0.0.1:8900;
}

server {
    listen 80;
    server_name visota.net www.visota.net;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name visota.net www.visota.net;

    ssl_certificate /etc/letsencrypt/live/visota.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/visota.net/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 50M;

    # Static files
    location /static/ {
        alias /opt/visota/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (private — served via X-Accel-Redirect)
    location /media/ {
        internal;
        alias /opt/visota/media/;
    }

    # Service Worker
    location = /static/sw.js {
        alias /opt/visota/app/static/sw.js;
        add_header Cache-Control "no-cache";
    }

    # App
    location / {
        proxy_pass http://visota;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    # Health check (no access log)
    location /health/ {
        proxy_pass http://visota;
        access_log off;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/visota /etc/nginx/sites-enabled/visota
sudo rm -f /etc/nginx/sites-enabled/default
```

## 11. SSL Certificate (Let's Encrypt)

```bash
# Trước tiên trỏ DNS visota.net → IP VPS

# Lấy certificate
sudo certbot --nginx -d visota.net -d www.visota.net

# Auto-renew
sudo systemctl enable certbot.timer
```

## 12. Khởi động services

```bash
sudo systemctl daemon-reload
sudo systemctl enable visota visota-worker
sudo systemctl start visota visota-worker

# Kiểm tra
sudo systemctl status visota
sudo systemctl status visota-worker

# Nginx
sudo nginx -t
sudo systemctl reload nginx
```

## 13. Verify

```bash
# Health check
curl https://visota.net/health/

# Landing page
curl -s https://visota.net/ | grep "Visota"

# Login page
curl -s https://visota.net/auth/login/ | grep "Đăng nhập"

# Static files
curl -sI https://visota.net/static/modern/css/main.css | head -5
```

## 14. Crontab — Backup hàng ngày

```bash
sudo crontab -u visota -e
```

```cron
# Backup DB 2h mỗi ngày
0 2 * * * /opt/visota/app/scripts/backup.sh >> /var/log/visota/backup.log 2>&1

# Backup weekly (Chủ nhật 3h)
0 3 * * 0 /opt/visota/app/scripts/backup.sh --weekly >> /var/log/visota/backup.log 2>&1
```

## 15. Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## 16. Monitoring (tùy chọn)

```bash
# Sentry error tracking
# Thêm SENTRY_DSN vào /opt/visota/.env
# Rồi restart: sudo systemctl restart visota

# Log rotation
sudo tee /etc/logrotate.d/visota <<EOF
/var/log/visota/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 visota visota
}
EOF
```

## Quick reference

| Lệnh | Mục đích |
|------|----------|
| `sudo systemctl restart visota` | Restart app |
| `sudo systemctl restart visota-worker` | Restart worker |
| `sudo journalctl -u visota -f` | Xem log real-time |
| `tail -f /var/log/visota/django.log` | Django log |
| `sudo nginx -t && sudo systemctl reload nginx` | Reload Nginx |
| `cd /opt/visota/app && git pull && scripts/deploy.sh` | Deploy mới |
| `sudo certbot renew --dry-run` | Test SSL renew |

## Troubleshooting

**502 Bad Gateway**: Gunicorn chưa chạy → `sudo systemctl status visota`

**Static files 404**: Chưa collectstatic → `python manage.py collectstatic`

**Database connection refused**: MariaDB chưa chạy → `sudo systemctl start mariadb`

**Permission denied (media)**: `sudo chown -R visota:www-data /opt/visota/media/`

**SSL error**: DNS chưa trỏ → `dig visota.net` kiểm tra IP
