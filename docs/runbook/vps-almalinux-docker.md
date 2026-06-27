# Visota — Deploy trên VPS AlmaLinux 10 (Docker, multi-app)

> Từ server trắng → visota.net chạy + sẵn sàng cho app khác
> OS: AlmaLinux 10 | Container: Docker CE | Proxy: Traefik (auto-SSL)

## Kiến trúc multi-app

```
Internet → [Firewalld: 80/443] → Traefik (Docker)
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                 visota        app-2          app-3
              (web+worker     (container     (container
               +db volumes)    :8081)         :8082)
```

- **Traefik** = edge proxy (80/443) → auto Let's Encrypt → route theo domain
- **Mỗi app** = 1 docker-compose riêng, dùng chung external network `web`
- **Firewalld** chỉ mở 22/80/443, inter-container traffic đi Docker network (không qua firewall)

## 1. Cài đặt AlmaLinux 10 (server trắng)

```bash
# Update hệ thống
sudo dnf update -y

# Gỡ xung đột (RHEL 10 có sẵn podman)
sudo dnf remove -y podman buildah runc 2>/dev/null || true

# Cài công cụ cơ bản
sudo dnf install -y dnf-utils curl wget git vim tar unzip
```

## 2. Cài Docker CE

```bash
# Thêm Docker CE repo (CentOS repo tương thích AlmaLinux)
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Cài Docker Engine + Compose plugin
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Khởi động
sudo systemctl enable --now docker

# Thêm user vào docker group (không cần sudo docker)
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
docker run hello-world
```

## 3. Cấu hình Firewalld

```bash
# Bật firewalld
sudo systemctl enable --now firewalld

# Chỉ mở port cần thiết
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-all
```

> **KHÔNG** mở port 3306 (MariaDB), 8900 (Gunicorn), 8080 (Traefik dashboard) ra ngoài — chúng chỉ truy cập nội bộ qua Docker network.

## 4. Tạo Docker network chung

```bash
# Network dùng chung cho Traefik + tất cả app
docker network create web
```

## 5. Cài Traefik (reverse proxy + auto-SSL)

```bash
sudo mkdir -p /opt/traefik
cd /opt/traefik

# Tạo email cho Let's Encrypt
echo "your-email@gmail.com" > acme_email.txt
```

Tạo `/opt/traefik/docker-compose.yml`:

```yaml
services:
  traefik:
    image: traefik:v3.2
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run.sock:ro
      - ./letsencrypt:/letsencrypt
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
    networks:
      - web

networks:
  web:
    external: true
```

Tạo `/opt/traefik/traefik.yml`:

```yaml
api:
  dashboard: true
  insecure: true

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false

certificatesResolvers:
  letsencrypt:
    acme:
      email: "your-email@gmail.com"
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web
```

```bash
mkdir -p letsencrypt
docker compose up -d
```

Verify: `http://[SERVER-IP]:8080` → Traefik dashboard.

## 6. Deploy Visota

```bash
sudo mkdir -p /opt/visota
sudo chown $USER:$USER /opt/visota
cd /opt/visota

git clone https://github.com/pkm2025/visota.git .
```

Tạo `.env`:

```bash
cp .env.docker .env
nano .env
# Đổi: SECRET_KEY, DB_ROOT_PASSWORD, DB_PASSWORD, SUPERUSER_PASSWORD
# Thêm: VISOTA_DOMAIN=visota.net (cho Traefik labels)
```

Sửa `docker-compose.yml` — thêm Traefik labels + external network:

```yaml
services:
  web:
    build: .
    restart: unless-stopped
    env_file: .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod
      - DB_HOST=db
      - DB_PORT=3306
    volumes:
      - static_files:/app/staticfiles
      - media_files:/app/media
    depends_on:
      db:
        condition: service_healthy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.visota.rule=Host(`visota.net`,`www.visota.net`)"
      - "traefik.http.routers.visota.entrypoints=websecure"
      - "traefik.http.routers.visota.tls.certresolver=letsencrypt"
      - "traefik.http.services.visota.loadbalancer.server.port=8900"
    networks:
      - web
      - visota-net

  worker:
    build: .
    restart: unless-stopped
    command: python manage.py qcluster
    env_file: .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod
      - DB_HOST=db
      - DB_PORT=3306
    volumes:
      - media_files:/app/media
    depends_on:
      db:
        condition: service_healthy
    networks:
      - visota-net

  db:
    image: mariadb:11.4
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
      - MYSQL_DATABASE=${DB_NAME:-visota}
      - MYSQL_USER=${DB_USER:-visota}
      - MYSQL_PASSWORD=${DB_PASSWORD}
    volumes:
      - db_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mariadb-admin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - visota-net

volumes:
  db_data:
  static_files:
  media_files:

networks:
  web:
    external: true
  visota-net:
    driver: bridge
```

> **Không cần nginx container** — Traefik làm proxy luôn. Static files serve qua Django Whitenoise hoặc thêm static-serving container nếu cần.

```bash
docker compose up -d --build
docker compose logs -f web  # xem migrate chạy
```

Sau 1-2 phút: `https://visota.net/` → landing page.

## 7. Thêm app khác (ví dụ: WordPress, n8n, Metabase)

Mỗi app chỉ cần 2 thứ:
1. docker-compose.yml riêng
2. Traefik labels với domain khác

```bash
mkdir -p /opt/metabase
cd /opt/metabase
```

`/opt/metabase/docker-compose.yml`:

```yaml
services:
  metabase:
    image: metabase/metabase:latest
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.metabase.rule=Host(`analytics.visota.net`)"
      - "traefik.http.routers.metabase.entrypoints=websecure"
      - "traefik.http.routers.metabase.tls.certresolver=letsencrypt"
      - "traefik.http.services.metabase.loadbalancer.server.port=3000"
    networks:
      - web

networks:
  web:
    external: true
```

```bash
docker compose up -d
```

Xong: `https://analytics.visota.net` → Metabase, SSL tự động.

## 8. Quản lý

### Portainer (UI quản lý container)

```bash
mkdir -p /opt/portainer
cd /opt/portainer

cat > docker-compose.yml << 'EOF'
services:
  portainer:
    image: portainer/portainer-ce:latest
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.portainer.rule=Host(`docker.visota.net`)"
      - "traefik.http.routers.portainer.entrypoints=websecure"
      - "traefik.http.routers.portainer.tls.certresolver=letsencrypt"
      - "traefik.http.services.portainer.loadbalancer.server.port=9000"
    networks:
      - web

volumes:
  portainer_data:

networks:
  web:
    external: true
EOF

docker compose up -d
```

→ `https://docker.visota.net` → Portainer UI.

### Backup

```bash
# Tạo script backup Visota DB
cat > /opt/visota/backup.sh << 'EOF'
#!/bin/bash
cd /opt/visota
source .env
TS=$(date +%Y%m%d_%H%M%S)
docker compose exec -T db mysqldump -u root -p${DB_ROOT_PASSWORD} ${DB_NAME} | gzip > backups/db_${TS}.sql.gz
find backups/ -name "db_*.sql.gz" -mtime +30 -delete
echo "Backup: db_${TS}.sql.gz"
EOF

mkdir -p /opt/visota/backups
chmod +x /opt/visota/backup.sh

# Crontab — 2h hàng ngày
echo "0 2 * * * /opt/visota/backup.sh >> /var/log/visota-backup.log 2>&1" | crontab -
```

### Monitoring (tùy chọn)

```bash
# Cài ctop — top cho container
sudo dnf install -y ctop
ctop

# Hoặc Watchtower — auto-update containers
docker run -d --name watchtower --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower --cleanup --interval 86400
```

## 9. Bảo mật

```bash
# SSH key only (tắt password SSH)
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Fail2ban
sudo dnf install -y epel-release
sudo dnf install -y fail2ban
sudo systemctl enable --now fail2ban

# Automatic security updates
sudo dnf install -y dnf-automatic
sudo systemctl enable --now dnf-automatic.timer
```

## 10. Quick reference

| Lệnh | Mục đích |
|------|----------|
| `docker compose ps` | Xem status tất cả services |
| `docker compose logs -f web` | Django log real-time |
| `docker compose restart web` | Restart app |
| `docker compose exec web python manage.py shell` | Django shell |
| `docker compose exec web python manage.py createsuperuser` | Tạo admin |
| `docker compose down` | Stop Visota |
| `docker compose up -d --build` | Rebuild + start |
| `docker compose exec db mysqldump ...` | Backup DB |
| `cd /opt/traefik && docker compose logs -f traefik` | Traefik log |
| `sudo firewall-cmd --list-all` | Kiểm tra firewall |
| `docker stats` | RAM/CPU per container |

## DNS setup

| Domain | Loại | Giá trị |
|--------|------|---------|
| `visota.net` | A | [VPS IP] |
| `www.visota.net` | CNAME | visota.net |
| `docker.visota.net` | A | [VPS IP] (Portainer) |
| `analytics.visota.net` | A | [VPS IP] (app khác) |

Traefik tự xin SSL cho mỗi domain khi container khởi động.
