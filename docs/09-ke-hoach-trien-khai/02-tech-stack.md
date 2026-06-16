# 02. Tech Stack chi tiết

> Đặc tả công nghệ, version, lựa chọn thay thế.

## 1. Backend Stack

### 1.1. Core

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| Python | 3.12+ | Stable, performance, async support |
| **Django** | **5.2 LTS** | Long-term support, mature, batteries-included |
| django-ninja | 1.2+ | Type-safe API, OpenAPI auto-gen |
| django-filter | 24+ | Filtering for QuerySet |
| django-extensions | 3+ | shell_plus, runserver_plus, etc |

### 1.2. Database

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| MariaDB | 11.4 LTS | Stable, performant, MySQL-compatible |
| mysqlclient | 2.2+ | Fast MySQL/MariaDB driver (C-based) |
| PyMySQL | 1.1+ | Pure Python alternative (cho dev) |

### 1.3. Task Queue & Background Jobs

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| **django-q2** | **2.0+** | Native Django task queue, **không cần Redis/broker ngoài** |
| **(broker)** | Django ORM | django-q2 dùng chính MariaDB làm broker |
| **(monitoring)** | django-q2 admin | Built-in admin UI, không cần Flower |

`django-q2` là một fork được duy trì tích cực của `django-q`. Nó chạy như một process độc lập (`python manage.py qcluster`), không cần Redis/RabbitMQ. Lưu task và kết quả trực tiếp vào bảng Django ORM (`django_q2_ororm`, `django_q2_task`, `django_q2_schedule`).

### 1.4. Cache & Session

| Công nghệ | Lý do |
|-----------|------|
| **Django database cache** | Dùng chính MariaDB, không cần Redis |
| Local memory cache | Cho single-process caching (per-worker) |
| File-based cache | Tùy chọn, cho session lớn |

Cấu hình `CACHES` dùng `DB cache` (chia sẻ giữa workers) + `LocMem cache` cho per-process:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
        'TIMEOUT': 3600,
        'OPTIONS': {'MAX_ENTRIES': 100000},
    },
    'local': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'per-process',
    },
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'  # DB + cache
```

### 1.5. Authentication & Security

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| django-allauth | 60+ | Authentication system |
| djangorestframework-simplejwt | 5.3+ | JWT tokens |
| django-otp | 1.5+ | 2FA TOTP |
| django-axes | 6.5+ | Brute-force protection |
| django-cors-headers | 4.3+ | CORS support |

### 1.6. Data validation

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| pydantic | 2.7+ | Type-safe schemas (đóng gói cùng django-ninja) |
| python-dateutil | 2.9+ | Date parsing |

## 2. Frontend Stack

### 2.1. Core

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| HTMX | 2.0+ | SPA-like UX với HTML fragments |
| Alpine.js | 3.14+ | Reactive UI nhỏ |
| Bootstrap | 5.3+ | CSS framework phổ biến VN |
| Bootstrap Icons | 1.11+ | Icon set |
| Tabulator | 6.2+ | Data grid thay DevExpress |

### 2.2. Utilities

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| dayjs | 1.11+ | Date manipulation |
| chart.js | 4.4+ | Dashboard charts |
| apexcharts | 3.45+ | Alternative charts |
| select2 | 4.0+ | Searchable dropdown |

### 2.3. Build tools

Không cần build step phức tạp. Vendor assets thẳng vào `static/`.

```bash
# scripts/install_vendor_assets.sh
npm install --no-save \
    bootstrap@5.3.3 \
    bootstrap-icons@1.11.3 \
    htmx.org@2.0.0 \
    alpinejs@3.14.1 \
    tabulator-tables@6.2.5 \
    chart.js@4.4.3 \
    dayjs@1.11.10 \
    select2@4.1.0

# Copy to static/
cp node_modules/bootstrap/dist/css/bootstrap.min.css static/vendor/css/
cp node_modules/bootstrap/dist/js/bootstrap.bundle.min.js static/vendor/js/
cp node_modules/bootstrap-icons/font/bootstrap-icons.min.css static/vendor/css/
cp node_modules/bootstrap-icons/font/fonts/* static/vendor/fonts/
cp node_modules/htmx.org/dist/htmx.min.js static/vendor/js/
cp node_modules/alpinejs/dist/cdn.min.js static/vendor/js/alpine.min.js
cp node_modules/tabulator-tables/dist/js/tabulator.min.js static/vendor/js/
cp node_modules/tabulator-tables/dist/css/tabulator.min.css static/vendor/css/
cp node_modules/chart.js/dist/chart.umd.min.js static/vendor/js/
cp node_modules/dayjs/dayjs.min.js static/vendor/js/
cp node_modules/select2/dist/js/select2.min.js static/vendor/js/
cp node_modules/select2/dist/css/select2.min.css static/vendor/css/
```

## 3. Documentation & PDF

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| WeasyPrint | 60+ | HTML/CSS → PDF |
| ReportLab | 4+ | Programmatic PDF (cho tờ khai XML PDF) |
| openpyxl | 3.1+ | Excel read/write |
| pandas | 2.2+ | Data analysis (optional) |

## 4. Testing

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| pytest | 8+ | Test framework |
| pytest-django | 4+ | Django integration |
| pytest-cov | 5+ | Coverage |
| factory_boy | 3.3+ | Test data factory |
| mixer | 7+ | Quick fixtures (alt) |
| pytest-mock | 3.14+ | Mocking |
| faker | 25+ | Fake data |
| pytest-xdist | 3+ | Parallel tests |
| model_bakery | 1.17+ | Fast fixture (alt) |

For E2E (optional):
| Playwright | 1.40+ | E2E browser testing |

## 5. Code Quality

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| ruff | 0.5+ | Linter + formatter (thay flake8+black) |
| mypy | 1.10+ | Static type checking |
| pre-commit | 3.7+ | Pre-commit hooks |
| django-stubs | 5+ | Django type stubs |

## 6. Dev Tools

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| uv | 0.4+ | Dependency management + virtualenv (thay Poetry, nhanh hơn) |
| Poetry | 1.8+ | Alternative dep manager |
| ipython | 8+ | Better REPL |
| ipdb | 0.13+ | Better debugger |
| django-debug-toolbar | 4+ | Debug SQL queries |
| silk | 5+ | Profiling |

## 7. Production Infrastructure (bare-metal / VPS)

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| Nginx | 1.24+ | Reverse proxy |
| Gunicorn | 22+ | WSGI server |
| systemd | 252+ | Process manager (cho gunicorn + qcluster) |
| MariaDB | 11.4+ | Database trên cùng server hoặc server riêng |
| Supervisor | 4+ | Process manager alt (nếu cần) |

Không sử dụng **Docker/Kubernetes** — deployment trực tiếp lên VPS/bare-metal bằng **systemd**, phù hợp với SME Việt Nam (đơn giản vận hành, ít chi phí).

## 8. Monitoring & Observability

| Công nghệ | Version | Lý do |
|-----------|--------|------|
| Sentry SDK | 2+ | Error tracking |
| prometheus-client | 0.20+ | Metrics |
| django-prometheus | 2.3+ | Django integration |
| Grafana | 11+ | Dashboard |
| Loki + Promtail | 3+ | Log aggregation |
| OpenTelemetry | 1.25+ | Distributed tracing |

## 9. External Integrations

| Service | Lý do |
|---------|------|
| BKAV eInvoice API | HĐĐT output |
| Viettel eInvoice API | HĐĐT output (alt) |
| TCT (Tổng cục Thuế) API | HĐĐT input + tờ khai |
| VNP QR / VietQR | Tạo mã QR thanh toán |
| SMTP (Gmail, SES) | Email |
| Twilio / Zalo API | SMS / Zalo OA |
| AWS S3 / MinIO | File storage (optional — có thể dùng local disk) |

## 10. Backup & Storage

| Công nghệ | Lý do |
|-----------|------|
| mariadb-backup | DB backup |
| restic | Incremental encrypted backup |
| aws-cli | S3 sync (optional) |
| rsync | Fast file sync |

## 11. CI/CD

| Công nghệ | Lý do |
|-----------|------|
| GitHub Actions | CI (mặc định) |
| GitLab CI | CI alternative |
| rsync + ssh | Deploy code lên server |
| systemd reload | Restart services sau deploy |

## 12. Tại sao không dùng?

| Tech | Lý do không dùng |
|------|-----------------|
| **Redis** | Thêm 1 service phải vận hành. Django DB cache + django-q2 đủ cho quy mô SME |
| **Celery** | Phức tạp hơn django-q2, cần broker (Redis/RabbitMQ). django-q2 native Django |
| **Docker / K8s** | Overkill cho SME. systemd đơn giản hơn, ít layer hơn |
| **React / Vue** | Overkill, HTMX đủ cho PMK |
| **Node.js** | Một ngôn ngữ đủ (Python) |
| **PostgreSQL** | MariaDB phổ biến ở VN kế toán, đủ dùng |
| **MongoDB** | ACID quan trọng cho kế toán |
| **GraphQL** | Overkill, REST đủ |
| **Spring Boot / Java** | Verbose, dev velocity thấp hơn Django |
| **.NET** | License cost cao, ít human resource ở VN |

## 13. Lựa chọn thay thế

| Layer | Alternative | Lý do thay thế |
|-------|------------|---------------|
| Backend | FastAPI (Django→FastAPI) | Async-first, nhưng thiếu ORM |
| Database | PostgreSQL | Advanced features (JSONB, GIS) |
| Frontend | Vue 3 + Vite | SPA-heavy nếu cần |
| Queue | RQ (dùng Redis) hoặc Huey | Nếu cần queue nặng |

→ Đề xuất giữ nguyên stack chính vì phù hợp nhất cho SME VN kế toán: ít moving parts, dễ deploy trên 1 VPS, đủ performance cho hàng trăm công ty.

## 14. django-q2: điểm cần lưu ý

### 14.1. Broker = Django ORM

django-q2 lưu task trong bảng `django_q2_ororm`, cluster đọc bảng này và thực thi. **Cần đảm bảo DB connection ổn định**.

### 14.2. Cluster operation

```bash
# Start cluster (foreground for debugging)
python manage.py qcluster

# Via systemd (production)
sudo systemctl start pmketoan-qcluster
sudo systemctl status pmketoan-qcluster
```

Cluster tự spawning các worker process dựa trên `Q_CLUSTER['workers']` config (mặc định 4).

### 14.3. Async tasks

```python
# apps/ledger/tasks.py
from django_q.tasks import async_task, schedule
from django_q.models import Schedule

def calculate_cost_period(company_id, period):
    """Background task: tính giá xuất kho"""
    # ... long-running computation
    pass

# Trigger
async_task(
    'apps.ledger.tasks.calculate_cost_period',
    company_id=1, period='2026-06',
    task_name=f'cost_calc_2026_06_company_1'
)

# Schedule periodic
Schedule.objects.create(
    func='apps.ledger.tasks.calculate_cost_period',
    schedule_type=Schedule.CRON,
    cron='0 0 1 * *',  # Ngày 1 hàng tháng
)
```

### 14.4. Limitations

- **Không realtime** như Celery+Redis (DB poll có độ trễ ~1-5s)
- **Throughput thấp hơn** Celery với Redis (đủ cho kế toán, không đủ cho high-traffic)
- **Database load tăng** (task queue ghi vào DB)
- **Retry phức tạp hơn** (phải dùng `attempt_count` + `retry`)

### 14.5. Khi nào cần chuyển sang Celery?

Nếu cần:
- Hàng nghìn task/giây
- Realtime processing (< 100ms)
- Distributed workers trên nhiều server

→ Lúc đó mới cân nhắc migrate sang Celery + Redis/RabbitMQ.

---

**Tiếp theo**: [03. Folder Structure](./03-folder-structure.md)
