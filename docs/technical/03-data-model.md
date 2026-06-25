# T3 — Mô hình dữ liệu & ERD

> Cấu trúc DB chính — 200+ table trên 31 app.

## Tổng quan

- **DBMS**: MariaDB 11.4
- **Charset**: utf8mb4 / utf8mb4_unicode_ci
- **Storage**: InnoDB (default), Aria (cho table log)
- **Total tables**: ~200 (cross 31 app)

## Pattern chung

### CompanyOwnedModel

Mọi table business kế thừa:

```python
class CompanyOwnedModel(models.Model):
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE)
    # auto fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyOwnedManager()  # auto-filter by request.company

    class Meta:
        abstract = True
```

Mọi query tự filter theo `request.current_company` → isolation multi-tenant.

### Audit fields

| Field | Ý nghĩa |
|-------|---------|
| `created_at` | Timestamp tạo |
| `updated_at` | Timestamp sửa cuối |
| `created_by` | User tạo (optional) |
| `updated_by` | User sửa cuối (optional, qua middleware) |

## Schema chính

### Core (`apps.core`)

```
Company
├── name, short_name, tax_code, address
├── accounting_regime (tt133/tt200)
├── sme_size (micro/small/medium/large)
├── branding fields (logo, primary_color, ...)
└── relationships:
    ├── CompanyOwnedModel → all business tables
    ├── Department (HR)
    ├── Role (Identity)
    └── ...

TaxRateConfig
├── company FK
├── vat_rates JSON {standard, reduced, zero, exempt}
├── pit_self_deduction (13.2M from 07/2026)
├── pit_dependent_deduction (5.2M)
├── pit_brackets JSON [(min, max, rate)]
├── cit_standard_rate (0.20)
├── cit_sme_rate (0.15)
├── bhxh_employee_rate (0.105)
├── bhxh_employer_rate (0.215)
└── kpcd_rate (0.02)

TaxType
├── code (VAT/CIT/PIT/...)
├── name
└── description

PITRateHistory
├── effective_from (date)
├── self_deduction
├── dependent_deduction
├── brackets JSON
└── legal_basis (text)

LegalReference
├── code (TT133, TT200, TT78, ...)
├── name
├── issuing_body
├── issued_date
├── effective_date
├── status (in_force/superseded/repealed)
└── url (link to thuvienphapluat.vn)
```

### Identity (`apps.identity`)

```
User (extends AbstractUser)
├── full_name, full_name_en
├── phone, avatar
├── two_factor_enabled
├── last_login_ip
├── failed_login_count
└── locked_until

Permission
├── code (unique, e.g. 'sales.access')
├── module (e.g. 'sales')
└── name

Role
├── company FK
├── code (e.g. 'accountant')
├── name
├── is_system (true = cannot delete)
└── permissions M2M Permission

UserCompanyRole
├── user FK
├── company FK
├── role FK
├── is_default
└── valid_from / valid_to
```

### Ledger (`apps.ledger`)

```
AccountingVoucher
├── company, fiscal_year, period
├── voucher_no (unique per company)
├── voucher_type (journal/receipt/payment/...)
├── voucher_date
├── description
├── currency_code, exchange_rate
├── total_vnd, total_fc
├── status (draft/ledger_posted/locked)
├── is_locked (bool)
├── created_by
└── lines → VoucherLine

VoucherLine
├── voucher FK
├── line_no
├── account_code (e.g. '131')
├── object_code (e.g. customer code)
├── debit_vnd, credit_vnd
├── debit_fc, credit_fc
├── description
└── M2M: voucher.documents

AccountPeriodBalance
├── company, fiscal_year, period, account_code
├── opening_debit, opening_credit
├── period_debit, period_credit
├── closing_debit, closing_credit
└── projection — re-computable from VoucherLine
```

### Sales (`apps.sales`)

```
Customer
├── code, name, tax_code, address
├── customer_group_code
├── credit_limit
├── default_vat_rate
├── gl_account_receivable (131)
└── ...

SalesInvoice
├── company, invoice_no, invoice_date
├── customer FK, sales_staff_code
├── currency_code, exchange_rate
├── subtotal, discount_amount, vat_amount, total_amount
├── paid_amount, payment_status
├── gl_voucher FK
├── status
└── lines → SalesInvoiceLine

SalesInvoiceLine
├── invoice FK, line_no
├── product FK
├── quantity, unit_price
├── vat_rate, vat_amount
├── amount_before_vat, amount
└── revenue_account (5111/5112/...)
```

### Purchasing, Inventory, Assets — similar pattern

### HR (`apps.hr`)

```
Employee
├── code, full_name, birth_date, gender
├── id_card_no, personal_tax_code, social_insurance_no
├── department FK, position FK
├── hire_date, leave_date
└── status (probation/active/maternity/resigned)

LaborContract
├── employee FK
├── contract_type (probation/indefinite/fixed)
├── start_date, end_date
├── base_salary, insurance_salary_base
├── allowances JSON
└── currency_code

Dependent (người phụ thuộc)
├── employee FK
├── full_name, relationship, birth_date
└── tax_code (of dependent, if any)

LeaveRecord
├── employee FK
├── leave_type (annual/sick/maternity/...)
├── from_date, to_date
├── days
├── reason
└── status (pending/approved/rejected)
```

### Payroll (`apps.payroll`)

```
PayrollRun
├── company, period_month, period_year
├── run_at
├── total_gross, total_bhxh, total_pit, total_net
├── gl_voucher FK
└── lines → PayrollLine

PayrollLine
├── payroll_run FK, employee FK
├── base_salary, allowances
├── gross
├── bhxh_employee, bhxh_employer
├── pit_self_deduction, pit_dependent_deduction
├── taxable_income
├── pit_amount
├── net
└── notes
```

### Contracts, CRM, Projects — similar pattern

### Notifications (`apps.notifications`)

```
Notification
├── user FK
├── company FK
├── type (info/success/warning/error/approval)
├── title, message
├── url
├── related_object_type (ContentType str)
├── related_object_id
├── is_read, read_at
└── created_at

EmailLog
├── company FK
├── from_email, to_emails, cc_emails
├── subject, body
├── status (sent/failed)
├── error_message
├── related_object_type, related_object_id
└── sent_by FK
```

### Approvals (`apps.approvals`)

```
ApprovalRule
├── company FK
├── voucher_type
├── min_amount, max_amount
├── approver_roles JSON [role codes]
└── is_active

ApprovalRequest
├── company FK
├── content_type FK, object_id (generic FK to anything)
├── object_label (cached)
├── voucher_type, amount
├── requested_by FK
├── status (pending/approved/rejected/cancelled)
├── rejection_reason
├── created_at, completed_at
└── steps → ApprovalStep

ApprovalStep
├── request FK, sequence
├── role_required
├── assigned_to FK
├── approved_by FK
├── status, note
└── acted_at
```

### EInvoice, Banking, Loans, Guarantees, Bidding, Budget, FX — similar pattern

## Indexes quan trọng

Mỗi table có:

```python
class Meta:
    indexes = [
        models.Index(fields=['company', '-created_at']),  # list query
        models.Index(fields=['company', 'status']),
        models.Index(fields=['company', 'fiscal_year', 'period']),  # for accounting
    ]
```

Plus unique constraints:
- `unique_together = [('company', 'code')]` — code per company
- `unique_together = [('company', 'invoice_no')]` — invoice number per company

## Triggers / Constraints

### DB-level

- FK constraints (ON DELETE CASCADE cho weak entity, SET_NULL cho optional)
- CHECK constraints (MariaDB 10.2+)
- Default values

### App-level

- VoucherNotBalancedError khi Nợ ≠ Có
- Duplicate detection
- Permission check via middleware

## Performance

### Hot tables (high write/read)

| Table | Read pattern | Write pattern |
|-------|-------------|---------------|
| `voucher_line` | by voucher, by account | on post/unpost |
| `account_period_balance` | by account × period | on every post |
| `notification` | by user, unread first | high freq |
| `attachment` | by object | on upload |

### Index strategy

```sql
-- Most queried patterns
CREATE INDEX idx_voucher_company_period ON voucher (company_id, fiscal_year, period);
CREATE INDEX idx_line_account ON voucher_line (account_code, voucher_id);
CREATE INDEX idx_notif_user_unread ON notification (user_id, is_read, created_at);
```

### Partitioning (for big tables)

Khi table > 10M rows, partition by year:

```sql
ALTER TABLE voucher_line PARTITION BY RANGE (YEAR(voucher_date)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

## Migration strategy

```bash
# Create migration
python manage.py makemigrations <app_name>

# Apply
python manage.py migrate <app_name>

# Reverse (if possible)
python manage.py migrate <app_name> <previous_migration>

# Squash (periodically)
python manage.py squashmigrations <app_name> <from> <to>
```

### Zero-downtime migrations

- **Add column**: with default → safe
- **Add column NOT NULL**: deploy in 2 phases (add nullable → backfill → set NOT NULL)
- **Drop column**: deploy in 2 phases (stop using → drop after 1 release)
- **Rename column**: 3 phases (add new → dual-write → drop old)
- **Index**: `CREATE INDEX ... ALGORITHM=INPLACE, LOCK=NONE`

## Backup cấu trúc

```bash
# Schema only
mysqldump --no-data --routines --triggers pmketoan > schema.sql

# Full dump with data
mysqldump --single-transaction --routines --triggers pmketoan > full.sql

# Specific tables
mysqldump pmketoan voucher voucher_line account_period_balance > acc.sql
```

## ERD visualization

Generate via:

```bash
# Django extensions
pip install django-extensions pygraphviz
python manage.py graph_models -a -o erd.png

# Or via DBeaver / MySQL Workbench reverse engineer
```

---

Tài liệu liên quan:
- [T1-architecture](01-architecture.md) — Kiến trúc tổng thể
- [T4-api](04-api.md) — API layer
- [A5-backup-restore](../admin-guide/05-backup-restore.md) — Backup strategy
