# Visota Observability Stack — Lean Edition

## Combo: CrowdSec + Beszel + Homepage

**Total: ~100MB RAM, <1% CPU** — nhẹ nhất có thể.

```
                ┌──────────────────────────────────┐
                │     Homepage (panel.visota.net)   │
                │      Single Pane of Glass UI      │
                └──────┬───────────┬────────────────┘
                       │           │
              ┌────────┘           └────────┐
              ▼                             ▼
    ┌─────────────────┐          ┌──────────────────┐
    │ CrowdSec (~30MB)│          │ Beszel (~30MB)   │
    │ IPS + blocklist │          │ Metrics + alerts │
    │                 │          │                  │
    │ Block bad IPs   │          │ CPU/RAM/Disk/    │
    │ at kernel level │          │ Docker stats     │
    │                 │          │ Historical data  │
    │ Reads Traefik   │          │ Web alerts       │
    │ access logs     │          │ (Telegram/webhook)│
    └─────────────────┘          └──────────────────┘
              │                             │
              ▼                             ▼
    ┌─────────────────┐          ┌──────────────────┐
    │ firewalld       │          │ Beszel Agent     │
    │ (iptables drop) │          │ (~10MB, Go binary)│
    └─────────────────┘          │ /proc + Docker   │
                                 └──────────────────┘
```

## Deploy

```bash
sudo visota-ctl deploy observability
```

## Setup sau deploy

### 1. Beszel — thêm server monitor

```bash
# Lấy agent key từ hub (chạy 1 lần sau khi container up)
docker exec beszel /beszel cli add-sys

# Output sẽ hiện key dạng: ssh-ed25519 AAAA...
# Copy key → set vào .env:
echo "BESZEL_AGENT_KEY=ssh-ed25519 AAAA..." >> /opt/visota/.env

# Restart agent
cd /opt/visota && docker compose -f docker/observability/docker-compose.observability.yml restart beszel-agent
```

Verify: `https://metrics.visota.net` → Beszel UI hiện CPU/RAM/Disk real-time.

### 2. Beszel — setup alerts (Telegram)

Trong Beszel UI → Settings → Notifications:
- Webhook URL: `https://api.telegram.org/bot<TOKEN>/sendMessage`
- Method: POST
- Body:
```json
{
  "chat_id": "<CHAT_ID>",
  "text": "🚨 {{.system.name }}: {{ .title }}"
}
```

### 3. Beszel — health check cho Visota

Trong Beszel UI → Systems → Edit → HTTP Checks:
```
URL: https://visota.net/health/
Expected: 200
Interval: 60s
```

### 4. Homepage config

Edit: `docker/observability/homepage-config/services.yaml`
- Thay `${DOMAIN}` bằng domain thật
- Restart: `docker restart homepage`

### 5. CrowdSec

Bouncer (block IPs via firewalld):
```bash
sudo bash /opt/visota/docker/crowdsec/install-crowdsec.sh
```

Check:
```bash
docker exec crowdsec cscli decisions list   # IPs đang bị block
docker exec crowdsec cscli metrics          # số tấn công đã chặn
```

## DNS Records

| Subdomain | Service |
|-----------|---------|
| `panel.visota.net` | Homepage dashboard |
| `metrics.visota.net` | Beszel metrics |
| `visota.net` | Visota ERP app |

## So sánh: combo cũ vs combo mới

| | Cũ (Netdata + Kuma) | Mới (Beszel only) |
|--|---------------------|-------------------|
| RAM | 200-620MB | **~100MB** |
| CPU | 2-5% | **<1%** |
| Uptime check | Uptime Kuma (50MB) | Beszel HTTP check (0MB extra) |
| Metrics | Netdata (150-500MB) | Beszel (~30MB) |
| Alerts | Uptime Kuma | Beszel (webhook/Telegram) |
| Services | 4 containers | **3 containers** |
| Dashboard | Homepage | Homepage |

**Tiết kiệm: 100-520MB RAM + bỏ 1 container.**
