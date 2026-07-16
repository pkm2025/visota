# Branding & UI Investigation: PMKetoan → Visota ERP Rebranding

> Generated: 2026-07-14
> Purpose: Comprehensive audit of all branding strings, UI structure, and positioning for rebranding from "PM Ketoan" to "Visota ERP".

---

## Executive Summary

The codebase has a **split identity**. The public-facing marketing site (landing page, signup, terms, privacy) has already been partially rebranded to **"Visota"** with domain `visota.net`. However, the **internal app UI** (layout, login, sidebar, dashboard, API titles, service worker, PWA manifest, blog templates) still uses **"PMKetoan"** throughout. Production settings (`config/settings/prod.py`) and `.env.example` use Visota naming, while base/dev/test settings still reference PMKetoan. The `Company` model has a white-label field `hide_pmketoan_branding` that is schema-locked (requires migration to rename).

**Key finding**: There is NO "PM Kế toán" (with Vietnamese diacritics) or "PMK" abbreviation anywhere. The brand string is consistently **"PMKetoan"** (one word, no space).

---

## 1. Branding Strings — Full Inventory

### 1.1 "PMKetoan" in User-Facing Templates

| File | Line/Context | String |
|------|-------------|--------|
| `templates/modern/base/layout.html` | `<meta apple-mobile-web-app-title>` | `PMKetoan` |
| `templates/modern/base/layout.html` | `<meta description>` | `PMKetoan ERP — Hệ thống kế toán VN tuân thủ TT133/2016, TT200/2014` |
| `templates/modern/base/layout.html` | PWA install banner JS | `<strong>Cài đặt PMKetoan</strong>` |
| `templates/modern/base/_right_sidebar.html` | System info widget | `Hệ thống: <strong>PMKetoan v0.8</strong>` |
| `templates/modern/reporting/report_export_pdf.html` | PDF footer | `Phát hành bởi PMKetoan — Tuân thủ TT133/2016 và TT200/2014` |
| `templates/public/blog_list.html` | `<title>` tag | `Blog — PMKetoan` |
| `templates/public/blog_list.html` | Navbar brand | `<i class="bi bi-calculator-fill text-primary"></i> PMKetoan` |
| `templates/public/blog_list.html` | Footer | `PMKetoan — © 2026` |
| `templates/public/blog_detail.html` | `<title>` tag | `{{ article.title }} — PMKetoan Blog` |
| `templates/public/blog_detail.html` | Navbar brand | `<i class="bi bi-calculator-fill text-primary"></i> PMKetoan` |
| `templates/public/blog_detail.html` | CTA | `Bạn muốn dùng thử PMKetoan?` |
| `templates/public/blog_detail.html` | Footer | `PMKetoan — © 2026` |

### 1.2 "PMKetoan" in Python Code & Settings

| File | Context | String/Usage |
|------|---------|-------------|
| `config/settings/base.py` | Module docstring | `"""Base Django settings for PMKetoan."""` |
| `config/settings/base.py` | DB defaults | `'NAME': os.environ.get('DB_NAME', 'pmketoan')` |
| `config/settings/base.py` | DB defaults | `'USER': os.environ.get('DB_USER', 'pmketoan')` |
| `config/settings/base.py` | Q_CLUSTER name | `'name': 'PMKetoan'` |
| `config/settings/dev.py` | Q_CLUSTER name | `Q_CLUSTER = {'name': 'PMKetoan', ...}` |
| `config/settings/test.py` | Test DB name | `"NAME": os.environ.get("TEST_DB_NAME", "test_pmketoan")` |
| `config/urls.py` | URL imports | `PMKetoanLoginView`, `PMKetoanLogoutView` |
| `apps/core/middleware.py` | DEFAULT_BRAND dict | `"name": "PMKetoan"` |
| `apps/core/middleware.py` | DEFAULT_BRAND dict | `"hide_pmketoan_branding": False` |
| `apps/core/middleware.py` | BrandingMiddleware | `"hide_pmketoan_branding": company.hide_pmketoan_branding` |
| `apps/core/models.py` | Company model field | `hide_pmketoan_branding = models.BooleanField(default=False)` |
| `apps/core/migrations/0001_initial.py` | Migration | `("hide_pmketoan_branding", models.BooleanField(default=False))` |
| `apps/core/api.py` | NinjaAPI title | `title="PMKetoan API"` |
| `apps/core/api.py` | Module docstring | `"""django-ninja API — REST API for PMKetoan."""` |
| `apps/core/logging_utils.py` | Module docstring | `"""Structured JSON logging ... for PMKetoan."""` |
| `apps/core/feature_flags.py` | Module docstring | `"""Feature flag system for PMKetoan."""` |
| `apps/identity/middleware_request_id.py` | Module docstring | `"""Request ID middleware ... for PMKetoan."""` |
| `apps/ui_modern/views/auth_views.py` | Class name | `class PMKetoanLoginView(LoginView)` |
| `apps/ui_modern/views/auth_views.py` | Class name | `class PMKetoanLogoutView(LogoutView)` |
| `apps/ui_modern/views/auth_views.py` | Docstring | `"""Login view with PMKetoan branding and Vietnamese UI."""` |
| `apps/ui_modern/views/__init__.py` | Imports/exports | `PMKetoanLoginView`, `PMKetoanLogoutView` |
| `apps/ui_modern/forms/auth_forms.py` | Docstring | `"""PMKetoan login form ..."""` |
| `apps/notifications/services.py` | Default email | `"no-reply@pmketoan.local"` |

### 1.3 "PMKetoan" in Static Assets

| File | Context |
|------|---------|
| `static/manifest.json` | `"name": "PMKetoan ERP"` |
| `static/manifest.json` | `"short_name": "PMKetoan"` |
| `static/manifest.json` | `"description": "Hệ thống kế toán ERP cho doanh nghiệp VN — tuân thủ TT133/2016, TT200/2014, TT78/2021"` |
| `static/sw.js` | Comment: `/* PMKetoan Service Worker ... */` |
| `static/sw.js` | `const CACHE_VERSION = "pmketoan-v5"` |
| `static/sw.js` | Push notification: `data.title \|\| "PMKetoan"` |
| `static/modern/js/mobile.js` | Comment: `/* PMKetoan mobile interactions ... */` |
| `static/images/logo.svg` | SVG `aria-label="PMKetoan"`, letter "P" |
| `static/icons/logo.svg` | Same as above (identical file) |
| `static/icons/icon-192.svg` | Letter "P", blue background |
| `static/icons/icon-512.svg` | Letter "P", blue background |

### 1.4 "PMKetoan" in Config & Deploy

| File | Context |
|------|---------|
| `pyproject.toml` | `name = "pmketoan"` |
| `pyproject.toml` | `description = "Vietnamese accounting software — PMKetoan"` |
| `docker-compose.dev.yml` | `container_name: pmketoan-mariadb` |
| `docker-compose.dev.yml` | `MARIADB_DATABASE: pmketoan` |
| `docker-compose.dev.yml` | `MARIADB_USER: pmketoan` |
| `docker-compose.dev.yml` | `container_name: pmketoan-redis` |
| `.devcontainer/devcontainer.json` | `"name": "PMKetoan"` |
| `.devcontainer/devcontainer.json` | `"DB_NAME": "pmketoan"` |
| `.devcontainer/devcontainer.json` | `"DB_USER": "pmketoan"` |
| `.pre-commit-config.yaml` | Comment: `# Pre-commit hooks for PMKetoan` |
| `.github/labels.yml` | Comment: `# PMKetoan issue/PR labels` |
| `.github/workflows/ci.yml` | `MARIADB_DATABASE: pmketoan_test` |
| `.github/workflows/ci.yml` | `MARIADB_USER: pmketoan` |
| `.github/workflows/ci.yml` | `TEST_DB_NAME: pmketoan_test` |
| `.github/workflows/deploy.yml` | `docker build -t pmketoan:latest .` |
| `.github/ISSUE_TEMPLATE/bug_report.md` | `- Phiên bản PMKetoan:` |
| `.github/workflows/deploy.yml` | Docker tag: `ghcr.io/pkm2025/visota:latest` (note: mixed) |
| `deploy/systemd/pmketoan-web.service` | Filename + content: `Description=PMKetoan Gunicorn Web Server`, `User=pmketoan`, paths |
| `deploy/systemd/pmketoan-qcluster.service` | Filename + content: `Description=PMKetoan django-q2 Cluster`, paths |
| `deploy/nginx/pmketoan.conf` | Filename + `server_name pmketoan.example.com`, SSL cert paths |
| `scripts/install_vendor_assets.sh` | `VENDOR_TMP=/tmp/pmketoan-vendor` |
| `scripts/run_comprehensive_tests.py` | HTML report title: `Báo cáo kiểm thử toàn diện — PMKetoan` |
| `README.md` | `# PMKetoan` |
| `README.md` | DB creation commands use `pmketoan` |
| `AGENTS.md` | `# AGENTS.md — PMKetoan (Visota)` |
| `CODEOWNERS` | `# Code owners for PMKetoan / Visota` |
| `PROMPT_FIX_DEPLOY.md` | Container names: `pmketoan-mariadb`/`pmketoan-redis` |
| `uv.lock` | `name = "pmketoan"` |
| `test-evidence/report.html` | Title: `Báo cáo kiểm thử toàn diện — PMKetoan` |

### 1.5 "PMKetoan" in Docs (`docs/`)

These appear across many doc files: `docs/INDEX.md`, `docs/technical/01-architecture.md`, `docs/technical/03-data-model.md`, `docs/technical/04-api.md`, `docs/technical/06-deployment.md`, `docs/admin-guide/01-users-roles.md`, `docs/admin-guide/04-tax-config.md`, `docs/admin-guide/05-backup-restore.md`, `docs/runbook/01-monthly-close.md`, `docs/runbook/02-yearly-close.md`, `docs/runbook/03-vat-filing.md`, `docs/runbook/05-einvoice-flow.md`, `docs/runbook/07-troubleshooting.md`, `docs/runbook/deployment-observability.md`, `docs/runbook/pre-deploy-test-plan.md`, `docs/runbook/test-report-v3.2.md`, `docs/user-guide/10-einvoice.md`.

All use "PMKetoan" (no diacritics, no space).

### 1.6 Tests Using "PMKetoan"

| File | Context |
|------|---------|
| `tests/test_middleware.py` | `assert req.brand['name'] == 'PMKetoan'` |
| `tests/test_login_view.py` | `assert 'PMKetoan' in content` |
| `tests/test_company_model.py` | `assert c.hide_pmketoan_branding is False` |
| `tests/test_pkm_interaction_sync_fallback.py` | `{"name": "PMKetoan", ...}` (4 occurrences) |
| `tests/e2e/test_00_login.py` | `assert "PMKetoan" in title or "Đăng nhập" in title` |

---

## 2. "Visota" Occurrences (Already Rebranded)

These files already use **Visota** branding:

| File | Context |
|------|---------|
| `config/settings/prod.py` | `"""Production settings — visota.net ..."""`, `ALLOWED_HOSTS='visota.net,...'`, `DB_NAME='visota'`, `DB_USER='visota'`, `EMAIL_HOST_USER='noreply@visota.net'`, `DEFAULT_FROM_EMAIL='Visota <...>'`, `Q_CLUSTER name='visota'` |
| `.env.example` | `# Visota — Production Environment`, all DB/email/paths use `visota` |
| `templates/public/landing.html` | Full landing page branded as **Visota** — hero, pricing, personas, footer, meta tags, `visota.net` |
| `templates/public/signup.html` | Branded as **Visota** — navbar, multi-step wizard |
| `templates/public/terms.html` | Branded as **Visota** — `legal@visota.net` |
| `templates/public/privacy.html` | Branded as **Visota** — `privacy@visota.net`, `security@visota.net` |
| `scripts/server/visota-ctl` | Filename |
| `scripts/visota.service` | Filename |
| `scripts/visota-worker.service` | Filename |
| `scripts/deploy.sh` | Deploy script uses Visota naming |
| `docs/strategy/go-to-market-startup-niche.md` | Full GTM strategy positioned as **Visota** |
| `docs/strategy/feature-gap-analysis-startup.md` | Feature analysis positioned as **Visota** |
| `docs/runbook/deploy-vps.md` | VPS deploy guide uses Visota |
| `apps/ui_modern/views/migration_views.py` | References Visota |

### Pricing on Landing Page (already Visota-branded)
- **Khởi đầu**: 299K/tháng — 3 users, 1 company
- **Doanh nghiệp** (popular): 899K/tháng — 20 users, 3 companies, all 31 modules
- **Enterprise**: Liên hệ — unlimited

### Pricing in Terms Page (Visota-branded)
- **Miễn phí**: Revenue < 1 tỷ VND/year
- **Professional**: 3,990,000 VND/year
- **Enterprise**: 9,990,000 VND/year

---

## 3. Login Page

**File**: `templates/modern/auth/login.html`

- **Standalone page** (does NOT extend layout.html)
- Shows `{{ brand.name }}` in logo area (resolves to "PMKetoan" via DEFAULT_BRAND)
- Shows `{{ brand.logo }}` if available (resolves to `/static/images/logo.svg` — shows letter "P")
- **No marketing tagline or positioning copy** — just username/password form
- Footer: `© 2026 {{ brand.name }}`
- Title: `Đăng nhập — {{ brand.name }}`
- No "forgot password" link
- No social login options
- Uses `static/modern/css/auth.css` for styling

**View**: `apps/ui_modern/views/auth_views.py` → `PMKetoanLoginView`
- URL: `/auth/login/`
- Redirects to `/modern/` (dashboard) on success
- Uses `LoginForm` from `apps/ui_modern/forms/auth_forms.py`

---

## 4. Sidebar / Navigation Structure

**File**: `templates/modern/base/layout.html` (single file, ~52KB)

The sidebar is permission-gated using `{% has_module_access "module_name" %}` template tags. Sections are collapsible (Alpine.js) with localStorage persistence.

### Top-level items:
1. **Trang chủ** (Dashboard) — always visible

### Collapsible sections:
2. **Dự án** (Projects) — gated by `projects` module
3. **Ghim** (Pinned items) — dynamic, JS-driven
4. **Cập nhật số liệu** (Data Entry):
   - Phiếu kế toán (Vouchers)
   - Phiếu thu (Cash Receipt)
   - Phiếu chi (Cash Payment)
   - Ngân hàng & Đối soát (Banking)
   - Bảo lãnh ngân hàng (Guarantees)
   - Vay vốn ngân hàng (Loans)
   - Hóa đơn đầu vào (Input Invoices)
   - Bút toán định kỳ (Recurring)

5. **Nghiệp vụ** (Operations):
   - Khách hàng (Customers)
   - Nhà cung cấp (Vendors)
   - Hàng hóa (Products)
   - Cơ hội đấu thầu (Bidding)
   - Hóa đơn bán (Sales Invoices)
   - Phiếu nhập mua (Purchase Invoices)
   - Phiếu nhập xuất (Stock)
   - Tổng quan kho (Stock Dashboard)
   - Kiểm kê (Stock Adjustment)
   - Thẻ kho (Stock Card)
   - Hợp đồng (Contracts)
   - Mẫu hợp đồng (Contract Templates)

6. **CRM** (hidden for micro/small companies — uses `sme_size` check):
   - Khách tiềm năng (Leads)
   - Cơ hội bán hàng (Opportunities)
   - Chăm sóc KH (Tickets) — hidden if micro/small
   - Chiến dịch (Campaigns) — hidden if micro/small

7. **Tài sản** (Assets):
   - Tài sản cố định / CCDC
   - Tính khấu hao kỳ
   - Giao dịch tài sản

8. **Nhân sự** (HR):
   - Nhân viên, Hợp đồng lao động, Người phụ thuộc, Nghỉ phép, BHXH
   - Tính lương (Payroll)

9. **Sổ sách & Báo cáo** (Books & Reports) — largest section:
   - Sổ sách: NK chung, NK thu/chi, NK bán/mua, Sổ cái, Sổ chữ T, Sổ quỹ, Sổ TGNH, Sổ chi tiết bán hàng, Sổ chi tiết KH/NCC
   - Báo cáo & Thuế: HĐĐT, BCĐTK, BCTC B01, KQ HĐKD B02, Tờ khai GTGT, Bảng kê HĐ, D62, Lao động, Quỹ lương, TNCN, Giá thành, Sổ ĐK CTGS, BC dòng tiền
   - Ngân sách (Budget), Dự phóng dòng tiền
   - Tỷ giá ngoại tệ, Định giá lại

10. **Danh mục** (Master Data): Hệ thống TK, Bộ phận hạch toán
11. **Chứng từ ghi sổ** (CTGS): Khai báo, Đăng ký, Kiểm tra, Bảng kê
12. **Công cụ cuối kỳ** (Period Closing): Kết chuyển, Phân bổ, KK, Đánh số, Dư đầu, Chuyển số dư
13. **Tri thức cá nhân** (PKM): Tổng quan, Ghi chú, Tài liệu, Hỏi đáp AI, Tìm kiếm, Cấu hình AI
14. **Hệ thống** (System): Phê duyệt, Hồ sơ công ty, Thông báo, Vai trò, Người dùng, Quyền, Trợ giúp

### Mobile Bottom Nav:
- Trang chủ, Phiếu, Menu, Thông báo, Tài khoản

### Top Bar:
- Hamburger toggle
- Brand logo (linked to dashboard)
- Super Search (Ctrl+K command palette)
- Company switcher dropdown
- Notification bell with badge
- Settings gear
- User dropdown (Hồ sơ, Đăng xuất)

---

## 5. Dashboard

**View**: `apps/ui_modern/views/dashboard_views.py` → `DashboardView`
**Template**: `templates/modern/dashboard/index.html`
**URL**: `/modern/` (name: `ui_modern:dashboard`)

### Two view modes (toggle via `?view=` parameter):

**CEO View** (default):
- Cash position card (Tiền mặt + Ngân hàng breakdown)
- P&L card (revenue, expense, profit/loss this month)
- Tax deadline calendar (VAT 20th, PIT 20th, BHXH end-of-month)
- AR Aging matrix (current / 1-30 / 31-60 / 60+ days)
- AP total card
- Inventory value card
- Recent vouchers table

**Kế toán View** (`?view=accountant`):
- 4 stat cards: Chứng từ hôm nay, Công nợ KH, Công nợ NCC, Tồn kho
- Recent vouchers table
- Quick info sidebar (total/posted/draft counts)

### Quick Action Buttons (above dashboard):
- Tạo Phiếu, Hóa đơn, Hợp đồng, Ghi chi nhanh, Phê duyệt

### Mobile Home Screen (d-md-none):
- Compact 3-card row: Tiền, Doanh thu, Công nợ
- 4-button grid: Phiếu, Duyệt, Báo cáo, Thông báo

### Additional Dashboard:
- **Quick Expense** at `/modern/dashboard/quick-expense/` — 1-line expense entry that auto-generates and posts a voucher

---

## 6. Settings / Configuration UI

### 6.1 Company Profile

**View**: `apps/ui_modern/views/company_views.py` → `CompanyProfileView`
**Template**: `templates/modern/admin/company_profile.html`
**URL**: `/modern/company-profile/` (name: `ui_modern:company_profile`)

**4 tabs:**
1. **Pháp lý** (Legal): Company name, short name, EN name, code, MST, phone, email, fax, address, GPKD info, website
   - **Chế độ kế toán** (Accounting Regime) dropdown:
     - `tt133` — TT133/2016 (DN nhỏ và vừa)
     - `tt200` — TT200/2014 (DN lớn)
     - `q48` — QĐ48/2006 (cũ)
   - **Quy mô DN** (SME Size) dropdown:
     - `micro` — Siêu nhỏ
     - `small` — Nhỏ
     - `medium` — Vừa
     - `large` — Lớn

2. **Đại diện** (Representatives): Legal rep info, chief accountant info

3. **Ngân hàng** (Bank Accounts): Dynamic JSON rows (bank, branch, account, holder)

4. **Thương hiệu** (Branding):
   - Logo upload, Logo dark mode, Favicon, Company stamp
   - Color pickers: brand_primary_color (default `#2563eb`), brand_accent_color (default `#16a34a`)
   - Brand name override
   - Facebook, LinkedIn, Zalo OA links

### 6.2 Accounting Regime Model

Defined in `apps/core/models.py` → `Company.AccountingRegime`:
- Default: `TT133` (for SMEs)
- Also has `TaxRateConfig` model with CIT rates tiered by company size:
  - `cit_rate_micro` = 15% (≤3 tỷ revenue)
  - `cit_rate_small` = 17% (3-50 tỷ)
  - `cit_rate_standard` = 20%

---

## 7. Existing Positioning & Marketing Copy

### 7.1 Landing Page (`templates/public/landing.html`) — Already "Visota"

**Hero headline**: "Vận hành doanh nghiệp, một hệ thống duy nhất"
**Sub-headline**: "Visota là nền tảng ERP toàn diện cho SME Việt Nam — kế toán, hóa đơn điện tử, CRM, HR, dự án, ngân hàng — vận hành trên 1 hệ thống, dữ liệu thông nhất theo thời gian thực."

**Trust stats**: 31+ modules, 5-minute setup, 25 roles, 712 tests

**Hero badge**: "Tuân thủ TT133 · TT200 · TT78/2021 · Luật Kế toán 2015"

**Persona targeting**: CEO/Owner, Kế toán trưởng, Sales/Account, HR/Manager

**CTA**: "Bắt đầu dùng thử" / "Khám phá tính năng"

**Footer**: visota.net, contact@visota.net, Hà Nội

### 7.2 Go-to-Market Strategy (`docs/strategy/go-to-market-startup-niche.md`)

Core positioning: **"Công cụ all-in-one miễn phí cho doanh nghiệp mới thành lập"**

3-tier upsell path:
- Year 1 (Revenue < 1 tỷ): FREE — basic TT133, HĐĐT, CRM, 5 contracts, 2 users
- Year 2-3 (1-10 tỷ): Professional 3.99M VND/year — HR, payroll, banking, all 21 contracts, 5 users
- Year 3+ (10 tỷ+): Enterprise 9.99M VND/year — Projects, bidding, FX, API, 15 users

### 7.3 In-App Positioning

The in-app UI has **minimal marketing copy**. There is no "about" page within the authenticated app. The right sidebar shows `PMKetoan v0.8` as system version info. The help index (`templates/modern/help/index.html`) is a simple article directory.

---

## 8. Branding System Architecture

### 8.1 Middleware Chain

```
TenantMiddleware → detects layout (modern/classic/mobile/portal) + current company
BrandingMiddleware → builds request.brand dict from company or DEFAULT_BRAND
```

### 8.2 Context Processor

`apps/core/context_processors.py` → `branding()` exposes to all templates:
- `{{ brand.name }}` — Display name
- `{{ brand.logo }}` — Logo URL
- `{{ brand.primary_color }}` — Primary hex color
- `{{ brand.accent_color }}` — Accent hex color
- `{{ brand.favicon }}`
- `{{ brand.custom_css }}`
- `{{ brand.hide_pmketoan_branding }}`

### 8.3 DEFAULT_BRAND (`apps/core/middleware.py`)

```python
DEFAULT_BRAND = {
    "name": "PMKetoan",
    "logo": "/static/images/logo.svg",
    "logo_dark": "/static/images/logo-dark.svg",  # NOTE: file does not exist
    "primary_color": "#2563eb",     # Blue
    "accent_color": "#16a34a",      # Green
    "favicon": "/static/images/favicon.ico",  # NOTE: file does not exist
    "hide_pmketoan_branding": False,
    "custom_css": "",
}
```

### 8.4 White-Label System

The `Company` model supports per-tenant branding override:
- `brand_name`, `brand_logo`, `brand_logo_dark`, `brand_favicon`, `company_stamp`
- `brand_primary_color`, `brand_accent_color`, `brand_sidebar_color`
- `hide_pmketoan_branding` — boolean to hide all PMKetoan/Visota branding
- `custom_css` — tenant-specific CSS injection
- `custom_domain` — custom domain support

**Migration note**: Renaming `hide_pmketoan_branding` requires a Django migration. The DB column name is `hide_pmketoan_branding`.

---

## 9. Files NOT Found (Referenced but Missing)

- `static/images/logo-dark.svg` — referenced in DEFAULT_BRAND but file does not exist
- `static/images/favicon.ico` — referenced in DEFAULT_BRAND but file does not exist
- `static/icons/apple-touch-icon.png` — exists (354 bytes, likely placeholder)

---

## 10. Summary: What Needs to Change for Visota ERP Rebranding

### Critical (User-visible):
1. `apps/core/middleware.py` — Change `DEFAULT_BRAND["name"]` from "PMKetoan" to "Visota ERP"
2. `static/manifest.json` — Change `name`, `short_name`, `description`
3. `static/images/logo.svg` + `static/icons/*.svg` — Replace "P" logo with Visota "V" logo
4. `static/sw.js` — Update cache version string, notification default title, comment
5. `templates/modern/base/layout.html` — Update `apple-mobile-web-app-title`, meta description, PWA install banner
6. `templates/modern/base/_right_sidebar.html` — Update "PMKetoan v0.8" version string
7. `templates/modern/reporting/report_export_pdf.html` — Update PDF footer brand
8. `templates/public/blog_list.html` + `blog_detail.html` — Rebrand navbar, title, footer, CTA
9. `apps/core/api.py` — Change NinjaAPI `title="PMKetoan API"` to `"Visota ERP API"`
10. `apps/notifications/services.py` — Change fallback email domain

### Schema (requires migration):
11. `apps/core/models.py` — Rename `hide_pmketoan_branding` field → `hide_visota_branding` (needs migration)
12. `apps/core/middleware.py` — Update field references

### Python class renames (low risk, internal):
13. `apps/ui_modern/views/auth_views.py` — `PMKetoanLoginView` → `VisotaLoginView`, `PMKetoanLogoutView` → `VisotaLogoutView`
14. `config/urls.py` — Update imports
15. `apps/ui_modern/views/__init__.py` — Update exports

### Settings/Config:
16. `config/settings/base.py` — Update docstring, DB defaults, Q_CLUSTER name
17. `config/settings/dev.py` — Update Q_CLUSTER name
18. `config/settings/test.py` — Update test DB name
19. `pyproject.toml` — Update project name/description
20. `.devcontainer/devcontainer.json` — Update name and DB env
21. `docker-compose.dev.yml` — Update container names and DB env
22. `.github/workflows/ci.yml` — Update DB env
23. `.github/workflows/deploy.yml` — Update Docker image name
24. `.github/ISSUE_TEMPLATE/bug_report.md` — Update label
25. `.github/labels.yml`, `.pre-commit-config.yaml` — Update comments

### Deploy/Infra:
26. `deploy/systemd/pmketoan-*.service` — Rename files + update content
27. `deploy/nginx/pmketoan.conf` — Rename + update
28. `scripts/install_vendor_assets.sh` — Update tmp dir name

### Docs (bulk text replacement):
29. All files in `docs/` — Replace PMKetoan → Visota ERP
30. `README.md`, `AGENTS.md`, `CODEOWNERS`, `PROMPT_FIX_DEPLOY.md`

### Tests:
31. `tests/test_middleware.py` — Update brand name assertion
32. `tests/test_login_view.py` — Update content assertion
33. `tests/test_company_model.py` — Update field name
34. `tests/test_pkm_interaction_sync_fallback.py` — Update Q_CLUSTER name
35. `tests/e2e/test_00_login.py` — Update title assertion

### Missing assets to create:
36. `static/images/logo-dark.svg` — Dark mode Visota logo
37. `static/images/favicon.ico` — Visota favicon
38. Replace all `static/icons/*.svg` with "V" branded icons
