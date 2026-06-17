# Phase 1: General Ledger + Master Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the accounting core: Chart of Accounts (TT133), voucher (phiếu kế toán) + posting service + Modern UI list/form + trial balance report. End-to-end: user creates voucher → posts → sees it in trial balance.

**Architecture:** Shared backend (`apps/master_data` for chart of accounts, `apps/ledger` for vouchers). Modern UI view layer in `apps/ui_modern/views/ledger_views.py`. Service layer handles business logic (VoucherPostingService updates AccountPeriodBalance projection).

**Tech Stack:** Django 5.2, MariaDB 11.4, HTMX 2.x, Alpine.js 3.x, Bootstrap 5.3, Tabulator 6.x, pytest.

---

## File Structure

```
pmketoan/
├── apps/
│   ├── master_data/                        # NEW
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── account.py                  # AccountType, ChartOfAccounts
│   │   ├── migrations/
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── load_tt133.py           # Load TT133 chart fixture
│   │   └── fixtures/
│   │       └── tt133_chart_of_accounts.json
│   ├── ledger/                             # NEW
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── voucher.py                  # AccountingVoucher, VoucherLine
│   │   │   └── balance.py                  # AccountPeriodBalance
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── voucher_posting_service.py  # post(), unpost()
│   │   └── migrations/
│   └── ui_modern/
│       └── views/
│           ├── ledger_views.py             # Voucher list/create/detail
│           └── report_views.py             # Trial balance
├── config/
│   └── settings/base.py                    # Add master_data + ledger to INSTALLED_APPS
├── templates/modern/
│   ├── ledger/
│   │   ├── voucher_list.html
│   │   ├── voucher_form.html
│   │   └── voucher_detail.html
│   └── reporting/
│       └── trial_balance.html
├── static/modern/css/
│   └── ledger.css                          # Grid + form styles
└── tests/
    ├── test_chart_of_accounts.py
    ├── test_voucher_model.py
    ├── test_voucher_posting_service.py
    ├── test_voucher_views.py
    └── test_trial_balance.py
```

---

## Task 1: Create `master_data` app + AccountType model

**Files:**
- Create: `apps/master_data/__init__.py`, `apps/master_data/apps.py`, `apps/master_data/models/__init__.py`, `apps/master_data/models/account.py`
- Create: `apps/master_data/migrations/__init__.py`
- Modify: `config/settings/base.py` (add to INSTALLED_APPS)
- Test: `tests/test_account_type.py`

- [ ] **Step 1: Write failing test**

`tests/test_account_type.py`:
```python
import pytest
from apps.master_data.models import AccountType


@pytest.mark.django_db
def test_account_type_creation():
    at = AccountType.objects.create(
        code=1, name='Tài sản ngắn hạn',
        balance_type='debit', category='asset',
    )
    assert at.pk is not None
    assert str(at) == '1 - Tài sản ngắn hạn'


@pytest.mark.django_db
def test_account_type_str_includes_code():
    at = AccountType(code=2, name='Nợ phải trả')
    assert '2' in str(at)
    assert 'Nợ phải trả' in str(at)
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd /Users/dkm/dev/pmketoan
.venv/bin/pytest tests/test_account_type.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create apps/master_data/apps.py**

```python
from django.apps import AppConfig


class MasterDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.master_data'
    verbose_name = 'Master Data'
```

- [ ] **Step 4: Create apps/master_data/models/account.py**

```python
"""Chart of Accounts models."""
from django.db import models


class AccountType(models.Model):
    """Type of account: asset, liability, equity, revenue, expense, etc."""

    class BalanceType(models.TextChoices):
        DEBIT = 'debit', 'Nợ'
        CREDIT = 'credit', 'Có'

    class Category(models.TextChoices):
        ASSET = 'asset', 'Tài sản'
        LIABILITY = 'liability', 'Nợ phải trả'
        EQUITY = 'equity', 'Vốn chủ sở hữu'
        REVENUE = 'revenue', 'Doanh thu'
        EXPENSE = 'expense', 'Chi phí'
        OTHER_INCOME = 'other_income', 'Thu nhập khác'
        OTHER_EXPENSE = 'other_expense', 'Chi phí khác'
        OFF_BALANCE = 'off_balance', 'Ngoài bảng'

    code = models.SmallIntegerField(unique=True)
    name = models.CharField(max_length=100)
    balance_type = models.CharField(
        max_length=10, choices=BalanceType.choices,
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'account_type'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'
```

- [ ] **Step 5: Create apps/master_data/models/__init__.py**

```python
from .account import AccountType

__all__ = ['AccountType']
```

- [ ] **Step 6: Add to INSTALLED_APPS in config/settings/base.py**

Insert `'apps.master_data',` after `'apps.identity',` in INSTALLED_APPS.

- [ ] **Step 7: Create migration + migrate**

```bash
.venv/bin/python manage.py makemigrations master_data
.venv/bin/python manage.py migrate
```

- [ ] **Step 8: Run tests**

```bash
.venv/bin/pytest tests/test_account_type.py -v
.venv/bin/pytest -v  # full suite — should still pass
```

- [ ] **Step 9: Commit**

```bash
git add apps/master_data/ config/settings/base.py tests/test_account_type.py
git commit -m "feat(master_data): AccountType model

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: ChartOfAccounts model (tree)

**Files:**
- Modify: `apps/master_data/models/account.py` (add ChartOfAccounts)
- Modify: `apps/master_data/models/__init__.py`
- Test: `tests/test_chart_of_accounts.py`

- [ ] **Step 1: Write failing test**

`tests/test_chart_of_accounts.py`:
```python
import pytest
from apps.master_data.models import ChartOfAccounts, AccountType


@pytest.fixture
def asset_type(db):
    return AccountType.objects.create(
        code=1, name='Tài sản', balance_type='debit', category='asset',
    )


@pytest.fixture
def company(db):
    from apps.core.models import Company
    return Company.objects.create(code='TCO', name='Test Co')


def test_account_creation(asset_type, company):
    acc = ChartOfAccounts.objects.create(
        company=company,
        account_code='111',
        account_name='Tiền mặt',
        parent_account_code=None,
        account_level=1,
        account_type=asset_type,
        is_posting_account=False,
        is_general_ledger_account=True,
    )
    assert acc.pk is not None
    assert str(acc) == '111 - Tiền mặt'


def test_account_tree(asset_type, company):
    """Parent-child relationship via account_code."""
    parent = ChartOfAccounts.objects.create(
        company=company, account_code='111', account_name='Tiền mặt',
        account_level=1, account_type=asset_type,
    )
    child = ChartOfAccounts.objects.create(
        company=company, account_code='1111', account_name='Tiền Việt Nam',
        parent_account_code='111',
        account_level=2, account_type=asset_type,
    )
    assert child.parent_account_code == '111'


def test_account_unique_per_company(asset_type, company):
    """Same account_code can exist in different companies."""
    from apps.core.models import Company
    other = Company.objects.create(code='OCO', name='Other Co')
    ChartOfAccounts.objects.create(
        company=company, account_code='111', account_name='A',
        account_level=1, account_type=asset_type,
    )
    ChartOfAccounts.objects.create(
        company=other, account_code='111', account_name='B',
        account_level=1, account_type=asset_type,
    )
    # No error — different companies
    assert ChartOfAccounts.objects.filter(company=company).count() == 1
    assert ChartOfAccounts.objects.filter(company=other).count() == 1


def test_account_duplicate_in_same_company_fails(asset_type, company):
    from django.db import IntegrityError
    ChartOfAccounts.objects.create(
        company=company, account_code='111', account_name='A',
        account_level=1, account_type=asset_type,
    )
    with pytest.raises(IntegrityError):
        ChartOfAccounts.objects.create(
            company=company, account_code='111', account_name='B',
            account_level=1, account_type=asset_type,
        )


def test_account_defaults(asset_type, company):
    """New account defaults to active, currency VND, regime-independent."""
    acc = ChartOfAccounts(
        company=company, account_code='X', account_name='Test',
        account_level=1, account_type=asset_type,
    )
    assert acc.is_active is True
    assert acc.currency_code == 'VND'
    assert acc.is_posting_account is False
```

- [ ] **Step 2: Run tests to fail**

```bash
.venv/bin/pytest tests/test_chart_of_accounts.py -v
```

- [ ] **Step 3: Modify apps/master_data/models/account.py — append ChartOfAccounts**

```python
# Append to apps/master_data/models/account.py


class ChartOfAccounts(CompanyOwnedModel):
    """Chart of accounts entry. Tree via parent_account_code (string FK)."""

    # Import here to avoid module-level circular dep (CompanyOwnedModel is in core.managers)
    from apps.core.managers import CompanyOwnedModel

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='accounts',
        db_index=True,
    )
    account_code = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    account_name_en = models.CharField(max_length=255, blank=True)
    short_name = models.CharField(max_length=100, blank=True)

    parent_account_code = models.CharField(max_length=20, blank=True, db_index=True)
    currency_code = models.CharField(max_length=3, default='VND')

    account_level = models.PositiveSmallIntegerField(default=1)
    account_type = models.ForeignKey(
        AccountType, on_delete=models.PROTECT, related_name='accounts',
    )

    is_posting_account = models.BooleanField(default=False,
        help_text='Có cho phép hạch toán trực tiếp?')
    is_general_ledger_account = models.BooleanField(default=False,
        help_text='Là tài khoản sổ cái?')
    is_active = models.BooleanField(default=True)

    allows_object_code = models.BooleanField(default=False)
    allows_cost_center = models.BooleanField(default=False)
    allows_project = models.BooleanField(default=False)
    allows_production_order = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'chart_of_accounts'
        unique_together = [('company', 'account_code')]
        ordering = ['account_code']
        indexes = [
            models.Index(fields=['company', 'parent_account_code']),
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return f'{self.account_code} - {self.account_name}'
```

**Fix circular import properly**: Move `from apps.core.managers import CompanyOwnedModel` to top of file (above AccountType class), and have ChartOfAccounts inherit from it:

Actually, cleaner: import at top:

```python
"""Chart of accounts models."""
from django.db import models
from apps.core.managers import CompanyOwnedModel


class AccountType(models.Model):
    # ... (same as before)


class ChartOfAccounts(CompanyOwnedModel):
    """Chart of accounts entry."""

    # Override 'company' FK with proper related_name (CompanyOwnedModel provides it generically)
    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='accounts',
        db_index=True,
    )
    account_code = models.CharField(max_length=20)
    # ... rest of fields
```

Important: `CompanyOwnedModel` defines `company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='+', db_index=True)` — the child model can override with `related_name='accounts'`. This works in Django.

- [ ] **Step 4: Update apps/master_data/models/__init__.py**

```python
from .account import AccountType, ChartOfAccounts

__all__ = ['AccountType', 'ChartOfAccounts']
```

- [ ] **Step 5: Create migration**

```bash
.venv/bin/python manage.py makemigrations master_data
.venv/bin/python manage.py migrate
```

- [ ] **Step 6: Run tests**

```bash
.venv/bin/pytest tests/test_chart_of_accounts.py -v
.venv/bin/pytest -v  # full
```

- [ ] **Step 7: Commit**

```bash
git add apps/master_data/ tests/test_chart_of_accounts.py
git commit -m "feat(master_data): ChartOfAccounts model with tree structure

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: TT133 fixture loader

**Files:**
- Create: `apps/master_data/fixtures/tt133_chart_of_accounts.json` (~120 accounts)
- Create: `apps/master_data/management/__init__.py`, `apps/master_data/management/commands/__init__.py`
- Create: `apps/master_data/management/commands/load_tt133.py`
- Test: `tests/test_load_tt133.py`

- [ ] **Step 1: Write test**

`tests/test_load_tt133.py`:
```python
import pytest
from django.core.management import call_command
from apps.master_data.models import ChartOfAccounts, AccountType
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test Co')


def test_load_tt133_creates_account_types(company):
    call_command('load_tt133', company_code='TCO')
    # TT133 has ~10 account types
    assert AccountType.objects.count() >= 9


def test_load_tt133_creates_accounts(company):
    call_command('load_tt133', company_code='TCO')
    # TT133 has ~100-120 accounts at minimum
    assert ChartOfAccounts.objects.filter(company=company).count() >= 100


def test_load_tt133_includes_key_accounts(company):
    call_command('load_tt133', company_code='TCO')
    codes = set(ChartOfAccounts.objects.filter(company=company)
                .values_list('account_code', flat=True))
    # Must have these critical accounts
    assert '111' in codes  # Tiền mặt
    assert '112' in codes  # TGNH
    assert '131' in codes  # Phải thu khách
    assert '331' in codes  # Phải trả NCC
    assert '511' in codes  # Doanh thu
    assert '632' in codes  # Giá vốn
    assert '911' in codes  # XĐKQ


def test_load_tt133_idempotent(company):
    """Running twice should not duplicate."""
    call_command('load_tt133', company_code='TCO')
    count1 = ChartOfAccounts.objects.filter(company=company).count()
    call_command('load_tt133', company_code='TCO')
    count2 = ChartOfAccounts.objects.filter(company=company).count()
    assert count1 == count2
```

- [ ] **Step 2: Run tests to fail**

```bash
.venv/bin/pytest tests/test_load_tt133.py -v
```

- [ ] **Step 3: Create fixture JSON**

`apps/master_data/fixtures/tt133_chart_of_accounts.json`:

```json
[
  {"code": 1, "name": "Tài sản ngắn hạn", "balance_type": "debit", "category": "asset"},
  {"code": 2, "name": "Tài sản dài hạn", "balance_type": "debit", "category": "asset"},
  {"code": 3, "name": "Nợ phải trả", "balance_type": "credit", "category": "liability"},
  {"code": 4, "name": "Vốn chủ sở hữu", "balance_type": "credit", "category": "equity"},
  {"code": 5, "name": "Doanh thu", "balance_type": "credit", "category": "revenue"},
  {"code": 6, "name": "Chi phí sản xuất kinh doanh", "balance_type": "debit", "category": "expense"},
  {"code": 7, "name": "Thu nhập khác", "balance_type": "credit", "category": "other_income"},
  {"code": 8, "name": "Chi phí khác", "balance_type": "debit", "category": "other_expense"},
  {"code": 9, "name": "Xác định kết quả kinh doanh", "balance_type": "credit", "category": "off_balance"},
  {"code": 0, "name": "Tài khoản ngoài bảng", "balance_type": "debit", "category": "off_balance"}
]
```

Note: the actual TT133 has many accounts. For testing, this fixture just covers the 9 account types. The `load_tt133` command will create accounts from a Python list (faster than 120 JSON entries).

Actually, better: hardcode account list in Python inside the command, since it's static data and easier to maintain.

- [ ] **Step 4: Create management command**

`apps/master_data/management/commands/load_tt133.py`:

```python
"""Load TT133/2016 chart of accounts for a company."""
from django.core.management.base import BaseCommand, CommandError
from apps.core.models import Company
from apps.master_data.models import AccountType, ChartOfAccounts


ACCOUNT_TYPES = [
    (1, 'Tài sản ngắn hạn', 'debit', 'asset'),
    (2, 'Tài sản dài hạn', 'debit', 'asset'),
    (3, 'Nợ phải trả', 'credit', 'liability'),
    (4, 'Vốn chủ sở hữu', 'credit', 'equity'),
    (5, 'Doanh thu', 'credit', 'revenue'),
    (6, 'Chi phí sản xuất kinh doanh', 'debit', 'expense'),
    (7, 'Thu nhập khác', 'credit', 'other_income'),
    (8, 'Chi phí khác', 'debit', 'other_expense'),
    (9, 'Xác định kết quả kinh doanh', 'credit', 'off_balance'),
    (0, 'Tài khoản ngoài bảng', 'debit', 'off_balance'),
]


# (code, name, parent_code, level, type_code, is_posting, is_gl, allows_object, allows_cost_center)
ACCOUNTS = [
    # Type 1 - Tài sản ngắn hạn
    ('111', 'Tiền mặt', None, 1, 1, False, True, False, False),
    ('1111', 'Tiền Việt Nam', '111', 2, 1, True, False, False, False),
    ('1112', 'Ngoại tệ', '111', 2, 1, True, False, False, False),
    ('1113', 'Vàng bạc, đá quý', '111', 2, 1, True, False, False, False),

    ('112', 'Tiền gửi ngân hàng', None, 1, 1, False, True, False, False),
    ('1121', 'Tiền Việt Nam', '112', 2, 1, True, False, False, False),
    ('1122', 'Ngoại tệ', '112', 2, 1, True, False, False, False),
    ('1123', 'Vàng bạc, đá quý', '112', 2, 1, True, False, False, False),

    ('113', 'Tiền đang chuyển', None, 1, 1, True, True, False, False),

    ('121', 'Đầu tư tài chính ngắn hạn', None, 1, 1, False, True, False, False),
    ('1211', 'Chứng khoán kinh doanh', '121', 2, 1, True, False, False, False),
    ('1212', 'Đầu tư nắm giữ đến ngày đáo hạn', '121', 2, 1, True, False, False, False),
    ('1213', 'Đầu tư khác', '121', 2, 1, True, False, False, False),

    ('128', 'Đầu tư nắm giữ đến ngày đáo hạn', None, 1, 1, False, True, False, False),
    ('1281', 'Tiền gửi có kỳ hạn', '128', 2, 1, True, False, False, False),
    ('1288', 'Đầu tư khác nắm giữ đến ngày đáo hạn', '128', 2, 1, True, False, False, False),

    ('129', 'Dự phòng giảm giá chứng khoán kinh doanh', None, 1, 1, True, True, False, False),

    ('131', 'Phải thu khách hàng', None, 1, 1, False, True, True, False),
    ('133', 'Thuế GTGT được khấu trừ', None, 1, 1, False, True, False, False),
    ('1331', 'Thuế GTGT được khấu trừ của HHDV', '133', 2, 1, True, False, False, False),
    ('1332', 'Thuế GTGT được khấu trừ của TSCĐ', '133', 2, 1, True, False, False, False),

    ('136', 'Phải thu nội bộ', None, 1, 1, False, True, True, False),
    ('1361', 'Vốn kinh doanh ở đơn vị trực thuộc', '136', 2, 1, True, False, True, False),
    ('1368', 'Phải thu nội bộ khác', '136', 2, 1, True, False, True, False),

    ('138', 'Phải thu khác', None, 1, 1, False, True, False, False),
    ('1381', 'Tài sản thiếu chờ xử lý', '138', 2, 1, True, False, False, False),
    ('1386', 'Phải thu cổ đông', '138', 2, 1, True, False, False, False),
    ('1388', 'Phải thu khác', '138', 2, 1, True, False, False, False),

    ('141', 'Tạm ứng', None, 1, 1, True, True, True, False),

    ('152', 'Nguyên liệu, vật liệu', None, 1, 1, False, True, False, False),
    ('153', 'Công cụ, dụng cụ', None, 1, 1, False, True, False, False),
    ('154', 'Chi phí SXKD dở dang', None, 1, 1, False, True, False, False),
    ('155', 'Thành phẩm', None, 1, 1, False, True, False, False),
    ('156', 'Hàng hóa', None, 1, 1, False, True, False, False),
    ('1561', 'Giá mua hàng hóa', '156', 2, 1, True, False, False, False),
    ('1562', 'Chi phí thu mua hàng hóa', '156', 2, 1, True, False, False, False),

    ('159', 'Dự phòng giảm giá HTK', None, 1, 1, True, True, False, False),

    # Type 2 - Tài sản dài hạn
    ('211', 'Tài sản cố định hữu hình', None, 1, 2, False, True, False, False),
    ('2111', 'Nhà cửa, vật kiến trúc', '211', 2, 2, True, False, False, False),
    ('2112', 'Máy móc, thiết bị', '211', 2, 2, True, False, False, False),
    ('2113', 'Phương tiện vận tải, truyền dẫn', '211', 2, 2, True, False, False, False),
    ('2114', 'Thiết bị, dụng cụ quản lý', '211', 2, 2, True, False, False, False),
    ('2115', 'Cây lâu năm, súc vật', '211', 2, 2, True, False, False, False),
    ('2118', 'TSCĐ khác', '211', 2, 2, True, False, False, False),

    ('212', 'TSCĐ thuê tài chính', None, 1, 2, False, True, False, False),

    ('213', 'TSCĐ vô hình', None, 1, 2, False, True, False, False),
    ('2131', 'Quyền sử dụng đất', '213', 2, 2, True, False, False, False),
    ('2132', 'Quyền phát hành', '213', 2, 2, True, False, False, False),
    ('2133', 'Bản quyền, bằng sáng chế', '213', 2, 2, True, False, False, False),
    ('2134', 'Phần mềm máy tính', '213', 2, 2, True, False, False, False),
    ('2136', 'Bản quyền phần mềm', '213', 2, 2, True, False, False, False),
    ('2138', 'TSCĐ vô hình khác', '213', 2, 2, True, False, False, False),

    ('214', 'Hao mòn TSCĐ', None, 1, 2, False, True, False, False),
    ('2141', 'Hao mòn TSCĐ hữu hình', '214', 2, 2, True, False, False, False),
    ('2142', 'Hao mòn TSCĐ thuê TC', '214', 2, 2, True, False, False, False),
    ('2143', 'Hao mòn TSCĐ vô hình', '214', 2, 2, True, False, False, False),

    ('217', 'Tài sản cố định khác', None, 1, 2, True, True, False, False),

    ('221', 'Bất động sản đầu tư', None, 1, 2, False, True, False, False),
    ('2211', 'Chi phí BĐS đầu tư hình thành', '221', 2, 2, True, False, False, False),
    ('2212', 'BĐS đầu tư hoàn thành', '221', 2, 2, True, False, False, False),

    ('228', 'Đầu tư dài hạn khác', None, 1, 2, False, True, False, False),
    ('229', 'Dự phòng tổn thất đầu tư TC dài hạn', None, 1, 2, True, True, False, False),

    ('241', 'Chi phí xây dựng cơ bản dở dang', None, 1, 2, False, True, False, False),
    ('242', 'Chi phí trả trước', None, 1, 2, True, True, False, False),

    # Type 3 - Nợ phải trả
    ('311', 'Vay và nợ thuê tài chính ngắn hạn', None, 1, 3, False, True, False, False),
    ('331', 'Phải trả cho người bán', None, 1, 3, False, True, True, False),
    ('333', 'Thuế và các khoản phải nộp nhà nước', None, 1, 3, False, True, False, False),
    ('3331', 'Thuế GTGT', '333', 2, 3, False, True, False, False),
    ('33311', 'Thuế GTGT đầu ra', '3331', 3, 3, True, False, False, False),
    ('33312', 'Thuế GTGT hàng nhập khẩu', '3331', 3, 3, True, False, False, False),
    ('3332', 'Thuế tiêu thụ đặc biệt', '333', 2, 3, True, False, False, False),
    ('3333', 'Thuế TNDN', '333', 2, 3, True, False, False, False),
    ('3334', 'Thuế nhà thầu', '333', 2, 3, True, False, False, False),
    ('3335', 'Thuế môn bài', '333', 2, 3, True, False, False, False),
    ('3336', 'Thuế TNCN', '333', 2, 3, True, False, False, False),
    ('33381', 'Phí, lệ phí', '333', 2, 3, True, False, False, False),
    ('3339', 'Khoản phải nộp khác', '333', 2, 3, True, False, False, False),

    ('334', 'Phải trả người lao động', None, 1, 3, False, True, False, False),
    ('335', 'Chi phí phải trả', None, 1, 3, False, True, False, False),
    ('336', 'Phải trả nội bộ', None, 1, 3, False, True, True, False),
    ('338', 'Phải trả, phải nộp khác', None, 1, 3, False, True, False, False),
    ('3381', 'Tài sản thừa chờ xử lý', '338', 2, 3, True, False, False, False),
    ('3382', 'Kinh phí công đoàn', '338', 2, 3, True, False, False, False),
    ('3383', 'Bảo hiểm xã hội', '338', 2, 3, True, False, False, False),
    ('3384', 'Bảo hiểm y tế', '338', 2, 3, True, False, False, False),
    ('3386', 'Bảo hiểm thất nghiệp', '338', 2, 3, True, False, False, False),
    ('3389', 'Quỹ khen thưởng, phúc lợi', '338', 2, 3, True, False, False, False),

    ('341', 'Vay và nợ thuê TC dài hạn', None, 1, 3, False, True, False, False),

    # Type 4 - Vốn CSH
    ('411', 'Vốn đầu tư của chủ sở hữu', None, 1, 4, False, True, False, False),
    ('4111', 'Vốn góp của chủ sở hữu', '411', 2, 4, True, False, False, False),
    ('4112', 'Thunk vốn góp', '411', 2, 4, True, False, False, False),
    ('4118', 'Vốn khác của chủ sở hữu', '411', 2, 4, True, False, False, False),

    ('412', 'Chênh lệch đánh giá lại tài sản', None, 1, 4, True, True, False, False),
    ('413', 'Chênh lệch tỷ giá hối đoái', None, 1, 4, True, True, False, False),
    ('418', 'Quỹ khen thưởng, phúc lợi', None, 1, 4, True, True, False, False),
    ('421', 'Lợi nhuận chưa phân phối', None, 1, 4, False, True, False, False),

    # Type 5 - Doanh thu
    ('511', 'Doanh thu', None, 1, 5, False, True, False, False),
    ('5111', 'Doanh thu bán hàng', '511', 2, 5, True, False, False, False),
    ('5112', 'Doanh thu cung cấp dịch vụ', '511', 2, 5, True, False, False, False),
    ('5113', 'Doanh thu trợ cấp, tài trợ', '511', 2, 5, True, False, False, False),
    ('5117', 'Doanh thu kinh doanh BĐS đầu tư', '511', 2, 5, True, False, False, False),
    ('5118', 'Doanh thu khác', '511', 2, 5, True, False, False, False),

    ('515', 'Doanh thu hoạt động tài chính', None, 1, 5, False, True, False, False),

    # Type 6 - Chi phí
    ('621', 'Chi phí NVL trực tiếp', None, 1, 6, False, True, False, False),
    ('622', 'Chi phí nhân công trực tiếp', None, 1, 6, False, True, False, False),
    ('627', 'Chi phí sản xuất chung', None, 1, 6, False, True, False, False),
    ('632', 'Giá vốn hàng bán', None, 1, 6, False, True, False, False),
    ('635', 'Chi phí tài chính', None, 1, 6, False, True, False, False),
    ('641', 'Chi phí bán hàng', None, 1, 6, False, True, False, False),
    ('642', 'Chi phí QLDN', None, 1, 6, False, True, False, False),

    # Type 7 - Thu nhập khác
    ('711', 'Thu nhập khác', None, 1, 7, False, True, False, False),

    # Type 8 - Chi phí khác
    ('811', 'Chi phí khác', None, 1, 8, False, True, False, False),
    ('821', 'Chi phí thuế TNDN', None, 1, 8, False, True, False, False),
    ('8211', 'Chi phí thuế TNDN hiện hành', '821', 2, 8, True, False, False, False),
    ('8212', 'Chi phí thuế TNDN hoãn lại', '821', 2, 8, True, False, False, False),

    # Type 9 - XĐKQ
    ('911', 'Xác định kết quả kinh doanh', None, 1, 9, False, True, False, False),
]


class Command(BaseCommand):
    help = 'Load TT133/2016 chart of accounts for a company'

    def add_arguments(self, parser):
        parser.add_argument('--company-code', required=True, help='Company code')

    def handle(self, *args, **options):
        code = options['company_code']
        try:
            company = Company.objects.get(code=code)
        except Company.DoesNotExist:
            raise CommandError(f'Company not found: {code}')

        # 1. Create account types
        types_created = 0
        type_map = {}
        for t_code, name, bal, cat in ACCOUNT_TYPES:
            at, created = AccountType.objects.update_or_create(
                code=t_code,
                defaults={'name': name, 'balance_type': bal, 'category': cat},
            )
            type_map[t_code] = at
            if created:
                types_created += 1

        # 2. Create accounts
        accounts_created = 0
        for acc_code, name, parent, level, t_code, is_posting, is_gl, allows_obj, allows_cc in ACCOUNTS:
            _, created = ChartOfAccounts.objects.update_or_create(
                company=company, account_code=acc_code,
                defaults={
                    'account_name': name,
                    'parent_account_code': parent or '',
                    'account_level': level,
                    'account_type': type_map[t_code],
                    'is_posting_account': is_posting,
                    'is_general_ledger_account': is_gl,
                    'allows_object_code': allows_obj,
                    'allows_cost_center': allows_cc,
                },
            )
            if created:
                accounts_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Loaded TT133: {types_created} types, {accounts_created} accounts for {code}'
        ))
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/pytest tests/test_load_tt133.py -v
```
Expected: all 4 tests pass.

- [ ] **Step 6: Run loader on dev DB**

```bash
.venv/bin/python manage.py load_tt133 --company-code PKM
.venv/bin/python manage.py shell -c "from apps.master_data.models import ChartOfAccounts; print('Accounts:', ChartOfAccounts.objects.count())"
```
Expected: ~100 accounts created.

- [ ] **Step 7: Commit**

```bash
git add apps/master_data/ tests/test_load_tt133.py
git commit -m "feat(master_data): TT133 fixture loader (~100 accounts)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Ledger app — Voucher + VoucherLine models

**Files:**
- Create: `apps/ledger/__init__.py`, `apps/ledger/apps.py`
- Create: `apps/ledger/models/__init__.py`, `apps/ledger/models/voucher.py`
- Create: `apps/ledger/migrations/__init__.py`
- Modify: `config/settings/base.py`
- Test: `tests/test_voucher_model.py`

- [ ] **Step 1: Write tests**

`tests/test_voucher_model.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test Co')


@pytest.fixture
def voucher(company):
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
        description='Test voucher',
        currency_code='VND', exchange_rate=Decimal('1'),
        status=AccountingVoucher.Status.DRAFT,
    )
    return v


def test_voucher_creation(voucher):
    assert voucher.pk is not None
    assert str(voucher) == 'BC0001 (2026-06-15)'


def test_voucher_status_choices():
    assert AccountingVoucher.Status.DRAFT == 0
    assert AccountingVoucher.Status.SUBSIDIARY == 1
    assert AccountingVoucher.Status.LEDGER == 2
    assert AccountingVoucher.Status.LOCKED == 3


def test_voucher_default_status_is_ledger():
    """If not set, defaults to LEDGER (status=2) per SIS behavior."""
    v = AccountingVoucher(
        company_id=1, fiscal_year=2026, period=6,
        voucher_no='X', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
    )
    assert v.status == AccountingVoucher.Status.LEDGER


def test_voucher_line_creation(voucher):
    line = VoucherLine.objects.create(
        voucher=voucher, line_no=1,
        account_code='111',
        debit_vnd=Decimal('1000'), credit_vnd=Decimal('0'),
    )
    assert line.pk is not None
    assert line.debit_vnd == Decimal('1000')


def test_voucher_unique_per_company_fy_type_no(company):
    AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
    )
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        AccountingVoucher.objects.create(
            company=company, fiscal_year=2026, period=6,
            voucher_no='BC0001', voucher_type='journal',
            voucher_date=date(2026, 6, 16),
        )


def test_voucher_line_object_code_can_be_blank(voucher):
    """Most lines don't need object_code (customer/vendor)."""
    line = VoucherLine.objects.create(
        voucher=voucher, line_no=1,
        account_code='5111', debit_vnd=Decimal('0'), credit_vnd=Decimal('100'),
    )
    assert line.object_code == ''
    assert line.object_type == ''
```

- [ ] **Step 2: Run to fail**

```bash
.venv/bin/pytest tests/test_voucher_model.py -v
```

- [ ] **Step 3: Create apps/ledger/apps.py**

```python
from django.apps import AppConfig


class LedgerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ledger'
    verbose_name = 'General Ledger'
```

- [ ] **Step 4: Create apps/ledger/models/voucher.py**

```python
"""Accounting voucher (phiếu kế toán) and bút toán (voucher line) models."""
from django.db import models
from apps.core.managers import CompanyOwnedModel


class AccountingVoucher(CompanyOwnedModel):
    """Accounting voucher (phiếu kế toán) — header for a set of bút toán."""

    class VoucherType(models.TextChoices):
        JOURNAL = 'journal', 'Phiếu kế toán'
        CASH_RECEIPT = 'cash_receipt', 'Phiếu thu'
        CASH_PAYMENT = 'cash_payment', 'Phiếu chi'
        SALES_INVOICE = 'sales_invoice', 'Hóa đơn bán'
        PURCHASE_INVOICE = 'purchase_invoice', 'Phiếu nhập mua'
        STOCK_VOUCHER = 'stock_voucher', 'Phiếu nhập xuất'
        DEPRECIATION = 'depreciation', 'Khấu hao'
        ALLOCATION = 'allocation', 'Phân bổ'
        CLOSING = 'closing', 'Kết chuyển'

    class Status(models.IntegerChoices):
        DRAFT = 0, 'Lưu tạm'
        SUBSIDIARY = 1, 'Ghi sổ phụ'
        LEDGER = 2, 'Ghi sổ cái'
        LOCKED = 3, 'Đã khóa'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='vouchers',
        db_index=True,
    )
    fiscal_year = models.SmallIntegerField()
    period = models.PositiveSmallIntegerField()
    voucher_no = models.CharField(max_length=50)
    voucher_type = models.CharField(max_length=30, choices=VoucherType.choices)
    voucher_date = models.DateField()
    posting_date = models.DateField(null=True, blank=True)
    book_code = models.CharField(max_length=20, blank=True)
    status = models.PositiveSmallIntegerField(
        choices=Status.choices, default=Status.LEDGER,
    )
    currency_code = models.CharField(max_length=3, default='VND')
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=6, default=1)
    total_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_vnd = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=20, default='manual')
    source_reference_id = models.BigIntegerField(null=True, blank=True)
    is_reversed = models.BooleanField(default=False)
    reversal_voucher = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reversals',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'identity.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vouchers_created',
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'identity.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vouchers_updated',
    )

    objects = models.Manager()

    class Meta:
        db_table = 'accounting_voucher'
        unique_together = [
            ('company', 'fiscal_year', 'voucher_type', 'voucher_no'),
        ]
        indexes = [
            models.Index(fields=['company', 'voucher_date']),
            models.Index(fields=['company', 'fiscal_year', 'period', 'status']),
            models.Index(fields=['company', 'voucher_type', 'voucher_date']),
        ]
        ordering = ['-voucher_date', '-id']

    def __str__(self):
        return f'{self.voucher_no} ({self.voucher_date})'

    @property
    def is_posted(self):
        return self.status >= self.Status.LEDGER

    @property
    def is_locked(self):
        return self.status == self.Status.LOCKED


class VoucherLine(models.Model):
    """Bút toán — single debit or credit entry in a voucher."""

    class ObjectType(models.TextChoices):
        NONE = '', '—'
        CUSTOMER = 'customer', 'Khách hàng'
        VENDOR = 'vendor', 'Nhà cung cấp'
        EMPLOYEE = 'employee', 'Nhân viên'
        BANK = 'bank', 'Ngân hàng'
        OTHER = 'other', 'Khác'

    voucher = models.ForeignKey(
        AccountingVoucher, on_delete=models.CASCADE, related_name='lines',
    )
    line_no = models.PositiveSmallIntegerField()
    account_code = models.CharField(max_length=20)
    object_type = models.CharField(
        max_length=20, choices=ObjectType.choices, blank=True, default='',
    )
    object_code = models.CharField(max_length=50, blank=True, default='')
    object_name = models.CharField(max_length=255, blank=True, default='')
    debit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    credit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    debit_vnd = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    credit_vnd = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    description = models.TextField(blank=True, default='')
    cost_center_code = models.CharField(max_length=50, blank=True, default='')
    project_code = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        db_table = 'voucher_line'
        unique_together = [('voucher', 'line_no')]
        indexes = [
            models.Index(fields=['account_code']),
            models.Index(fields=['object_type', 'object_code']),
        ]
        ordering = ['line_no']

    def __str__(self):
        side = 'Nợ' if self.debit_vnd > 0 else 'Có'
        amount = self.debit_vnd or self.credit_vnd
        return f'{self.line_no}. {self.account_code} {side} {amount}'
```

- [ ] **Step 5: Create apps/ledger/models/__init__.py**

```python
from .voucher import AccountingVoucher, VoucherLine

__all__ = ['AccountingVoucher', 'VoucherLine']
```

- [ ] **Step 6: Add to INSTALLED_APPS**

Add `'apps.ledger',` after `'apps.master_data',` in `config/settings/base.py`.

- [ ] **Step 7: Create migration + migrate**

```bash
.venv/bin/python manage.py makemigrations ledger
.venv/bin/python manage.py migrate
```

- [ ] **Step 8: Run tests**

```bash
.venv/bin/pytest tests/test_voucher_model.py -v
.venv/bin/pytest -v
```

- [ ] **Step 9: Commit**

```bash
git add apps/ledger/ config/settings/base.py tests/test_voucher_model.py
git commit -m "feat(ledger): AccountingVoucher + VoucherLine models

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: AccountPeriodBalance (projection)

**Files:**
- Modify: `apps/ledger/models/__init__.py`
- Create: `apps/ledger/models/balance.py`
- Test: `tests/test_account_balance.py`

- [ ] **Step 1: Write tests**

`tests/test_account_balance.py`:
```python
import pytest
from decimal import Decimal
from apps.ledger.models import AccountPeriodBalance
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test')


def test_balance_creation(company):
    b = AccountPeriodBalance.objects.create(
        company=company, fiscal_year=2026, period=6,
        account_code='111',
        opening_debit=Decimal('1000'),
        period_debit=Decimal('500'),
        period_credit=Decimal('200'),
        closing_debit=Decimal('1300'),
        closing_credit=Decimal('0'),
    )
    assert b.pk is not None
    assert b.closing_debit == Decimal('1300')


def test_balance_unique_per_company_period_account(company):
    AccountPeriodBalance.objects.create(
        company=company, fiscal_year=2026, period=6,
        account_code='111',
    )
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        AccountPeriodBalance.objects.create(
            company=company, fiscal_year=2026, period=6,
            account_code='111',
        )


def test_balance_with_object_code(company):
    """Same account can have multiple balances per object_code."""
    AccountPeriodBalance.objects.create(
        company=company, fiscal_year=2026, period=6,
        account_code='131', object_type='customer', object_code='KH001',
    )
    AccountPeriodBalance.objects.create(
        company=company, fiscal_year=2026, period=6,
        account_code='131', object_type='customer', object_code='KH002',
    )
    assert AccountPeriodBalance.objects.filter(account_code='131').count() == 2
```

- [ ] **Step 2: Run to fail**

```bash
.venv/bin/pytest tests/test_account_balance.py -v
```

- [ ] **Step 3: Create apps/ledger/models/balance.py**

```python
"""Account balance projections — pre-computed for fast reporting."""
from django.db import models


class AccountPeriodBalance(models.Model):
    """Period balance per account (+ optional object).

    Updated by VoucherPostingService on post/unpost.
    Rebuildable from voucher_line table.
    """

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='balances',
        db_index=True,
    )
    fiscal_year = models.SmallIntegerField()
    period = models.PositiveSmallIntegerField()
    account_code = models.CharField(max_length=20)
    object_type = models.CharField(max_length=20, blank=True, default='')
    object_code = models.CharField(max_length=50, blank=True, default='')

    opening_debit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    opening_credit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_debit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_credit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_debit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_credit = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    opening_debit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    opening_credit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_debit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_credit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_debit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_credit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    last_transaction_date = models.DateField(null=True, blank=True)
    transaction_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'account_period_balance'
        unique_together = [
            ('company', 'fiscal_year', 'period', 'account_code', 'object_type', 'object_code'),
        ]
        indexes = [
            models.Index(fields=['company', 'fiscal_year', 'period']),
            models.Index(fields=['account_code']),
            models.Index(fields=['object_type', 'object_code']),
        ]

    def __str__(self):
        return f'{self.account_code} P{self.period}/{self.fiscal_year}'

    def recalculate_closing(self):
        """Compute closing from opening + period. Side with larger value wins."""
        d = self.opening_debit + self.period_debit
        c = self.opening_credit + self.period_credit
        if d >= c:
            self.closing_debit = d - c
            self.closing_credit = 0
        else:
            self.closing_credit = c - d
            self.closing_debit = 0
```

- [ ] **Step 4: Update __init__.py**

```python
from .voucher import AccountingVoucher, VoucherLine
from .balance import AccountPeriodBalance

__all__ = ['AccountingVoucher', 'VoucherLine', 'AccountPeriodBalance']
```

- [ ] **Step 5: Create migration**

```bash
.venv/bin/python manage.py makemigrations ledger
.venv/bin/python manage.py migrate
```

- [ ] **Step 6: Run tests**

```bash
.venv/bin/pytest tests/test_account_balance.py -v
.venv/bin/pytest -v
```

- [ ] **Step 7: Commit**

```bash
git add apps/ledger/ tests/test_account_balance.py
git commit -m "feat(ledger): AccountPeriodBalance projection model

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: VoucherPostingService

**Files:**
- Create: `apps/ledger/services/__init__.py`
- Create: `apps/ledger/services/voucher_posting_service.py`
- Test: `tests/test_voucher_posting_service.py`

- [ ] **Step 1: Write tests**

`tests/test_voucher_posting_service.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from apps.ledger.models import AccountingVoucher, VoucherLine, AccountPeriodBalance
from apps.ledger.services import VoucherPostingService
from apps.core.models import Company


@pytest.fixture
def company(db):
    from apps.master_data.management.commands.load_tt133 import Command
    c = Company.objects.create(code='TCO', name='Test', fiscal_year_start_month=1)
    # Load chart so accounts exist (for validation if needed)
    # Actually we don't validate account existence in service — just balance
    return c


def _make_voucher(company, debit_lines, credit_lines, status=AccountingVoucher.Status.DRAFT):
    """Helper: create voucher with given lines. Each line is (account_code, amount)."""
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no=f'BC-{company.pk}-{AccountingVoucher.objects.count()+1}',
        voucher_type='journal', voucher_date=date(2026, 6, 15),
        status=status,
    )
    line_no = 1
    for acc, amt in debit_lines:
        VoucherLine.objects.create(
            voucher=v, line_no=line_no, account_code=acc,
            debit_vnd=Decimal(str(amt)), credit_vnd=Decimal('0'),
        )
        line_no += 1
    for acc, amt in credit_lines:
        VoucherLine.objects.create(
            voucher=v, line_no=line_no, account_code=acc,
            debit_vnd=Decimal('0'), credit_vnd=Decimal(str(amt)),
        )
        line_no += 1
    return v


def test_post_balanced_voucher_updates_balance(company):
    v = _make_voucher(
        company,
        debit_lines=[('111', 1000)],
        credit_lines=[('5111', 1000)],
    )
    service = VoucherPostingService()
    service.post(v)

    v.refresh_from_db()
    assert v.status == AccountingVoucher.Status.LEDGER
    assert v.total_vnd == Decimal('1000')

    bal = AccountPeriodBalance.objects.get(
        company=company, fiscal_year=2026, period=6, account_code='111',
    )
    assert bal.period_debit == Decimal('1000')
    assert bal.closing_debit == Decimal('1000')
    assert bal.closing_credit == Decimal('0')

    bal5111 = AccountPeriodBalance.objects.get(
        company=company, fiscal_year=2026, period=6, account_code='5111',
    )
    assert bal5111.period_credit == Decimal('1000')
    assert bal5111.closing_credit == Decimal('1000')


def test_post_unbalanced_voucher_raises(company):
    from apps.ledger.services.voucher_posting_service import VoucherNotBalancedError
    v = _make_voucher(
        company,
        debit_lines=[('111', 1000)],
        credit_lines=[('5111', 500)],  # imbalance
    )
    service = VoucherPostingService()
    with pytest.raises(VoucherNotBalancedError):
        service.post(v)


def test_post_already_posted_is_idempotent(company):
    v = _make_voucher(
        company,
        debit_lines=[('111', 1000)],
        credit_lines=[('5111', 1000)],
        status=AccountingVoucher.Status.LEDGER,  # already posted
    )
    service = VoucherPostingService()
    # Should not raise; should not double-count
    service.post(v)
    # Verify balance was added once (not twice)
    bal = AccountPeriodBalance.objects.get(
        company=company, fiscal_year=2026, period=6, account_code='111',
    )
    assert bal.period_debit == Decimal('1000')  # not 2000


def test_unpost_reverts_balance(company):
    v = _make_voucher(
        company,
        debit_lines=[('111', 1000)],
        credit_lines=[('5111', 1000)],
    )
    service = VoucherPostingService()
    service.post(v)
    service.unpost(v)

    v.refresh_from_db()
    assert v.status == AccountingVoucher.Status.DRAFT

    bal = AccountPeriodBalance.objects.get(
        company=company, fiscal_year=2026, period=6, account_code='111',
    )
    assert bal.period_debit == Decimal('0')


def test_post_locked_voucher_raises(company):
    from apps.ledger.services.voucher_posting_service import VoucherLockedError
    v = _make_voucher(
        company,
        debit_lines=[('111', 1000)],
        credit_lines=[('5111', 1000)],
        status=AccountingVoucher.Status.LOCKED,
    )
    service = VoucherPostingService()
    with pytest.raises(VoucherLockedError):
        service.post(v)
```

- [ ] **Step 2: Run to fail**

```bash
.venv/bin/pytest tests/test_voucher_posting_service.py -v
```

- [ ] **Step 3: Create apps/ledger/services/__init__.py**

```python
from .voucher_posting_service import VoucherPostingService

__all__ = ['VoucherPostingService']
```

- [ ] **Step 4: Create apps/ledger/services/voucher_posting_service.py**

```python
"""VoucherPostingService: post/unpost voucher → updates AccountPeriodBalance."""
from decimal import Decimal
from django.db import transaction
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance


class VoucherNotBalancedError(Exception):
    """Raised when voucher debit total != credit total."""

    def __init__(self, total_debit, total_credit):
        self.total_debit = total_debit
        self.total_credit = total_credit
        super().__init__(
            f'Voucher not balanced: debit={total_debit} credit={total_credit} '
            f'diff={total_debit - total_credit}'
        )


class VoucherLockedError(Exception):
    """Raised when attempting to modify a locked voucher."""


class VoucherPostingService:
    """Service for posting/unposting vouchers and updating balance projections."""

    BALANCE_TOLERANCE = Decimal('0.01')  # 1 VND rounding tolerance

    @transaction.atomic
    def post(self, voucher: AccountingVoucher) -> None:
        """Post a voucher: validate + update AccountPeriodBalance + set status=LEDGER."""
        if voucher.is_locked:
            raise VoucherLockedError(f'Voucher {voucher.voucher_no} is locked')

        if voucher.is_posted:
            return  # idempotent — already posted

        self._validate_balanced(voucher)
        self._update_balances(voucher, sign=+1)

        voucher.status = AccountingVoucher.Status.LEDGER
        voucher.save(update_fields=['status', 'updated_at'])

    @transaction.atomic
    def unpost(self, voucher: AccountingVoucher) -> None:
        """Unpost a voucher: revert balance updates + set status=DRAFT."""
        if voucher.is_locked:
            raise VoucherLockedError(f'Voucher {voucher.voucher_no} is locked')

        if not voucher.is_posted:
            return  # idempotent — already unposted

        self._update_balances(voucher, sign=-1)

        voucher.status = AccountingVoucher.Status.DRAFT
        voucher.save(update_fields=['status', 'updated_at'])

    def _validate_balanced(self, voucher: AccountingVoucher) -> None:
        """Verify total debit == total credit."""
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        for line in voucher.lines.all():
            total_debit += line.debit_vnd or Decimal('0')
            total_credit += line.credit_vnd or Decimal('0')

        if abs(total_debit - total_credit) > self.BALANCE_TOLERANCE:
            raise VoucherNotBalancedError(total_debit, total_credit)

        # Also update voucher totals
        voucher.total_vnd = total_debit
        voucher.total_fc = sum((l.debit_fc or 0 for l in voucher.lines.all()), Decimal('0'))

    def _update_balances(self, voucher: AccountingVoucher, sign: int) -> None:
        """Update AccountPeriodBalance for each line. sign=+1 for post, -1 for unpost."""
        for line in voucher.lines.all():
            self._update_one_balance(voucher, line, sign)

    def _update_one_balance(self, voucher: AccountingVoucher, line, sign: int) -> None:
        """Update or create the balance row for one line."""
        balance, _ = AccountPeriodBalance.objects.get_or_create(
            company=voucher.company,
            fiscal_year=voucher.fiscal_year,
            period=voucher.period,
            account_code=line.account_code,
            object_type=line.object_type or '',
            object_code=line.object_code or '',
            defaults={
                'opening_debit': Decimal('0'),
                'opening_credit': Decimal('0'),
            },
        )

        # Apply delta (sign controls direction)
        balance.period_debit += sign * (line.debit_vnd or Decimal('0'))
        balance.period_credit += sign * (line.credit_vnd or Decimal('0'))
        balance.period_debit_fc += sign * (line.debit_fc or Decimal('0'))
        balance.period_credit_fc += sign * (line.credit_fc or Decimal('0'))

        # Recalculate closing
        balance.recalculate_closing()

        # Track last txn
        if sign > 0:
            if not balance.last_transaction_date or voucher.voucher_date > balance.last_transaction_date:
                balance.last_transaction_date = voucher.voucher_date
            balance.transaction_count = (balance.transaction_count or 0) + 1
        else:
            balance.transaction_count = max(0, (balance.transaction_count or 0) - 1)

        balance.save()
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/pytest tests/test_voucher_posting_service.py -v
.venv/bin/pytest -v
```

- [ ] **Step 6: Commit**

```bash
git add apps/ledger/ tests/test_voucher_posting_service.py
git commit -m "feat(ledger): VoucherPostingService with post/unpost + balance projection

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: Voucher list view (Modern UI)

**Files:**
- Create: `apps/ui_modern/views/ledger_views.py`
- Modify: `apps/ui_modern/views/__init__.py`
- Modify: `apps/ui_modern/urls.py`
- Create: `templates/modern/ledger/voucher_list.html`
- Create: `static/modern/css/ledger.css`
- Test: `tests/test_voucher_views.py`

- [ ] **Step 1: Write tests**

`tests/test_voucher_views.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from django.test import Client
from django.urls import reverse
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.core.models import Company
from apps.identity.models import User


@pytest.fixture
def setup_user_company(db):
    company = Company.objects.create(code='TCO', name='Test')
    user = User.objects.create_user(username='alice', password='Secret123')
    return company, user


@pytest.fixture
def auth_client(setup_user_company):
    _, user = setup_user_company
    c = Client()
    c.force_login(user)
    return c


def test_voucher_list_requires_login(db):
    c = Client()
    response = c.get('/modern/vouchers/')
    assert response.status_code == 302
    assert '/auth/login/' in response.url


@pytest.mark.django_db
def test_voucher_list_loads_empty(auth_client):
    response = auth_client.get('/modern/vouchers/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'Phiếu kế toán' in content
    assert 'Thêm' in content  # Add button


@pytest.mark.django_db
def test_voucher_list_shows_voucher(setup_user_company, auth_client):
    company, _ = setup_user_company
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), description='Test voucher',
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code='111',
        debit_vnd=Decimal('1000000'), credit_vnd=Decimal('0'),
    )

    response = auth_client.get('/modern/vouchers/')
    content = response.content.decode('utf-8')
    assert 'BC0001' in content
    assert 'Test voucher' in content
```

- [ ] **Step 2: Run to fail**

```bash
.venv/bin/pytest tests/test_voucher_views.py -v
```

- [ ] **Step 3: Create view**

`apps/ui_modern/views/ledger_views.py`:
```python
"""Ledger views — voucher list, form, detail."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.shortcuts import render
from apps.ledger.models import AccountingVoucher


class VoucherListView(LoginRequiredMixin, ListView):
    """List of accounting vouchers for the current company."""
    template_name = 'modern/ledger/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 25
    login_url = '/auth/login/'

    def get_queryset(self):
        # TODO: filter by request.current_company once company switcher wired
        qs = AccountingVoucher.objects.select_related('company').order_by('-voucher_date', '-id')
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Phiếu kế toán'
        ctx['status_choices'] = AccountingVoucher.Status.choices
        return ctx
```

- [ ] **Step 4: Update views/__init__.py**

Add `from .ledger_views import VoucherListView` and add to `__all__`.

- [ ] **Step 5: Update urls.py**

```python
from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import DashboardView, VoucherListView

app_name = 'ui_modern'

urlpatterns = [
    path('', login_required(DashboardView.as_view()), name='dashboard'),
    path('vouchers/', login_required(VoucherListView.as_view()), name='voucher_list'),
]
```

- [ ] **Step 6: Create template**

`templates/modern/ledger/voucher_list.html`:
```html
{% extends 'modern/base/layout.html' %}

{% block content %}
<div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb mb-1">
                    <li class="breadcrumb-item"><a href="{% url 'ui_modern:dashboard' %}">Trang chủ</a></li>
                    <li class="breadcrumb-item active">Phiếu kế toán</li>
                </ol>
            </nav>
            <h1 class="h3 mb-0">{{ page_title }}</h1>
        </div>
        <div>
            <button class="btn btn-outline-secondary btn-sm">
                <i class="bi bi-download"></i> Xuất Excel
            </button>
            <a href="#" class="btn btn-primary btn-sm">
                <i class="bi bi-plus"></i> Thêm mới
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
            <form method="get" class="row g-2 mb-3">
                <div class="col-auto">
                    <input type="text" class="form-control form-control-sm" name="search"
                           placeholder="Tìm theo số CT hoặc diễn giải..."
                           value="{{ request.GET.search }}">
                </div>
                <div class="col-auto">
                    <select class="form-select form-select-sm" name="status">
                        <option value="">Tất cả trạng thái</option>
                        {% for code, label in status_choices %}
                        <option value="{{ code }}" {% if request.GET.status == code|stringformat:"s" %}selected{% endif %}>{{ label }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-auto">
                    <button type="submit" class="btn btn-outline-primary btn-sm">
                        <i class="bi bi-funnel"></i> Lọc
                    </button>
                </div>
            </form>

            <div class="table-responsive">
                <table class="table table-sm table-hover align-middle">
                    <thead class="table-light">
                        <tr>
                            <th>Ngày</th>
                            <th>Số CT</th>
                            <th>Loại</th>
                            <th>Diễn giải</th>
                            <th class="text-end">Tổng tiền (VND)</th>
                            <th>Trạng thái</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for voucher in vouchers %}
                        <tr>
                            <td>{{ voucher.voucher_date|date:"d/m/Y" }}</td>
                            <td><a href="#" class="text-decoration-none">{{ voucher.voucher_no }}</a></td>
                            <td><small class="text-muted">{{ voucher.get_voucher_type_display }}</small></td>
                            <td>{{ voucher.description|truncatechars:60 }}</td>
                            <td class="text-end font-mono">{{ voucher.total_vnd|floatformat:0 }}</td>
                            <td>
                                {% if voucher.status == 0 %}<span class="badge bg-warning">Lưu tạm</span>
                                {% elif voucher.status == 1 %}<span class="badge bg-info">Sổ phụ</span>
                                {% elif voucher.status == 2 %}<span class="badge bg-success">Đã ghi sổ</span>
                                {% elif voucher.status == 3 %}<span class="badge bg-secondary">Đã khóa</span>
                                {% endif %}
                            </td>
                            <td>
                                <a href="#" class="btn btn-sm btn-outline-secondary py-0">
                                    <i class="bi bi-eye"></i>
                                </a>
                            </td>
                        </tr>
                        {% empty %}
                        <tr>
                            <td colspan="7" class="text-center text-muted py-4">
                                <i class="bi bi-inbox display-6 d-block mb-2"></i>
                                Chưa có phiếu kế toán nào. Bấm "Thêm mới" để tạo.
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            {% if is_paginated %}
            <nav>
                <ul class="pagination pagination-sm justify-content-end">
                    {% if page_obj.has_previous %}
                    <li class="page-item"><a class="page-link" href="?page={{ page_obj.previous_page_number }}">←</a></li>
                    {% endif %}
                    <li class="page-item active"><span class="page-link">{{ page_obj.number }} / {{ page_obj.paginator.num_pages }}</span></li>
                    {% if page_obj.has_next %}
                    <li class="page-item"><a class="page-link" href="?page={{ page_obj.next_page_number }}">→</a></li>
                    {% endif %}
                </ul>
            </nav>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 7: Add CSS**

`static/modern/css/ledger.css`:
```css
.font-mono { font-family: 'JetBrains Mono', 'Consolas', monospace; font-variant-numeric: tabular-nums; }
.table-hover tbody tr:hover { cursor: pointer; }
```

Add to base layout: `<link rel="stylesheet" href="{% static 'modern/css/ledger.css' %}">` after `main.css`.

- [ ] **Step 8: Run tests**

```bash
.venv/bin/pytest tests/test_voucher_views.py -v
.venv/bin/pytest -v
```

- [ ] **Step 9: Commit**

```bash
git add apps/ui_modern/ templates/modern/ static/modern/ tests/test_voucher_views.py
git commit -m "feat(ui_modern): voucher list view with filter + pagination

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8: Voucher create form (Standard style)

**Files:**
- Modify: `apps/ui_modern/views/ledger_views.py` (add VoucherCreateView)
- Create: `apps/ui_modern/forms/__init__.py` update
- Create: `apps/ui_modern/forms/voucher_form.py`
- Modify: `apps/ui_modern/urls.py`
- Create: `templates/modern/ledger/voucher_form.html`
- Modify: `tests/test_voucher_views.py` (add form tests)

- [ ] **Step 1: Add tests**

Append to `tests/test_voucher_views.py`:
```python
@pytest.mark.django_db
def test_voucher_create_form_loads(auth_client):
    response = auth_client.get('/modern/vouchers/new/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'name="voucher_no"' in content or 'voucher_no' in content
    assert 'Bút toán' in content or 'lines' in content


@pytest.mark.django_db
def test_voucher_create_post_valid(setup_user_company, auth_client):
    company, _ = setup_user_company
    response = auth_client.post('/modern/vouchers/new/', {
        'voucher_no': 'BC0001',
        'voucher_date': '2026-06-15',
        'voucher_type': 'journal',
        'description': 'Test',
        'lines-TOTAL_FORMS': '2',
        'lines-INITIAL_FORMS': '0',
        'lines-MIN_NUM_FORMS': '2',
        'lines-MAX_NUM_FORMS': '1000',
        'lines-0-account_code': '111',
        'lines-0-debit_vnd': '1000',
        'lines-0-credit_vnd': '0',
        'lines-1-account_code': '5111',
        'lines-1-debit_vnd': '0',
        'lines-1-credit_vnd': '1000',
    })
    assert response.status_code == 302
    assert '/modern/vouchers/' in response.url
    v = AccountingVoucher.objects.get(voucher_no='BC0001')
    assert v.lines.count() == 2
    assert v.total_vnd == 1000
    # Default status is LEDGER (auto-posted)
    assert v.status == AccountingVoucher.Status.LEDGER


@pytest.mark.django_db
def test_voucher_create_unbalanced_fails(setup_user_company, auth_client):
    response = auth_client.post('/modern/vouchers/new/', {
        'voucher_no': 'BC0001',
        'voucher_date': '2026-06-15',
        'voucher_type': 'journal',
        'description': 'Test',
        'lines-TOTAL_FORMS': '2',
        'lines-INITIAL_FORMS': '0',
        'lines-0-account_code': '111',
        'lines-0-debit_vnd': '1000',
        'lines-0-credit_vnd': '0',
        'lines-1-account_code': '5111',
        'lines-1-debit_vnd': '0',
        'lines-1-credit_vnd': '500',  # imbalance
    })
    # Should re-render form with error, not crash
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'không cân đối' in content.lower() or 'not balanced' in content.lower() or 'alert' in content
```

- [ ] **Step 2: Run tests to fail**

```bash
.venv/bin/pytest tests/test_voucher_views.py -v
```

- [ ] **Step 3: Create forms**

`apps/ui_modern/forms/voucher_form.py`:
```python
"""Forms for voucher creation."""
from django import forms
from django.forms import formset_factory

from apps.ledger.models import AccountingVoucher


class VoucherHeaderForm(forms.Form):
    """Voucher header fields."""
    voucher_no = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Tự động nếu để trống',
        }),
    )
    voucher_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
    )
    voucher_type = forms.ChoiceField(
        choices=AccountingVoucher.VoucherType.choices,
        initial=AccountingVoucher.VoucherType.JOURNAL,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm', 'rows': 2,
        }),
    )


class VoucherLineForm(forms.Form):
    """Single bút toán line."""
    account_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm font-mono',
            'placeholder': 'TK',
            'list': 'account-list',
        }),
    )
    object_code = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Đối tượng',
        }),
    )
    debit_vnd = forms.DecimalField(
        required=False, max_digits=20, decimal_places=4,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm text-end font-mono',
            'step': '0.0001',
        }),
    )
    credit_vnd = forms.DecimalField(
        required=False, max_digits=20, decimal_places=4,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm text-end font-mono',
            'step': '0.0001',
        }),
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Diễn giải dòng',
        }),
    )


VoucherLineFormSet = formset_factory(
    VoucherLineForm,
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=True,
)
```

Update `apps/ui_modern/forms/__init__.py`:
```python
from .auth_forms import LoginForm
from .voucher_form import VoucherHeaderForm, VoucherLineForm, VoucherLineFormSet

__all__ = ['LoginForm', 'VoucherHeaderForm', 'VoucherLineForm', 'VoucherLineFormSet']
```

- [ ] **Step 4: Create view**

Add to `apps/ui_modern/views/ledger_views.py`:
```python
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from decimal import Decimal
from datetime import datetime

from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.ledger.services.voucher_posting_service import VoucherNotBalancedError
from apps.ui_modern.forms import VoucherHeaderForm, VoucherLineFormSet


class VoucherCreateView(LoginRequiredMixin, View):
    """Create a new accounting voucher (Standard style — full form)."""
    template_name = 'modern/ledger/voucher_form.html'
    login_url = '/auth/login/'

    def get(self, request, *args, **kwargs):
        header_form = VoucherHeaderForm()
        line_formset = VoucherLineFormSet()

        return render(request, self.template_name, {
            'page_title': 'Tạo phiếu kế toán',
            'header_form': header_form,
            'line_formset': line_formset,
            'is_new': True,
        })

    def post(self, request, *args, **kwargs):
        header_form = VoucherHeaderForm(request.POST)
        line_formset = VoucherLineFormSet(request.POST)

        if not header_form.is_valid() or not line_formset.is_valid():
            return render(request, self.template_name, {
                'page_title': 'Tạo phiếu kế toán',
                'header_form': header_form,
                'line_formset': line_formset,
                'is_new': True,
            }, status=400)

        # Compute totals
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        for line_form in line_formset:
            if line_form.cleaned_data.get('DELETE'):
                continue
            d = line_form.cleaned_data.get('debit_vnd') or Decimal('0')
            c = line_form.cleaned_data.get('credit_vnd') or Decimal('0')
            total_debit += d
            total_credit += c

        if abs(total_debit - total_credit) > Decimal('0.01'):
            messages.error(request, f'Chứng từ không cân đối: Nợ={total_debit} Có={total_credit}')
            return render(request, self.template_name, {
                'page_title': 'Tạo phiếu kế toán',
                'header_form': header_form,
                'line_formset': line_formset,
                'is_new': True,
                'total_debit': total_debit,
                'total_credit': total_credit,
            }, status=400)

        # Get the company — for now use first company (TODO: use request.current_company)
        from apps.core.models import Company
        company = Company.objects.first()
        if not company:
            messages.error(request, 'No company configured.')
            return redirect('ui_modern:voucher_list')

        # Create voucher
        cd = header_form.cleaned_data
        voucher = AccountingVoucher.objects.create(
            company=company,
            fiscal_year=cd['voucher_date'].year,
            period=cd['voucher_date'].month,
            voucher_no=cd.get('voucher_no') or f'AUTO-{AccountingVoucher.objects.count() + 1:04d}',
            voucher_type=cd['voucher_type'],
            voucher_date=cd['voucher_date'],
            description=cd.get('description', ''),
            currency_code='VND',
            exchange_rate=Decimal('1'),
            total_vnd=total_debit,
            status=AccountingVoucher.Status.DRAFT,  # create as draft, then post
            created_by=request.user,
        )

        line_no = 1
        for line_form in line_formset:
            if line_form.cleaned_data.get('DELETE'):
                continue
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=line_form.cleaned_data['account_code'],
                object_code=line_form.cleaned_data.get('object_code', ''),
                debit_vnd=line_form.cleaned_data.get('debit_vnd') or Decimal('0'),
                credit_vnd=line_form.cleaned_data.get('credit_vnd') or Decimal('0'),
                description=line_form.cleaned_data.get('description', ''),
            )
            line_no += 1

        # Auto-post
        try:
            VoucherPostingService().post(voucher)
            messages.success(request, f'Đã ghi sổ phiếu {voucher.voucher_no}')
        except VoucherNotBalancedError as e:
            messages.error(request, str(e))

        return redirect('ui_modern:voucher_list')
```

- [ ] **Step 5: Update views/__init__.py**

```python
from .dashboard_views import DashboardView
from .auth_views import PMKetoanLoginView, PMKetoanLogoutView
from .health_views import health_simple, health_detailed
from .ledger_views import VoucherListView, VoucherCreateView

__all__ = [
    'DashboardView', 'PMKetoanLoginView', 'PMKetoanLogoutView',
    'health_simple', 'health_detailed',
    'VoucherListView', 'VoucherCreateView',
]
```

- [ ] **Step 6: Update urls.py**

```python
urlpatterns = [
    path('', login_required(DashboardView.as_view()), name='dashboard'),
    path('vouchers/', login_required(VoucherListView.as_view()), name='voucher_list'),
    path('vouchers/new/', login_required(VoucherCreateView.as_view()), name='voucher_create'),
]
```

- [ ] **Step 7: Create template**

`templates/modern/ledger/voucher_form.html`:
```html
{% extends 'modern/base/layout.html' %}
{% load static %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'modern/css/ledger.css' %}">
{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb mb-1">
                    <li class="breadcrumb-item"><a href="{% url 'ui_modern:dashboard' %}">Trang chủ</a></li>
                    <li class="breadcrumb-item"><a href="{% url 'ui_modern:voucher_list' %}">Phiếu kế toán</a></li>
                    <li class="breadcrumb-item active">{{ page_title }}</li>
                </ol>
            </nav>
            <h1 class="h3 mb-0">{{ page_title }}</h1>
        </div>
        <a href="{% url 'ui_modern:voucher_list' %}" class="btn btn-outline-secondary btn-sm">
            <i class="bi bi-arrow-left"></i> Hủy
        </a>
    </div>

    <form method="post">
        {% csrf_token %}

        {% if messages %}
        {% for message in messages %}
        <div class="alert alert-{{ message.tags|default:'info' }} alert-dismissible">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        {% endfor %}
        {% endif %}

        <div class="card mb-3">
            <div class="card-header py-2"><strong>Thông tin chung</strong></div>
            <div class="card-body">
                <div class="row g-2">
                    <div class="col-md-2">
                        <label class="form-label small">Ngày sổ cái *</label>
                        {{ header_form.voucher_date }}
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small">Số CT</label>
                        {{ header_form.voucher_no }}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small">Loại CT</label>
                        {{ header_form.voucher_type }}
                    </div>
                    <div class="col-md-5">
                        <label class="form-label small">Diễn giải</label>
                        {{ header_form.description }}
                    </div>
                </div>
            </div>
        </div>

        <div class="card mb-3">
            <div class="card-header py-2 d-flex justify-content-between align-items-center">
                <strong>Bút toán</strong>
                <span class="text-muted small">Tối thiểu 2 dòng</span>
            </div>
            <div class="card-body p-0">
                {{ line_formset.management_form }}
                <table class="table table-sm mb-0">
                    <thead class="table-light">
                        <tr>
                            <th style="width: 50px;">#</th>
                            <th style="width: 120px;">Tài khoản</th>
                            <th style="width: 150px;">Đối tượng</th>
                            <th class="text-end" style="width: 150px;">Nợ (VND)</th>
                            <th class="text-end" style="width: 150px;">Có (VND)</th>
                            <th>Diễn giải</th>
                            <th style="width: 40px;"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for form in line_formset %}
                        <tr>
                            <td class="text-muted">{{ forloop.counter }}</td>
                            <td>{{ form.account_code }}</td>
                            <td>{{ form.object_code }}</td>
                            <td>{{ form.debit_vnd }}</td>
                            <td>{{ form.credit_vnd }}</td>
                            <td>{{ form.description }}</td>
                            <td>{{ form.DELETE }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                    {% if total_debit is not None %}
                    <tfoot>
                        <tr class="table-light fw-bold">
                            <td colspan="3" class="text-end">Tổng cộng:</td>
                            <td class="text-end font-mono">{{ total_debit|floatformat:0 }}</td>
                            <td class="text-end font-mono">{{ total_credit|floatformat:0 }}</td>
                            <td colspan="2"></td>
                        </tr>
                    </tfoot>
                    {% endif %}
                </table>
            </div>
        </div>

        <div class="d-flex justify-content-end gap-2">
            <a href="{% url 'ui_modern:voucher_list' %}" class="btn btn-outline-secondary btn-sm">Hủy</a>
            <button type="submit" class="btn btn-primary btn-sm">
                <i class="bi bi-check-circle"></i> Lưu & ghi sổ
            </button>
        </div>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 8: Run tests**

```bash
.venv/bin/pytest tests/test_voucher_views.py -v
.venv/bin/pytest -v
```

- [ ] **Step 9: Commit**

```bash
git add apps/ui_modern/ templates/modern/ledger/voucher_form.html tests/test_voucher_views.py
git commit -m "feat(ui_modern): voucher create form (Standard style)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 9: Trial Balance view

**Files:**
- Create: `apps/ui_modern/views/report_views.py`
- Modify: `apps/ui_modern/views/__init__.py`
- Modify: `apps/ui_modern/urls.py`
- Create: `templates/modern/reporting/trial_balance.html`
- Test: `tests/test_trial_balance.py`

- [ ] **Step 1: Write tests**

`tests/test_trial_balance.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from django.test import Client
from apps.ledger.models import AccountingVoucher, VoucherLine, AccountPeriodBalance
from apps.ledger.services import VoucherPostingService
from apps.core.models import Company
from apps.identity.models import User


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    user = User.objects.create_user(username='alice', password='Secret123')
    return company, user


@pytest.fixture
def auth_client(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_trial_balance_requires_login(db):
    c = Client()
    response = c.get('/modern/reports/trial-balance/')
    assert response.status_code == 302


@pytest.mark.django_db
def test_trial_balance_loads_empty(auth_client):
    response = auth_client.get('/modern/reports/trial-balance/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'Bảng cân đối tài khoản' in content or 'BCĐ' in content


@pytest.mark.django_db
def test_trial_balance_shows_data(setup, auth_client):
    company, _ = setup
    # Create + post a voucher
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), status=AccountingVoucher.Status.DRAFT,
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code='111',
        debit_vnd=Decimal('1000'), credit_vnd=Decimal('0'),
    )
    VoucherLine.objects.create(
        voucher=v, line_no=2, account_code='5111',
        debit_vnd=Decimal('0'), credit_vnd=Decimal('1000'),
    )
    VoucherPostingService().post(v)

    response = auth_client.get('/modern/reports/trial-balance/?fiscal_year=2026&period=6')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert '111' in content  # TK 111
    assert '5111' in content  # TK 5111
    # Should have 1.000 in debit and credit totals
    assert '1.000' in content or '1000' in content


@pytest.mark.django_db
def test_trial_balance_totals_balanced(setup, auth_client):
    """Total debit must equal total credit."""
    company, _ = setup
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code='111',
        debit_vnd=Decimal('5000'), credit_vnd=Decimal('0'),
    )
    VoucherLine.objects.create(
        voucher=v, line_no=2, account_code='5111',
        debit_vnd=Decimal('0'), credit_vnd=Decimal('5000'),
    )
    VoucherPostingService().post(v)

    response = auth_client.get('/modern/reports/trial-balance/?fiscal_year=2026&period=6')
    assert response.context['total_period_debit'] == Decimal('5000')
    assert response.context['total_period_credit'] == Decimal('5000')
```

- [ ] **Step 2: Run to fail**

```bash
.venv/bin/pytest tests/test_trial_balance.py -v
```

- [ ] **Step 3: Create report view**

`apps/ui_modern/views/report_views.py`:
```python
"""Reporting views — trial balance, etc."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import render
from decimal import Decimal
from datetime import date

from apps.ledger.models import AccountPeriodBalance


class TrialBalanceView(LoginRequiredMixin, TemplateView):
    """Bảng cân đối tài khoản (S06-DN)."""
    template_name = 'modern/reporting/trial_balance.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        fiscal_year = int(self.request.GET.get('fiscal_year', today.year))
        period = int(self.request.GET.get('period', today.month))

        balances = AccountPeriodBalance.objects.filter(
            fiscal_year=fiscal_year, period=period,
        ).select_related('company').order_by('account_code')

        # Compute totals
        total_opening_d = Decimal('0')
        total_opening_c = Decimal('0')
        total_period_d = Decimal('0')
        total_period_c = Decimal('0')
        total_closing_d = Decimal('0')
        total_closing_c = Decimal('0')

        rows = []
        for b in balances:
            # Skip rows where everything is 0 (no activity)
            if (b.opening_debit or 0) == 0 and (b.opening_credit or 0) == 0 \
               and (b.period_debit or 0) == 0 and (b.period_credit or 0) == 0:
                continue

            rows.append(b)
            total_opening_d += b.opening_debit or 0
            total_opening_c += b.opening_credit or 0
            total_period_d += b.period_debit or 0
            total_period_c += b.period_credit or 0
            total_closing_d += b.closing_debit or 0
            total_closing_c += b.closing_credit or 0

        ctx.update({
            'page_title': 'Bảng cân đối tài khoản',
            'fiscal_year': fiscal_year,
            'period': period,
            'balances': rows,
            'total_opening_debit': total_opening_d,
            'total_opening_credit': total_opening_c,
            'total_period_debit': total_period_d,
            'total_period_credit': total_period_c,
            'total_closing_debit': total_closing_d,
            'total_closing_credit': total_closing_c,
            'is_balanced': total_closing_d == total_closing_c,
        })
        return ctx
```

- [ ] **Step 4: Update views/__init__.py**

Add `from .report_views import TrialBalanceView` and append to `__all__`.

- [ ] **Step 5: Update urls.py**

```python
from .views import (
    DashboardView, VoucherListView, VoucherCreateView, TrialBalanceView,
)

urlpatterns = [
    path('', login_required(DashboardView.as_view()), name='dashboard'),
    path('vouchers/', login_required(VoucherListView.as_view()), name='voucher_list'),
    path('vouchers/new/', login_required(VoucherCreateView.as_view()), name='voucher_create'),
    path('reports/trial-balance/', login_required(TrialBalanceView.as_view()), name='trial_balance'),
]
```

- [ ] **Step 6: Create template**

`templates/modern/reporting/trial_balance.html`:
```html
{% extends 'modern/base/layout.html' %}
{% load humanize %}

{% block content %}
<div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb mb-1">
                    <li class="breadcrumb-item"><a href="{% url 'ui_modern:dashboard' %}">Trang chủ</a></li>
                    <li class="breadcrumb-item">Báo cáo</li>
                    <li class="breadcrumb-item active">BCĐ tài khoản</li>
                </ol>
            </nav>
            <h1 class="h3 mb-0">{{ page_title }}</h1>
            <p class="text-muted mb-0">Kỳ: Tháng {{ period }} / {{ fiscal_year }}</p>
        </div>
        <form method="get" class="d-flex gap-2">
            <select name="fiscal_year" class="form-select form-select-sm">
                {% for y in '2024,2025,2026'|split:',' %}
                <option value="{{ y }}" {% if y|stringformat:"s" == fiscal_year|stringformat:"s" %}selected{% endif %}>{{ y }}</option>
                {% endfor %}
            </select>
            <select name="period" class="form-select form-select-sm">
                {% for p in '1,2,3,4,5,6,7,8,9,10,11,12'|split:',' %}
                <option value="{{ p }}" {% if p|stringformat:"s" == period|stringformat:"s" %}selected{% endif %}>Tháng {{ p }}</option>
                {% endfor %}
            </select>
            <button type="submit" class="btn btn-primary btn-sm">Xem</button>
        </form>
    </div>

    <div class="card">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-sm table-bordered mb-0 align-middle">
                    <thead class="table-light">
                        <tr>
                            <th rowspan="2">TK</th>
                            <th colspan="2" class="text-center">Số dư đầu</th>
                            <th colspan="2" class="text-center">Phát sinh trong kỳ</th>
                            <th colspan="2" class="text-center">Số dư cuối</th>
                        </tr>
                        <tr>
                            <th class="text-end">Nợ</th>
                            <th class="text-end">Có</th>
                            <th class="text-end">Nợ</th>
                            <th class="text-end">Có</th>
                            <th class="text-end">Nợ</th>
                            <th class="text-end">Có</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for b in balances %}
                        <tr>
                            <td class="font-mono">{{ b.account_code }}</td>
                            <td class="text-end font-mono">{{ b.opening_debit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ b.opening_credit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ b.period_debit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ b.period_credit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ b.closing_debit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ b.closing_credit|floatformat:0|intcomma }}</td>
                        </tr>
                        {% empty %}
                        <tr><td colspan="7" class="text-center text-muted py-4">
                            <i class="bi bi-inbox display-6 d-block mb-2"></i>
                            Không có dữ liệu cho kỳ này.
                        </td></tr>
                        {% endfor %}
                    </tbody>
                    {% if balances %}
                    <tfoot class="table-light fw-bold">
                        <tr>
                            <td>Tổng cộng</td>
                            <td class="text-end font-mono">{{ total_opening_debit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ total_opening_credit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ total_period_debit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ total_period_credit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ total_closing_debit|floatformat:0|intcomma }}</td>
                            <td class="text-end font-mono">{{ total_closing_credit|floatformat:0|intcomma }}</td>
                        </tr>
                    </tfoot>
                    {% endif %}
                </table>
            </div>
        </div>
        {% if balances %}
        <div class="card-footer d-flex justify-content-between align-items-center">
            <small class="text-muted">
                {% if is_balanced %}
                <span class="text-success"><i class="bi bi-check-circle"></i> Cân đối: Nợ = Có</span>
                {% else %}
                <span class="text-danger"><i class="bi bi-exclamation-triangle"></i> Mất cân đối!</span>
                {% endif %}
            </small>
            <button class="btn btn-outline-secondary btn-sm" onclick="window.print()">
                <i class="bi bi-printer"></i> In / PDF
            </button>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}
```

Note: Django doesn't have a built-in `split` filter. Need to add a custom template tag, or just pass period_choices and year_choices from view context. Simpler: in the view, add `period_choices = list(range(1, 13))` and `year_choices = [2024, 2025, 2026]` to context. Update template to iterate over those.

Update the view's `get_context_data` to add:
```python
ctx['period_choices'] = list(range(1, 13))
ctx['year_choices'] = [2024, 2025, 2026, 2027]
```

Update template to use:
```html
{% for y in year_choices %}
<option value="{{ y }}" {% if y == fiscal_year %}selected{% endif %}>{{ y }}</option>
{% endfor %}
...
{% for p in period_choices %}
<option value="{{ p }}" {% if p == period %}selected{% endif %}>Tháng {{ p }}</option>
{% endfor %}
```

- [ ] **Step 7: Run tests**

```bash
.venv/bin/pytest tests/test_trial_balance.py -v
.venv/bin/pytest -v
```

- [ ] **Step 8: Commit**

```bash
git add apps/ui_modern/ templates/modern/reporting/ tests/test_trial_balance.py
git commit -m "feat(ui_modern): trial balance view with balanced totals check

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 10: Update seed_demo + final verification

**Files:**
- Modify: `apps/core/management/commands/seed_demo.py` (load TT133 after creating company)
- Modify: `templates/modern/base/layout.html` (link voucher routes in sidebar)
- Run end-to-end verification

- [ ] **Step 1: Update seed_demo**

In `apps/core/management/commands/seed_demo.py`, after creating company, call load_tt133:

```python
# After company creation, load TT133 chart
from django.core.management import call_command
call_command('load_tt133', company_code=company.code)
self.stdout.write(f'Loaded TT133 chart for {company.code}')
```

- [ ] **Step 2: Update sidebar in layout.html**

Replace the placeholders `#` links with real URLs:

```html
<a href="{% url 'ui_modern:voucher_list' %}" class="nav-item">
    <i class="bi bi-receipt"></i> Phiếu kế toán
</a>
...
<a href="{% url 'ui_modern:trial_balance' %}" class="nav-item">
    <i class="bi bi-bar-chart"></i> BCĐ tài khoản
</a>
```

- [ ] **Step 3: Re-seed demo data**

```bash
.venv/bin/python manage.py seed_demo
```

- [ ] **Step 4: Run full test suite**

```bash
.venv/bin/pytest -v
.venv/bin/ruff check apps/
.venv/bin/python manage.py check
```

- [ ] **Step 5: Run server + manual verify**

```bash
.venv/bin/python manage.py runserver 8765 > /tmp/pmketoan.log 2>&1 &
SERVER_PID=$!
sleep 3

# Health check
curl -s http://localhost:8765/health/ | head -1
# Login as admin/admin123, then:
curl -s -c /tmp/cookies.txt -b /tmp/cookies.txt -X POST http://localhost:8765/auth/login/ \
  -d "username=admin&password=admin123" -L -o /tmp/login_resp.html
curl -s -b /tmp/cookies.txt http://localhost:8765/modern/vouchers/ -o /tmp/voucher_list.html
curl -s -b /tmp/cookies.txt http://localhost:8765/modern/vouchers/new/ -o /tmp/voucher_form.html
curl -s -b /tmp/cookies.txt http://localhost:8765/modern/reports/trial-balance/ -o /tmp/trial_balance.html

# Check sizes — should be non-zero
ls -la /tmp/*resp.html /tmp/voucher_*.html /tmp/trial_balance.html

kill $SERVER_PID
```

- [ ] **Step 6: Compare with SIS**

Open browser to verify:
- SIS: https://pkm.erpsme.vn/glctpk1/wg_ct_01 (Phiếu kế toán list)
- PMKetoan: http://localhost:8765/modern/vouchers/

Take screenshots for comparison.

- [ ] **Step 7: Commit**

```bash
git add apps/core/management/commands/seed_demo.py templates/modern/base/layout.html
git commit -m "feat: wire TT133 loader in seed + sidebar links to real routes

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git tag v0.2.0-phase1
```

---

## Phase 1 Acceptance Criteria

- [ ] All tests pass: `make test`
- [ ] Coverage ≥ 85% for `apps/master_data/`, `apps/ledger/`
- [ ] Lint clean: `make lint`
- [ ] Django check clean: `python manage.py check`
- [ ] TT133 chart loads (~100 accounts) for PKM company
- [ ] Voucher list renders with filter + pagination
- [ ] Voucher create form works: validates N=C, creates voucher, auto-posts
- [ ] Trial balance shows correct totals (N=C verified)
- [ ] Sidebar links work
- [ ] Verified against SIS at `/glctpk1/wg_ct_01` and `/dmtk/wg_dm_01`

---

**Plan complete.** 10 tasks. Estimated effort: ~1 week of focused work.

After Phase 1: Phase 2 (Treasury + Sales + Purchasing + Inventory) — core business modules.
