# 03. Cấu trúc thư mục code chi tiết

> Layout đầy đủ của repo dự án PMKetoan.

## 1. Cấu trúc root

```
pmketoan/
├── apps/                          ← Django apps (xem chi tiết section 2)
├── config/                        ← Django project config
├── shared/                        ← Code dùng chung
├── templates/                     ← HTML templates
├── static/                        ← CSS/JS/images
├── locale/                        ← i18n files
├── tests/                         ← Tests (ngoài unit tests trong apps)
├── scripts/                       ← Utility scripts (deploy, backup, ...)
├── docs/                          ← Tài liệu (bộ này)
├── deploy/                        ← Deployment configs (systemd, nginx)
├── .github/                       ← GitHub Actions
├── requirements/                  ← Pip requirements
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── manage.py
├── pyproject.toml                 ← Project metadata (PEP 621) + uv config
├── uv.lock                        ← uv lock file
├── package.json                   ← Frontend deps (vendor assets)
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── Makefile                       ← Shortcut commands
├── README.md
├── CHANGELOG.md
├── LICENSE
└── CONTRIBUTING.md
```

## 2. Cấu trúc Django app chi tiết (ví dụ: `ledger`)

```
apps/ledger/
├── __init__.py
├── apps.py
│
├── models/
│   ├── __init__.py
│   ├── voucher.py                 ← AccountingVoucher, VoucherLine
│   ├── balance.py                 ← AccountOpeningBalance, AccountPeriodBalance
│   ├── closing.py                 ← ClosingTemplate, ClosingTemplateLine, ClosingRun
│   └── year_end.py                ← YearEndCarryForward
│
├── managers.py                    ← Custom QuerySets
├── validators.py                  ← Domain validators
├── signals.py                     ← Pre/post save signals
│
├── services/
│   ├── __init__.py
│   ├── voucher_service.py         ← CRUD voucher + business logic
│   ├── posting_service.py         ← Post/unpost voucher → update balances
│   ├── closing_service.py         ← Period closing
│   ├── year_end_service.py        ← Year-end carry-forward
│   ├── rebuild_service.py         ← Rebuild account_period_balance
│   └── reversal_service.py        ← Reversal voucher
│
├── api/
│   ├── __init__.py
│   ├── schemas.py                 ← Pydantic schemas
│   ├── vouchers.py                ← Voucher CRUD endpoints
│   ├── balances.py                ← Balance query endpoints
│   ├── closing.py                 ← Closing endpoints
│   └── reports.py                 ← Report endpoints
│
├── views/                         ← HTML views for HTMX
│   ├── __init__.py
│   ├── voucher_views.py
│   ├── balance_views.py
│   └── closing_views.py
│
├── forms/
│   ├── __init__.py
│   ├── voucher_form.py            ← Voucher form
│   └── voucher_line_formset.py    ← Voucher line formset
│
├── admin/
│   ├── __init__.py
│   ├── voucher_admin.py
│   └── balance_admin.py
│
├── tasks.py                       ← django-q2 tasks (async)
├── migrations/
│   ├── __init__.py
│   ├── 0001_initial.py
│   ├── 0002_voucher_index.py
│   └── ...
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                ← Fixtures specific
│   ├── factories.py               ← Factory Boy factories
│   ├── test_models.py
│   ├── test_voucher_service.py
│   ├── test_posting_service.py
│   ├── test_closing_service.py
│   ├── test_year_end_service.py
│   ├── test_api.py
│   └── test_views.py
│
└── README.md                      ← App-specific notes
```

## 3. Templates structure

```
templates/
├── base/
│   ├── base.html                  ← Master layout
│   ├── layout.html                ← Layout with sidebar/topbar
│   ├── navigation.html
│   ├── sidebar.html
│   ├── topbar.html
│   ├── footer.html
│   ├── pagination.html
│   ├── messages.html              ← Django messages
│   └── login_layout.html
│
├── components/                    ← Reusable components
│   ├── _badge.html
│   ├── _button.html
│   ├── _card.html
│   ├── _form_field.html
│   ├── _form_field_horizontal.html
│   ├── _grid.html                 ← Data grid wrapper
│   ├── _grid_pagination.html
│   ├── _modal.html
│   ├── _tabs.html
│   ├── _breadcrumb.html
│   ├── _empty_state.html
│   ├── _loading.html
│   ├── _alert.html
│   ├── _toast.html
│   └── _select2.html
│
├── registration/
│   ├── login.html
│   ├── logout.html
│   ├── password_reset.html
│   └── password_change.html
│
├── dashboard/
│   └── index.html
│
├── core/
│   ├── company_switch.html
│   └── ...
│
├── identity/
│   ├── user_list.html
│   ├── user_form.html
│   ├── user_detail.html
│   ├── role_list.html
│   └── ...
│
├── master_data/
│   ├── chart_of_accounts_list.html
│   ├── chart_of_accounts_form.html
│   ├── customer_list.html
│   ├── customer_form.html
│   ├── customer_detail.html
│   ├── vendor_list.html
│   ├── product_list.html
│   └── ...
│
├── ledger/
│   ├── voucher/
│   │   ├── list.html
│   │   ├── _list_rows.html        ← HTMX partial
│   │   ├── _detail.html           ← HTMX partial
│   │   ├── form.html
│   │   ├── _form_header.html
│   │   ├── _form_lines.html
│   │   ├── _form_actions.html
│   │   └── print.html
│   ├── balance/
│   │   ├── opening_balance.html
│   │   └── period_balance.html
│   └── closing/
│       ├── template_list.html
│       └── run_closing.html
│
├── treasury/
│   ├── cash_receipt_list.html
│   ├── cash_receipt_form.html
│   ├── cash_payment_list.html
│   ├── cash_payment_form.html
│   ├── bank_transaction_list.html
│   ├── advance_payment_list.html
│   └── ...
│
├── sales/
│   ├── invoice_list.html
│   ├── invoice_form.html
│   ├── invoice_detail.html
│   ├── customer_aging.html
│   └── ...
│
├── purchasing/
│   ├── invoice_list.html
│   ├── invoice_form.html
│   └── ...
│
├── inventory/
│   ├── product_list.html
│   ├── stock_voucher_list.html
│   ├── stock_card.html
│   └── ...
│
├── assets/
│   ├── asset_list.html
│   ├── asset_form.html
│   ├── depreciation_run.html
│   └── ...
│
├── hr/
│   ├── employee_list.html
│   ├── employee_form.html
│   ├── employee_detail.html
│   ├── _personal_info_tab.html
│   ├── _contract_tab.html
│   ├── _family_tab.html
│   └── ...
│
├── payroll/
│   ├── attendance_list.html
│   ├── leave_request_list.html
│   └── ...
│
├── reporting/
│   ├── trial_balance.html
│   ├── balance_sheet.html
│   ├── pnl.html
│   ├── cash_flow.html
│   ├── _report_filter.html
│   └── _export_buttons.html
│
├── tax/
│   ├── vat_return.html
│   ├── _vat_return_form.html
│   ├── output_listing.html
│   └── input_listing.html
│
└── errors/
    ├── 403.html
    ├── 404.html
    └── 500.html
```

## 4. Static files

```
static/
├── css/
│   ├── main.css                   ← Main stylesheet
│   ├── variables.css              ← CSS custom properties
│   ├── components.css             ← Component styles
│   ├── grid.css                   ← Grid (Tabulator) customization
│   ├── forms.css                  ← Form styles
│   ├── accounting.css             ← Accounting-specific (negative red, etc)
│   ├── print.css                  ← Print styles
│   └── vendor/
│       ├── bootstrap.min.css
│       ├── bootstrap-icons.min.css
│       ├── tabulator.min.css
│       └── select2.min.css
│
├── js/
│   ├── main.js                    ← Global JS
│   ├── htmx.config.js             ← HTMX configuration
│   ├── alpine.components.js       ← Alpine components
│   ├── utils.js                   ← Utility functions
│   ├── formatters.js              ← Number/date formatters
│   ├── validators.js              ← Client-side validators
│   ├── grid.config.js             ← Tabulator config
│   └── vendor/
│       ├── bootstrap.bundle.min.js
│       ├── htmx.min.js
│       ├── alpine.min.js
│       ├── tabulator.min.js
│       ├── chart.umd.min.js
│       ├── dayjs.min.js
│       └── select2.min.js
│
├── images/
│   ├── logo.svg
│   ├── logo-white.svg
│   ├── favicon.ico
│   ├── avatar-placeholder.png
│   └── ...
│
├── fonts/
│   ├── Be Vietnam Pro/           ← Vietnamese font
│   │   ├── BeVietnamPro-Regular.woff2
│   │   ├── BeVietnamPro-Medium.woff2
│   │   └── BeVietnamPro-Bold.woff2
│   └── JetBrains Mono/           ← Monospace cho numbers
│       └── JetBrainsMono-Regular.woff2
│
└── reports/                       ← Report templates (HTML/PDF)
    ├── trial_balance_template.html
    ├── balance_sheet_template.html
    ├── pnl_template.html
    ├── cash_flow_template.html
    ├── vat_return_template.html
    └── voucher_print_template.html
```

## 5. Config structure

```
config/
├── __init__.py
├── settings/
│   ├── __init__.py
│   ├── base.py                    ← Settings chung
│   ├── dev.py                     ← Development
│   ├── test.py                    ← Testing
│   ├── staging.py                 ← Staging
│   └── prod.py                    ← Production
├── urls.py                        ← Root URL routing
├── wsgi.py                        ← WSGI entry
├── asgi.py                        ← ASGI entry
├── api.py                         ← django-ninja API instance
└── initial_data/
    ├── tt133_chart_of_accounts.json
    ├── tt200_chart_of_accounts.json
    ├── currencies.json
    ├── provinces.json
    ├── districts.json
    ├── wards.json
    ├── countries.json
    ├── hr_dictionaries.json
    └── ...
```

## 6. Shared code

```
shared/
├── __init__.py
├── models.py                      ← Abstract base models (TimestampedModel, etc)
├── middleware/
│   ├── __init__.py
│   ├── tenant.py                  ← TenantMiddleware
│   ├── audit_log.py               ← AuditLogMiddleware
│   └── request_context.py         ← Thread-local context
├── permissions.py                 ← Base permission classes
├── exceptions.py                  ← Custom exceptions
├── pagination.py                  ← Custom pagination
├── renderers.py                   ← Custom renderers
├── response.py                    ← Response envelope
├── value_objects.py               ← Money, DateRange, etc
├── decimal_utils.py               ← Decimal helpers
├── date_utils.py                  ← Date helpers (fiscal period, etc)
├── tax_utils.py                   ← VAT/TNDN/PIT calculations
├── exchange.py                    ← Exchange rate service
├── pdf.py                         ← PDF helpers
├── excel.py                       ← Excel helpers
├── xml.py                         ← XML helpers (for e-invoice)
├── crypto.py                      ← Cryptography helpers
└── validators.py                  ← Common validators (tax_code, etc)
```

## 7. Tests structure

```
tests/
├── __init__.py
├── conftest.py                    ← Global fixtures
├── factories/                     ← Factory Boy
│   ├── __init__.py
│   ├── company_factory.py
│   ├── user_factory.py
│   ├── voucher_factory.py
│   ├── customer_factory.py
│   └── ...
├── unit/
│   ├── test_decimal_utils.py
│   ├── test_tax_utils.py
│   └── ...
├── integration/
│   ├── test_voucher_workflow.py
│   ├── test_period_closing.py
│   └── ...
├── e2e/
│   ├── test_login.py
│   ├── test_create_voucher.py
│   └── ...
├── performance/
│   ├── test_voucher_list_perf.py
│   └── ...
└── fixtures/
    ├── sample_company.json
    ├── sample_chart_of_accounts.json
    └── sample_vouchers.json
```

## 8. Deploy structure (server-side configs)

Không dùng Docker. Các file config được lưu trong repo để copy lên server khi deploy:

```
deploy/
├── nginx/
│   ├── pmketoan.conf              ← Nginx vhost
│   └── snippets/
│       ├── proxy_params.conf
│       └── ssl.conf
├── systemd/
│   ├── pmketoan-web.service       ← Gunicorn unit
│   └── pmketoan-qcluster.service  ← django-q2 cluster unit
├── mariadb/
│   └── 50-server.cnf              ← MariaDB server config
├── logrotate/
│   └── pmketoan                   ← Log rotation config
└── README.md                      ← Hướng dẫn deploy step-by-step
```

Setup script (`scripts/setup_server.sh`) copy các file này vào đúng vị trí trên server và enable systemd units.

## 9. Deployment structure

```
deploy/
├── kubernetes/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml                   ← Horizontal Pod Autoscaler
│   ├── pdb.yaml                   ← Pod Disruption Budget
│   └── kustomize/
│       ├── base/
│       └── overlays/
│           ├── dev/
│           ├── staging/
│           └── prod/
├── helm/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
└── ansible/                       ← Optional: for on-premise deployment
    ├── inventory/
    └── playbooks/
```

## 10. Scripts

```
scripts/
├── setup_dev.sh                   ← Setup dev environment
├── install_vendor_assets.sh       ← Install vendor CSS/JS
├── backup_db.sh                   ← DB backup
├── restore_db.sh                  ← DB restore
├── seed_demo_data.py              ← Generate demo data
├── load_initial_master_data.py    ← Load chart of accounts, currencies, ...
├── migrate_tt133_to_tt200.py      ← Migration script (nếu cần)
├── benchmark_voucher_list.py      ← Performance test
└── lint.sh                        ← Run all linters
```

## 11. Documentation

```
docs/
├── README.md                      ← Index (file này đang đọc)
├── 01-tong-quan/
├── 02-yeu-cau/
├── 03-phan-tich-module/
├── 04-mo-hinh-du-lieu/
├── 05-kien-truc-ky-thuat/
├── 06-tai-lieu-api/
├── 07-mau-giao-dien/
├── 08-tuan-thu-ke-toan/
├── 09-ke-hoach-trien-khai/
└── user_manual/                   ← (sẽ tạo ở Phase 6)
    ├── getting_started.md
    ├── create_voucher.md
    ├── close_period.md
    └── ...
```

## 12. Makefile shortcuts

```makefile
# Makefile
.PHONY: help install dev test lint format migrate

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync
	npm install
	bash scripts/install_vendor_assets.sh

dev: ## Start development server (Django + django-q2)
	uv run python manage.py migrate
	uv run python manage.py runserver
	# Trong terminal khác: uv run python manage.py qcluster

qcluster: ## Start django-q2 cluster (dev)
	uv run python manage.py qcluster

test: ## Run tests
	uv run pytest --cov=apps

lint: ## Run linters
	uv run ruff check apps/
	uv run ruff format --check apps/
	uv run mypy apps/

format: ## Format code
	uv run ruff format apps/

migrate: ## Run migrations
	uv run python manage.py migrate

makemigrations: ## Create migrations
	uv run python manage.py makemigrations

shell: ## Django shell
	uv run python manage.py shell_plus

dbshell: ## DB shell
	uv run python manage.py dbshell

superuser: ## Create superuser
	uv run python manage.py createsuperuser

test-fast: ## Run tests parallel
	uv run pytest -n auto --cov=apps

deploy: ## Deploy to production (run on server)
	bash scripts/deploy.sh

backup: ## Trigger DB backup
	bash scripts/backup_db.sh

clean: ## Clean cache files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
```

## 13. .env.example

```bash
# .env.example
# Django
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=dev-insecure-key-change-in-prod
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=mysql://pmketoan:devpass@localhost:3306/pmketoan
DB_CONN_MAX_AGE=60

# django-q2 (broker = Django ORM, không cần URL riêng)
Q_CLUSTER_WORKERS=4
Q_CLUSTER_TIMEOUT=600

# Email (dev: console)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Sentry (dev: disabled)
SENTRY_DSN=

# External APIs
BKAV_API_URL=https://test-api.bkav.com/eInvoice
BKAV_API_KEY=
```

---

**Tiếp theo**: [04. Testing Strategy](./04-testing-strategy.md)
