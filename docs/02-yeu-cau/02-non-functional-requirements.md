# 02. Yêu cầu phi chức năng (Non-Functional Requirements)

> Yêu cầu về hiệu năng, bảo mật, độ ổn định, mở rộng, v.v.

## 1. Performance

### 1.1. Page load time

| Loại trang | Target P50 | Target P95 | Target P99 |
|-----------|-----------|-----------|-----------|
| Login | < 300ms | < 800ms | < 1.5s |
| Dashboard | < 500ms | < 1.5s | < 3s |
| List view (10k records) | < 1s | < 2s | < 5s |
| Detail view | < 500ms | < 1s | < 2s |
| Form load | < 500ms | < 1s | < 2s |
| Report (trial balance) | < 2s | < 5s | < 10s |
| Report (B01-DN) | < 3s | < 7s | < 15s |
| HTMX partial update | < 300ms | < 700ms | < 1.5s |

### 1.2. API response time

| Endpoint type | Target P50 | Target P95 |
|--------------|-----------|-----------|
| GET list (paginated) | < 200ms | < 500ms |
| GET detail | < 150ms | < 400ms |
| POST create | < 400ms | < 1s |
| POST voucher (with validation + posting) | < 1s | < 2s |
| Period closing (async) | < 30s | < 2 phút |

### 1.3. Background job

| Job | Target |
|-----|--------|
| Cost calculation (10k products) | < 5 phút |
| Year-end carry-forward | < 10 phút |
| Backup database | < 30 phút |
| Generate full BCTC | < 1 phút |

### 1.4. Throughput

- 200 users đồng thời (concurrent)
- 1000 requests/phút (peak)
- 10.000 vouchers/ngày

### 1.5. Database

- Connection pool: 50 connections
- Slow query threshold: 1s
- Index hit ratio: > 99%

## 2. Scalability

### 2.1. Vertical scale (single instance)

| Resource | Min | Recommended |
|----------|-----|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Disk | 100 GB | 500 GB SSD |
| Network | 100 Mbps | 1 Gbps |

### 2.2. Horizontal scale

- App server: 2-10 instances
- DB: primary + 1-3 replicas
- django-q2 cluster: 2-20 workers
- DB cache tables trong MariaDB

### 2.3. Data growth limits

| Entity | Year 1 | Year 3 | Year 5 |
|--------|--------|--------|--------|
| Companies | 50 | 500 | 2.000 |
| Users | 500 | 5.000 | 20.000 |
| Vouchers | 500K | 5M | 20M |
| Voucher lines | 2.5M | 25M | 100M |
| Stock movements | 1M | 10M | 50M |
| DB size | 5 GB | 50 GB | 200 GB |

## 3. Availability & Reliability

### 3.1. Uptime targets

| Tier | Uptime | Downtime/tháng |
|------|--------|---------------|
| Standard | 99.5% | ~3.6 giờ |
| Premium | 99.9% | ~43 phút |
| Enterprise | 99.95% | ~21 phút |

### 3.2. Maintenance window

- 23:00 - 02:00 Chủ nhật hàng tuần (nếu cần)
- Thông báo trước 24 giờ
- Hot updates (zero-downtime) cho bug fixes

### 3.3. Failure tolerance

- Single point of failure (SPOF): không có (multi-AZ nếu cloud)
- Auto-restart: systemd (`Restart=on-failure`)
- Health check endpoint: `/health/`
- Graceful shutdown: kết thúc request đang chạy

### 3.4. Data integrity

- ACID transactions
- Foreign key constraints
- Periodic consistency check (cron job)
- Validation trước khi commit

## 4. Security

### 4.1. Authentication

- Password policy:
  - Tối thiểu 8 ký tự
  - Có ít nhất 1 chữ hoa, 1 chữ thường, 1 số
  - Không trùng password cũ (lịch sử 5)
  - Bắt buộc đổi password đầu tiên
- Session timeout: 30 phút không hoạt động
- 2FA: TOTP (Google Authenticator)
- Brute-force protection: lock sau 5 lần sai

### 4.2. Authorization

- RBAC (Role-Based Access Control)
- Row-level security: company_id, department_id
- Column-level: sensitive fields (lương, MST) yêu cầu permission riêng
- Action-level: view, create, edit, delete, post, lock

### 4.3. Transport security

- TLS 1.2+ (TLS 1.3 preferred)
- HSTS header
- HTTPS redirect
- Secure cookies

### 4.4. Data encryption

- At rest: MariaDB transparent data encryption (TDE)
- In transit: TLS
- Sensitive fields (MST, salary, password_hash): AES-256 at app level
- Backup encryption: restic + age/AES

### 4.5. Common attacks

| Attack | Mitigation |
|--------|-----------|
| SQL Injection | ORM, prepared statements |
| XSS | Django template autoescape, CSP |
| CSRF | Django middleware, SameSite cookies |
| SSRF | Whitelist outbound domains |
| Path traversal | Django storage API, validated paths |
| Brute force | django-axes, rate limit |
| DDoS | Cloudflare / Nginx rate limit |
| Clickjacking | X-Frame-Options DENY |

### 4.6. OWASP Top 10 mapping

| Risk | Control |
|------|--------|
| A01 - Broken Access Control | RBAC + row-level + audit |
| A02 - Cryptographic Failures | AES-256, TLS 1.3 |
| A03 - Injection | ORM + parameterized queries |
| A04 - Insecure Design | Threat modeling, secure SDLC |
| A05 - Security Misconfiguration | Hardened systemd units, UFW firewall, CIS benchmarks |
| A06 - Vulnerable Components | Dependabot, npm audit, pip-audit |
| A07 - Auth Failures | 2FA, password policy |
| A08 - Software/Data Integrity | Code signing, hash verification |
| A09 - Logging/Monitoring Failures | Sentry, audit log |
| A10 - SSRF | Network policies, whitelists |

### 4.7. Privacy (GDPR/PDPA tương tự)

- Data minimization: chỉ thu thập cần thiết
- Right to be forgotten: hard delete (theo yêu cầu)
- Data export: user có thể export data của mình
- Audit log: mọi access sensitive data

## 5. Maintainability

### 5.1. Code quality

- Test coverage: ≥ 80% line, ≥ 70% branch
- Linting: ruff clean
- Type checking: mypy --strict
- Code review: 1+ approver
- Documentation: docstring cho mọi public API

### 5.2. Modular architecture

- Django apps độc lập, loose coupling
- Bounded context rõ ràng
- Service layer tách biệt business logic
- DDD patterns

### 5.3. Deployment

- CI/CD: GitHub Actions
- Blue-green deployment
- Database migrations: backward compatible
- Rollback: < 5 phút
- Hotfix SLA: < 2 giờ

### 5.4. Documentation

- API: OpenAPI auto-gen
- Code: docstrings
- User manual: markdown
- Operations: runbook

## 6. Observability

### 6.1. Logging

- App logs: structured JSON
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Retention: 30 ngày (app), 90 ngày (error)
- Storage: Loki hoặc ELK

### 6.2. Metrics

- Prometheus + Grafana
- RED metrics: Rate, Errors, Duration
- Business metrics: vouchers/day, active users, companies

### 6.3. Tracing

- OpenTelemetry SDK
- Distributed tracing across services
- Sentry Performance

### 6.4. Alerting

- Error rate > 1% trong 5 phút → PagerDuty
- Latency P95 > 5s → warning
- DB connections > 80% → critical
- Disk > 80% → critical

## 7. Backup & Recovery

### 7.1. Backup schedule

| Type | Frequency | Retention |
|------|----------|-----------|
| Full DB backup | Daily 02:00 | 30 ngày |
| Incremental (binlog) | Hourly | 7 ngày |
| Static files | Daily | 90 ngày |
| Media files | Daily | 90 ngày |
| Code | Git push | Forever |

### 7.2. RPO/RTO

- **RPO** (Recovery Point Objective): ≤ 1 giờ
- **RTO** (Recovery Time Objective): ≤ 4 giờ

### 7.3. Backup storage

- Onsite: 7 ngày full backup gần nhất
- Offsite (S3/Cloud): 90 ngày
- Geo-redundant: multi-region

### 7.4. DR test

- Quarterly DR drill
- Restore DB to staging
- Verify integrity

## 8. Localization & Internationalization

### 8.1. Language

- Tiếng Việt (default)
- Tiếng Anh (optional)
- Locale-aware: dates, numbers, currency

### 8.2. Timezone

- Server: UTC
- Display: Asia/Ho_Chi_Minh (UTC+7)
- All datetime stored as UTC, convert on display

### 8.3. Currency

- Default: VND
- Multi-currency: USD, EUR, JPY, ...
- Exchange rates: cập nhật hàng ngày

### 8.4. Number format

- Vietnamese: 1.234.567,89
- English: 1,234,567.89
- Toggle theo locale

## 9. Compliance

### 9.1. Vietnamese regulations

- Luật Kế toán 88/2015/QH13
- TT133/2016 (DN vừa và nhỏ)
- TT200/2014 (DN lớn)
- TT78/2021 → TT32/2025 (Hóa đơn điện tử)
- TT80/2021 (Tờ khai thuế)
- ND 123/2020, ND 109/2022 (Hóa đơn)

### 9.2. Data residency

- Dữ liệu kế toán phải lưu tại Việt Nam (theo luật)
- Backup có thể ở nước ngoài nếu được phép

### 9.3. Audit trail

- Lưu trữ tối thiểu 5 năm (chứng từ, sổ, BCTC)
- Hồ sơ nhân sự: 50 năm
- Audit log: vĩnh viễn (compressed)

## 10. Browser support

| Browser | Version | Support level |
|---------|---------|--------------|
| Chrome | 100+ | Full |
| Firefox | 100+ | Full |
| Safari | 15+ | Full |
| Edge | 100+ | Full |
| Mobile Chrome | latest | Basic (responsive) |
| Mobile Safari | latest | Basic (responsive) |
| IE 11 | – | **Không hỗ trợ** |

## 11. Accessibility

- WCAG 2.1 Level AA target
- Keyboard navigation
- Screen reader compatible
- High contrast mode
- Skip to content link

## 12. Performance budget

| Asset type | Budget |
|-----------|--------|
| Initial HTML | < 50 KB |
| CSS | < 100 KB (gzipped) |
| JS | < 150 KB (gzipped) |
| Fonts | < 50 KB |
| Total initial load | < 500 KB |
| Time to interactive | < 3s (3G) |

## 13. API rate limits

| Endpoint type | Limit |
|--------------|------|
| Login | 5 requests/phút |
| Password reset | 3 requests/giờ |
| API (authenticated) | 1000 requests/giờ |
| API (read-heavy reports) | 100 requests/giờ |
| Webhook inbound | 100 requests/phút |

---

**Tiếp theo**: [Phân tích module →](../03-phan-tich-module/00-tong-quan-module.md)
