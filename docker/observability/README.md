# Visota Observability Stack Setup Guide

## Combo: CrowdSec + Netdata + Uptime Kuma + Homepage

```
                    ┌─────────────────────────────────┐
                    │      Homepage (panel.visota.net) │
                    │     Single Pane of Glass UI      │
                    └──────┬──────┬──────┬─────────────┘
                           │      │      │
              ┌────────────┘      │      └────────────┐
              ▼                   ▼                   ▼
    ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────┐
    │ CrowdSec (~30MB)│ │ Netdata (~80MB)  │ │ Uptime Kuma      │
    │ IPS + blocklist │ │ Real-time metrics│ │ (~50MB)          │
    │                 │ │ CPU/RAM/Disk/DB  │ │ HTTP/TCP/cert    │
    │ Block bad IPs   │ │ Per-second data  │ │ Push alerts      │
    │ at kernel level │ │ Built-in alarms  │ │ Telegram/email   │
    └─────────────────┘ └──────────────────┘ └──────────────────┘
              │                                       │
              ▼                                       ▼
    ┌─────────────────┐                    ┌──────────────────┐
    │ firewalld       │                    │ External probes  │
    │ (iptables drop) │                    │ (every 60s)      │
    └─────────────────┘                    └──────────────────┘
```

## Deploy

```bash
# 1. Deploy all 4 services
sudo visota-ctl
> 2 (Deploy Apps)
> 7 (Observability Stack)

# Hoặc CLI:
sudo visota-ctl deploy observability
```

## Sau deploy — cần config thủ công

### 1. Homepage (panel.visota.net)
- Truy cập `https://panel.visota.net`
- Homepage auto-discovers Docker containers
- Edit config: `docker exec homepage vi /app/config/services.yaml`
- Đổi `${DOMAIN}` thành domain thật trong services.yaml

### 2. Uptime Kuma (status.visota.net)
- Truy cập `https://status.visota.net`
- Tạo admin account (lần đầu)
- Add monitors:
  ```
  Monitor 1: HTTPS → https://visota.net/health/
    Type: HTTP(s)
    Interval: 60s
    Expected status: 200
    
  Monitor 2: TCP → visota-db:3306
    Type: TCP Port
    Hostname: visota-db (Docker DNS)
    Port: 3306
    
  Monitor 3: HTTPS Certificate → visota.net
    Type: Keyword/HTTPS
    Check SSL cert expiry
  ```
- Setup notifications: Telegram / Email / Discord

### 3. Netdata (metrics.visota.net)
- Truy cập `https://metrics.visota.net` (admin:admin — đổi trong Traefik middleware)
- Auto-collects: CPU, RAM, Disk, Docker containers, MariaDB (if mysql plugin enabled)
- Enable MariaDB plugin:
  ```bash
  docker exec netdata bash -c "
  cat > /etc/netdata/python.d/mysql.conf << 'EOF'
  tcp:
    name: 'visota'
    host: 'visota-db'
    port: 3306
    user: 'root'
    pass: 'YOUR_DB_ROOT_PASSWORD'
  EOF
  "
  docker restart netdata
  ```
- Optional: Claim to Netdata Cloud for remote access:
  ```bash
  # Sign up at https://app.netdata.cloud → get token
  docker exec netdata netdata-claim.sh -token=YOUR_TOKEN -rooms=ROOM_ID -url=https://app.netdata.cloud
  ```

### 4. CrowdSec
- Bouncer auto-installed via `install-crowdsec.sh`
- View blocked IPs: `docker exec crowdsec cscli decisions list`
- View metrics: `docker exec crowdsec cscli metrics`
- Optional: Register at https://app.crowdsec.net for dashboard

## DNS Records

| Subdomain | A Record | Service |
|-----------|----------|---------|
| `panel.visota.net` | VPS IP | Homepage dashboard |
| `status.visota.net` | VPS IP | Uptime Kuma |
| `metrics.visota.net` | VPS IP | Netdata |
| `visota.net` | VPS IP | Django app |

Traefik auto-generates SSL cho mỗi subdomain.

## Resource Summary

| Component | RAM | VPS 2GB | VPS 4GB |
|-----------|-----|---------|---------|
| CrowdSec | 30MB | ✅ | ✅ |
| Netdata | 80MB | ⚠️ Optional | ✅ |
| Uptime Kuma | 50MB | ✅ | ✅ |
| Homepage | 40MB | ✅ | ✅ |
| **Total** | **200MB** | OK (bỏ Netdata) | **Dư dả** |

## Alert Setup (Telegram — recommended cho VN)

1. Tạo bot: Telegram → @BotFather → `/newbot` → copy token
2. Tạo group: Thêm bot vào group → copy chat_id
3. Uptime Kuma → Settings → Notifications → Telegram:
   ```
   Bot Token: 123456:ABC-DEF...
   Chat ID: -100123456789
   ```

## So sánh combo này vs Monit (đề xuất cũ)

| | Monit | Combo 4 service |
|--|-------|-----------------|
| Dashboard | ❌ CLI | ✅ Homepage đẹp |
| Metrics | ❌ Không | ✅ Netdata real-time |
| External check | ❌ | ✅ Uptime Kuma |
| Threat intel | ❌ | ✅ CrowdSec |
| Telegram alert | ❌ | ✅ |
| RAM | 5MB | 200MB |
| Setup effort | Thấp | Trung bình |
| **Phù hợp** | VPS 2GB | **VPS 4GB+** |
