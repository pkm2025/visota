# R7 — Khôi phục sự cố (Troubleshooting)

> Các lỗi thường gặp và cách xử lý.

## Cấp độ nghiêm trọng

| Severity | Định nghĩa | SLA |
|----------|-----------|-----|
| **P0** | Hệ thống không truy cập được / mất dữ liệu | 30 phút |
| **P1** | Chức năng chính không dùng được (login, post voucher, HĐĐT) | 2 giờ |
| **P2** | Bug không block workflow | 1 ngày |
| **P3** | UX issue / cosmetic | 1 tuần |

## Quy trình xử lý

1. **Xác định severity** → nếu P0/P1, gọi oncall ngay
2. **Reproduce** — xác nhận lỗi tái diễn được không
3. **Tìm workaround** tạm thời
4. **Root cause** — đọc log, trace stack
5. **Fix** — code patch hoặc config change
6. **Verify** — test fix + add regression test
7. **Postmortem** (P0/P1) — sau 48 giờ

## Các lỗi thường gặp

### 1. Không đăng nhập được

**Triệu chứng**: nhập đúng pass nhưng vẫn về trang login.

**Check**:

```bash
# 1. User active?
sudo -u pmketoan python manage.py shell -c "
from apps.identity.models import User
u = User.objects.get(username='xxx')
print(f'active={u.is_active}, last_login={u.last_login}, failed_count={u.failed_login_count}')
"

# 2. Axes lockout?
sudo -u pmketoan python manage.py axes_list
sudo -u pmketoan python manage.py axes_reset username

# 3. Session expired?
# → user login lại

# 4. DB up?
sudo systemctl status mariadb
```

### 2. Trang trắng / 500 error

**Check**:

```bash
# 1. Sentry (nếu có)
# → check error dashboard

# 2. App log
sudo tail -100 /var/log/pmketoan/app.log | grep -A20 ERROR

# 3. Gunicorn log
sudo tail -100 /var/log/pmketoan/gunicorn.error.log

# 4. Reproduce
curl -v https://erp.pkm.vn/<broken-path>

# 5. Common causes:
#    - Template missing {% load humanize %}
#    - Field type mismatch (Decimal vs float)
#    - Migration not applied
sudo -u pmketoan python manage.py showmigrations | grep -v '\[X\]'
sudo -u pmketoan python manage.py migrate
```

### 3. Voucher không cân đối (Nợ ≠ Có)

**Triệu chứng**: Tạo phiếu bị báo lỗi "Không cân đối".

**Check**:

```bash
# Find the unbalanced voucher
python manage.py shell <<'EOF'
from apps.ledger.models import AccountingVoucher
from decimal import Decimal
for v in AccountingVoucher.objects.filter(status=0):
    d = sum((l.debit_vnd or 0 for l in v.lines.all()), Decimal('0'))
    c = sum((l.credit_vnd or 0 for l in v.lines.all()), Decimal('0'))
    if abs(d - c) > Decimal('0.01'):
        print(f'UNBALANCED #{v.id} {v.voucher_no}: Dr={d} Cr={c} diff={d-c}')
EOF
```

**Fix**: Edit phiếu → thêm/bớt dòng để cân → Save.

### 4. BCĐTK không cân

**Triệu chứng**: Tổng PS Nợ ≠ Tổng PS Có trong Bảng CĐTK.

**Cause**:

1. **Có phiếu chưa post** (`status=draft`)
   - Fix: post tất cả hoặc xóa draft

2. **KC kỳ chưa chạy** (TK 911 có balance)
   - Fix: chạy KC lại

3. **Có phiếu post nhưng balance projection lỗi**
   - Fix: rebuild projection:

```python
from apps.ledger.models import AccountPeriodBalance
AccountPeriodBalance.objects.all().delete()
# Then re-post all vouchers (or run service)
```

4. **Có phiếu sai kỳ** (voucher_date kỳ khác vs period/fiscal_year)
   - Fix: edit phiếu, sửa period

### 5. HĐĐT không phát hành được

**Triệu chứng**: Bấm "Phát hành" nhưng status vẫn `draft`.

**Check**:

```bash
# 1. EInvoiceConfig có active?
python manage.py shell -c "
from apps.einvoice.models import EInvoiceConfig
print(EInvoiceConfig.objects.filter(is_active=True).count())
"

# 2. Provider API lỗi?
# → xem EInvoice.error_message

# 3. Manual mode?
# → user phải upload PDF thủ công sau khi publish
```

**Fix**: Nếu provider thật báo lỗi, switch sang manual mode tạm:

```python
from apps.einvoice.models import EInvoiceConfig
config = EInvoiceConfig.objects.first()
config.provider = 'manual'
config.save()
```

### 6. Performance chậm

**Triệu chứng**: Trang load > 5 giây.

**Check**:

```bash
# 1. DB slow queries
sudo mysql -e "SHOW PROCESSLIST;"
sudo tail -f /var/log/mysql/slow.log

# 2. Django debug toolbar (dev only)
# → check query count per page

# 3. Connection pool full?
sudo mysql -e "SHOW STATUS LIKE 'Threads_connected';"

# 4. Memory?
free -h

# 5. Disk full?
df -h
```

**Fix**:

- Index missing: thêm `db_index=True` hoặc composite index
- N+1 query: thêm `select_related`/`prefetch_related`
- Cache miss: tăng TTL hoặc invalidate properly
- Heavy report: chuyển sang async (django-q2)

### 7. Email không gửi được

**Check**:

```bash
# 1. SMTP credentials đúng?
python manage.py shell -c "
from django.core.mail import send_mail
send_mail('test', 'body', 'noreply@pkm.vn', ['test@example.com'])
"

# 2. EmailLog status?
python manage.py shell -c "
from apps.notifications.models import EmailLog
for log in EmailLog.objects.filter(status='failed')[:5]:
    print(f'{log.subject} → {log.to_emails} | {log.error_message[:100]}')
"

# 3. SMTP server reachable?
telnet smtp.gmail.com 587
```

### 8. Task queue stuck

**Triệu chứng**: Async task không chạy (VD: HĐĐT auto-issue không xảy ra).

**Check**:

```bash
# 1. Worker running?
sudo systemctl status pmketoan-worker

# 2. Failed tasks?
python manage.py shell -c "
from django_q.models import Failure
for f in Failure.objects.all()[:10]:
    print(f'{f.name}: {f.func}: {f.result[:100]}')
"

# 3. Stuck tasks?
python manage.py monitor  # TUI
```

**Fix**:

```bash
# Restart worker
sudo systemctl restart pmketoan-worker

# Clear failed
python manage.py shell -c "
from django_q.models import Failure
Failure.objects.all().delete()
"
```

### 9. File upload fail

**Triệu chứng**: Upload PDF báo lỗi.

**Check**:

```bash
# 1. File too big? (default 10 MB)
# → check MEDIA_MAX_SIZE in settings

# 2. Disk full?
df -h /var/lib/pmketoan/media

# 3. Permission?
ls -ld /var/lib/pmketoan/media

# 4. MIME type không cho phép?
# → check ALLOWED_UPLOAD_MIMES
```

### 10. Browser cache gây bug

**Triệu chứng**: Sửa CSS/JS nhưng vẫn thấy cũ.

**Fix**:
- Hard refresh: Ctrl+Shift+R (Win) / Cmd+Shift+R (Mac)
- Hoặc Settings → Clear cache
- Hoặc run `python manage.py collectstatic --clear`

## Khôi phục dữ liệu

### Xóa nhầm 1 phiếu

**Trong vòng 24h**:

```bash
# Find in binlog
mysqlbinlog --start-datetime="..." /var/lib/mysql/mysql-bin.001234 \
  | grep -A5 "DELETE FROM voucher_line WHERE id=123"
```

Restore record.

**Sau 24h**:

- Restore từ backup đêm qua sang DB riêng
- Export phiếu + lines
- Import lại production

### Xóa nhầm nhiều data (P0)

**Stop app ngay**:

```bash
sudo systemctl stop pmketoan
```

**Restore from backup** (xem [A5-backup-restore](../admin-guide/05-backup-restore.md)):

```bash
gunzip -c /var/backups/pmketoan/db_20260623_020000.sql.gz | \
  mysql -u pmk -p pmketoan_prod
```

**Notify stakeholders** — mất dữ liệu từ thời điểm backup đến thời điểm restore.

## Liên hệ hỗ trợ

| Cấp độ | Liên hệ |
|--------|---------|
| Bug kỹ thuật | `#erp-engineering` Slack |
| Vấn đề nghiệp vụ | `#erp-support` Slack |
| P0 sau giờ hành chính | Oncall (Lark +1) |
| Đề xuất tính năng | `erp-feedback@pkm.vn` |

## Postmortem template (P0/P1)

```markdown
# Postmortem: <incident name>

**Date**: YYYY-MM-DD
**Severity**: P0/P1
**Duration**: X hours
**Impact**: <users affected, data loss, etc>

## Timeline
- HH:MM — Detected by <monitoring/user>
- HH:MM — Oncall engaged
- HH:MM — Root cause identified
- HH:MM — Fix deployed
- HH:MM — Verified resolved

## Root cause
<technical explanation>

## What went well
- ...

## What went wrong
- ...

## Action items
- [ ] <action> (owner, due date)
- [ ] ...
```

---

Tài liệu liên quan:
- [A5-backup-restore](../admin-guide/05-backup-restore.md) — Backup/restore
- [T6-deployment](../technical/06-deployment.md) — Deployment
