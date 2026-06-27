# Visota Monitor — mon.visota.net

1 URL duy nhất. Tất cả monitoring trên 1 trang.

```
mon.visota.net → Homepage
                    │
        ┌───────────┼───────────┐
        │           │           │
   Beszel Stats  CrowdSec    Docker Stats
   (CPU/RAM/Disk) (Blocked IPs) (Containers)
   (iframe + API)  (widget)    (widget)
        │
   Links → Visota admin / Portainer / Traefik
```

**3 containers, ~100MB RAM, 1 subdomain.**

## Deploy

```bash
# DNS: mon.visota.net → VPS IP
sudo visota-ctl deploy observability
```

## Setup sau deploy

### 1. Beszel — kết nối agent

```bash
# Get agent key
docker exec beszel /beszel cli add-sys
# Copy the ssh-ed25519 key

# Set in .env
echo "BESZEL_AGENT_KEY=ssh-ed25519 AAAA..." >> /opt/visota/.env

# Restart agent
docker compose -f /opt/visota/docker/observability/docker-compose.observability.yml restart beszel-agent
```

### 2. Homepage widgets

Truy cập `https://mon.visota.net`:
- Docker stats: tự động hiển thị (Homepage đọc Docker API)
- Beszel: widget hiển thị CPU/RAM/Disk %
- CrowdSec: widget hiển thị số IP blocked

Edit config: `docker/observability/homepage-config/services.yaml`

### 3. CrowdSec — tạo API user cho widget

```bash
docker exec crowdsec cscli bouncers add homepage -o raw
# Copy API token → set in Homepage config
```

### 4. Beszel alerts (Telegram)

Trong Beszel UI (qua Homepage link): Settings → Notifications → Telegram webhook.

## DNS

| Domain | Point to |
|--------|----------|
| `mon.visota.net` | VPS IP (chỉ Homepage) |
| `visota.net` | VPS IP (app chính) |

**Không cần** metrics/status/docker subdomains.
