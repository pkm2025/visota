# Ledger, Reporting & Accounting Structure Investigation — TT58/2026 Gap Analysis

> **Date**: 2026-07-14
> **Scope**: Deep analysis of Visota's accounting/ledger structure, reporting, core settings, PKM, templates, and configuration for Thông tư 58/2026/TT-BTC compliance.

---

## Executive Summary

Visota implements a **traditional double-entry accounting system** built around a TT133/TT200 chart of accounts (hệ thống tài khoản). The entire ledger, reporting, and voucher system is **hardcoded to account-code-based accounting**: every voucher line references an `account_code`, all balances are keyed by `account_code`, and all financial reports aggregate by `account_code` patterns.

**No support exists** for any aspect of TT58/2026:

- **No TT132/2018 support** — the `AccountingRegime` enum has `tt133`, `tt200`, `q48` only. No `tt132` or `tt58` choice.
- **No simplified ledger model** — TT58's S1-DNSN, S2a/S2b/S2c/S2d, S3a/S3b ledger forms do not exist. The system only knows `AccountingVoucher` + `VoucherLine` (traditional nhật ký chung).
- **No "no chart of accounts" mode** — the system cannot operate without `ChartOfAccounts` entries; voucher lines require `account_code`.
- **No tax method selection** — only GTGT khấu trừ (deduction method) is supported. No GTGT by % on revenue.
- **No simplified financial reports** — only B01-DN, B02-DN, B03-DN exist. No B01-DNSN or B02-DNSN.
- **No household business (hộ kinh doanh) entity type** — `Company` model is for doanh nghiệp only.
- **No balance conversion tools** — no mechanism to convert TT132 account balances to TT58 ledger opening balances.

**Bottom line**: TT58 compliance requires a fundamentally new accounting mode that bypasses the chart of accounts entirely, new simplified ledger models, new report templates, and new tax calculation methods. This is a major feature addition, not a minor extension.

---

## 1. apps/ledger/ — Models, Services, Double-Entry Mechanics

### 1.1 Models (`apps/ledger/models/`)

The ledger app has exactly **3 models** across 2 files:

#### `voucher.py` — `AccountingVoucher` + `VoucherLine`

**`AccountingVoucher`** (table: `accounting_voucher`)
- **Purpose**: Header for a set of bút toán (journal entry lines).
- **Key fields**: `company`, `fiscal_year`, `period`, `voucher_no`, `voucher_type`, `voucher_date`, `posting_date`, `book_code`, `status`, `currency_code`, `exchange_rate`, `total_fc`, `total_vnd`, `description`, `source`, `source_reference_id`, `is_reversed`, `reversal_voucher`.
- **`VoucherType` choices**: `journal`, `cash_receipt`, `cash_payment`, `sales_invoice`, `purchase_invoice`, `stock_voucher`, `depreciation`, `allocation`, `closing`.
- **`Status` choices** (IntegerChoices): `DRAFT=0` (Lưu tạm), `SUBSIDIARY=1` (Ghi sổ phụ), `LEDGER=2` (Ghi sổ cái), `LOCKED=3` (Đã khóa).
- **Unique together**: `(company, fiscal_year, voucher_type, voucher_no)`.
- **Inherits from** `CompanyOwnedModel` (multi-tenant via `company_id`).
- **Properties**: `is_posted` (status >= LEDGER), `is_locked` (status == LOCKED).

**`VoucherLine`** (table: `voucher_line`)
- **Purpose**: Single debit or credit entry (bút toán) within a voucher.
- **Key fields**: `voucher` (FK), `line_no`, `account_code` (string, max 20), `object_type`, `object_code`, `object_name`, `debit_fc`, `credit_fc`, `debit_vnd`, `credit_vnd`, `description`, `cost_center_code`, `project_code`.
- **Tax fields** (labeled "M1"): `invoice_no`, `invoice_date`, `invoice_form`, `invoice_symbol`, `invoice_serial`, `tax_code` (FK to `master_data.TaxRateCode`), `tax_rate`, `goods_amount_vnd`, `tax_amount_vnd`, `offset_account_code`, `invoice_group_code` (FK to `master_data.InvoiceGroup`), `object_address`, `is_auto_tax_posting`.
- **Running balance fields** (labeled "M3"): `running_balance_debit`, `running_balance_credit` — cumulative totals per `account_code` ordered by `(voucher_date, voucher_id, line_no)`.
- **Unique together**: `(voucher, line_no)`.
- **Critical observation**: `account_code` is a plain `CharField` with no FK to `ChartOfAccounts`. It is a free-text field, though in practice it should match an account in the chart. This means TT58's "no chart of accounts" mode could technically work at the voucher line level, but all reporting and balance aggregation depends on account codes.

#### `balance.py` — `AccountPeriodBalance`

**`AccountPeriodBalance`** (table: `account_period_balance`)
- **Purpose**: Pre-computed period balance per account (+ optional object code). Updated by `VoucherPostingService` on post/unpost. Rebuildable from `voucher_line` table.
- **Key fields**: `company`, `fiscal_year`, `period`, `account_code`, `object_type`, `object_code`.
- **Balance fields** (VND + FC): `opening_debit`, `opening_credit`, `period_debit`, `period_credit`, `closing_debit`, `closing_credit` (and `_fc` variants).
- **Metadata**: `last_transaction_date`, `transaction_count`.
- **Unique together**: `(company, fiscal_year, period, account_code, object_type, object_code)`.
- **Method**: `recalculate_closing()` — computes closing from opening + period; side with larger value wins.
- **Critical observation**: This model is **entirely account-code-based**. For TT58's S-ledgers (which don't use account codes), a completely different balance model would be needed, or the existing model would need a `ledger_type` discriminator.

#### `__init__.py`
Exports: `AccountingVoucher`, `VoucherLine`, `AccountPeriodBalance`.

### 1.2 Services (`apps/ledger/services/`)

#### `voucher_posting_service.py` — `VoucherPostingService`

**Key methods**:
- `post(voucher)` — Validates balance (debit == credit within 1 VND tolerance), updates `AccountPeriodBalance` rows (sign=+1), sets status to `LEDGER`, recomputes running balances for affected account codes, sends notification to superusers.
- `unpost(voucher)` — Reverts balance updates (sign=-1), sets status to `DRAFT`, clears running balances, recomputes for affected codes.
- `_validate_balanced(voucher)` — Sums all `debit_vnd` and `credit_vnd` from voucher lines; raises `VoucherNotBalancedError` if difference > 0.01 VND.
- `_update_one_balance(voucher, line, sign)` — Gets or creates `AccountPeriodBalance` row for `(company, fiscal_year, period, account_code, object_type, object_code)`, applies delta to period debit/credit, recalculates closing.
- `_recompute_running_balances_for_codes(company, account_codes)` — Orders all posted `VoucherLine` rows for given account codes by `(voucher_date, voucher_id, line_no)`, computes cumulative debit/credit totals, bulk-updates `running_balance_debit`/`running_balance_credit`.

**Exceptions**: `VoucherNotBalancedError`, `VoucherLockedError`.

**TT58 gap**: The posting service enforces double-entry balance (debit == credit). TT58's simplified ledgers (S1-DNSN, etc.) are single-entry or cash-basis — they don't follow traditional debit/credit balance rules. The service would need a different posting path for TT58 mode.

#### `period_closing_service.py` — `PeriodClosingService`

**Key method**: `close_period(fiscal_year, period)`
- Transfers revenue (TK 5xx, 7xx) and expense (TK 6xx, 8xx) balances to TK 911 (XĐKQ), then transfers profit/loss to TK 421 (Lợi nhuận chưa phân phối).
- **Account code prefixes hardcoded**: `REVENUE_PREFIXES = ("5", "7")`, `EXPENSE_PREFIXES = ("6", "8")`, `PROFIT_ACCOUNT = "421"`, `RESULT_ACCOUNT = "911"`.
- Creates a closing voucher with `voucher_type="closing"`, `source="closing"`.
- Idempotent: skips if a closing voucher already exists for the period.

**TT58 gap**: Period closing is entirely account-code-driven. TT58's simplified regime doesn't use TK 911 or TK 421 — it has its own profit determination method based on revenue and tax rates.

### 1.3 Admin (`apps/ledger/admin.py`)

Standard Django admin registration for `AccountingVoucher` (with `VoucherLineInline`), `VoucherLine`, and `AccountPeriodBalance`. No custom logic.

### 1.4 Existing Accounting Regime Support

**There is no regime-aware logic anywhere in the ledger app.** The `Company.accounting_regime` field is never checked in any ledger model, service, or view. The ledger operates identically regardless of whether the company is TT133, TT200, or Q48.

The only regime-specific behavior in the entire codebase is:
- `load_tt133` management command loads TT133 chart of accounts.
- Report line configuration (`FinancialReportLine`) uses TT133/TT200 account code patterns.

---

## 2. apps/reporting/ — Financial Reports

### 2.1 Models (`apps/reporting/models.py`)

#### `FinancialReportLine` (table: `reporting_financial_report_line`)
- **Purpose**: Configuration row for financial-statement report lines. Database-driven instead of hard-coded Python.
- **`report_type` choices**: `B01-DN` (Balance Sheet), `B02-DN` (P&L), `B03-DN-direct` (Cash Flow direct), `B03-DN-indirect` (Cash Flow indirect).
- **Data source fields**: `tk_no_pattern`, `tk_co_pattern` (wildcard account-code patterns like `1331*`), `tk_doi_ung_pattern` (counterpart account pattern for cash-flow direct method), `cong_thuc` (formula like `110+120+130+140`), `tinh_giam_tru` (subtraction formula).
- **Display fields**: `stt`, `ma_so`, `chi_tieu`, `thuyet_minh`, `is_header`, `parent_ma_so`, `display_order`.
- **Unique together**: `(report_type, display_order)`.
- **TT58 gap**: No `B01-DNSN` or `B02-DNSN` report types. The entire config-driven report engine is account-code-pattern-based, which is incompatible with TT58's "no chart of accounts" approach.

#### `VATReportLine` (table: `reporting_vat_report_line`)
- **Purpose**: Configuration row for VAT return (TT80/2021 form 01/GTGT).
- **`line_code`**: e.g. "21", "22", "40".
- **`section` choices**: `A` (Thông tin chung), `B-I` (HHDV mua vào), `B-II` (HHDV bán ra), `C` (Thuế GTGT phải nộp).
- **Filter fields**: `tk_filter` (account code pattern), `invoice_group_filter`, `tax_code_filter`.
- **`amount_field` choices**: `tax_amount_vnd`, `goods_amount_vnd`, `debit_vnd`, `credit_vnd`.
- **`cong_thuc`**: Formula referencing sibling line codes like `[25]+[26]-[27]`.
- **TT58 gap**: TT80 VAT return is for the khấu trừ method only. TT58 companies using GTGT by % on revenue need a completely different VAT declaration.

### 2.2 Services (`apps/reporting/services/`)

#### `balance_sheet.py` — `BalanceSheetService`
- Generates B01-DN data from `FinancialReportLine` config rows.
- Falls back to legacy first-digit grouping (1xx/2xx = assets, 3xx = liabilities, 4xx = equity) when no config exists.
- Splits rendered lines into asset/liability/equity groups based on `parent_ma_so` prefix (A = assets, L = liabilities, E = equity).
- Checks `is_balanced` (total assets == total liabilities + equity).

#### `pnl.py` — `PnLService`
- Generates B02-DN data from config or legacy hard-coded account-prefix logic.
- Legacy logic maps: 5xx = revenue, 632 = COGS, 641 = selling expense, 642 = admin expense, 635 = financial expense, 711 = other income, 811 = other expense, 821 = PIT expense.
- Returns dict with named keys: `revenue`, `cogs`, `gross_profit`, `operating_profit`, `profit_before_tax`, `profit_after_tax`, etc.

#### `cash_flow.py` — `CashFlowService`
- Generates B03-DN (direct and indirect methods).
- Config-driven with legacy fallback.
- Direct method uses `tk_doi_ung_pattern` to filter cash-account vouchers by counterpart account.

#### `vat_return.py` — `VATReturnService`
- Generates TT80/2021 VAT return (01/GTGT).
- Evaluates `VATReportLine` config rows with formula resolution (supports `+`, `-`, `*` operators with recursive reference resolution and cycle detection).
- Falls back to `AccountPeriodBalance`-based computation (TK 33311 = output VAT, TK 1331 = input VAT) when no config exists.
- Returns legacy compat keys: `vat_output`, `vat_input_credit`, `vat_payable`, `vat_credit`, `is_payable`.

#### `formula_parser.py` — `ReportEngine`, `ReportLine`
- Config-driven report evaluation engine shared by all financial reports.
- `ReportLine` dataclass: `stt`, `ma_so`, `chi_tieu`, `thuyet_minh`, `is_header`, `parent_ma_so`, `value`, `raw_config`.
- Evaluates lines by: (1) formula if present, (2) account-code pattern aggregation from `AccountPeriodBalance`, (3) blank for headers.
- Supports wildcard suffix `*` in account patterns.

#### `hr_reports.py`
- `D62ReportService` — per-employee BHXH contribution summary.
- `LaborUsageReportService`, `SalaryFundReportService`, `PITMonthlyReportService`.

### 2.3 Management Commands (`apps/reporting/management/commands/`)

- `seed_financial_report_lines.py` — Seeds `FinancialReportLine` rows for B01-DN (~50 lines), B02-DN (~30 lines), B03-DN-direct (~20 lines), B03-DN-indirect (~20 lines). All account-code patterns follow TT133.
- `seed_vat_tt80.py` — Seeds `VATReportLine` rows for TT80/2021 VAT return form.

### 2.4 Report Templates (`templates/modern/reporting/`)

| Template | Purpose |
|----------|---------|
| `balance_sheet.html` | B01-DN Balance Sheet |
| `pnl.html` | B02-DN Profit & Loss |
| `cash_flow.html` | B03-DN Cash Flow |
| `trial_balance.html` | S06-DN Bảng cân đối tài khoản |
| `general_ledger.html` | Sổ cái |
| `general_journal.html` | Nhật ký chung |
| `detail_book.html` | Sổ chi tiết |
| `sub_ledger.html` | Sổ phụ |
| `book_entry_register.html` | Sổ đăng ký chứng từ |
| `specialized_journal.html` | Nhật ký đặc biệt |
| `vat_return.html` | TT80/2021 VAT return |
| `vat_input_list.html` | Input VAT list |
| `vat_output_list.html` | Output VAT list |
| `d62.html` | D62 BHXH report |
| `cost_report.html` | Cost report |
| `labor_usage.html` | Labor usage report |
| `pit_monthly.html` | PIT monthly report |
| `salary_fund.html` | Salary fund report |
| `t_account.html` | T-account view |
| `report_export_pdf.html` | PDF export wrapper |

**TT58 gap**: No B01-DNSN or B02-DNSN templates. No simplified ledger templates (S1-DNSN, S2a/b/c/d, S3a/b).

---

## 3. apps/core/ — Company Settings, Tax Configuration, Regime Selection

### 3.1 `Company` Model (`apps/core/models.py`)

**Key fields for accounting regime**:
- `accounting_regime` — `CharField` with `AccountingRegime` choices:
  - `TT133 = "tt133"` — TT133/2016 (DN nhỏ và vừa)
  - `TT200 = "tt200"` — TT200/2014 (DN lớn)
  - `Q48 = "q48"` — QĐ48/2006 (cũ)
  - **No TT132, no TT58.**
- `sme_size` — `SMESize` choices: `MICRO = "micro"` (Siêu nhỏ), `SMALL = "small"` (Nhỏ), `MEDIUM = "medium"` (Vừa), `LARGE = "large"` (Lớn). Per ND 80/2021.
- `annual_revenue` — `DecimalField` for SME classification.
- `chief_accountant` — `CharField` for kế toán trưởng name.
- `chief_accountant_license` — `CharField` for license number.
- `chief_accountant_phone` — `CharField`.

**TT58 implications**:
- TT58 applies to "doanh nghiệp siêu nhỏ" (micro enterprises). The `sme_size=MICRO` classification exists but has no accounting-regime implications.
- TT58 removes the requirement for kế toán trưởng and allows family members as accountants. The `chief_accountant` fields exist but are not validated against any requirement.
- TT58 also applies to hộ kinh doanh (household businesses). The `Company` model has no `entity_type` or `business_type` field to distinguish doanh nghiệp from hộ kinh doanh.
- Adding TT58 support requires adding `"tt58"` to the `AccountingRegime` enum, or creating a new `AccountingRegime` choice.

### 3.2 `TaxRateConfig` Model

Comprehensive tax rate configuration including:
- **CIT rates** (Luật TNDN 2025): `cit_rate_standard` (20%), `cit_rate_small` (17%), `cit_rate_micro` (15%).
- **VAT rates** (ND 174/2025): `vat_rate_standard` (10%), `vat_rate_reduced` (8%), `vat_rate_reduced_active` (boolean toggle).
- **PIT** (Luật 09/2026/QH16): `pit_personal_deduction_2026` (15.5M), `pit_dependent_deduction_2026` (6.2M), `pit_brackets_2026` (5-bracket system).
- **TTĐB** (special consumption tax), **lệ phí môn bài**, **lệ phí trước bạ**, **thuế nhà thầu** (FCT).
- **Insurance**: `bhxh_cap`, `base_salary`.

**TT58 gap**: No support for GTGT by % on revenue (phương pháp tính trực tiếp). The `TaxRateConfig` only has VAT rates for the deduction method. TT58's tax method groups 1 and 2 use GTGT by % on revenue, which requires a different calculation (VAT = revenue × rate, no input VAT credit).

### 3.3 `TaxConfigService` (`apps/core/services/tax_config_service.py`)

- `get_active(company)` — Returns current active `TaxRateConfig`.
- `get_cit_rate(company)` — Returns CIT rate based on `sme_size` (micro=15%, small=17%, else 20%).
- `get_vat_rate(is_reduced)` — Returns 8% or 10% based on `vat_rate_reduced_active` toggle.
- `classify_sme(annual_revenue, total_capital, employee_count, sector)` — Classifies company per ND 80/2021 thresholds. Sector-aware (Agri/Industry vs Commerce/Service). Lower tier from revenue or capital wins.

**TT58 gap**: No method to determine or return GTGT by % on revenue rate. No concept of "tax method group" (nhóm phương pháp thuế).

### 3.4 Other Core Models

- **`LegalReference`** — Vietnamese legal document reference tracker. Fields: `code`, `name`, `issuing_body`, `issue_date`, `effective_date`, `expiry_date`, `replaced_by`, `status` (active/superseded/repealed). No TT58 or TT132 entry exists.
- **`TaxType`** — Master record of all Vietnamese tax types (direct, indirect, fee categories).
- **`PITRateHistory`** — Historical PIT rates since 2009 for audit.
- **`FeatureFlag`** — Per-company or global feature flags with env var override. Default flags: `new_reporting_engine`, `ai_assistant`, `batch_einvoice`, `multi_currency`, `advanced_budget`. No TT58-related flag.
- **`UserSearchAffinity`** — Per-user search personalization.

### 3.5 Middleware (`apps/core/middleware.py`)

- **`TenantMiddleware`** — Detects current layout from URL path (`/modern/`, `/classic/`, `/mobile/`, `/portal/`) and loads `current_company` from session.
- **`BrandingMiddleware`** — Sets `request.brand` from current company's branding fields or `DEFAULT_BRAND`.

### 3.6 Context Processors (`apps/core/context_processors.py`)

- `branding(request)` — Exposes `brand`, `current_layout`, `current_company`, `available_layouts` to all templates.

---

## 4. apps/pkm/ — Personal Knowledge Management

### 4.1 Purpose

PKM stands for **Personal Knowledge Management**. It is a RAG-powered (Retrieval-Augmented Generation) document Q&A system integrated into the ERP. It is **not related to accounting** — it is an AI assistant feature that lets users upload documents (PDF, DOCX, etc.), chunk and embed them, and ask questions about the content.

### 4.2 Models (`apps/pkm/models/`)

| Model | Purpose |
|-------|---------|
| `PKMDocument` | Uploaded source document (file, status: pending → processing → processed/failed) |
| `DocumentChunk` | Text chunk extracted from a document for RAG |
| `Embedding` | Vector embedding for a document chunk |
| `KnowledgeNote` | User-created knowledge note |
| `QAHistory` | Q&A interaction history (question, answer, sources, context) |
| `Tag` | Tagging for documents and notes |
| `UserInteractionLog` | User interaction tracking (page views, clicks, etc.) |
| `UserLLMConfig` | Per-user LLM configuration (API keys, model preferences) |

### 4.3 Services (`apps/pkm/services/`)

| Service | Purpose |
|---------|---------|
| `rag_pipeline.py` | Full RAG pipeline (ingest → chunk → embed → store) |
| `qa_service.py` | Question answering with context retrieval |
| `llm_service.py` | LLM API client (multiple providers) |
| `vector_store.py` | Vector storage and similarity search |
| `chunking_service.py` | Document text chunking |
| `doc_parser.py` | Document file parsing (PDF, DOCX, TXT, MD) |
| `encryption_service.py` | Encryption for sensitive data |
| `interaction_service.py` | User interaction logging and context building |

### 4.4 Middleware

`PKMInteractionMiddleware` — Logs `page_view` interactions for `/modern/knowledge/` URLs. Non-blocking.

### 4.5 URL Pattern

PKM pages are served at `/modern/knowledge/*`. The API is at `apps/pkm/api.py` (34KB file with full CRUD endpoints).

**TT58 relevance**: PKM is unrelated to accounting compliance. It could potentially be used to help users understand TT58 regulations by uploading TT58-related documents, but it has no structural impact on TT58 implementation.

---

## 5. Templates — Structure, Dashboard, Reports, Branding

### 5.1 Template Directory Structure (`templates/modern/`)

```
templates/modern/
├── base/
│   ├── layout.html          (52KB — main layout with sidebar, topbar)
│   └── _right_sidebar.html
├── dashboard/
│   ├── index.html           (main dashboard, CEO + kế toán views)
│   └── quick_expense.html
├── ledger/
│   ├── chart_of_accounts_list.html
│   ├── voucher_list.html
│   ├── voucher_form.html
│   ├── voucher_guided.html
│   ├── voucher_detail.html
│   ├── closing.html
│   └── change_account_code.html
├── reporting/
│   ├── balance_sheet.html
│   ├── pnl.html
│   ├── cash_flow.html
│   ├── trial_balance.html
│   ├── general_ledger.html
│   ├── general_journal.html
│   ├── detail_book.html
│   ├── sub_ledger.html
│   ├── book_entry_register.html
│   ├── specialized_journal.html
│   ├── vat_return.html
│   ├── vat_input_list.html
│   ├── vat_output_list.html
│   ├── d62.html
│   ├── cost_report.html
│   ├── labor_usage.html
│   ├── pit_monthly.html
│   ├── salary_fund.html
│   ├── t_account.html
│   └── report_export_pdf.html
├── pkm/                     (knowledge management templates)
├── sales/, purchasing/, inventory/, hr/, payroll/
├── assets/, banking/, contracts/, crm/
├── einvoice/, input_docs/, projects/
├── master_data/, tools/, budget/
├── approvals/, notifications/, recurring/
├── guarantees/, loans/, bidding/, fx/
├── treasury/, products/
├── admin/, auth/, help/, search/
├── no_access.html, offline.html, _vietqr_modal.html
```

### 5.2 Base Layout (`templates/modern/base/layout.html`)

- **827 lines**, the main application shell.
- Contains: topbar with brand logo, company switcher, super search; sidebar navigation; content area; right sidebar.
- **Branding**: Uses `{{ brand.name }}`, `{{ brand.logo }}`, `{{ brand.primary_color }}`, `{{ brand.accent_color }}` throughout.
- **Meta tags**: `<meta name="apple-mobile-web-app-title" content="PMKetoan">`, `<meta name="description" content="PMKetoan ERP — Hệ thống kế toán VN tuân thủ TT133/2016, TT200/2014">`.
- **PWA**: Has install banner with "Cài đặt PMKetoan" text.
- **Sidebar navigation**: Hardcoded URL references to `ui_modern:` named URLs for all modules.

### 5.3 Dashboard (`templates/modern/dashboard/index.html`)

- Dual-view: CEO view (revenue, AR aging, cash position, recent invoices) and kế toán view (voucher stats, recent vouchers, period closing status).
- Uses `AccountPeriodBalance` and `AccountingVoucher` data.
- No regime-specific content — all widgets assume traditional double-entry accounting.

### 5.4 Branding: "PMKetoan" vs "Visota"

The codebase has a **split identity** (detailed in `.factory/branding-investigation.md`):
- **Internal app UI** (layout, login, sidebar, dashboard, API titles, settings) uses **"PMKetoan"** (one word, no space, no Vietnamese diacritics).
- **Public-facing site** (landing, signup, terms, privacy, blog) has been partially rebranded to **"Visota"** with domain `visota.net`.
- **Production settings** (`config/settings/prod.py`) and `.env.example` use Visota naming.
- The `Company` model has a `hide_pmketoan_branding` boolean field for white-labeling.
- `DEFAULT_BRAND` in `apps/core/middleware.py` uses `"name": "PMKetoan"`.
- The API title in `apps/core/api.py` is `NinjaAPI(title="PMKetoan API", ...)`.

**No "PM Kế toán" (with Vietnamese diacritics) or "PMK" abbreviation exists.** The brand string is consistently "PMKetoan".

---

## 6. Settings & Configuration

### 6.1 Settings Files (`config/settings/`)

| File | Purpose |
|------|---------|
| `base.py` | Base settings: INSTALLED_APPS (28 apps), MIDDLEWARE, DB config (MySQL/MariaDB), cache (DB cache), django-q2, Axes, templates |
| `dev.py` | Development overrides |
| `prod.py` | Production settings (uses "Visota" naming) |
| `test.py` | Test settings |
| `e2e.py` | End-to-end test settings |

### 6.2 INSTALLED_APPS (28 apps)

All 28 apps in `apps/` are registered:
- **Foundation**: `core`, `identity`, `master_data`
- **Domain**: `ledger`, `sales`, `purchasing`, `inventory`, `assets`, `hr`, `payroll`, `reporting`, `contracts`, `input_docs`, `recurring`, `projects`, `crm`, `einvoice`, `banking`, `guarantees`, `loans`, `bidding`, `budget`, `fx`, `costing`
- **Infrastructure**: `documents`, `notifications`, `approvals`, `pkm`, `public`
- **UI**: `ui_modern`

### 6.3 Database

- **Engine**: MySQL/MariaDB (`django.db.backends.mysql`)
- **Default DB name**: `pmketoan` (in `base.py`)
- **Charset**: `utf8mb4`
- **Cache**: Django DB cache (no Redis)

### 6.4 Accounting Regime Configuration

The accounting regime is configured per-company via the `Company.accounting_regime` field. However, **this field is almost never read by application code**. A grep for `accounting_regime` across `apps/` found it referenced only in:
- `apps/core/models.py` (definition)
- `apps/core/management/commands/seed_demo.py` (sets demo company to `"tt133"`)
- `apps/ui_modern/views/company_views.py` (likely in company settings form)
- Various test files

**There is no runtime logic that branches behavior based on `accounting_regime`.** The chart of accounts, voucher types, posting service, period closing, and all reports work identically regardless of the regime setting.

### 6.5 Chart of Accounts Loading

- **TT133**: `load_tt133` management command loads ~120 accounts (Types 0-9, all TT133 standard accounts from 111 to 911).
- **TT200**: No equivalent command exists. TT200 has a different, more detailed chart of accounts.
- **TT132**: No support at all. No command, no fixture, no model.
- **TT58**: No support. TT58 doesn't use a chart of accounts at all.
- **Fixture**: `apps/master_data/fixtures/tt133_chart_of_accounts.json` contains 10 `AccountType` definitions only (not individual accounts).

### 6.6 Tax Rate Configuration

- `TaxRateConfig` model stores all tax rates (CIT, VAT, PIT, TTĐB, fees, FCT, insurance).
- `TaxConfigService` provides lookup methods.
- **No VAT method field** — the system assumes khấu trừ (deduction method) everywhere.
- **No TNDN method field** — the system assumes TNDN on taxable income, not % on revenue.
- Seed command: `apps/core/management/commands/seed_demo.py` creates demo company with `accounting_regime="tt133"`.

### 6.7 Feature Flags (`apps/core/feature_flags.py`)

Database-backed feature flags with env var override. Default flags:
- `new_reporting_engine` (False)
- `ai_assistant` (False)
- `batch_einvoice` (False)
- `multi_currency` (False)
- `advanced_budget` (False)

**No TT58-related feature flag exists.** A `tt58_simplified_regime` flag could be added to gate the new functionality.

### 6.8 Makefile Commands

| Command | Description |
|---------|-------------|
| `make dev` | Migrate + seed_demo + runserver |
| `make test` | pytest |
| `make test-fast` | pytest -n auto |
| `make lint` | ruff check + format check |
| `make format` | ruff format |
| `make migrate` | Django migrate |
| `make makemigrations` | Django makemigrations |
| `make seed` | seed_demo command |

### 6.9 Migration History

**Ledger app** (5 migrations):
1. `0001_initial` — Creates `AccountingVoucher` and `VoucherLine`
2. `0002_accountperiodbalance` — Creates `AccountPeriodBalance`
3. `0003_voucherline_goods_amount_vnd_and_more` — Adds tax fields to `VoucherLine`
4. `0004_voucherline_is_auto_tax_posting` — Adds `is_auto_tax_posting`
5. `0005_voucherline_running_balances` — Adds running balance fields

**Core app** (10 migrations):
1. `0001_initial` — Creates `Company`
2. `0002_legalreference` — Creates `LegalReference`
3. `0003_company_annual_revenue_company_sme_size_and_more` — Adds `sme_size`, `annual_revenue`, branding fields
4. `0004_taxrateconfig_pit_brackets` — Adds PIT brackets to `TaxRateConfig`
5. `0005_taxtype_taxrateconfig_fct_cit_rate_and_more` — Adds TTĐB, fees, FCT rates
6. `0006_pit_history_and_bidding` — Creates `PITRateHistory`
7. `0007_alter_taxrateconfig_pit_dependent_deduction_and_more` — PIT 2026 updates
8. `0008_company_profile` — Company profile fields
9. `0009_featureflag` — Creates `FeatureFlag`
10. `0010_usersearchaffinity` — Creates `UserSearchAffinity`

---

## 7. master_data/ — Chart of Accounts, Tax Codes, Invoice Groups

### 7.1 `ChartOfAccounts` (`apps/master_data/models/account.py`)

- **Table**: `chart_of_accounts`
- **Inherits**: `CompanyOwnedModel` (multi-tenant)
- **Key fields**: `company`, `account_code`, `account_name`, `parent_account_code` (self-referential tree via string), `account_level`, `account_type` (FK to `AccountType`), `is_posting_account`, `is_general_ledger_account`, `is_active`, `currency_code`, exchange rate methods.
- **Object/cost center/project tracking**: `allows_object_code`, `allows_cost_center`, `allows_project`, `allows_production_order`.
- **Unique together**: `(company, account_code)`.
- **`AccountType` model**: 10 types (codes 0-9) with `BalanceType` (debit/credit) and `Category` (asset, liability, equity, revenue, expense, other_income, other_expense, off_balance).

### 7.2 `TaxRateCode` (`apps/master_data/models/tax_rate.py`)

- **Table**: `master_data_taxratecode`
- GTGT tax rate codes per TT78/2021: `00` (0%), `05` (5%), `04` (5% special), `10` (10%), `08` (10% special), `KT` (không chịu thuế), `TS05`, `kht`.
- Fields: `code`, `rate`, `display_name`, `is_active`, `sort_order`.

### 7.3 `InvoiceGroup` (`apps/master_data/models/invoice_group.py`)

- **Table**: `master_data_invoicegroup`
- Groups: `4` (INPUT — hóa đơn đầu vào), `5` (OUTPUT — hóa đơn đầu ra), `6` (OTHER).
- Fields: `code`, `name_vi`, `name_en`, `default_tax_account_debit`, `default_tax_account_credit`, `sort_order`.

---

## 8. TT58/2026 Compliance Gap Summary

### 8.1 What Exists (Reusable)

| Feature | Status | TT58 Usability |
|---------|--------|----------------|
| Multi-tenant Company model | ✅ Exists | Reusable — needs `tt58` regime choice |
| SME classification (micro/small/medium) | ✅ Exists | Reusable — micro enterprises are TT58 targets |
| Voucher header/line model | ✅ Exists | Partially reusable — lines use `account_code` which TT58 doesn't need |
| Double-entry posting service | ✅ Exists | Not applicable for simplified ledgers |
| Period closing (kết chuyển) | ✅ Exists | Not applicable — TT58 has no TK 911/421 |
| Config-driven financial reports | ✅ Exists | Pattern reusable — but needs new report types (B01-DNSN, B02-DNSN) |
| Config-driven VAT return | ✅ Exists | Not applicable — TT58 uses different VAT calculation |
| Tax rate configuration | ✅ Exists | Partially reusable — needs GTGT % on revenue rates |
| Feature flag system | ✅ Exists | Reusable — can gate TT58 features |
| Branding/white-label system | ✅ Exists | Reusable |
| Chart of accounts model | ✅ Exists | Not needed for TT58 (but needed for TT132→TT58 conversion) |

### 8.2 What's Missing (Must Build)

| TT58 Requirement | Gap |
|------------------|-----|
| **TT58 accounting regime choice** | Add `"tt58"` to `Company.AccountingRegime` enum |
| **No chart of accounts mode** | New ledger mode that bypasses `ChartOfAccounts` |
| **Simplified ledgers (S1-DNSN, S2a/b/c/d, S3a/b)** | New models for each ledger type, or a generic `SimplifiedLedgerEntry` model |
| **4 tax method groups** | New `TaxMethodGroup` field on `Company` (or a combination of `vat_method` + `tdn_method` fields) |
| **GTGT by % on revenue** | New VAT calculation service, new VAT return form |
| **TNDN by % on revenue** | New TNDN calculation service |
| **TNDN by % on taxable income** | Different from current (which is on taxable income but via TK 821) |
| **B01-DNSN report** | New `FinancialReportLine` report type + template |
| **B02-DNSN report** | New `FinancialReportLine` report type + template |
| **Hộ kinh doanh entity type** | New `entity_type` field on `Company` or separate model |
| **TT132 balance conversion** | New management command to convert TT132 account balances to TT58 opening balances |
| **No kế toán trưởng requirement** | Make `chief_accountant` fields optional (already optional, but may need UI changes) |
| **Family member accountant** | No structural change needed, just documentation/policy |
| **Simplified ledger templates** | New templates for each S-ledger type |
| **TT58 dashboard/widgets** | New dashboard widgets for simplified regime |
| **TT58 report seed data** | New seed commands for B01-DNSN, B02-DNSN report lines |

### 8.3 Key Architectural Challenge

The fundamental architectural challenge is that **the entire system is built around account codes**:

1. `VoucherLine.account_code` — every journal entry line references an account code.
2. `AccountPeriodBalance.account_code` — all balances are keyed by account code.
3. `FinancialReportLine.tk_no_pattern` / `tk_co_pattern` — all report lines aggregate by account code patterns.
4. `VATReportLine.tk_filter` — VAT return lines filter by account code.
5. `PeriodClosingService` — uses hardcoded account code prefixes (5xx, 6xx, 7xx, 8xx, 421, 911).
6. `VoucherPostingService._validate_balanced()` — enforces debit == credit, which is a double-entry concept.

TT58's simplified regime operates on **cash-basis or revenue-basis ledgers** without account codes. This means either:

- **Option A**: Create a parallel set of models (`SimplifiedLedgerEntry`, `SimplifiedLedgerBalance`) for TT58 mode, completely separate from the existing ledger.
- **Option B**: Extend existing models with a `regime` or `ledger_type` discriminator and make `account_code` optional, with different posting/balance logic per regime.
- **Option C**: Use a mapping layer where TT58 ledger entries are mapped to pseudo-account codes behind the scenes (least compliant with TT58's "no chart of accounts" philosophy).

**Option A is recommended** — it provides the cleanest separation and avoids polluting the existing double-entry system with simplified-regime special cases.

---

## 9. File Reference Index

### Models
| File Path | Key Models |
|-----------|------------|
| `apps/ledger/models/voucher.py` | `AccountingVoucher`, `VoucherLine` |
| `apps/ledger/models/balance.py` | `AccountPeriodBalance` |
| `apps/core/models.py` | `Company`, `LegalReference`, `TaxRateConfig`, `PITRateHistory`, `TaxType`, `FeatureFlag`, `UserSearchAffinity` |
| `apps/master_data/models/account.py` | `AccountType`, `ChartOfAccounts` |
| `apps/master_data/models/tax_rate.py` | `TaxRateCode` |
| `apps/master_data/models/invoice_group.py` | `InvoiceGroup` |
| `apps/reporting/models.py` | `FinancialReportLine`, `VATReportLine` |
| `apps/identity/models.py` | `User`, `Permission`, `Role`, `UserCompanyRole` |
| `apps/pkm/models/` | `PKMDocument`, `DocumentChunk`, `Embedding`, `KnowledgeNote`, `QAHistory`, `Tag`, `UserInteractionLog`, `UserLLMConfig` |

### Services
| File Path | Key Services |
|-----------|-------------|
| `apps/ledger/services/voucher_posting_service.py` | `VoucherPostingService` |
| `apps/ledger/services/period_closing_service.py` | `PeriodClosingService` |
| `apps/core/services/tax_config_service.py` | `TaxConfigService` |
| `apps/reporting/services/balance_sheet.py` | `BalanceSheetService` |
| `apps/reporting/services/pnl.py` | `PnLService` |
| `apps/reporting/services/cash_flow.py` | `CashFlowService` |
| `apps/reporting/services/vat_return.py` | `VATReturnService` |
| `apps/reporting/services/formula_parser.py` | `ReportEngine`, `ReportLine` |
| `apps/reporting/services/hr_reports.py` | `D62ReportService`, `LaborUsageReportService`, `SalaryFundReportService`, `PITMonthlyReportService` |
| `apps/core/feature_flags.py` | `is_enabled()`, `enable()`, `disable()` |

### Views
| File Path | Key Views |
|-----------|----------|
| `apps/ui_modern/views/ledger_views.py` | `VoucherListView`, `VoucherCreateView`, etc. |
| `apps/ui_modern/views/report_views.py` | `TrialBalanceView`, report views |
| `apps/ui_modern/views/dashboard_views.py` | `DashboardView` |
| `apps/ui_modern/views/chart_of_accounts_views.py` | `ChartOfAccountsListView`, `ChartOfAccountsChangeCodeView` |
| `apps/ui_modern/views/closing_views.py` | Period closing views |
| `apps/ui_modern/views/company_views.py` | Company settings views |
| `apps/ui_modern/views/migration_views.py` | Excel import from MISA/Fast |
| `apps/ui_modern/views/vat_list_views.py` | VAT input/output list views |
| `apps/ui_modern/views/vat_xml_views.py` | VAT XML export |
| `apps/ui_modern/views/report_export_views.py` | PDF/Excel report export |
| `apps/ui_modern/urls.py` | All URL patterns (34KB) |

### Management Commands
| File Path | Command |
|-----------|---------|
| `apps/master_data/management/commands/load_tt133.py` | Load TT133 chart of accounts |
| `apps/master_data/management/commands/seed_invoice_groups.py` | Seed invoice groups |
| `apps/master_data/management/commands/seed_tax_rates.py` | Seed tax rate codes |
| `apps/reporting/management/commands/seed_financial_report_lines.py` | Seed B01-DN, B02-DN, B03-DN report lines |
| `apps/reporting/management/commands/seed_vat_tt80.py` | Seed TT80/2021 VAT return lines |
| `apps/core/management/commands/seed_demo.py` | Seed demo company + data |

### Configuration
| File Path | Purpose |
|-----------|---------|
| `config/settings/base.py` | Base Django settings |
| `config/settings/dev.py` | Dev settings |
| `config/settings/prod.py` | Production settings |
| `apps/core/middleware.py` | `TenantMiddleware`, `BrandingMiddleware` |
| `apps/core/context_processors.py` | `branding` context processor |
| `Makefile` | Build commands |

### Templates
| File Path | Purpose |
|-----------|---------|
| `templates/modern/base/layout.html` | Main layout (827 lines) |
| `templates/modern/dashboard/index.html` | Dashboard |
| `templates/modern/ledger/` | Ledger templates (8 files) |
| `templates/modern/reporting/` | Report templates (21 files) |
| `templates/modern/pkm/` | PKM templates |
