# Deploy Visota lên VPS AlmaLinux 10 — hướng dẫn từ con số 0

> Giả định: bạn vừa mua VPS trống (chỉ có OS), chưa có kinh nghiệm deploy.
> Kết thúc: visota.net chạy production, có quản trị được qua web.
> Thời gian: ~45-60 phút (bao gồm build image lần đầu).

---

## Phần 0 — Bạn cần chuẩn bị trước

### 0.1. Mua VPS

Nơi mua uy tín ở Việt Nam / quốc tế:

| Nhà cung cấp | Gói rẻ enough | Ưu điểm |
|--------------|---------------|---------|
| **Viettel IDC** | Cloud VPS 2CPU/4GB ~ 400k/tháng | Server VN, ping thấp |
| **VinaHost** | VPS NVMe 2CPU/4GB ~ 350k/tháng | Hỗ trợ TV |
| **Hetzner Cloud** (Đức) | CX22 (2CPU/4GB) ~ 100k/tháng | Rẻ nhất, chất lượng tốt |
| **DigitalOcean** | Basic 2CPU/4GB ~ 320k/tháng | UI dễ, có SG region |

**Spec khuyến nghị tối thiểu:**
- 2 CPU cores
- 4 GB RAM (2 GB nếu tài chính eo hẹp, nhưng build image chậm)
- 40 GB SSD disk
- 1 IPv4 public
- **OS: AlmaLinux 10** (chọn lúc đặt VPS, không cần cài thủ công)

### 0.2. Mua domain (nếu chưa có)

Mua ở Bit.ly / Mắt Bão / Namecheap ~ 200-300k/năm cho `.net` hoặc `.vn`.

---

## Phần 1 — Truy cập VPS lần đầu

### 1.1. Lấy thông tin từ provider

Sau khi mua, provider gửi email có:
- IP VPS (ví dụ `123.45.67.89`)
- Username: `root`
- Password tạm thời (hoặc SSH key đã upload lúc đăng ký)

### 1.2. Trên máy bạn — kiểm tra có SSH chưa

**Mac/Linux:** mở Terminal, gõ `ssh` enter — nếu ra usage là có.

**Windows 10/11:** mở PowerShell, gõ `ssh` enter — Windows 10+ đã có OpenSSH client sẵn.

### 1.3. Tạo SSH key trên máy bạn (bỏ qua nếu đã có `~/.ssh/id_ed25519.pub`)

```bash
ssh-keygen -t ed25519 -C "visota-admin"
# Enter 3 lần để default (không cần passphrase nếu máy bạn đã có disk encryption)
```

Check đã có key:

```bash
ls ~/.ssh/id_ed25519.pub
# /Users/you/.ssh/id_ed25519.pub  ← có nghĩa OK
```

### 1.4. Copy key lên VPS

Nếu provider có form upload SSH key lúc đăng ký → đã xong, bỏ qua.

Nếu chỉ có password:

```bash
ssh-copy-id root@123.45.67.89
# nhập password tạm từ email
```

Hoặc làm thủ công (nếu `ssh-copy-id` không có):

```bash
cat ~/.ssh/id_ed25519.pub  # copy output
ssh root@123.45.67.89      # login bằng password
# trên VPS:
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo 'PASTE_PUBLIC_KEY_VÀO_ĐÂY' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
exit
```

### 1.5. Test login bằng key (không cần password)

```bash
ssh root@123.45.67.89
# vào luôn, không hỏi password → OK
```

---

## Phần 2 — Trỏ domain về VPS

### 2.1. Lấy IP VPS (đã có từ Part 1).

### 2.2. Vào trang quản lý domain (Bit.ly / Mắt Bão / Cloudflare)

Tạo 2 record DNS kiểu **A**:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `@` | `123.45.67.89` | 600 |
| A | `www` | `123.45.67.89` | 600 |

### 2.3. Đợi DNS propagate (5-30 phút)

Test từ máy bạn:

```bash
# Mac/Linux
dig +short visota.net
# 123.45.67.89  ← phải ra IP VPS bạn

# Windows
nslookup visota.net
```

**Chỉ chạy Part 3 khi `dig` ra đúng IP.** Nếu chạy deploy khi DNS chưa trỏ, Let's Encrypt sẽ fail cấp cert.

---

## Phần 3 — Cài visota-ctl + deps (chạy 1 lần)

### 3.1. SSH vào VPS

```bash
ssh root@123.45.67.89
```

Từ đây mọi lệnh chạy **trên VPS**.

### 3.2. Update OS

```bash
dnf update -y
# chạy 2-5 phút lần đầu
```

### 3.3. Copy script visota-ctl lên VPS

Repo private nên không curl trực tiếp được. Có 2 cách:

**Cách A — scp từ máy bạn** (đơn giản nhất)

Trên máy dev (đã clone repo):

```bash
scp /Users/bạn/path/to/visota/scripts/server/visota-ctl \
    root@123.45.67.89:/usr/local/bin/visota-ctl
```

Rồi trên VPS:

```bash
chmod +x /usr/local/bin/visota-ctl
```

**Cách B — copy-paste qua SSH session**

Nếu không có repo trên máy, mở file trên GitHub (đã login), copy toàn bộ nội dung, rồi:

```bash
ssh root@123.45.67.89
cat > /usr/local/bin/visota-ctl <<'VISOTA-CTL'
# paste nội dung script vào đây
VISOTA-CTL
chmod +x /usr/local/bin/visota-ctl
```

Test:

```bash
visota-ctl help
# in ra:
# visota-ctl v4 — Menu: sudo visota-ctl | CLI: sudo visota-ctl <cmd>
# Commands: install deploy update status containers logs restart backup shell security cleanup minio
```

### 3.4. Chạy install — cài Podman, Traefik, Cockpit, CrowdSec

```bash
visota-ctl install
```

Script sẽ hỏi:

```
Email Let's Encrypt: █  ← nhập email bạn (dùng để nhắc khi cert sắp hết hạn)
Xác nhận? (yes/no): █  ← gõ yes
```

Sau đó script tự động:
- Cài `podman`, `podman-compose`, `cockpit`, `cockpit-podman`, `firewalld`, `crowdsec-firewall-bouncer`, `dnf-automatic` (auto security updates)
- Bật firewalld, mở port 22/80/443/9090
- Tạo docker network `web` (Traefik + các app chia sẻ)
- Khởi động Traefik edge proxy với auto Let's Encrypt
- Bật Cockpit web UI ở port 9090
- Bật CrowdSec (IPS, block IP tấn công)

Mất ~10 phút. Cuối cùng báo: `✓ Done → Menu 2 Deploy`.

---

## Phần 4 — Deploy Visota

### 4.1. Chạy deploy

```bash
visota-ctl deploy visota visota.net
```

(Thay `visota.net` bằng domain bạn.)

Script tự động:
1. Clone code từ GitHub vào `/opt/visota`
2. Gen `.env` với SECRET_KEY + DB password + admin password random
3. Build Docker image (lần đầu 3-5 phút — tải Python packages)
4. Start 3 container: `visota-web`, `visota-worker`, `visota-db`
5. Chạy migrate DB, createcachetable, seed permissions, collectstatic, tạo superuser
6. Traefik auto-issue cert Let's Encrypt cho visota.net

### 4.2. Lưu admin password

Khi xong script in ra:

```
═══ LOGIN ═══
  URL: https://visota.net/
  Admin: admin
  Pass: aBcDeFgHiJkLmNoP
Lưu lại!
```

**Copy password này vào password manager ngay.** Không bao giờ lấy lại được (chỉ reset được).

### 4.3. Truy cập app

Mở browser: **https://visota.net/**

Login `admin` + password vừa lưu.

Nếu browser báo cert chưa trust (thường sau 1-2 phút đầu Let's Encrypt vẫn đang cấp) → đợi 2 phút reload lại.

### 4.4. Truy cập Cockpit (monitor)

Mở: **https://123.45.67.89:9090/** (dùng IP vì chưa trỏ domain cho Cockpit)

Login bằng user `root` + password root VPS (đặt lại nếu chưa có: chạy `passwd` trên VPS).

Cockpit cho xem: CPU/RAM/Disk real-time, log system, quản lý container, terminal web.

---

## Phần 5 — Tự động backup (crontab)

### 5.1. Mở crontab

```bash
crontab -e
```

### 5.2. Thêm dòng (chạy backup 3h sáng mỗi ngày)

```cron
0 3 * * * /usr/local/bin/visota-ctl backup >> /var/log/visota-backup.log 2>&1
```

Lưu lại (vim: `:wq`).

### 5.3. Test backup ngay

```bash
visota-ctl backup
# → tạo file /opt/visota/backups/visota_db_YYYYMMDD_HHMMSS.sql.gz
ls /opt/visota/backups/
```

Backup tự xóa file cũ quá 30 ngày.

---

## Phần 6 — Harden SSH (tắt password login)

Sau khi chắc SSH key login được (Part 1.5), tắt password auth để brute-force không hiệu quả:

```bash
visota-ctl  # menu → 11 (Security) → 3 (SSH harden) → yes
```

Hoặc chạy CLI:

```bash
visota-ctl security
```

---

## Phần 7 — Các thao tác vận hành phổ biến

| Việc | Lệnh |
|------|------|
| Xem status | `visota-ctl status` |
| Xem log web | `visota-ctl logs web` |
| Restart web | `visota-ctl restart web` |
| Backup ngay | `visota-ctl backup` |
| Restore DB | `visota-ctl` → menu 8 |
| Django shell | `visota-ctl shell web` |
| Migrate sau đổi code | `visota-ctl update` (pull code + rebuild + migrate) |
| Audit security | `visota-ctl security` |
| Cleanup disk | `visota-ctl cleanup` |
| Xem .env | `visota-ctl` → menu 14 → 3 |

Hoặc gọi `visota-ctl` không có arg để vào menu tương tác.

---

## Phần 8 — Khi có sự cố

### 8.1. Không vào được https://visota.net

```bash
# Kiểm tra container có chạy không
visota-ctl status

# Nếu visota-web không có "healthy" → xem log
visota-ctl logs web

# Phổ biến nhất:
# - DB chưa healthy → đợi thêm 30s
# - Domain chưa trỏ DNS → dig +short visota.net phải ra IP VPS
# - Let's Encrypt rate limit → đợi 1h
```

### 8.2. Quên admin password

```bash
visota-ctl shell web
# Trong Python prompt:
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(username='admin')
u.set_password('new_password_here')
u.save()
exit()
```

### 8.3. Disk full

```bash
df -h /
# Nếu / dùng > 85%:
visota-ctl cleanup
# Xóa image/volume/container thừa
```

### 8.4. Restore từ backup

```bash
visota-ctl  # menu → 8 (Restore) → chọn file → gõ 'RESTORE' để xác nhận
```

---

## Phần 9 — Optional: deploy thêm apps

Sau khi Visota chạy ổn, có thể add thêm:

```bash
# Metabase — BI / dashboard
visota-ctl deploy metabase analytics.visota.net

# n8n — workflow automation
visota-ctl deploy n8n flow.visota.net
```

Mỗi app một domain riêng, Traefik route tự động.

---

## TL;DR — cheat sheet

```bash
# 0. Trên máy bạn — scp script lên VPS (repo private, không curl được)
scp scripts/server/visota-ctl root@IP_VPS:/usr/local/bin/

# 1. SSH vào VPS
ssh root@IP_VPS
chmod +x /usr/local/bin/visota-ctl

# 2. Update OS
dnf update -y

# 3. Cài deps (Podman/Traefik/Cockpit/CrowdSec/Git/SSH key)
visota-ctl install
# → in ra SSH deploy key, dán vào github.com/pkm2025/visota/settings/keys

# 4. Deploy (DNS phải đã trỏ domain)
visota-ctl deploy visota visota.net

# 5. Lưu admin password script in ra
# 6. Mở https://visota.net/ → login admin + pass
```
