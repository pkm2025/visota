# Visota — Docker Deployment Guide

## Quick Start (5 minutes)

```bash
# 1. Clone
git clone https://github.com/pkm2025/visota.git
cd visota

# 2. Create .env
cp .env.docker .env
# Edit .env — change SECRET_KEY, DB_PASSWORD, SUPERUSER_PASSWORD

# 3. Build + Start
docker compose up -d --build

# 4. Check
docker compose ps
curl http://localhost/health/
```

Open `http://localhost/` → Visota landing page.
Login: `http://localhost/auth/login/` with admin / [SUPERUSER_PASSWORD from .env]

## Services

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| **web** | visota-web | 8900 (internal) | Django + Uvicorn |
| **worker** | visota-worker | — | django-q2 background tasks |
| **db** | visota-db | 3306 | MariaDB 11.4 |
| **nginx** | visota-nginx | 80, 443 | Reverse proxy + TLS |

## Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f nginx

# Restart single service
docker compose restart web

# Stop all
docker compose down

# Stop + remove data (CAREFUL — deletes DB)
docker compose down -v

# Run Django management command
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell
docker compose exec web python manage.py migrate

# Backup database
docker compose exec db mysqldump -u root -p${DB_ROOT_PASSWORD} visota | gzip > backup.sql.gz

# Restore
gunzip < backup.sql.gz | docker compose exec -T db mysql -u root -p${DB_ROOT_PASSWORD} visota
```

## SSL (Let's Encrypt)

### Option A: Certbot on host

```bash
# Get certs (after DNS points to server)
sudo certbot certonly --standalone -d visota.net -d www.visota.net

# Copy to Docker
sudo cp /etc/letsencrypt/live/visota.net/fullchain.pem docker/certs/
sudo cp /etc/letsencrypt/live/visota.net/privkey.pem docker/certs/
docker compose restart nginx
```

### Option B: HTTP-only (dev)

Edit `docker/nginx.conf` — comment out SSL lines, use `listen 80` only.

## Scaling

```bash
# Scale web workers (horizontal)
docker compose up -d --scale web=3

# Adjust Uvicorn workers per container
echo "UVICORN_WORKERS=8" >> .env
docker compose up -d
```

## Environment Variables (.env)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SECRET_KEY` | — | ✓ | Django secret (50 random chars) |
| `DB_ROOT_PASSWORD` | — | ✓ | MariaDB root password |
| `DB_PASSWORD` | — | ✓ | MariaDB visota user password |
| `DB_NAME` | visota | | Database name |
| `DB_USER` | visota | | Database user |
| `ALLOWED_HOSTS` | visota.net | | Comma-separated domains |
| `SUPERUSER_EMAIL` | admin@visota.net | | First admin email |
| `SUPERUSER_PASSWORD` | — | ✓ | First admin password |
| `EMAIL_HOST` | smtp.gmail.com | | SMTP server |
| `EMAIL_HOST_USER` | noreply@visota.net | | SMTP user |
| `EMAIL_HOST_PASSWORD` | — | | SMTP password |
| `UVICORN_WORKERS` | 4 | | Workers per container |
| `SENTRY_DSN` | — | | Error tracking (optional) |

## Volumes

| Volume | Mount | Description |
|--------|-------|-------------|
| `db_data` | MariaDB data | Persistent database |
| `static_files` | /app/staticfiles | Collected static (CSS/JS) |
| `media_files` | /app/media | User uploads (HĐĐT, attachments) |

## Health Check

```bash
curl http://localhost/health/
# {"status": "ok", ...}
```

## Troubleshooting

**502 Bad Gateway**: `docker compose logs web` — check if Django started

**Database connection refused**: `docker compose ps db` — wait for healthy

**Static files 404**: `docker compose exec web python manage.py collectstatic --noinput`

**Permission denied (media)**: `docker compose exec web chown -R visota:visota /app/media`
