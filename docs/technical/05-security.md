# T5 — Bảo mật & Phân quyền

> Mô hình bảo mật, hardening checklist, OWASP top 10.

## 1. Multi-layer security

```
┌─ Network ────────────┐
│  Firewall, VPC, DDoS │
└──────────┬───────────┘
           ▼
┌─ TLS / HTTPS ────────┐
│  TLS 1.2+, HSTS       │
└──────────┬───────────┘
           ▼
┌─ Application ────────┐
│  AuthN → AuthZ        │
│  CSRF, XSS, SQLi      │
└──────────┬───────────┘
           ▼
┌─ Module permission ──┐
│  Middleware + Mixin   │
└──────────┬───────────┘
           ▼
┌─ Row-level filter ───┐
│  CompanyOwnedManager  │
└──────────┬───────────┘
           ▼
┌─ Audit trail ────────┐
│  Logging + monitoring │
└──────────────────────┘
```

## 2. Authentication

### Backend

```python
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'apps.identity.backends.RoleBasedBackend',  # username or email
    'django.contrib.auth.backends.ModelBackend',
]
```

### Password policy

- Minimum 8 chars (per `AUTH_PASSWORD_VALIDATORS`)
- Common password check
- Numeric password check
- Similarity check

### Brute-force protection

Axes middleware:
- Lock account after 5 failed attempts
- Cool-off period: 1 hour
- IP-based + username-based lockout

```python
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_RESET_ON_SUCCESS = True
```

### Session

```python
SESSION_COOKIE_AGE = 8 * 3600  # 8 hours
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
```

### 2FA (planned)

Field `User.two_factor_enabled` đã có. Cần:
- `django-otp` hoặc `django-two-factor-auth`
- TOTP setup (Google Authenticator)
- Backup codes

## 3. Authorization (RBAC)

4-layer defense (xem [T1-architecture](01-architecture.md#8-permission-enforcement)):

1. **Middleware**: PATH-based module check
2. **View Mixin**: staff/superuser check
3. **Service**: action-level (approve/submit) check
4. **Template**: nav filter

### Permission catalog

25 modules × `<module>.access`:

```python
# apps/identity/management/commands/seed_permissions.py
MODULE_PERMISSIONS = [
    ('ledger', '...'),
    ('sales', '...'),
    ...
]
```

### Role catalog

8 system roles per company:

| Role | Số module |
|------|-----------|
| admin | 25 (full) |
| chief_accountant | 25 (full) |
| accountant | 19 |
| sales | 9 |
| project_manager | 7 |
| purchaser | 6 |
| hr_officer | 6 |
| viewer | 3 |

Custom roles có thể tạo (chưa có UI).

### Multi-tenant isolation

`CompanyOwnedManager` auto-filter:

```python
class CompanyOwnedManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self, '_current_company') and self._current_company:
            return qs.filter(company=self._current_company)
        return qs
```

Middleware set `_current_company` per request.

## 4. OWASP Top 10 mitigation

### A01 - Broken Access Control ✓

- Middleware kiểm `<module>.access`
- Mixin `StaffRequiredMixin` cho admin
- `CompanyOwnedManager` multi-tenant isolation
- Test `tests/test_module_permissions.py` (11 tests)

### A02 - Cryptographic Failures

- TLS 1.2+ only
- AES-256 cho backup encryption
- Bcrypt cho password (Django default)
- API tokens: 256-bit random

**Cần thêm**:
- Field-level encryption cho PII (CCCD, MST)
- Vault cho secrets (hiện để trong env file)

### A03 - Injection ✓

- Django ORM → SQL injection không thể
- Template auto-escape → XSS không thể
- Form validation mọi input

### A04 - Insecure Design

- Defense in depth (4-layer)
- Fail-secure (default deny)
- Audit log mọi action nhạy cảm

### A05 - Security Misconfiguration ✓

- `DEBUG=False` in prod
- `SECURE_HSTS_*` headers
- Allowed hosts explicit
- Secrets trong env, không hardcode

```bash
python manage.py check --deploy
```

### A06 - Vulnerable Components

```bash
# Check for known vulns
pip install safety
safety check

# Update regularly
pip list --outdated
```

### A07 - Auth Failures ✓

- Axes brute-force protection
- Password policy enforced
- Session timeout
- Logout invalidates session

### A08 - Software/Data Integrity

- Subresource Integrity (SRI) for static files (planned)
- Signed cookies (Django default)
- Signed URLs for password reset

### A09 - Logging/Monitoring Failures

- Sentry error tracking
- Log every login/logout
- Log every voucher post
- Log every role/permission change

**Cần thêm**:
- Audit log table (planned: django-auditlog)
- SIEM integration

### A10 - SSRF

- Validate external URL (e-invoice callback, webhook)
- Whitelist allowed hosts for outgoing HTTP

## 5. CSRF / XSS / Clickjacking

### CSRF

```python
MIDDLEWARE += ['django.middleware.csrf.CsrfViewMiddleware']
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
```

Mọi POST phải có `{% csrf_token %}`.

### XSS

Django template auto-escape by default. Cho user-input hiển thị HTML:
- Use `|safe` filter với caution
- Sanitize HTML qua `bleach` library

### Clickjacking

```python
X_FRAME_OPTIONS = 'DENY'
MIDDLEWARE += ['django.middleware.clickjacking.XFrameOptionsMiddleware']
```

## 6. SQL injection

Django ORM ngăn chặn tự động. **Cấm**:
- `raw()` queries với user input
- `extra()` với user input

Nếu cần raw SQL: dùng parameterized:

```python
# GOOD
MyModel.objects.raw('SELECT * FROM x WHERE id = %s', [user_id])

# BAD — SQL injection
MyModel.objects.raw(f'SELECT * FROM x WHERE id = {user_id}')
```

## 7. File upload security

```python
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_UPLOAD_MIMES = [
    'application/pdf',
    'image/jpeg', 'image/png',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

# Scan virus (planned): ClamAV
```

Validate file extension AND content type (not just extension).

## 8. Data retention

| Loại | Lưu | Lý do |
|------|-----|-------|
| User records | Forever | Audit |
| Accounting vouchers | 10 năm | Luật KT 2015 |
| HĐĐT XML/PDF | 10 năm | TT78/2021 |
| Logs | 90 ngày | Performance |
| Backup | 30 ngày daily + 12 tháng monthly + 10 năm yearly | DR + compliance |
| Failed login | 30 ngày | Axes |

## 9. Privacy (PII)

Dữ liệu nhạy cảm:
- MST cá nhân
- CCCD
- Số BHXH
- Lương
- Thông tin sức khỏe (nghỉ ốm, thai sản)

**Bảo vệ**:
- Access control (chỉ HR role xem lương)
- Log access
- Encrypt at-rest (planned)
- Mask in display (`****1234`)

## 10. Audit log

### Hiện tại

- Login/logout: tracked qua Axes
- Voucher post/unpost: tracked qua `created_by`, `updated_at`
- Email sent: `EmailLog`
- Notification: `Notification`

### Cần thêm (planned)

- `django-auditlog` hoặc `django-simple-history`
- Track mọi create/update/delete
- Diff old vs new
- Track IP + user agent

## 11. Security checklist (pre-prod)

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` random 50+ chars
- [ ] `ALLOWED_HOSTS` explicit
- [ ] HTTPS only (TLS 1.2+)
- [ ] HSTS header
- [ ] CSP header
- [ ] X-Frame-Options: DENY
- [ ] X-Content-Type-Options: nosniff
- [ ] Secure cookies
- [ ] Axes enabled
- [ ] Backup encrypted
- [ ] Sentry configured
- [ ] fail2ban SSH
- [ ] Firewall rules
- [ ] `python manage.py check --deploy` pass

## 12. Penetration testing

Khuyến nghị thực hiện hàng năm bởi firm thứ 3:
- OWASP ZAP automated scan
- Manual penetration test
- Source code review

## 13. Incident response

### Severity

| Level | Definition | SLA |
|-------|-----------|-----|
| P0 | Data breach, hệ thống sập | 1 giờ |
| P1 | Security hole (XSS, SQLi) | 4 giờ |
| P2 | Phishing, brute-force detected | 1 ngày |

### Khi có incident

1. **Contain** — block IP, disable account
2. **Investigate** — read logs, find scope
3. **Notify** — stakeholders + CQT if data breach
4. **Fix** — patch + add detection
5. **Postmortem** — root cause + prevention

## 14. Compliance

### Luật Kế toán 2015

- Lưu sổ kế toán ≥ 10 năm ✓
- Bảo mật thông tin kế toán ✓

### Nghị định 13/2023 (Bảo vệ dữ liệu cá nhân)

- Consent cho data processing
- Right to access / delete
- DPO appointment (planned)

### Luật An ninh mạng 2018

- Báo incident cho Bộ TTTT trong 24h
- Lưu log ≥ 90 ngày

---

Tài liệu liên quan:
- [A1-users-roles](../admin-guide/01-users-roles.md) — Quản trị RBAC
- [T6-deployment](06-deployment.md) — Deployment security
- [07-troubleshooting](../runbook/07-troubleshooting.md) — Incident response
