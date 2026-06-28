# Deploy Visota lên VPS AlmaLinux 10

> Server trắng → visota.net chạy production. ~15 phút.
> Stack: Podman + Traefik + Cockpit + CrowdSec.

## 1. Yêu cầu VPS

| Spec | Tối thiểu | Khuyến nghị |
|------|----------|-------------|
| OS | AlmaLinux 10 | AlmaLinux 10 |
| RAM | 2 GB | 4 GB |
| CPU | 1 core | 2 cores |
| Disk | 20 GB SSD | 50 GB SSD |
| Domain | 1 cái | 1 cái |

Port mở: 22 (SSH), 80/443 (web), 9090 (Cockpit — optional, có thể giới hạn IP).

## 2. Cài script

```bash
# Tải script từ repo
sudo curl -o /usr/local/bin/visota-ctl \
  https://raw.githubusercontent.com/pkm2025/visota/main/scripts/server/visota-ctl
sudo chmod +x /usr/local/bin/visota-ctl

# Chạy install — cài podman-compose, Traefik, Cockpit, CrowdSec, firewalld
sudo visota-ctl install
# → hỏi email Let's Encrypt, gõ yes để xác nhận
```

## 3. Deploy Visota

```bash
# DNS visota.net → IP VPS trước khi chạy
sudo visota-ctl deploy visota visota.net
```

Script tự:
1. Clone code vào `/opt/visota`
2. Gen `.env` (SECRET_KEY, DB password, admin password)
3. Build image (3-5 phút)
4. Khởi động web + worker + db
5. Chạy migrate + collectstatic + tạo superuser
6. Traefik auto-issue cert Let's Encrypt

Output cuối in ra **admin password** — lưu lại.

## 4. Truy cập

| URL | What |
|-----|------|
| `https://visota.net/` | App — login `admin` + password từ script |
| `https://visota.net/modern/` | Dashboard |
| `https://server-ip:9090/` | Cockpit — monitor + container UI (login bằng user OS) |

## 5. Các thao tác sau deploy

```bash
sudo visota-ctl                  # Menu tương tác
sudo visota-ctl status           # Xem container + tài nguyên
sudo visota-ctl backup           # Backup DB + media → /opt/visota/backups
sudo visota-ctl security         # Audit firewalld/CrowdSec/disk
sudo visota-ctl help             # Toàn bộ CLI
```

## 6. Optionally deploy thêm apps

```bash
sudo visota-ctl deploy metabase analytics.visota.net
sudo visota-ctl deploy n8n flow.visota.net
```

## 7. Troubleshooting

| Triệu chứng | Fix |
|-------------|-----|
| Traefik 502 Bad Gateway | `visota-ctl logs web` xem lỗi, thường DB chưa healthy |
| Let's Encrypt rate limit | Đợi 1h hoặc đổi sang staging (edit traefik.yml) |
| Disk full | `visota-ctl cleanup` xóa image/volume thừa |
| Quên admin password | `visota-ctl shell web` → `python manage.py changepassword admin` |

## Backup schedule

Thêm vào crontab root:
```cron
0 3 * * * /usr/local/bin/visota-ctl backup >> /var/log/visota-backup.log 2>&1
```

Backup tự xóa file cũ >30 ngày.
