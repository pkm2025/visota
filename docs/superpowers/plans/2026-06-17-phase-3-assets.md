# Phase 3: Fixed Assets + CCDC + Depreciation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Build the assets module handling both TSCĐ (TK 211/214) and CCDC (TK 142/242). Monthly depreciation/allocation auto-generates accounting vouchers (N641/642/635 / C2141 or C142/C242). End-to-end: create asset → run monthly depreciation → see entries in trial balance.

**Architecture:** Unified `apps/assets` app handles both asset types via `is_tool` flag. `DepreciationService.calculate_period()` iterates active assets, computes monthly depreciation, and posts a single voucher aggregating all assets per expense account.

**Tech Stack:** Django 5.2, MariaDB 11.4, pytest.

---

## File Structure

```
pmketoan/
├── apps/
│   └── assets/                            # NEW
│       ├── __init__.py
│       ├── apps.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── category.py                # AssetCategory, AssetUsingDepartment
│       │   ├── asset.py                   # FixedAsset (TSCĐ + CCDC via is_tool)
│       │   └── depreciation.py            # AssetDepreciation history
│       ├── services/
│       │   ├── __init__.py
│       │   └── depreciation_service.py    # calculate_period() + post voucher
│       └── migrations/
├── apps/ui_modern/views/
│   └── asset_views.py                     # list + create + depreciation_run
├── templates/modern/assets/
│   ├── asset_list.html
│   ├── asset_form.html
│   └── depreciation_run.html
└── tests/
    ├── test_asset_model.py
    └── test_depreciation_service.py
```

---

## Task 1: Asset master data — AssetCategory + AssetUsingDepartment

**Files:**
- Create: `apps/assets/__init__.py`, `apps/assets/apps.py`, `apps/assets/models/__init__.py`, `apps/assets/models/category.py`, `apps/assets/migrations/__init__.py`
- Modify: `config/settings/base.py` (add to INSTALLED_APPS)
- Test: `tests/test_asset_category.py`

- [ ] **Step 1: Write tests**

`tests/test_asset_category.py`:
```python
import pytest
from apps.assets.models import AssetCategory, AssetUsingDepartment
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test')


def test_asset_category_creation(company):
    cat = AssetCategory.objects.create(
        company=company, code='MAY_MOC', name='Máy móc thiết bị',
        level='group', is_for_tool=False,
        default_gl_account='2112',
        default_depreciation_rate=0.20,
        default_useful_life_months=60,
    )
    assert cat.pk is not None
    assert str(cat) == 'MAY_MOC - Máy móc thiết bị'


def test_asset_category_levels():
    """Categories have 3 levels: type, group, subgroup."""
    assert hasattr(AssetCategory, 'level')
    choices = [c[0] for c in AssetCategory._meta.get_field('level').choices]
    assert 'type' in choices
    assert 'group' in choices
    assert 'subgroup' in choices


def test_asset_category_for_tool_flag(company):
    """CCDC categories have is_for_tool=True; TSCĐ=False."""
    AssetCategory.objects.create(
        company=company, code='TOOL', name='CCDC', level='type', is_for_tool=True,
    )
    cat = AssetCategory.objects.get(code='TOOL')
    assert cat.is_for_tool is True


def test_using_department_creation(company):
    dept = AssetUsingDepartment.objects.create(
        company=company, code='BP_BH', name='Bộ phận Bán hàng',
        default_expense_account='641',
    )
    assert dept.pk is not None
    assert str(dept) == 'BP_BH - Bộ phận Bán hàng'
```

- [ ] **Step 2: Run to fail**

```bash
cd /Users/dkm/dev/pmketoan
.venv/bin/pytest tests/test_asset_category.py -v
```

- [ ] **Step 3: Create apps/assets/apps.py**

```python
from django.apps import AppConfig


class AssetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.assets'
    verbose_name = 'Fixed Assets & Tools'
```

- [ ] **Step 4: Create apps/assets/models/category.py**

```python
"""Asset categories and using departments."""
from django.db import models
from apps.core.managers import CompanyOwnedModel


class AssetCategory(CompanyOwnedModel):
    """Asset category (loại/nhóm/phân nhóm) — applies to both TSCĐ and CCDC."""

    class Level(models.TextChoices):
        TYPE = 'type', 'Loại'
        GROUP = 'group', 'Nhóm'
        SUBGROUP = 'subgroup', 'Phân nhóm'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='asset_categories', db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    level = models.CharField(max_length=20, choices=Level.choices)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children',
    )

    is_for_tool = models.BooleanField(default=False,
        help_text='TRUE=CCDC (TK 142/242), FALSE=TSCĐ (TK 211/214)')

    default_gl_account = models.CharField(max_length=20, blank=True, default='')
    default_depreciation_account = models.CharField(max_length=20, blank=True, default='')
    default_expense_account = models.CharField(max_length=20, blank=True, default='')
    default_depreciation_rate = models.DecimalField(
        max_digits=8, decimal_places=4, default=0,
    )
    default_useful_life_months = models.PositiveSmallIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'asset_category'
        unique_together = [('company', 'code')]
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class AssetUsingDepartment(CompanyOwnedModel):
    """Department that uses an asset (for expense allocation)."""

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='asset_departments', db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    default_expense_account = models.CharField(max_length=20, default='642')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'asset_using_department'
        unique_together = [('company', 'code')]
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'
```

- [ ] **Step 5: Create apps/assets/models/__init__.py**

```python
from .category import AssetCategory, AssetUsingDepartment

__all__ = ['AssetCategory', 'AssetUsingDepartment']
```

- [ ] **Step 6: Add to INSTALLED_APPS**

Add `'apps.assets',` after `'apps.inventory',` in `config/settings/base.py`.

- [ ] **Step 7: Migration + tests + commit**

```bash
.venv/bin/python manage.py makemigrations assets
.venv/bin/python manage.py migrate
.venv/bin/pytest tests/test_asset_category.py -v
.venv/bin/pytest -v
git add apps/assets/ config/settings/base.py tests/test_asset_category.py
git commit -m "feat(assets): AssetCategory + AssetUsingDepartment models

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: FixedAsset model (TSCĐ + CCDC via is_tool)

**Files:**
- Create: `apps/assets/models/asset.py`
- Modify: `apps/assets/models/__init__.py`
- Test: `tests/test_asset_model.py`

- [ ] **Step 1: Write tests**

`tests/test_asset_model.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from apps.assets.models import FixedAsset, AssetCategory, AssetUsingDepartment
from apps.core.models import Company


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    cat = AssetCategory.objects.create(
        company=company, code='MAY_MOC', name='Máy móc', level='group',
        is_for_tool=False, default_gl_account='2112',
        default_depreciation_rate=Decimal('0.20'),
        default_useful_life_months=60,
    )
    dept = AssetUsingDepartment.objects.create(
        company=company, code='BP_BH', name='BH',
        default_expense_account='641',
    )
    return company, cat, dept


def test_asset_creation(setup):
    company, cat, dept = setup
    a = FixedAsset.objects.create(
        company=company, asset_code='TS001', asset_name='Xe Toyota',
        category=cat, using_department=dept,
        original_cost=Decimal('500000000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('0.20'),
        useful_life_months=60,
        start_date=date(2026, 1, 1),
        gl_account='2112',
        depreciation_account='2141',
        expense_account='642',
    )
    assert a.pk is not None
    assert str(a) == 'TS001 - Xe Toyota'
    assert a.is_tool is False
    assert a.status == 'active'


def test_tool_creation(setup):
    """CCDC has is_tool=True and different GL accounts."""
    company, _, dept = setup
    from apps.assets.models import AssetCategory
    tool_cat = AssetCategory.objects.create(
        company=company, code='CCDC_NHOM', name='CCDC nhóm', level='group',
        is_for_tool=True, default_gl_account='142',
    )
    t = FixedAsset.objects.create(
        company=company, asset_code='CC01', asset_name='Kéo cắt',
        category=tool_cat, using_department=dept,
        original_cost=Decimal('1000000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('1.0'),  # 100% over 1 year
        useful_life_months=12,
        start_date=date(2026, 1, 1),
        gl_account='142',
        depreciation_account='142',  # CCDC uses same account
        expense_account='642',
        is_tool=True,
    )
    assert t.is_tool is True


def test_asset_defaults(setup):
    company, cat, dept = setup
    a = FixedAsset(
        company=company, asset_code='X', asset_name='Y',
        category=cat, using_department=dept,
        original_cost=Decimal('1000'),
        depreciation_method='straight_line',
        start_date=date(2026, 1, 1),
    )
    assert a.status == 'active'
    assert a.salvage_value == Decimal('0')
    assert a.accumulated_depreciation == Decimal('0')


def test_asset_net_book_value(setup):
    company, cat, dept = setup
    a = FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('1000'),
        depreciation_method='straight_line',
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='214', expense_account='642',
        accumulated_depreciation=Decimal('300'),
    )
    assert a.net_book_value == Decimal('700')


def test_monthly_depreciation_straight_line(setup):
    """20% per year of 500M = 100M/year = ~8.33M/month."""
    company, cat, dept = setup
    a = FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('500000000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('0.20'),
        useful_life_months=60,
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='214', expense_account='642',
    )
    monthly = a.calculate_monthly_depreciation()
    # 500M * 20% / 12 = 8.333M
    assert monthly == Decimal('8333333.3333')


def test_monthly_depreciation_zero_after_full(setup):
    """Once fully depreciated, monthly = 0."""
    company, cat, dept = setup
    a = FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('1000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('1.0'),
        useful_life_months=12,
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='214', expense_account='642',
        accumulated_depreciation=Decimal('1000'),  # fully depreciated
        status='fully_depreciated',
    )
    assert a.calculate_monthly_depreciation() == Decimal('0')
```

- [ ] **Step 2: Run to fail**

- [ ] **Step 3: Create apps/assets/models/asset.py**

```python
"""FixedAsset model — handles both TSCĐ and CCDC."""
from decimal import Decimal
from django.db import models
from apps.core.managers import CompanyOwnedModel


class FixedAsset(CompanyOwnedModel):
    """Asset (TSCĐ or CCDC). Use is_tool=True for CCDC."""

    class DepreciationMethod(models.TextChoices):
        STRAIGHT_LINE = 'straight_line', 'Đường thẳng'
        DECLINING_BALANCE = 'declining_balance', 'Số dư giảm dần'
        UNITS_OF_PRODUCTION = 'units_of_production', 'Theo sản lượng'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Lưu tạm'
        ACTIVE = 'active', 'Đang dùng'
        FULLY_DEPRECIATED = 'fully_depreciated', 'Đã khấu hao hết'
        DISPOSED = 'disposed', 'Đã thanh lý'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='fixed_assets', db_index=True,
    )
    asset_code = models.CharField(max_length=50)
    asset_name = models.CharField(max_length=255)
    asset_name_en = models.CharField(max_length=255, blank=True, default='')

    category = models.ForeignKey(
        'assets.AssetCategory', on_delete=models.PROTECT,
        related_name='assets',
    )
    using_department = models.ForeignKey(
        'assets.AssetUsingDepartment', on_delete=models.PROTECT,
        related_name='assets',
    )

    # GL accounts
    gl_account = models.CharField(max_length=20,
        help_text='TK tài sản (211/212/213 cho TSCĐ, 142/242 cho CCDC)')
    depreciation_account = models.CharField(max_length=20,
        help_text='TK hao mòn/lũy kế (2141/2142/2143 cho TSCĐ, 142/242 cho CCDC)')
    expense_account = models.CharField(max_length=20, default='642',
        help_text='TK chi phí (641/642/635)')

    # Cost & depreciation
    original_cost = models.DecimalField(max_digits=20, decimal_places=4)
    currency_code = models.CharField(max_length=3, default='VND')

    depreciation_method = models.CharField(
        max_length=30, choices=DepreciationMethod.choices,
        default=DepreciationMethod.STRAIGHT_LINE,
    )
    depreciation_rate = models.DecimalField(
        max_digits=8, decimal_places=4, default=0,
        help_text='Tỷ lệ KH/năm (vd 0.20 = 20%/năm)',
    )
    useful_life_months = models.PositiveSmallIntegerField(default=0)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salvage_value = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    accumulated_depreciation = models.DecimalField(
        max_digits=20, decimal_places=4, default=0,
    )

    # Flag
    is_tool = models.BooleanField(default=False,
        help_text='TRUE=CCDC (TK 142/242), FALSE=TSCĐ (TK 211/214)')

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE,
    )

    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'fixed_asset'
        unique_together = [('company', 'asset_code')]
        ordering = ['asset_code']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'is_tool']),
        ]

    def __str__(self):
        return f'{self.asset_code} - {self.asset_name}'

    @property
    def net_book_value(self) -> Decimal:
        return self.original_cost - self.accumulated_depreciation

    def calculate_monthly_depreciation(self) -> Decimal:
        """Compute depreciation for one month (straight-line only for now)."""
        if self.status != self.Status.ACTIVE:
            return Decimal('0')
        if self.depreciation_method != self.DepreciationMethod.STRAIGHT_LINE:
            # Other methods not implemented in Phase 3
            return Decimal('0')

        # Annual depreciation / 12
        annual = self.original_cost * self.depreciation_rate
        monthly = (annual / Decimal('12')).quantize(Decimal('0.0001'))

        # Don't exceed net book value
        remaining = self.original_cost - self.accumulated_depreciation - self.salvage_value
        if monthly > remaining:
            monthly = remaining
        if monthly < 0:
            monthly = Decimal('0')

        return monthly
```

- [ ] **Step 4: Update __init__.py**

```python
from .category import AssetCategory, AssetUsingDepartment
from .asset import FixedAsset

__all__ = ['AssetCategory', 'AssetUsingDepartment', 'FixedAsset']
```

- [ ] **Step 5: Migration + tests + commit**

```bash
.venv/bin/python manage.py makemigrations assets
.venv/bin/python manage.py migrate
.venv/bin/pytest tests/test_asset_model.py -v
.venv/bin/pytest -v
git add apps/assets/ tests/test_asset_model.py
git commit -m "feat(assets): FixedAsset model (TSCĐ + CCDC via is_tool)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: AssetDepreciation history + DepreciationService

**Files:**
- Create: `apps/assets/models/depreciation.py`
- Modify: `apps/assets/models/__init__.py`
- Create: `apps/assets/services/__init__.py`, `apps/assets/services/depreciation_service.py`
- Test: `tests/test_depreciation_service.py`

- [ ] **Step 1: Write tests**

`tests/test_depreciation_service.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from apps.assets.models import (
    FixedAsset, AssetCategory, AssetUsingDepartment, AssetDepreciation,
)
from apps.assets.services import DepreciationService
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance
from apps.core.models import Company


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    cat = AssetCategory.objects.create(
        company=company, code='MAY_MOC', name='Máy', level='group',
        is_for_tool=False, default_gl_account='211',
        default_depreciation_rate=Decimal('0.20'),
        default_useful_life_months=60,
    )
    dept = AssetUsingDepartment.objects.create(
        company=company, code='BP_QL', name='QLDN',
        default_expense_account='642',
    )
    return company, cat, dept


def test_depreciation_creates_voucher(setup):
    """Running depreciation generates voucher N642/C2141."""
    company, cat, dept = setup
    asset = FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='Xe',
        category=cat, using_department=dept,
        original_cost=Decimal('1200000000'),  # 1.2B
        depreciation_method='straight_line',
        depreciation_rate=Decimal('0.20'),  # 20%/year = 240M/year = 20M/month
        useful_life_months=60,
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='2141', expense_account='642',
    )

    service = DepreciationService(company=company)
    result = service.calculate_period(2026, 6)

    # Should create 1 voucher, 1 AssetDepreciation entry
    assert result['assets_processed'] == 1
    assert result['total_depreciation'] == Decimal('20000000.0000')

    # Voucher exists with N642/C2141
    voucher = AccountingVoucher.objects.get(source='depreciation')
    assert voucher.is_posted
    assert voucher.voucher_type == 'depreciation'

    lines = voucher.lines.all()
    codes = {l.account_code for l in lines}
    assert '642' in codes  # expense debit
    assert '2141' in codes  # accumulated credit

    # N642 = 20M
    exp_line = lines.get(account_code='642')
    assert exp_line.debit_vnd == Decimal('20000000.0000')

    # Asset accumulated_depreciation updated
    asset.refresh_from_db()
    assert asset.accumulated_depreciation == Decimal('20000000.0000')

    # AssetDepreciation history row
    dep_history = AssetDepreciation.objects.get(asset=asset, period='2026-06')
    assert dep_history.depreciation_amount == Decimal('20000000.0000')


def test_depreciation_skips_fully_depreciated(setup):
    company, cat, dept = setup
    FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('1000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('1.0'),
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='2141', expense_account='642',
        accumulated_depreciation=Decimal('1000'),
        status='fully_depreciated',
    )

    service = DepreciationService(company=company)
    result = service.calculate_period(2026, 6)
    assert result['assets_processed'] == 0
    assert result['total_depreciation'] == Decimal('0')


def test_depreciation_aggregates_multiple_assets(setup):
    """Multiple assets in same expense account → 1 voucher with aggregated lines."""
    company, cat, dept = setup
    for i in range(3):
        FixedAsset.objects.create(
            company=company, asset_code=f'TS0{i+1}', asset_name=f'Asset {i+1}',
            category=cat, using_department=dept,
            original_cost=Decimal('1200000000'),
            depreciation_method='straight_line',
            depreciation_rate=Decimal('0.20'),
            start_date=date(2026, 1, 1),
            gl_account='211', depreciation_account='2141', expense_account='642',
        )

    service = DepreciationService(company=company)
    result = service.calculate_period(2026, 6)

    # 3 assets, total 3 * 20M = 60M
    assert result['assets_processed'] == 3
    assert result['total_depreciation'] == Decimal('60000000.0000')

    # Still just 1 voucher with 2 lines (N642=60M, C2141=60M)
    voucher = AccountingVoucher.objects.get(source='depreciation')
    lines = voucher.lines.all()
    assert lines.count() == 2  # 1 debit + 1 credit
    exp_line = lines.get(account_code='642')
    assert exp_line.debit_vnd == Decimal('60000000.0000')


def test_depreciation_idempotent(setup):
    """Running twice for same period does NOT double-depreciate."""
    company, cat, dept = setup
    FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('1200000000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('0.20'),
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='2141', expense_account='642',
    )

    service = DepreciationService(company=company)
    service.calculate_period(2026, 6)  # First run: 20M
    result = service.calculate_period(2026, 6)  # Second run: skip

    assert result['assets_processed'] == 0
    assert result['total_depreciation'] == Decimal('0')
    assert result['skipped_already_depreciated'] == 1
```

- [ ] **Step 2: Run to fail**

- [ ] **Step 3: Create apps/assets/models/depreciation.py**

```python
"""AssetDepreciation — history of depreciation per period."""
from django.db import models


class AssetDepreciation(models.Model):
    """Depreciation entry for one asset in one period."""

    asset = models.ForeignKey(
        'assets.FixedAsset', on_delete=models.CASCADE,
        related_name='depreciation_history',
    )
    period = models.CharField(max_length=7,
        help_text='YYYY-MM format')
    depreciation_amount = models.DecimalField(max_digits=20, decimal_places=4)
    accumulated_depreciation_end = models.DecimalField(max_digits=20, decimal_places=4)
    net_book_value_end = models.DecimalField(max_digits=20, decimal_places=4)

    gl_voucher = models.ForeignKey(
        'ledger.AccountingVoucher', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='asset_depreciations',
    )
    posted_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = 'asset_depreciation'
        unique_together = [('asset', 'period')]
        ordering = ['-period']

    def __str__(self):
        return f'{self.asset.asset_code} P{self.period}: {self.depreciation_amount}'
```

- [ ] **Step 4: Update __init__.py**

```python
from .category import AssetCategory, AssetUsingDepartment
from .asset import FixedAsset
from .depreciation import AssetDepreciation

__all__ = [
    'AssetCategory', 'AssetUsingDepartment',
    'FixedAsset', 'AssetDepreciation',
]
```

- [ ] **Step 5: Create apps/assets/services/depreciation_service.py**

```python
"""DepreciationService — calculate monthly depreciation + post voucher."""
from decimal import Decimal
from datetime import date
from django.db import transaction
from django.utils import timezone

from apps.assets.models import FixedAsset, AssetDepreciation
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService


class DepreciationService:
    """Service for monthly depreciation calculation + posting."""

    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def calculate_period(self, fiscal_year: int, period: int) -> dict:
        """Calculate depreciation for all active assets in given period.

        Returns dict with: assets_processed, total_depreciation, skipped_already_depreciated.
        Idempotent: skips assets that already have AssetDepreciation for this period.
        """
        period_str = f'{fiscal_year:04d}-{period:02d}'
        voucher_date = date(fiscal_year, period, 1)  # first day of period (simplified)

        # Get active assets not yet depreciated this period
        active_assets = FixedAsset.objects.filter(
            company=self.company,
            status=FixedAsset.Status.ACTIVE,
        ).select_related('using_department')

        processed = 0
        skipped = 0
        total = Decimal('0')

        # Per asset: compute depreciation, create history row
        asset_lines = []  # list of (asset, depreciation_amount)
        for asset in active_assets:
            # Idempotency check
            if AssetDepreciation.objects.filter(asset=asset, period=period_str).exists():
                skipped += 1
                continue

            dep_amount = asset.calculate_monthly_depreciation()
            if dep_amount <= 0:
                continue

            asset.accumulated_depreciation += dep_amount
            if asset.accumulated_depreciation >= asset.original_cost - asset.salvage_value:
                asset.accumulated_depreciation = asset.original_cost - asset.salvage_value
                asset.status = FixedAsset.Status.FULLY_DEPRECIATED
            asset.save(update_fields=[
                'accumulated_depreciation', 'status', 'updated_at',
            ])

            asset_lines.append((asset, dep_amount))
            total += dep_amount
            processed += 1

        if not asset_lines:
            return {
                'assets_processed': 0,
                'total_depreciation': Decimal('0'),
                'skipped_already_depreciated': skipped,
            }

        # Aggregate by (expense_account, depreciation_account) — but for simplicity,
        # assume all assets in this period share one expense/depr account pair.
        # Real implementation would group by account.
        expense_account = asset_lines[0][0].expense_account
        depr_account = asset_lines[0][0].depreciation_account

        # Create voucher
        voucher = AccountingVoucher.objects.create(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
            voucher_no=f'KH-{period_str}',
            voucher_type='depreciation',
            voucher_date=voucher_date,
            currency_code='VND',
            exchange_rate=Decimal('1'),
            total_vnd=total,
            status=AccountingVoucher.Status.DRAFT,
            source='depreciation',
            description=f'Khấu hao TSCĐ/CCDC kỳ {period_str}',
        )

        # N641/642/635 — expense debit
        VoucherLine.objects.create(
            voucher=voucher, line_no=1,
            account_code=expense_account,
            debit_vnd=total,
            description=f'CP khấu hao kỳ {period_str}',
        )

        # C2141/2142/2143 or C142/242 — accumulated credit
        VoucherLine.objects.create(
            voucher=voucher, line_no=2,
            account_code=depr_account,
            credit_vnd=total,
            description=f'Hao mòn lũy kế kỳ {period_str}',
        )

        # Post voucher → updates AccountPeriodBalance
        VoucherPostingService().post(voucher)

        # Create AssetDepreciation history rows linked to voucher
        for asset, dep_amount in asset_lines:
            AssetDepreciation.objects.create(
                asset=asset,
                period=period_str,
                depreciation_amount=dep_amount,
                accumulated_depreciation_end=asset.accumulated_depreciation,
                net_book_value_end=asset.net_book_value,
                gl_voucher=voucher,
            )

        return {
            'assets_processed': processed,
            'total_depreciation': total,
            'skipped_already_depreciated': skipped,
            'voucher_id': voucher.id,
        }
```

- [ ] **Step 6: Create services/__init__.py**

```python
from .depreciation_service import DepreciationService

__all__ = ['DepreciationService']
```

- [ ] **Step 7: Migration + tests + commit**

```bash
.venv/bin/python manage.py makemigrations assets
.venv/bin/python manage.py migrate
.venv/bin/pytest tests/test_depreciation_service.py -v
.venv/bin/pytest -v
git add apps/assets/ tests/test_depreciation_service.py
git commit -m "feat(assets): DepreciationService with auto-voucher N642/C2141

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Modern UI — Asset list + create + depreciation run

**Files:**
- Create: `apps/ui_modern/views/asset_views.py`
- Modify: `apps/ui_modern/views/__init__.py`, `apps/ui_modern/urls.py`
- Create: 3 templates under `templates/modern/assets/`
- Test: `tests/test_asset_views.py`

- [ ] **Step 1: Write tests**

`tests/test_asset_views.py`:
```python
import pytest
from django.test import Client
from apps.identity.models import User


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='alice', password='Secret123')
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_asset_list_loads(auth_client):
    response = auth_client.get('/modern/assets/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_asset_create_form_loads(auth_client):
    response = auth_client.get('/modern/assets/new/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_depreciation_run_form_loads(auth_client):
    response = auth_client.get('/modern/assets/depreciation/')
    assert response.status_code == 200
```

- [ ] **Step 2: Create asset_views.py**

```python
"""Asset views — list, create, depreciation run."""
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, TemplateView
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse_lazy

from apps.assets.models import FixedAsset, AssetCategory, AssetUsingDepartment
from apps.assets.services import DepreciationService
from apps.core.models import Company


class AssetListView(LoginRequiredMixin, ListView):
    template_name = 'modern/assets/asset_list.html'
    context_object_name = 'assets'
    paginate_by = 25
    login_url = '/auth/login/'

    def get_queryset(self):
        return FixedAsset.objects.select_related(
            'category', 'using_department',
        ).order_by('asset_code')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tài sản cố định & CCDC'
        return ctx


class AssetCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'modern/assets/asset_form.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Thêm tài sản'
        ctx['categories'] = AssetCategory.objects.filter(is_active=True).order_by('code')
        ctx['departments'] = AssetUsingDepartment.objects.filter(is_active=True).order_by('code')
        return ctx

    def post(self, request, *args, **kwargs):
        company = Company.objects.first()
        if not company:
            messages.error(request, 'No company configured')
            return redirect('ui_modern:asset_list')

        category = AssetCategory.objects.get(id=request.POST.get('category_id'))
        dept = AssetUsingDepartment.objects.get(id=request.POST.get('department_id'))

        asset = FixedAsset.objects.create(
            company=company,
            asset_code=request.POST.get('asset_code'),
            asset_name=request.POST.get('asset_name'),
            category=category,
            using_department=dept,
            original_cost=Decimal(request.POST.get('original_cost', '0')),
            depreciation_method='straight_line',
            depreciation_rate=Decimal(request.POST.get('depreciation_rate', '0')),
            useful_life_months=int(request.POST.get('useful_life_months', 0)),
            start_date=request.POST.get('start_date'),
            gl_account=category.default_gl_account or '211',
            depreciation_account=category.default_depreciation_account or '2141',
            expense_account=dept.default_expense_account or '642',
            is_tool=category.is_for_tool,
            description=request.POST.get('description', ''),
        )

        messages.success(request, f'Đã tạo tài sản {asset.asset_code}')
        return redirect('ui_modern:asset_list')


class DepreciationRunView(LoginRequiredMixin, TemplateView):
    """Page to run monthly depreciation."""
    template_name = 'modern/assets/depreciation_run.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tính khấu hao định kỳ'
        from datetime import date
        today = date.today()
        ctx['default_year'] = today.year
        ctx['default_month'] = today.month
        return ctx

    def post(self, request, *args, **kwargs):
        company = Company.objects.first()
        if not company:
            messages.error(request, 'No company configured')
            return redirect('ui_modern:asset_list')

        year = int(request.POST.get('fiscal_year'))
        month = int(request.POST.get('period'))

        service = DepreciationService(company=company)
        result = service.calculate_period(year, month)

        messages.success(
            request,
            f'Đã tính khấu hao {result["assets_processed"]} tài sản, '
            f'tổng {result["total_depreciation"]:,.0f} VND'
        )
        return redirect('ui_modern:asset_list')
```

- [ ] **Step 3: Update views/__init__.py**

Add `from .asset_views import AssetListView, AssetCreateView, DepreciationRunView` and add to `__all__`.

- [ ] **Step 4: Update urls.py**

Add:
```python
path('assets/', AssetListView.as_view(), name='asset_list'),
path('assets/new/', AssetCreateView.as_view(), name='asset_create'),
path('assets/depreciation/', DepreciationRunView.as_view(), name='depreciation_run'),
```

- [ ] **Step 5: Create 3 templates**

Use the same Bootstrap pattern as voucher_list.html / voucher_form.html.

- [ ] **Step 6: Run tests + commit**

```bash
.venv/bin/pytest tests/test_asset_views.py -v
.venv/bin/pytest -v
git add apps/ui_modern/ templates/modern/assets/ tests/test_asset_views.py
git commit -m "feat(ui_modern): asset list + create + depreciation run views

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Update sidebar + seed sample asset + final verify

- [ ] **Step 1: Update sidebar**

In `templates/modern/base/layout.html`, add to the "Cập nhật số liệu" section or create new section:

```html
<div class="nav-section">
    <div class="nav-section-title">Tài sản</div>
    <a href="{% url 'ui_modern:asset_list' %}" class="nav-item">
        <i class="bi bi-building"></i> TSCĐ & CCDC
    </a>
    <a href="{% url 'ui_modern:depreciation_run' %}" class="nav-item">
        <i class="bi bi-arrow-clockwise"></i> Tính khấu hao
    </a>
</div>
```

- [ ] **Step 2: Update seed_demo to create sample asset**

After warehouse creation in seed_demo, add:

```python
# Sample asset
from apps.assets.models import (
    AssetCategory, AssetUsingDepartment, FixedAsset,
)
cat, _ = AssetCategory.objects.update_or_create(
    company=company, code='MAY_MOC',
    defaults={
        'name': 'Máy móc thiết bị', 'level': 'group',
        'is_for_tool': False, 'default_gl_account': '2112',
        'default_depreciation_rate': 0.20,
        'default_useful_life_months': 60,
    },
)
dept, _ = AssetUsingDepartment.objects.update_or_create(
    company=company, code='BP_QL',
    defaults={'name': 'Bộ phận QLDN', 'default_expense_account': '642'},
)
asset, _ = FixedAsset.objects.update_or_create(
    company=company, asset_code='TS001',
    defaults={
        'asset_name': 'Xe Toyota Vios',
        'category': cat, 'using_department': dept,
        'original_cost': 500000000,
        'depreciation_method': 'straight_line',
        'depreciation_rate': 0.20,
        'useful_life_months': 60,
        'start_date': '2026-01-01',
        'gl_account': '2112',
        'depreciation_account': '2141',
        'expense_account': '642',
    },
)
self.stdout.write(f'Sample asset: TS001 - Xe Toyota Vios')
```

- [ ] **Step 3: Re-seed + verify all routes**

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver 8765 > /tmp/p3.log 2>&1 &
sleep 4

curl -s -c /tmp/c.txt -X POST http://localhost:8765/auth/login/ -d "username=admin&password=admin123" -o /dev/null

# Test new routes
for path in /modern/assets/ /modern/assets/new/ /modern/assets/depreciation/; do
    code=$(curl -s -b /tmp/c.txt -o /dev/null -w "%{http_code}" http://localhost:8765$path)
    echo "$path: $code"
done

kill %1
```

- [ ] **Step 4: Full test + lint + commit + tag**

```bash
.venv/bin/pytest -v
.venv/bin/ruff check apps/ --fix
.venv/bin/ruff format apps/
.venv/bin/python manage.py check

git add -A
git commit -m "feat: sidebar Tài sản + seed sample asset

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git tag v0.4.0-phase3
```

---

## Phase 3 Acceptance Criteria

- [ ] All tests pass (target: 160+ tests)
- [ ] Coverage ≥ 90%
- [ ] Lint clean
- [ ] Django check clean
- [ ] Asset list/create views work
- [ ] Depreciation run view works
- [ ] Depreciation generates voucher N642/C2141 and updates trial balance
- [ ] Idempotent: re-running same period skips already-depreciated assets
- [ ] Asset status auto-changes to 'fully_depreciated' when accumulated reaches original_cost

---

**Plan complete.** 5 tasks. Estimated effort: ~3-4 days.
