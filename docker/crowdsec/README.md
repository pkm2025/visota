# CrowdSec Setup Guide — Visota + AlmaLinux 10

## Tổng quan

CrowdSec = fail2ban thế hệ mới:
- **Block trước tấn công** — community blocklist từ hàng triệu server toàn cầu
- **Đọc Traefik logs** — phát hiện SQLi, XSS, CVE, brute-force web (fail2ban chỉ SSH)
- **~15-30MB RAM** — gần như 0 CPU impact
- **Free** — mã nguồn mở, community blocklist miễn phí

## Kiến trúc

```
Internet → CrowdSec Bouncer (firewalld/iptables)
              ↓ (block bad IPs tại kernel)
         Traefik (SSL + routing)
              ↓
              ├→ Traefik access.log → CrowdSec Agent (phân tích)
              ├→ /var/log/auth.log  → CrowdSec Agent (SSH)
              │
         Visota (Django + WhiteNoise)
```

## Cài đặt (qua visota-ctl hoặc thủ công)

### Bước 1: Deploy CrowdSec container

```bash
# Via visota-ctl
sudo visota-ctl
> 2 (Deploy)
> 6 (CrowdSec)

# Hoặc thủ công
cd /opt/crowdsec
docker compose -f /opt/visota/docker/crowdsec/docker-compose.crowdsec.yml up -d
```

### Bước 2: Cài bouncer trên host

```bash
sudo bash /opt/visota/docker/crowdsec/install-crowdsec.sh
```

### Bước 3: Tắt fail2ban (nếu đang dùng)

```bash
sudo systemctl stop fail2ban
sudo systemctl disable fail2ban
```

### Bước 4: Đăng ký console (tùy chọn — dashboard)

```bash
# Lấy enrollment token từ https://app.crowdsec.net
docker exec crowdsec cscli console enroll <your-token>
```

## Quản lý

```bash
# Xem IPs đang bị block
docker exec crowdsec cscli decisions list

# Xem metrics (số tấn công đã chặn)
docker exec crowdsec cscli metrics

# Xem alerts
docker exec crowdsec cscli alerts list

# Block thủ công 1 IP
docker exec crowdsec cscli decisions add 1.2.3.4

# Unblock 1 IP
docker exec crowdsec cscli decisions delete 1.2.3.4

# Cập nhật collections
docker exec crowdsec cscli hub update
docker exec crowdsec cscli hub upgrade

# Xem bouncer status
systemctl status crowdsec-firewall-bouncer

# Xem log bouncer
journalctl -u crowdsec-firewall-bouncer -f
```

## Collections đã cài sẵn

| Collection | Chống |
|-----------|-------|
| `crowdsecurity/traefik` | Đọc Traefik access logs |
| `crowdsecurity/http-cve` | CVE exploits (Log4Shell, Spring4Shell...) |
| `crowdsecurity/whitelist-good-actors` | Không block Google/Cloudflare/AWS |

Thêm collection:
```bash
docker exec crowdsec cscli collections install crowdsecurity/nginx-bf
docker exec crowdsec cscli collections install crowdsecurity/http-backdoors-attempt
```

## So sánh resource

| | fail2ban | CrowdSec |
|--|---------|----------|
| RAM | 10MB | 15-30MB |
| CPU | ~0 | ~0 (Go, non-blocking) |
| Phát hiện | SSH only | SSH + Web + CVE + Community |
| Preemptive block | ❌ | ✅ (community blocklist) |
| Dashboard | ❌ | ✅ (console.crowdsec.net) |
| Traefik integration | ❌ | ✅ native |
| Docker | Host only | Container + Host |

## Khuyến nghị

**Dùng CrowdSec** khi:
- VPS expose ra internet (80/443)
- Có Traefik reverse proxy
- Muốn block IP xấu toàn cầu trước khi tấn công

**Giữ fail2ban** khi:
- VPS chỉ internal / VPN
- Không cần web attack detection
- Muốn tối giản (1 package, 0 container)
