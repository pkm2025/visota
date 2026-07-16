# Visota ERP — Roles, Permissions & Seed Data Investigation

> Generated for dogfooding planning. Source: `apps/identity/`, `apps/core/`,
> `apps/ui_modern/`, seed management commands.

---

## 1. Identity Model Overview

**File**: `apps/identity/models.py`

| Model | Purpose |
|-------|---------|
| `User` | Custom user (extends `AbstractUser`). Adds `full_name`, `phone`, `avatar`, 2FA fields, lockout fields. No company FK — user↔company is many-to-many via `UserCompanyRole`. |
| `Permission` | Single catalog of permission codes. `code` (unique), `module`, `name`, `description`. |
| `Role` | Tenant-scoped role. `company` FK (nullable), `code`, `name`, `is_system` flag, M2M `permissions`. Unique on `(company, code)`. |
| `UserCompanyRole` | Join table: user + company + role (+ `is_default`, validity dates). Unique on `(user, company, role)`. |

### Permission Granularity

Visota uses **module-level permissions**, not CRUD-level. Each business module
has a single `<module>.access` permission (per product decision 2026-06-20).
Old CRUD permissions (e.g. `gl.voucher.view`, `gl.voucher.create`) are removed
during `seed_permissions`.

The only exception is the **PKM** module, which has three additional
fine-grained permissions:
- `pkm.notes.manage`
- `pkm.documents.manage`
- `pkm.qa.use`

---

## 2. All Module Permissions

**Source**: `apps/identity/management/commands/seed_permissions.py` → `MODULE_PERMISSIONS`

| Module Code | Permission Code | Vietnamese Name | Description |
|-------------|-----------------|-----------------|-------------|
| `master_data` | `master_data.access` | Danh mục hệ thống | Products, customers, vendors, categories |
| `ledger` | `ledger.access` | Kế toán tổng hợp | Vouchers, general ledger, journal entries, period close |
| `sales` | `sales.access` | Bán hàng | Sales invoices, customers, AR |
| `purchasing` | `purchasing.access` | Mua hàng | Purchase invoices, vendors, AP |
| `inventory` | `inventory.access` | Kho | Stock in/out, warehouse, stocktake |
| `assets` | `assets.access` | Tài sản cố định | Fixed assets, depreciation, disposal |
| `hr` | `hr.access` | Nhân sự | Employees, labor contracts, BHXH, leave |
| `payroll` | `payroll.access` | Tính lương | Payroll, PIT, BHXH, salary fund |
| `reporting` | `reporting.access` | Báo cáo tài chính | B01, B02, BCĐTK, VAT, PIT, D62 |
| `documents` | `documents.access` | Tài liệu đính kèm | Attachment management |
| `contracts` | `contracts.access` | Hợp đồng & biên bản | Contracts, templates |
| `input_docs` | `input_docs.access` | Chứng từ đầu vào | Input invoice upload/OCR |
| `recurring` | `recurring.access` | Bút toán định kỳ | Depreciation, allocation, recurring entries |
| `projects` | `projects.access` | Quản lý dự án | Projects, phases, resources |
| `crm` | `crm.access` | CRM | Leads, opportunities, tickets, campaigns |
| `treasury` | `treasury.access` | Quỹ tiền mặt | Cash receipts, cash payments, fund |
| `banking` | `banking.access` | Ngân hàng & Đối soát | Bank statements, reconciliation |
| `guarantees` | `guarantees.access` | Bảo lãnh ngân hàng | Bid bond, performance, advance payment |
| `loans` | `loans.access` | Vay vốn ngân hàng | Short/long-term loans, interest, settlement |
| `bidding` | `bidding.access` | Đấu thầu | Bidding opportunities per Luật 23/2023 |
| `budget` | `budget.access` | Ngân sách & Dòng tiền | Annual budget, variance, cash flow forecast |
| `fx` | `fx.access` | Tỷ giá & Định giá ngoại tệ | Exchange rate, period-end revaluation |
| `einvoice` | `einvoice.access` | Hóa đơn điện tử | E-invoice per ND 254/2026 + TT 91/2026 |
| `approvals` | `approvals.access` | Phê duyệt | Approval chains for vouchers/invoices |
| `notifications` | `notifications.access` | Thông báo | System notification inbox |
| `pkm` | `pkm.access` | Quản lý tri thức cá nhân | PKM - Notes, RAG documents, Q&A AI |

**Total**: 26 module-level `.access` permissions + 3 PKM fine-grained = **29 permissions**.

---

## 3. System Roles (from `seed_permissions`)

**Source**: `SYSTEM_ROLES` in `seed_permissions.py`. All are created with
`is_system=True` and scoped to `Company.objects.first()`.

### 3.1 `admin` — Quản trị hệ thống (System Administrator)
- **Description**: Toàn quyền truy cập mọi module (full access to all modules)
- **Permissions**: ALL 26 modules + PKM fine-grained
- **Note**: In `AdminRoleEditView`, the `admin` role cannot be edited (its
  permissions are "toàn quyền" / all-powerful). Superusers bypass permission
  checks entirely.

### 3.2 `chief_accountant` — Kế toán trưởng (Chief Accountant)
- **Description**: Toàn quyền kế toán + duyệt khóa sổ + HĐĐT + quản trị
- **Permissions**: ALL 26 modules + PKM fine-grained (same as admin)
- **Note**: Has the same module access as admin but is intended for
  accounting-focused users who also approve period close.

### 3.3 `accountant` — Kế toán viên (Accountant)
- **Description**: Kế toán tổng hợp + mua/bán + báo cáo + HĐ + nhân sự + HĐĐT + ngân hàng + FX
- **Permissions** (19 modules):
  `ledger`, `sales`, `purchasing`, `reporting`, `contracts`, `documents`,
  `hr`, `payroll`, `recurring`, `master_data`, `input_docs`, `treasury`,
  `einvoice`, `approvals`, `notifications`, `banking`, `guarantees`, `loans`, `fx`
- **Does NOT have**: `inventory`, `assets`, `projects`, `crm`, `bidding`,
  `budget`, `pkm`

### 3.4 `sales` — Nhân viên kinh doanh (Sales Representative)
- **Description**: Bán hàng + CRM + khách hàng + hợp đồng + HĐĐT + đấu thầu
- **Permissions** (9 modules):
  `sales`, `crm`, `contracts`, `documents`, `projects`, `master_data`,
  `einvoice`, `notifications`, `bidding`

### 3.5 `purchaser` — Nhân viên mua hàng (Purchasing Officer)
- **Description**: Mua hàng + nhà cung cấp + kho + thông báo
- **Permissions** (6 modules):
  `purchasing`, `inventory`, `documents`, `master_data`, `input_docs`, `notifications`

### 3.6 `hr_officer` — Nhân sự (HR Officer)
- **Description**: Quản lý nhân sự + HĐLĐ + BHXH + thông báo
- **Permissions** (6 modules):
  `hr`, `payroll`, `documents`, `master_data`, `reporting`, `notifications`

### 3.7 `project_manager` — Quản lý dự án (Project Manager)
- **Description**: Quản lý dự án + CRM + hợp đồng + báo cáo + thông báo
- **Permissions** (7 modules):
  `projects`, `crm`, `contracts`, `documents`, `sales`, `reporting`, `notifications`

### 3.8 `viewer` — Chỉ xem (Read-Only Viewer)
- **Description**: Toàn quyền xem báo cáo, không ghi/sửa
- **Permissions** (3 modules):
  `reporting`, `ledger`, `notifications`
- **Note**: Despite the name, this role has `.access` to ledger and reporting,
  which at module level includes create/edit capabilities in the UI. True
  read-only enforcement would require finer-grained permissions.

---

## 4. Permission Enforcement Layers

Visota enforces permissions at **three layers**:

### Layer 1: URL-Based Middleware (`ModulePermissionMiddleware`)
**File**: `apps/identity/middleware.py`

Maps URL path prefixes → module codes via `PATH_MODULE_MAP`. On every request
to `/modern/*`:
1. Superusers bypass entirely.
2. Exempt paths (`/auth/`, `/admin/`, `/static/`, `/api/`, etc.) bypass.
3. Dashboard (`/modern/`, `/modern/dashboard*`) is always allowed.
4. For other paths, resolves the module and checks `<module>.access`.
5. If denied: GET → redirect to `/no-access/`; POST/PUT/DELETE → HTTP 403.

**Important**: If no `current_company` is set on the request, the middleware
falls back to `Company.objects.first()`. This means a user without an
explicit `UserCompanyRole` can still access modules if they're a superuser,
but non-superusers would have no permissions (empty set from
`UserService._load_permissions`).

### Layer 2: Template Tags (`perm_tags.py`)
**File**: `apps/ui_modern/templatetags/perm_tags.py`

- `{% has_module_access "sales" %}` — checks both **module visibility**
  (sidebar config) AND **permission** (`<module>.access`). Superusers bypass
  the permission check but NOT the module visibility check.
- `{% user_permissions_for %}` — returns the set of permission codes.

### Layer 3: View-Level (per-view)
Views use `UserService(user, company).has_permission(code)` directly or
via the `has_perm` context processor. Admin views (`StaffRequiredMixin`)
require `is_superuser or is_staff`.

---

## 5. Company (Tenant) Context

### Company Model (`apps/core/models.py`)

Multi-tenant isolation via `company_id` column on all business models.

**Accounting Regimes** (critical for dashboard + features):
| Code | Name | Notes |
|------|------|-------|
| `tt133` | TT133/2016 (SME) | Default. Standard double-entry ledger. |
| `tt200` | TT200/2014 (Large enterprise) | Full chart of accounts. |
| `tt58` | TT58/2026 (Micro/super-small — DNSN) | Simplified cash-basis ledger. Dashboard switches to DNSN mode. |
| `q48` | QĐ48/2006 (deprecated) | Legacy only. Do not use. |

**Key fields**: `code`, `tax_code`, `accounting_regime`, `vat_method`,
`tndn_method`, `sme_size`, `enabled_modules` (JSON for module visibility),
`bank_accounts` (JSON array).

### How Current Company Is Set

1. **TenantMiddleware** (`apps/core/middleware.py`): reads
   `session["current_company_id"]` and sets `request.current_company`.
2. **CompanySwitchView** (`apps/ui_modern/views/company_switch.py`): POST to
   switch company. Verifies user has a `UserCompanyRole` for the target
   company (or is superuser), then sets `session["current_company_id"]`.
3. **Fallback**: `ModulePermissionMiddleware` falls back to
   `Company.objects.first()` if no company is set (to avoid errors), but
   this is a safety net, not the intended flow.

### User-Company Relationship

Users are NOT directly assigned to companies. The relationship is:
```
User → UserCompanyRole → (Company, Role)
```
A user can have multiple roles across multiple companies. `is_default`
marks the primary role for a given company.

---

## 6. Module Visibility (Sidebar)

**File**: `apps/core/module_config.py`

### Core Modules (always visible when company is set)
- `ke_toan` (Kế toán) → maps to `ledger, treasury, banking, input_docs, recurring`
- `ban_hang` (Bán hàng) → `sales`
- `mua_hang` (Mua hàng) → `purchasing`
- `hoa_don` (Hóa đơn) → `einvoice`
- `kho` (Kho) → `inventory`
- `bao_cao` (Báo cáo) → `reporting`

### Advanced Modules (gated for DNSN/TT58 companies)
- `nhan_su` → `hr, payroll`
- `tai_san` → `assets`
- `crm` → `crm`
- `ngan_sach` → `budget`
- `dau_thau` → `bidding`
- `du_an` → `projects`
- `vay` → `loans`
- `bao_lanh` → `guarantees`

**Visibility rules**:
- For **non-DNSN** companies (tt133/tt200/q48): ALL modules visible by default.
- For **DNSN** (tt58) companies: advanced modules hidden unless explicitly
  enabled in `Company.enabled_modules` JSON.
- `Hệ thống` (system) section is always visible.

---

## 7. Existing Test Users & Credentials

### From `seed_demo.py`

| Username | Password | Type | Full Name | Notes |
|----------|----------|------|-----------|-------|
| `admin` | `admin123` | Superuser + Staff | Administrator | Full access, bypasses all permission checks. Only user created by seed. |

**That's the ONLY seeded user.** The `seed_demo.py` command creates:
- 1 admin user (superuser)
- 1 `accountant` Role (assigned to company PKM, with ledger perms) — but
  this role is **NOT assigned to any user** in the seed.

### From `seed_permissions.py` (system roles)

Creates 8 system roles (`admin`, `chief_accountant`, `accountant`, `sales`,
`purchaser`, `hr_officer`, `project_manager`, `viewer`) scoped to
`Company.objects.first()`, but **does NOT create any users** or assign
roles to users.

### Login Flow
**File**: `apps/ui_modern/views/auth_views.py`

- Login URL: `/auth/login/`
- Form: `LoginForm` (standard Django auth)
- Redirect after login: `ui_modern:dashboard` (`/modern/`)
- No company selection at login — company is set via session/switcher.
- Logout: POST to `/auth/logout/` (Django 4+ security).

### What's Missing for Dogfooding
- **No role-based test users exist.** Only `admin/admin123` (superuser).
- To dogfood different roles, you need to create users and assign
  `UserCompanyRole` records manually or via a new seed command.

---

## 8. Dashboard Behavior by Role

**File**: `apps/ui_modern/views/dashboard_views.py`

The dashboard does **NOT** differ by role. It differs by:
1. **Accounting regime**: TT58 (DNSN) companies get `_get_dnsn_metrics()`
   with simplified cash-basis widgets. Others get the full CEO/accountant
   dashboard.
2. **View mode toggle**: `?view=ceo` (default) — but this is just passed
   to the template; the backend doesn't filter data by it.

The dashboard shows the same data to all authenticated users who have a
company context. Permission-based differences come from the **sidebar**
(module visibility) and **middleware** (URL-level access), not from the
dashboard itself.

### Dashboard Widgets (non-DNSN)
- Vouchers today / total / posted / draft
- AR Aging (current, 1-30, 31-60, 60+ days)
- Cash Position (cash + bank balances)
- P&L (revenue, expense, profit for current month)
- AP Total
- Inventory Value
- Tax Deadlines (VAT, PIT, BHXH)
- Unpaid invoices count
- Pending approvals count
- Stock vouchers today

### Dashboard Widgets (DNSN/TT58)
- Revenue today / period revenue / period cost / profit
- Tax payable (VAT + TNDN)
- Receivables / Payables
- Inventory value (from S2c ledger)
- Cash total (from S2d ledger)
- Recent DNSN vouchers

---

## 9. Seed Data Inventory

### Company
- **PKM** — CÔNG TY CỔ PHẦN CÔNG NGHỆ PKM
  - Tax code: 0101218690
  - Regime: `tt133`
  - Address: Tầng 06, Toà Nhà Icon4, Số 243A Đê La Thành, Hà Nội

### Chart of Accounts
- Full TT133 chart loaded via `load_tt133` management command.

### Master Data
| Type | Code | Name |
|------|------|------|
| Customer | KH001 | Công ty ABC |
| Vendor | NCC001 | Nhà cung cấp XYZ |
| Product | SP001 | Sản phẩm demo |
| Warehouse | KHO_HN | Kho Hà Nội |

### Fixed Assets
| Code | Name | Cost | Method |
|------|------|------|--------|
| TS001 | Xe Toyota Vios | 800,000,000 VND | Straight-line, 5yr, 20% |

### HR Data
| Code | Name | Position | Base Salary | Allowance |
|------|------|----------|-------------|-----------|
| NV001 | Nguyễn Thị Mai | Kế toán viên | 15,000,000 | 2,000,000 |
| NV002 | Trần Văn Hùng | Kế toán viên | 20,000,000 | 3,000,000 |

- Department: KE_TOAN (Kế toán)
- Position: KE_TOAN_VIEN (Kế toán viên, level 2)

### HR Detail (NV001 only)
- Labor contract: HDL001 (fixed-term, 2024-2026, 15M base / 17M gross)
- Dependent: Nguyễn Minh Khôi (child, 6.2M deduction)
- Leave balance: 12 days (2026)

### Configuration
- Recurring templates (defaults from `RecurringService.setup_defaults`)
- Contract templates (`seed_contract_templates`)
- Legal references (`seed_legal_references`)
- Tax types (`seed_tax_types`)
- TaxRateConfig: CIT/VAT/PIT/TTĐB/monbai/truoc_ba/FCT (effective 2026-07-01)

---

## 10. Business Flows Each Role Should Test

### `admin` / `chief_accountant` — Full System
- **All modules** accessible
- Company profile editing, module visibility toggle
- User management (create users, assign roles)
- Role management (edit non-system roles)
- Period close (khóa sổ)
- Full reporting
- E-invoice issuance
- Approvals management

### `accountant` — Core Accounting
- **Can access**: vouchers, sales/purchase invoices, reports, contracts,
  HR, payroll, recurring entries, master data, input invoices, treasury,
  e-invoices, approvals, notifications, banking, guarantees, loans, FX
- **Cannot access**: inventory, fixed assets, projects, CRM, bidding,
  budget, PKM
- **Key flows**:
  - Create/post/lock accounting vouchers
  - Sales invoice creation + e-invoice issuance
  - Purchase invoice processing
  - Treasury (cash receipts/payments)
  - Bank reconciliation
  - Payroll processing
  - Period close
  - Financial reports (B01, B02, VAT, PIT)

### `sales` — Sales Representative
- **Can access**: sales, CRM, contracts, documents, projects, master data,
  e-invoice, notifications, bidding
- **Cannot access**: ledger, purchasing, inventory, assets, HR, payroll,
  treasury, banking, reports, recurring, input_docs, approvals, guarantees,
  loans, budget, fx, pkm
- **Key flows**:
  - Create sales invoices
  - Customer management
  - CRM (leads, opportunities, tickets)
  - Contract management
  - E-invoice issuance for sales
  - Bidding opportunities
  - Project tracking

### `purchaser` — Purchasing Officer
- **Can access**: purchasing, inventory, documents, master data,
  input_docs, notifications
- **Cannot access**: ledger, sales, assets, HR, payroll, reports, contracts,
  recurring, projects, crm, treasury, banking, guarantees, loans, bidding,
  budget, fx, einvoice, approvals, pkm
- **Key flows**:
  - Create purchase invoices
  - Vendor management
  - Stock vouchers (warehouse in/out)
  - Input invoice upload/OCR
  - Inventory management

### `hr_officer` — HR Officer
- **Can access**: hr, payroll, documents, master_data, reporting, notifications
- **Cannot access**: ledger, sales, purchasing, inventory, assets, contracts,
  recurring, projects, crm, treasury, banking, guarantees, loans, bidding,
  budget, fx, einvoice, approvals, pkm
- **Key flows**:
  - Employee management
  - Labor contracts
  - BHXH / insurance
  - Leave management
  - Dependent management
  - Payroll processing
  - HR reports

### `project_manager` — Project Manager
- **Can access**: projects, crm, contracts, documents, sales, reporting,
  notifications
- **Cannot access**: ledger, purchasing, inventory, assets, hr, payroll,
  master_data, recurring, treasury, banking, guarantees, loans, bidding,
  budget, fx, einvoice, approvals, input_docs, pkm
- **Key flows**:
  - Project creation/management
  - Phase tracking
  - CRM activities
  - Contract management
  - Sales invoice creation
  - Project reports

### `viewer` — Read-Only Viewer
- **Can access**: reporting, ledger, notifications
- **Cannot access**: everything else
- **Key flows**:
  - View financial reports
  - View ledger/vouchers (module-level .access includes view)
  - View notifications
- **Note**: The `.access` permission is module-level, not view-only. The
  viewer can technically create/edit within these modules at the permission
  level. True read-only would need additional enforcement.

---

## 11. Key Findings & Gaps for Dogfooding

### What Works
1. **Permission model is well-structured**: module-level `.access` is clean
   and easy to reason about.
2. **Three-layer enforcement**: middleware (URL) + template tags (sidebar) +
   view-level (service) provides defense in depth.
3. **Multi-tenant**: company scoping via `UserCompanyRole` is correct.
4. **DNSN support**: dashboard and module visibility adapt to TT58 regime.

### What's Missing
1. **No role-based test users**: Only `admin/admin123` exists. To dogfood
   roles, need to create 7 additional users (one per non-admin system role)
   and assign `UserCompanyRole` records.
2. **No company selection at login**: User lands on dashboard without a
   company context if no session is set. `ModulePermissionMiddleware` falls
   back to `Company.objects.first()`, which works for single-company
   dogfooding but is not the intended UX.
3. **`viewer` role is not truly read-only**: `.access` grants full CRUD at
   the module level. If read-only enforcement matters for dogfooding, this
   needs attention.
4. **No seed for multiple companies**: Only PKM exists. To test
   multi-tenant or DNSN flows, need a TT58 company.
5. **`seed_permissions` uses `Company.objects.first()`**: System roles are
   scoped to whatever company happens to be first. If PKM isn't first (e.g.,
   after adding companies), roles may be created for the wrong tenant.

### Recommended Dogfooding Setup
1. Create test users for each system role.
2. Assign `UserCompanyRole` for each user → PKM company → corresponding role.
3. Optionally create a second company with TT58 regime for DNSN testing.
4. Test login + dashboard + sidebar visibility for each role.
5. Test URL-level access denial for modules outside each role's scope.
