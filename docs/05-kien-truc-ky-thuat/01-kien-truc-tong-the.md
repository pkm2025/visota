# 01. Kiến trúc tổng thể

## 1. Sơ đồ kiến trúc tổng thể

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                              │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │
│  │   HTML (Django │  │     HTMX       │  │   Alpine.js    │         │
│  │   templates)   │  │  (ax-* attrs)  │  │  (x-data reactivity)│    │
│  └────────────────┘  └────────────────┘  └────────────────┘         │
│                                                                      │
│  ┌────────────────────────────────────────────────────────┐         │
│  │   Bootstrap 5 / TailwindCSS (CSS framework)            │         │
│  └────────────────────────────────────────────────────────┘         │
│  ┌────────────────────────────────────────────────────────┐         │
│  │   Tabulator / Grid.js (data grid, thay DevExpress)     │         │
│  └────────────────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────────────────┘
                                  │ HTTPS
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│                       REVERSE PROXY (Nginx/Caddy)                    │
│                                                                      │
│  - TLS termination                                                   │
│  - Static files (CSS/JS/images)                                      │
│  - Rate limiting                                                     │
│  - Gzip compression                                                  │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│                    DJANGO APPLICATION SERVER                         │
│                    (gunicorn, 4-8 workers)                           │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  Django 5.2 LTS (MTV framework)                          │        │
│  └─────────────────────────────────────────────────────────┘        │
│                                  │                                   │
│         ┌────────────────────────┴───────────────────────┐           │
│         ↓                                                ↓           │
│  ┌──────────────────┐                          ┌─────────────────┐   │
│  │  django-ninja    │                          │  Django Views   │   │
│  │  (REST API +     │                          │  (HTML rendering│   │
│  │   OpenAPI)       │                          │   for HTMX)     │   │
│  └──────────────────┘                          └─────────────────┘   │
│         │                                                │           │
│         ↓                                                ↓           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Domain Services Layer (business logic, framework-agnostic)  │   │
│  │                                                              │   │
│  │  - VoucherService (post voucher)                            │   │
│  │  - InventoryCostCalculator                                   │   │
│  │  - DepreciationCalculator                                    │   │
│  │  - PeriodCloser                                              │   │
│  │  - FinancialReportGenerator                                  │   │
│  │  - YearEndCarryForwarder                                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                  │                                   │
│                                  ↓                                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Django ORM (Models)  +  Django DB cache  +  django-q2 ORM   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│                  MariaDB 11.4 LTS                                    │
│    - Business data (multi-tenant: company_id)                        │
│    - Cache tables (Django DB cache backend)                          │
│    - Sessions (cached_db engine)                                     │
│    - django-q2 broker (django_q2_ororm, _task, _schedule)            │
│    - Partitioned tables (voucher_line, attendance_record, ...)       │
└──────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ (đọc task queue)
                                  │
┌──────────────────────────────────────────────────────────────────────┐
│                django-q2 cluster (separate systemd unit)             │
│                  python manage.py qcluster                           │
│                                                                      │
│   - Period closing (async)                                           │
│   - Year-end carry-forward                                           │
│   - Report generation (PDF/Excel)                                    │
│   - Cost calculation (end-of-month)                                  │
│   - E-invoice sync (BKAV / TCT)                                      │
│   - Scheduled cron jobs (via django_q2_schedule)                     │
└──────────────────────────────────────────────────────────────────────┘
                                              │
                                              ↓
                              ┌──────────────────────────────┐
                              │   External integrations       │
                              │  - BKAV e-invoice API         │
                              │  - TCT (Tổng cục Thuế) API    │
                              │  - Bank statement API         │
                              │  - Time clock machine API     │
                              └──────────────────────────────┘
```

## 2. Lớp kiến trúc

Hệ thống chia làm **6 lớp (layers)** rõ ràng, mỗi lớp chỉ phụ thuộc vào lớp ngay dưới:

### 2.1. Presentation Layer (UI) — **Đa giao diện × Đa luồng thao tác**

Hệ thống tách UX thành **3 chiều độc lập** qua plugin registry:

#### Chiều 1: Layout Packs (cấu trúc UI)

Nhiều layout packs chạy song song qua URL riêng. Mỗi layout pack là một Django app + template dir độc lập:

| Layout | URL | App | Đặc điểm |
|--------|-----|-----|----------|
| Modern (mặc định) | `/modern/*` | `apps/ui_modern` | Sidebar trái, HTMX, Bootstrap 5.3 |
| Classic | `/classic/*` | `apps/ui_classic` | Top nav, dense grid, giống MISA/Bravo |
| Mobile (PWA) | `/mobile/*` | `apps/ui_mobile` | Bottom tab, touch-first |
| Portal (KH/NCC) | `/portal/*` | `apps/ui_portal` | OTP login, xem công nợ |

#### Chiều 2: Interaction Styles (cách thao tác)

Cùng operation có nhiều style, tối ưu theo user/tình huống:

| Style | Mục đích | Đặc điểm |
|-------|---------|----------|
| **Guided** | Người mới | Wizard từng bước, tooltip, smart defaults |
| **Standard** | Kế toán chuyên nghiệp (mặc định) | Form đầy đủ, keyboard shortcuts |
| **Quick** | Nhập liệu nhanh | Minimal fields, type-ahead, save & new |
| **Bulk** | Nhập nhiều cùng lúc | Paste Excel, preview, validate, bulk create |

URL riêng cho mỗi style: `/modern/invoices/new/guided/`, `/modern/invoices/new/quick/`, ...

#### Chiều 3: Workflows (nguồn dữ liệu)

| Workflow | Mô tả |
|----------|------|
| From-scratch | Nhập tay (mặc định) |
| From-template | Dùng voucher template có sẵn |
| From-photo | Chụp ảnh hóa đơn → OCR → auto-fill |
| From-import | Upload Excel/CSV |
| From-email | Inbox auto-parse attachment PDF |
| From-API | Partner push qua API |

#### Plugin Registry Pattern

Thêm UX variant mới = register 1 class, không sửa code hiện tại:

```python
# apps/core/ux/registry.py
class InteractionStyle:
    code = 'guided'
    name = 'Hướng dẫn'
    template_prefix = 'interaction/guided'
    supported_operations = ['invoice.create', 'voucher.create']
    # ...

class InteractionStyleRegistry:
    _registry = {}
    
    @classmethod
    def register(cls, style_class):
        cls._registry[style_class.code] = style_class
```

Tổ hợp: Layout × Style × Workflow tạo ra vô số UX variant. Service layer dùng chung — chỉ View + Template khác.

Chi tiết:
- [07-mau-giao-dien/05-multi-ui-architecture.md](../07-mau-giao-dien/05-multi-ui-architecture.md) — Layout packs + Branding
- [07-mau-giao-dien/06-ux-variants-architecture.md](../07-mau-giao-dien/06-ux-variants-architecture.md) — Interaction styles + Workflows

### 2.2. HTTP Layer
- **django-ninja** cho REST API (JSON, OpenAPI docs)
- **Django Views** (trong `apps/ui_<layout>/`) cho HTML rendering (cho HTMX fragments)
- **Authentication middleware** (session-based)
- **Tenant middleware** (set company context + branding)

### 2.3. Service Layer (Business Logic)
- Nghiệp vụ kế toán phức tạp được đóng gói thành Service class
- Không phụ thuộc Django/HTTP — dễ unit test
- Ví dụ: `VoucherPostingService`, `InventoryCostCalculator`, `PeriodClosingService`

### 2.4. Domain Layer (Entities & Value Objects)
- Django Models = entities
- Custom managers cho queries nghiệp vụ
- Validators domain-specific (ví dụ: voucher phải cân đối N=C)

### 2.5. Data Access Layer
- Django ORM + MariaDB
- Custom queryset methods (vd: `Voucher.objects.for_company(c).in_period(p).posted()`)
- Database-level constraints + indexes

### 2.6. Infrastructure Layer
- File storage (local filesystem hoặc Django storages với S3/MinIO)
- Cache (Django DB cache — dùng chính MariaDB)
- Task queue (django-q2 — broker là Django ORM)
- Email (SMTP hoặc SES)
- External APIs (BKAV, TCT, banks)

## 3. Nguyên tắc thiết kế

### 3.1. Bounded Context với Django apps

Apps chia làm **2 nhóm**: shared backend (models + services + API) và layout packs (view + template).

```
project_root/
├── apps/
│   │
│   │  ─── Shared backend (models + services + API) ───
│   ├── core/              # Tenant, company (+ branding fields), audit
│   ├── identity/          # User, role, permission (+ layout preference)
│   ├── master_data/       # Chart of accounts, currency, cost center
│   ├── ledger/            # Accounting voucher, posting (Service only, không có views)
│   ├── treasury/          # Cash, bank, advance, loan
│   ├── sales/             # Customer, sales invoice, AR
│   ├── purchasing/        # Vendor, purchase invoice, AP
│   ├── inventory/         # Product, warehouse, stock movement
│   ├── assets/            # Fixed assets, tools, depreciation
│   ├── costing/           # Cost calculation, workshop
│   ├── hr/                # Employee, contract
│   ├── payroll/           # Time attendance, payroll
│   ├── reporting/         # Financial reports, trial balance
│   ├── tax/               # VAT returns, tax reports
│   ├── system/            # Fiscal year, parameters, voucher book
│   │
│   │  ─── Layout packs (View + Template layer, multi-UI) ───
│   ├── ui_modern/         # /modern/*  — Modern UI (default)
│   ├── ui_classic/        # /classic/* — Classic UI
│   ├── ui_mobile/         # /mobile/*  — Mobile UI (PWA)
│   └── ui_portal/         # /portal/*  — Customer/vendor portal
```

### 3.2. Single Source of Truth

- **Voucher line** là nguồn dữ liệu kế toán chính xác
- **Stock ledger** là nguồn dữ liệu tồn kho chính xác
- Mọi báo cáo chỉ là **projection** từ dữ liệu gốc
- **Không cache business data** ở DB cache — chỉ cache reports và params

### 3.3. CQRS-lite

- **Command side**: voucher, invoice, stock_voucher tạo → gọi Service → update projections
- **Query side**: SELECT từ projections (account_period_balance, stock_card, etc.)
- Projections có thể rebuild được từ command side

### 3.4. Idempotency

- Mọi API mutation có `Idempotency-Key` header
- Mọi background job có `job_id` unique
- Có thể retry an toàn

### 3.5. Multi-tenant isolation

```python
# Middleware: set company context
class TenantMiddleware:
    def __call__(self, request):
        company_id = request.session.get('current_company_id')
        if company_id:
            request.company_id = company_id
            # Tự động filter mọi query theo company_id
        return self.get_response(request)

# Model manager
class CompanyQuerySet(models.QuerySet):
    def for_company(self, company_id):
        return self.filter(company_id=company_id)

class Voucher(models.Model):
    objects = CompanyManager.from_queryset(CompanyQuerySet)()
```

## 4. Công nghệ chi tiết

| Lớp | Công nghệ | Phiên bản | Lý do |
|-----|-----------|----------|------|
| Python | CPython | 3.12 | Stable, performance |
| Web framework | Django | **5.2 LTS** | Mature, ORM mạnh, admin built-in, LTS |
| API framework | django-ninja | 1.x | Django-native, OpenAPI, Pydantic |
| Database | MariaDB | 11.4 LTS | Tương thích MySQL, GA |
| Cache | **Django DB cache** | – | Dùng chính MariaDB, không cần Redis |
| Task queue | **django-q2** | 2.x | Native Django, broker = Django ORM |
| WSGI server | Gunicorn | 22+ | Mature, performant |
| Process manager | systemd | – | Built-in Linux, không cần Docker |
| Reverse proxy | Nginx | 1.24+ | TLS, static files, rate limit |
| Frontend interactivity | HTMX | 2.x | SPA-like UX, ít JS |
| Frontend reactivity | Alpine.js | 3.x | Lightweight, kết hợp HTMX tốt |
| CSS framework | Bootstrap | 5.3 | Nhanh, phổ biến ở VN |
| Data grid | Tabulator | 6.x | Thay DevExpress Blazor grid |
| Charts | Chart.js hoặc Apache ECharts | – | Dashboard quản trị |
| PDF | WeasyPrint | 60+ | HTML/CSS → PDF chất lượng cao |
| Excel | openpyxl | 3.x | Đọc + ghi Excel |
| Search | MariaDB FULLTEXT + Meilisearch (optional) | – | Tìm voucher nhanh |

## 5. Deployment topology

### 5.1. Single-server (small deployment — mặc định)

```
1 VPS (8 core, 16GB RAM, SSD):
  - Nginx (reverse proxy + static)
  - Gunicorn (WSGI, 4-8 workers, systemd unit pmketoan-web)
  - django-q2 cluster (systemd unit pmketoan-qcluster)
  - MariaDB 11.4
  - Optional: file-based logrotate, restic backup

→ phục vụ 5-20 công ty, 50-200 users đồng thời
```

Mọi thứ chạy trên **1 server**, quản lý bằng **systemd**. Không Docker.

### 5.2. Multi-server (medium)

```
2 web servers + Nginx load balancer (hoặc HAProxy)
1 DB server (MariaDB primary + 1 replica)
django-q2 cluster trên 1 trong các web server (hoặc server riêng)

→ phục vụ 50-200 công ty, 500-1000 users đồng thời
```

### 5.3. Large (khi cần)

```
Nginx → nhiều Gunicorn servers (auto-scale bằng Ansible)
MariaDB Galera cluster (3 nodes)
django-q2 cluster trên dedicated workers
S3-compatible storage cho media
```

(Không dùng Kubernetes — overkill cho phần mềm kế toán SME.)

## 6. Performance targets

| Metric | Target | Strategy |
|--------|--------|---------|
| Page load (P50) | < 500ms | HTMX partial render, DB cache |
| API response (P50) | < 200ms | Optimized queries, indexing |
| Voucher list (10k records) | < 1s | Pagination, indexed columns |
| Trial balance | < 3s | Pre-calculated `account_period_balance` |
| Period closing | < 30s | django-q2 async + optimized SQL |
| Year-end carry-forward | < 5 phút | django-q2 async, batch processing |

## 7. Security architecture

### 7.1. Authentication
- Session-based (Django auth)
- 2FA TOTP (django-otp)
- Brute-force protection (django-axes)

### 7.2. Authorization
- RBAC: role → permissions
- Row-level security: company_id, department_id
- Action-level: view, create, edit, delete, post, lock

### 7.3. Data security
- TLS everywhere (HTTPS)
- Encryption at rest (MariaDB transparent encryption)
- Sensitive fields encrypted at app level (AES-256): tax_code, salary
- Audit log mọi thay đổi (user_access_log)

### 7.4. Backup
- Daily: full backup
- Hourly: incremental backup
- PITR (Point-In-Time Recovery) trong 7 ngày

---

**Tiếp theo**: [02. Django Apps](./02-django-apps.md)
