# Phase 1A — Physical Structure Discovery

## Project Overview

**Project:** Visota ERP — Vietnamese accounting software for micro and small enterprises
**Framework:** Django 5.2 (single monolith) + django-ninja 1.2 (REST API) + HTMX (frontend interactivity)
**Database:** MariaDB / MySQL (`django.db.backends.mysql`, utf8mb4, `STRICT_TRANS_TABLES`)
**Python:** 3.12+, line length 100 (ruff), mypy strict mode enabled
**Auth model:** `AUTH_USER_MODEL = 'identity.User'` (custom user extending `AbstractUser`)
**Auth backends:** Axes (brute-force protection) → `RoleBasedBackend` (custom) → Django `ModelBackend`
**Cache:** Django DB cache (`DatabaseCache`, table `django_cache`) — no Redis in base config
**Sessions:** `cached_db` session engine
**Task queue:** django-q2 (broker = Django ORM, 4 workers, 600s timeout)
**Static files:** WhiteNoise (compressed + manifest)
**Language:** Vietnamese (`vi`) primary, English (`en`) secondary. Time zone `Asia/Ho_Chi_Minh`.
**Compliance targets:** TT133/2016, TT200/2014, TT78/2021 (Vietnamese accounting regulations)

### Key middleware (in order)
1. `SecurityMiddleware`
2. `WhiteNoiseMiddleware`
3. `SessionMiddleware`
4. `CommonMiddleware`
5. `CsrfViewMiddleware`
6. `AuthenticationMiddleware`
7. `MessageMiddleware`
8. `XFrameOptionsMiddleware`
9. `AxesMiddleware` — brute-force lockout
10. `apps.identity.middleware_request_id.RequestIDMiddleware` — correlation IDs
11. `apps.core.middleware.TenantMiddleware` — multi-company tenant scoping
12. `apps.core.middleware.BrandingMiddleware` — white-label theming
13. `apps.identity.middleware.ModulePermissionMiddleware` — per-module RBAC
14. `apps.pkm.middleware.PKMInteractionMiddleware` — logs user interactions for the PKM/RAG module

### REST framework config
- **django-ninja** `NinjaAPI` instance in `apps/core/api.py`, mounted at `/api/v1/` (namespace `api_v1`).
- Session (cookie) auth for browsers; `X-API-Key` header (`pmk_`-prefixed) for service-to-service.
- JWT support noted as planned for Phase 2.
- Sub-routers: `apps.ledger.dnsn_api.register_dnsn_endpoints(api)` (DNSN voucher CRUD), `apps.pkm.api.router` mounted at `/api/v1/pkm/`.

## Table A — Module Inventory (from INSTALLED_APPS)

App counts below are derived from grepping class definitions in `apps/<app>/models*`, `apps/<app>/views*`, `apps/<app>/services*`, and `apps/<app>/management/commands/*.py` (excluding `__init__.py`). Django contrib / third-party apps are listed separately.

### Local Visota apps (30 apps in `apps/`)

| # | App | Type | #models | #views | #services | #cmds | Has urls | Notes |
|---|-----|------|--------:|-------:|----------:|------:|:--------:|-------|
| 1 | `apps.core` | core | 7 | 0 | 2 | 6 | no (hosts `api.py` at `/api/v1/`) | Foundation: `Company`, tax configs, `CompanyOwnedModel` base, feature flags, search affinity. Holds the django-ninja `api` instance. |
| 2 | `apps.identity` | core | 4 | 0 | 1 | 1 | no | `User`, `Role`, `Permission`, `UserCompanyRole`. Auth backends, RBAC middleware, request-ID middleware. |
| 3 | `apps.master_data` | core | 9 | 0 | 0 | 3 | no | `Customer`, `Vendor`, `Product`, `Warehouse`, `ChartOfAccounts`, `AccountType`, `ProductPrice`, `ProductVariant`, `TaxRateCode`, `InvoiceGroup`. (10 concrete models; count includes `InvoiceGroup`.) |
| 4 | `apps.ledger` | domain | 6 | 0 | 4 | 0 | no (has `dnsn_api.py` sub-router) | Core accounting: `AccountingVoucher`, `VoucherLine`, `AccountPeriodBalance`, `DnsnVoucher`, `DnsnLedgerEntry`, `DnsnLedgerBalance`. Posting & period-closing services. |
| 5 | `apps.pkm` | domain | 8 | 0 | 8 | 0 | no (has `api.py` router at `/api/v1/pkm/`) | Personal Knowledge Management / RAG: `PKMDocument`, `DocumentChunk`, `Embedding`, `KnowledgeNote`, `Tag`, `QAHistory`, `UserLLMConfig`, `UserInteractionLog`. LLM, vector store, chunking, QA services. Has its own middleware. |
| 6 | `apps.sales` | domain | 2 | 0 | 1 | 0 | no | `SalesInvoice`, `SalesInvoiceLine`. |
| 7 | `apps.purchasing` | domain | 2 | 0 | 1 | 0 | no | `PurchaseInvoice`, `PurchaseInvoiceLine`. |
| 8 | `apps.inventory` | domain | 6 | 0 | 2 | 0 | no | `StockVoucher`, `StockVoucherLine`, `StockLedger`, `StockAdjustment`, `StockAdjustmentLine`, `StockAlert`. |
| 9 | `apps.assets` | domain | 5 | 0 | 2 | 0 | no | Fixed assets: `FixedAsset`, `AssetCategory`, `AssetUsingDepartment`, `AssetDepreciation`, `AssetTransaction`. |
| 10 | `apps.hr` | domain | 8 | 0 | 1 | 0 | no | `Department`, `Position`, `Employee`, `LaborContract`, `Dependent`, `InsuranceContribution`, `LeaveRecord`, `LeaveBalance`. |
| 11 | `apps.payroll` | domain | 3 | 0 | 1 | 0 | no | `AttendanceRecord`, `PayrollRun`, `PayrollLine`. |
| 12 | `apps.reporting` | domain | 2 | 0 | 7 | 2 | no | `FinancialReportLine`, `VATReportLine`. Balance sheet, P&L, VAT return, cash flow, DNSN report, HR report services. |
| 13 | `apps.documents` | domain | 2 | 0 | 4 | 0 | no | `VoucherDocument`, `Attachment`. Print, DOCX export, attachment services. |
| 14 | `apps.contracts` | domain | 3 | 0 | 2 | 1 | no | `Contract`, `ContractTemplate`, `Minutes`. Template + print services, seeder. |
| 15 | `apps.input_docs` | domain | 1 | 0 | 1 | 0 | no | `InputInvoice` (vendor invoice ingestion + extraction). |
| 16 | `apps.recurring` | domain | 1 | 0 | 1 | 0 | no | `RecurringTemplate`. |
| 17 | `apps.projects` | domain | 4 | 0 | 1 | 0 | no | `Project`, `ProjectPhase`, `ProjectResource`, `ProjectTransaction`. |
| 18 | `apps.crm` | domain | 10 | 0 | 1 | 0 | no | `CRMLead`, `CRMAccount`, `CRMContact`, `Opportunity`, `OpportunityLine`, `Activity`, `Ticket`, `TicketResponse`, `Campaign`, `CampaignMember`. |
| 19 | `apps.notifications` | support | 2 | 4 | 1 | 1 | yes (`/notifications/`) | `Notification`, `EmailLog`. Only domain app besides `public` with its own UI views wired into root urls. |
| 20 | `apps.approvals` | domain | 3 | 5 | 1 | 0 | yes (has `urls.py`, not included in `config/urls.py`) | `ApprovalRule`, `ApprovalRequest`, `ApprovalStep`. Views re-exported via `ui_modern`. |
| 21 | `apps.einvoice` | domain | 2+ | 8 | 1 | 0 | yes (has `urls.py`, not included in `config/urls.py`) | E-invoice: `EInvoice`, `EInvoiceConfig`, `EInvoiceReportBatch` + provider/form/category TextChoices. Views re-exported via `ui_modern`. |
| 22 | `apps.banking` | domain | 4 | 7 | 1 | 0 | yes (has `urls.py`, not included in `config/urls.py`) | `BankAccount`, `BankStatementImport`, `BankTransaction`, `ReconciliationMatch`. VietQR service. Views re-exported via `ui_modern`. |
| 23 | `apps.guarantees` | domain | 1 | 1 | 0 | 0 | yes (has `urls.py`, not included in `config/urls.py`) | `BankGuarantee`. Thin — single list view. |
| 24 | `apps.loans` | domain | 4 | 1 | 0 | 0 | yes (has `urls.py`, not included in `config/urls.py`) | `BankLoan`, `LoanDisbursement`, `LoanRepayment`, `LoanInterestAccrual`. Thin — single list view. |
| 25 | `apps.bidding` | domain | 5 | 3 | 1 | 0 | yes (has `urls.py`, not included in `config/urls.py`) | `BidOpportunity`, `BidSubmission`, `BidResult`, `BidDocument`, `ContractorProfile`. Views re-exported via `ui_modern`. |
| 26 | `apps.budget` | domain | 3 | 6 | 1 | 0 | yes (has `urls.py`, not included in `config/urls.py`) | `Budget`, `BudgetLine`, `CashFlowProjection`. Views re-exported via `ui_modern`. |
| 27 | `apps.fx` | domain | 3 | 3 | 1 | 0 | yes (has `urls.py`, not included in `config/urls.py`) | `Currency`, `ExchangeRate`, `FxRevaluationBatch`. Views re-exported via `ui_modern`. |
| 28 | `apps.costing` | domain | 0 | 0 | 1 | 0 | no | Cost accounting logic only (service in `services/__init__.py`). No own models — reads from ledger `VoucherLine`. Exposed via `ui_modern` `CostReportView`. |
| 29 | `apps.public` | support | 4 | 7 | 0 | 1 | yes (`/` namespace `public`) | Landing page + blog: `BlogCategory`, `BlogArticle`, `ContactRequest`, `NewsletterSubscriber`. |
| 30 | `apps.ui_modern` | ui | 0 | ~170 (across 50 view modules) | 0 | 0 | yes (`/modern/`) | UI layer: aggregates views from all domain apps via `views/__init__.py` and wires ~230 URL patterns. Forms, templates, health checks, login/logout. No own models. |

**Totals (local apps):** ~97 concrete models · ~219 view classes/functions · ~42 service modules · ~15 management commands.

### Third-party apps
| App | Purpose |
|-----|---------|
| `django.contrib.admin` | Django admin |
| `django.contrib.auth` | Built-in auth (supplemented by `apps.identity`) |
| `django.contrib.contenttypes` | Content types framework |
| `django.contrib.sessions` | Session framework (engine: `cached_db`) |
| `django.contrib.messages` | Messaging framework |
| `django.contrib.staticfiles` | Static files |
| `django.contrib.humanize` | Template filters |
| `django_extensions` | Dev utilities (`shell_plus`, `runserver_plus`, etc.) |
| `django_q` | django-q2 async task queue (ORM broker) |
| `axes` | Brute-force login protection |

`django_debug_toolbar` and `django_allauth` are listed as dependencies in `pyproject.toml` but are **not** in `INSTALLED_APPS` in `base.py` (debug toolbar is conditionally added when `DEBUG` is true and present in `INSTALLED_APPS`; allauth is declared as a dependency but not registered here).

## URL-to-App Map

URL routing is heavily centralized: `config/urls.py` mounts only **5 includes** plus a handful of top-level views. The vast majority of application URLs live under `/modern/` and are served by `apps/ui_modern`.

| Path prefix | Includes | Owning app(s) |
|-------------|----------|---------------|
| `/admin/` | `admin.site.urls` | Django admin |
| `/auth/login/`, `/auth/logout/` | direct views | `apps.ui_modern.views.auth_views` |
| `/health/`, `/health/detailed/` | direct functions | `apps.ui_modern.views.health_views` |
| `/no-access/`, `/offline/` | `TemplateView` | static templates |
| `/notifications/` | `apps.notifications.urls` | `apps.notifications` |
| `/` (root) | `apps.public.urls` (namespace `public`) | `apps.public` (landing, blog, contact) |
| `/switch-company/` | direct view | `apps.ui_modern.views.company_switch` |
| `/app/` | `RedirectView` → `/modern/` | redirect only |
| `/modern/` | `apps.ui_modern.urls` (app_name `ui_modern`) | **All domain apps** — views are aggregated in `ui_modern.views.__init__` |
| `/api/v1/` | `apps.core.api.api.urls` (django-ninja) | `apps.core` (vouchers, master data, sales, reports, e-invoice) + `apps.ledger` (DNSN sub-router) + `apps.pkm` (PKM sub-router) |

### `/modern/` sub-paths (served by `ui_modern`, backed by domain apps)
- `/modern/` — dashboard, quick expense, global search, attachments, admin (roles/users/company/migration)
- `/modern/approvals/` — `apps.approvals`
- `/modern/einvoices/` — `apps.einvoice`
- `/modern/banking/`, `/modern/guarantees/`, `/modern/loans/` — `apps.banking`, `apps.guarantees`, `apps.loans`
- `/modern/bidding/` — `apps.bidding`
- `/modern/budget/`, `/modern/cash-flow/` — `apps.budget`
- `/modern/fx/` — `apps.fx`
- `/modern/vouchers/`, `/modern/dnsn-vouchers/`, `/modern/dnsn-ledgers/`, `/modern/dnsn-reports/`, `/modern/dnsn-conversion/` — `apps.ledger`
- `/modern/customers/`, `/modern/vendors/`, `/modern/products/`, `/modern/chart-of-accounts/` — `apps.master_data`
- `/modern/sales-invoices/` — `apps.sales`
- `/modern/purchase-invoices/`, `/modern/input-invoices/` — `apps.purchasing`, `apps.input_docs`
- `/modern/stock-vouchers/`, `/modern/inventory/` — `apps.inventory`
- `/modern/assets/` — `apps.assets`
- `/modern/employees/`, `/modern/labor-contracts/`, `/modern/dependents/`, `/modern/leave/`, `/modern/insurance/` — `apps.hr`
- `/modern/payroll/` — `apps.payroll`
- `/modern/reports/` (trial balance, balance sheet, P&L, VAT, general journal/ledger, cash flow, sub-ledger, cost, book entry, specialized journals, T-account, export) — `apps.reporting`, `apps.costing`, `apps.ledger`, `apps.master_data`
- `/modern/contracts/`, `/modern/contract-templates/` — `apps.contracts`
- `/modern/recurring/` — `apps.recurring`
- `/modern/projects/` — `apps.projects`
- `/modern/crm/` (leads, accounts, opportunities, tickets, campaigns) — `apps.crm`
- `/modern/closing/`, `/modern/tools/` (year-end, period allocation, voucher renumber, opening balances) — `apps.ledger` closing services
- `/modern/treasury/` — `apps.ledger` (cash receipt/payment vouchers)
- `/modern/ctgs/`, `/modern/departments/` — `apps.ledger` source-doc scheduling, `apps.hr` department master
- `/modern/knowledge/` (notes, search, QA, LLM config, documents) — `apps.pkm`
- `/modern/help/` — help articles (from `apps.public` seed)

### `/api/v1/` sub-paths (django-ninja)
- `/api/v1/vouchers/`, `/api/v1/vouchers/{id}`, `/api/v1/vouchers/{id}/post` — `apps.ledger`
- `/api/v1/customers/`, `/api/v1/vendors/`, `/api/v1/products/` — `apps.master_data`
- `/api/v1/sales/invoices/`, `/api/v1/sales/invoices/{id}` — `apps.sales`
- `/api/v1/reports/trial-balance`, `/api/v1/reports/ar-aging`, `/api/v1/reports/cash-position` — `apps.reporting` / `apps.ledger`
- `/api/v1/einvoice/issue/{id}`, `/api/v1/einvoice/{id}/publish` — `apps.einvoice`
- `/api/v1/dnsn/...` (registered via `register_dnsn_endpoints`) — `apps.ledger`
- `/api/v1/pkm/...` (notes, llm-configs, documents, ask, search, stats) — `apps.pkm`

## Dead/Placeholder Apps

**No fully dead apps were found.** Every app in `INSTALLED_APPS` has at least one of: models, services, views, or management commands, and is wired into either the UI (`ui_modern`) or the API (`core.api`).

Apps that are **thin / single-purpose** (worth flagging for consolidation review, but not dead):

| App | Concern |
|-----|---------|
| `apps.costing` | **No models, no views, no urls.** Single service module (`services/__init__.py`) implementing cost aggregation against ledger `VoucherLine`. Exposed only through `ui_modern`'s `CostReportView`. Candidate for merging into `apps.reporting` or `apps.ledger`. |
| `apps.guarantees` | 1 model (`BankGuarantee`), 1 list view, 0 services. Re-uses `ui_modern` for all UI. Very thin. |
| `apps.loans` | 4 models, 1 list view, 0 services. All UI routed through `ui_modern`. Thin services layer. |
| `apps.input_docs` | 1 model (`InputInvoice`), 1 service (extraction). No own views/urls — UI via `ui_modern`. Narrow scope but coherent. |
| `apps.recurring` | 1 model, 1 service, no own views/urls. Thin but self-contained. |

Apps whose own `urls.py` is **not included in `config/urls.py`** (their views are re-exported through `apps.ui_modern.views.__init__` and routed under `/modern/`): `approvals`, `einvoice`, `banking`, `guarantees`, `loans`, `bidding`, `budget`, `fx`. The per-app `urls.py` files appear to be vestigial / alternate entry points that are currently unused at the root level.

## Key Configuration

### INSTALLED_APPS (43 entries: 10 contrib/3rd-party + 30 local + 3 implicit)

**Django contrib (7):** `admin`, `auth`, `contenttypes`, `sessions`, `messages`, `staticfiles`, `humanize`

**Third-party (3):** `django_extensions`, `django_q`, `axes`

**Local — shared backend / foundation (3):** `apps.core`, `apps.identity`, `apps.master_data`

**Local — domain apps (22):** `apps.ledger`, `apps.pkm`, `apps.sales`, `apps.purchasing`, `apps.inventory`, `apps.assets`, `apps.hr`, `apps.payroll`, `apps.reporting`, `apps.documents`, `apps.contracts`, `apps.input_docs`, `apps.recurring`, `apps.projects`, `apps.crm`, `apps.notifications`, `apps.approvals`, `apps.einvoice`, `apps.banking`, `apps.guarantees`, `apps.loans`, `apps.bidding`, `apps.budget`, `apps.fx`, `apps.costing`, `apps.public`

**Local — UI layer (1):** `apps.ui_modern`

> The `pyproject.toml` `[tool.importlinter]` contract defines an enforced layered architecture:
> - Layer 1 (top): `apps.ui_modern`
> - Layer 2 (domain, feature apps): `banking`, `bidding`, `budget`, `contracts`, `crm`, `einvoice`, `fx`, `guarantees`, `inventory`, `loans`, `notifications`, `payroll`, `projects`, `public`, `purchasing`, `recurring`, `sales`, `input_docs`
> - Layer 3 (domain, core services): `ledger`, `reporting`, `costing`, `hr`, `assets`, `documents`, `approvals`, `pkm`
> - Layer 4 (foundation): `master_data`, `core`, `identity`

### MIDDLEWARE (14 entries)
Standard Django middleware (security, sessions, common, CSRF, auth, messages, clickjacking) + `axes` + 5 Visota-specific middlewares:
- `apps.identity.middleware_request_id.RequestIDMiddleware` — request correlation IDs
- `apps.core.middleware.TenantMiddleware` — multi-company tenant scoping (sets `request.current_company`)
- `apps.core.middleware.BrandingMiddleware` — white-label theming
- `apps.identity.middleware.ModulePermissionMiddleware` — per-module RBAC enforcement
- `apps.pkm.middleware.PKMInteractionMiddleware` — PKM user-interaction logging

### Database config
- **Engine:** `django.db.backends.mysql` (MariaDB)
- **Default DB:** `visota` on `127.0.0.1:3306` (env-driven: `DB_NAME`, `DB_USER`, `DB_HOST`, `DB_PORT`)
- **Charset:** `utf8mb4`, `sql_mode='STRICT_TRANS_TABLES'`
- **Connection pooling:** `CONN_MAX_AGE=60` (persistent connections)
- **No read replicas / multi-db configured** in `base.py`.

### Other notable config
- `DEFAULT_AUTO_FIELD = BigAutoField`
- `SESSION_ENGINE = cached_db` (DB-backed + cache)
- `CACHES` = `DatabaseCache` at `django_cache` (no Redis in base config; AGENTS.md mentions Redis via docker-compose but it is not wired in `base.py`)
- `LOGIN_URL = /auth/login/`, redirect to `/modern/`
- `AXES_FAILURE_LIMIT = 5`, cool-off 1 hour, reset on success
- `Q_CLUSTER` (django-q2): 4 workers, 600s timeout, ORM broker
- Templates: single `DIRS=[BASE_DIR/'templates']`, `APP_DIRS=True`. Context processors pull branding, user permissions, notifications, approvals.

---

*Generated by Phase 1A auto-scope evaluation. Source files inspected: `config/settings/base.py`, `config/urls.py`, `AGENTS.md`, `pyproject.toml`, all `apps/*/urls.py`, all `apps/*/models*`, all `apps/*/views*`, all `apps/*/services*`, all `apps/*/management/commands/*`.*
