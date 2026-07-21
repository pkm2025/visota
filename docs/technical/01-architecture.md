# T1 — Tổng quan Kiến trúc

> Kiến trúc kỹ thuật Visota ERP.

## 1. Sơ đồ tổng thể

```
┌──────────────────────────────────────────────────────────────┐
│                       Browser (User)                          │
│              HTMX 2.x + Alpine.js 3.x                         │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                   Reverse Proxy (Nginx)                       │
│   TLS · rate-limit · static files · gzip · HTTP/2            │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                    Django 5.2 LTS App                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Middleware:                                          │   │
│  │  Security → Session → CSRF → Auth → Axes →           │   │
│  │  Tenant → Branding → ModulePermission                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  31 Django Apps:                                      │   │
│  │  core · identity · master_data · ledger · sales ·    │   │
│  │  purchasing · inventory · assets · hr · payroll ·    │   │
│  │  reporting · documents · contracts · input_docs ·    │   │
│  │  recurring · projects · crm · notifications ·        │   │
│  │  approvals · einvoice · banking · guarantees ·       │   │
│  │  loans · bidding · budget · fx · ui_modern           │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬─────────────────────────────────────────┘
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
  ┌─────────┐   ┌──────────┐  ┌────────────┐
  │ MariaDB │   │ django-q │  │  File      │
  │  11.4   │   │ workers  │  │  Storage   │
  │ primary │   │ (4)      │  │ (local/S3) │
  └─────────┘   └──────────┘  └────────────┘
                     │
                     ▼
              ┌─────────────┐
              │ DB-backed   │
              │ cache +     │
              │ sessions    │
              └─────────────┘
```

## 2. Tech stack

| Layer | Tech | Lý do |
|-------|------|-------|
| Backend | **Django 5.2 LTS** | Mature, secure, batteries-included |
| API | **django-ninja** | FastAPI-like trên Django |
| Frontend interactivity | **HTMX 2.x** | Hypermedia — không cần SPA |
| JS framework | **Alpine.js 3.x** | Lightweight state cho dropdowns/modals |
| Database | **MariaDB 11.4** | MySQL-compatible, Aria engine tốt cho read |
| Cache / Session | DB cache | Không cần Redis (Q smaller) |
| Task queue | **django-q2** | ORM-backed, không cần broker |
| PDF | **WeasyPrint** | HTML/CSS → PDF, hỗ trợ tiếng Việt |
| DOCX | **python-docx** | Word export |
| Excel | **openpyxl** | .xlsx native, không phụ thuộc Excel |
| Auth | **AbstractUser + Axes** | Custom User + brute-force protection |
| WSGI/ASGI | **uvicorn** | Production-grade ASGI |
| Reverse proxy | **Nginx** | TLS termination + static |

## 3. Multi-tenant

### Pattern: **shared DB, shared schema**

- Tất cả table kế thừa `CompanyOwnedModel` → có cột `company_id`
- Mọi query tự động filter theo `request.current_company`
- Set bởi `TenantMiddleware` từ `session['current_company_id']`

### Ưu điểm

- 1 DB cho nhiều công ty → dễ quản trị
- Backup/restore đơn giản
- Cross-company reporting dễ

### Trade-off

- Phải cẩn thận query filter (đã handle qua middleware + manager)
- Cần index composite `(company_id, ...)`

## 4. Multi-UI

Hệ thống có nhiều **layout pack** cùng dùng backend:

| Layout | URL prefix | Use case |
|--------|-----------|----------|
| Modern | `/modern/` | Desktop kế toán (mặc định) |
| Classic | `/classic/` | Old-school desktop |
| Mobile | `/mobile/` | Mobile browser |
| Portal | `/portal/` | Self-service cho KH/NCC |

Hiện chỉ Modern được phát triển đầy đủ. Khác là placeholder.

## 5. Domain-Driven Design

Mỗi app là một **bounded context** độc lập:

```
apps/
├── core/             # Công ty, MST, cấu hình thuế
├── identity/         # User, Role, Permission, Auth
├── master_data/      # HTTK, KH, NCC, sản phẩm
├── ledger/           # Phiếu kế toán, sổ cái, kết chuyển
├── sales/            # HĐ bán, Auto-voucher N131/C5111
├── purchasing/       # HĐ mua, Auto-voucher N156/C331
├── inventory/        # Kho, nhập-xuất-tồn
├── assets/           # TSCĐ, khấu hao, thanh lý
├── hr/               # NV, HĐLĐ, phép, BHXH
├── payroll/          # Tính lương, PIT
├── contracts/        # HĐ + biên bản + mẫu HĐ
├── crm/              # Lead/Opp/Ticket/Campaign
├── projects/         # Quản lý dự án
├── documents/        # Attachment universal
├── input_docs/       # Hóa đơn đầu vào (OCR planned)
├── recurring/        # Bút toán định kỳ
├── notifications/    # Inbox + Email
├── approvals/        # Phê duyệt workflow
├── einvoice/         # HĐĐT TT78
├── banking/          # Đối soát ngân hàng
├── guarantees/       # Bảo lãnh BL
├── loans/            # Vay vốn
├── bidding/          # Đấu thầu
├── budget/           # Ngân sách + cash flow
├── fx/               # Tỷ giá + định giá lại
├── ui_modern/        # Modern UI layout pack
└── reporting/        # Báo cáo tài chính
```

### Rule: 1 app = 1 bounded context

- App không import trực tiếp model của app khác → qua service layer
- VD: `apps.sales.services.InvoiceService` thay vì `from apps.ledger.models import ...`

## 6. Single Source of Truth

```
VoucherLine (sự thật duy nhất)
       ↓
AccountPeriodBalance (projection — re-computable)
       ↓
Reports (B01, B02, BCĐTK, VAT)
```

Khi voucher post:
1. Insert `VoucherLine` rows
2. Cập nhật `AccountPeriodBalance` (projection)
3. (Trigger) refresh reports cache

Khi voucher unpost:
1. Trừ lại `AccountPeriodBalance`
2. Voucher về `draft`

## 7. Auto-voucher generation pattern

Mọi business document tự sinh voucher khi `post()`:

```python
class SalesInvoiceService:
    def __init__(self, company):
        self.company = company

    def _post(self, invoice: SalesInvoice) -> AccountingVoucher:
        voucher = AccountingVoucher.objects.create(...)
        # Dr 131 (AR)
        VoucherLine.objects.create(account_code='131', debit_vnd=total, ...)
        # Cr 5111 (Revenue) — per line
        for line in invoice.lines.all():
            VoucherLine.objects.create(account_code='5111',
                                       credit_vnd=line.amount_before_vat, ...)
        # Cr 33311 (VAT output)
        VoucherLine.objects.create(account_code='33311',
                                   credit_vnd=invoice.vat_amount, ...)
        VoucherPostingService().post(voucher)
        return voucher
```

## 8. Permission enforcement

### Layered defense

```
┌─ Layer 1: Middleware (PATH-based) ────────────────┐
│  ModulePermissionMiddleware checks `<module>.access │
│  for every /modern/<path>/ request                 │
└────────────────────────────────────────────────────┘
                       ↓ (pass)
┌─ Layer 2: View mixin ─────────────────────────────┐
│  StaffRequiredMixin for admin views                │
└────────────────────────────────────────────────────┘
                       ↓ (pass)
┌─ Layer 3: Service-level checks ───────────────────┐
│  ApprovalService._notify_next_approver() checks    │
│  role in user_roles                                 │
└────────────────────────────────────────────────────┘
                       ↓
┌─ Layer 4: Template (nav filtering) ───────────────┐
│  {% has_module_access "sales" %} hides sidebar     │
│  items the user can't access                       │
└────────────────────────────────────────────────────┘
```

## 9. Notification system

Mọi event quan trọng → fire notification qua `NotificationService`:

```python
NotificationService.send(
    user=approver,
    type="approval",
    title="Cần phê duyệt phiếu",
    message="...",
    url="/modern/approvals/1/",
)
# Hoặc broadcast:
NotificationService.send_to_role(role_code="accountant", ...)
NotificationService.send_to_superusers(...)
```

Notification được inject vào context processor → render bell icon với unread
count ở mọi trang.

## 10. Async tasks (django-q2)

Task chạy nền không block request:

```python
from django_q.tasks import async_task

# Schedule heavy work
async_task('apps.einvoice.services.call_provider_api', einvoice_id)
```

Use cases:
- Gửi email hàng loạt
- Gọi API e-invoice provider
- Generate báo cáo lớn (B01, BC01 XML)
- Auto-post voucher sau duyệt

## 11. Configuration

### Settings inheritance

```
config/settings/
├── base.py    # Common to all envs
├── dev.py     # Dev (DEBUG=True, console email)
├── test.py    # Test (in-memory DB, no email)
└── prod.py    # Production (DEBUG=False, SMTP, secure cookies)
```

### Secrets

- Dev: plaintext in `.env` (gitignored)
- Prod: Vault / AWS Secrets Manager / `/etc/pmketoan/secrets.env` (root only)

## 12. Logging

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {'class': 'logging.handlers.RotatingFileHandler',
                 'filename': '/var/log/pmketoan/app.log',
                 'maxBytes': 50*1024*1024, 'backupCount': 10},
        'sentry': {'level': 'ERROR', 'class': '...SentryHandler'},
    },
    'loggers': {
        'apps': {'handlers': ['file', 'sentry'], 'level': 'INFO'},
    },
}
```

- INFO: business events (login, voucher post, HĐĐT issue)
- WARNING: anomalies (failed login, balance tolerance exceeded)
- ERROR: exceptions

## 13. Performance considerations

| Pattern | Implementation |
|---------|---------------|
| DB connection pool | `CONN_MAX_AGE=60` (persistent conn) |
| Query optimization | `select_related`, `prefetch_related` |
| Cache | `django.core.cache.backends.db` 5min TTL |
| Pagination | 25-50 items/page default |
| Heavy reports | Async via django-q2 |
| Static files | Nginx serve directly |
| Media files | S3-compatible (Boto3) |

## 14. Scalability

### Vertical (single node)

- 8 cores, 32 GB RAM, SSD
- Tầm 100 users đồng thời, 1M phiếu

### Horizontal (multi-node) — khi cần

- 2-4 app servers + load balancer
- MariaDB primary + 2 replica (read)
- Shared storage (S3)
- Sticky session hoặc shared cache (Redis/Memcached)

Hiện chưa cần horizontal — single node đủ cho 100 users.

---

Tài liệu liên quan:
- [T2-tech-stack](02-tech-stack.md) — Chi tiết dependencies
- [T3-data-model](03-data-model.md) — ERD
- [T4-api](04-api.md) — REST API
- [T5-security](05-security.md) — Bảo mật
- [T6-deployment](06-deployment.md) — Deployment
