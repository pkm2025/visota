# Phase 5: Financial Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Add the 3 core Vietnamese financial reports: Balance Sheet (B01a-DN), P&L (B02a-DN), VAT Return (01/GTGT). Each reads from `AccountPeriodBalance` (updated by all prior services) and renders formatted output.

**Architecture:** Report services live in `apps/reporting/services/`. They aggregate `AccountPeriodBalance` rows by account type → compute indicators → return structured data. Views render templates. No new models needed — reports are projections.

**Tech Stack:** Django 5.2, MariaDB 11.4, pytest.

---

## Task 1: Balance Sheet (B01a-DN) — service + view + template

**Files:**
- Create: `apps/reporting/__init__.py`, `apps/reporting/apps.py`
- Create: `apps/reporting/services/__init__.py`, `apps/reporting/services/balance_sheet.py`
- Create: `apps/ui_modern/views/report_views.py` (modify — add BalanceSheetView alongside TrialBalanceView)
- Create: `templates/modern/reporting/balance_sheet.html`
- Modify: `apps/ui_modern/urls.py`, `apps/ui_modern/views/__init__.py`
- Test: `tests/test_balance_sheet.py`

- [ ] **Step 1: Write tests**

`tests/test_balance_sheet.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from apps.ledger.models import AccountingVoucher, VoucherLine, AccountPeriodBalance
from apps.ledger.services import VoucherPostingService
from apps.core.models import Company


@pytest.fixture
def company_with_data(db):
    """Company with posted vouchers so balances exist."""
    company = Company.objects.create(code='TCO', name='Test')
    # Post a simple voucher: N111 1000 / C411 1000
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), status=0,
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='111', debit_vnd=Decimal('1000'))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='411', credit_vnd=Decimal('1000'))
    VoucherPostingService().post(v)
    return company


def test_balance_sheet_returns_dict(company_with_data):
    from apps.reporting.services import BalanceSheetService
    svc = BalanceSheetService(company=company_with_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert 'assets' in result
    assert 'liabilities_equity' in result
    assert isinstance(result['assets'], dict)


def test_balance_sheet_assets_include_111(company_with_data):
    from apps.reporting.services import BalanceSheetService
    svc = BalanceSheetService(company=company_with_data)
    result = svc.generate(fiscal_year=2026, period=6)
    # TK 111 (Tiền mặt) is asset type 1 → should be in assets
    assert result['assets']['total'] > 0
    # The amount should include 1000 from N111
    assert Decimal('1000') in [r['amount'] for r in result['assets']['rows']]


def test_balance_sheet_balanced(company_with_data):
    """Total assets must equal total liabilities + equity."""
    from apps.reporting.services import BalanceSheetService
    svc = BalanceSheetService(company=company_with_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['assets']['total'] == result['liabilities_equity']['total']


def test_balance_sheet_view_loads(db):
    from django.test import Client
    from apps.identity.models import User
    user = User.objects.create_user(username='alice', password='Secret123')
    client = Client()
    client.force_login(user)
    response = client.get('/modern/reports/balance-sheet/')
    assert response.status_code == 200
    assert 'Báo cáo tình hình tài chính' in response.content.decode('utf-8')
```

- [ ] **Step 2: Run to fail**

- [ ] **Step 3: Create apps/reporting/ structure**

`apps/reporting/apps.py`:
```python
from django.apps import AppConfig

class ReportingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reporting'
    verbose_name = 'Financial Reports'
```

`apps/reporting/services/balance_sheet.py`:
```python
"""Balance Sheet (B01a-DN) generator."""
from decimal import Decimal
from apps.ledger.models import AccountPeriodBalance
from apps.master_data.models import AccountType


class BalanceSheetService:
    """Generate Balance Sheet data from AccountPeriodBalance."""

    # Map account type category to balance sheet section
    ASSET_CATEGORIES = ['asset']
    LIABILITY_CATEGORIES = ['liability']
    EQUITY_CATEGORIES = ['equity']

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        balances = AccountPeriodBalance.objects.filter(
            company=self.company, fiscal_year=fiscal_year, period=period,
        ).select_related('company')

        # Aggregate by account category (join to ChartOfAccounts → AccountType)
        # Since we don't have FK from balance to account, we match by code prefix
        # Group by first digit of account_code
        asset_rows = []
        liability_rows = []
        equity_rows = []

        for b in balances:
            closing = max(b.closing_debit or 0, b.closing_credit or 0)
            if closing == 0:
                continue

            first_digit = b.account_code[0] if b.account_code else '0'
            row = {'account_code': b.account_code, 'amount': closing}

            if first_digit in ('1', '2'):
                # Types 1-2 = Assets
                asset_rows.append(row)
            elif first_digit == '3':
                liability_rows.append(row)
            elif first_digit == '4':
                equity_rows.append(row)

        total_assets = sum((r['amount'] for r in asset_rows), Decimal('0'))
        total_liabilities = sum((r['amount'] for r in liability_rows), Decimal('0'))
        total_equity = sum((r['amount'] for r in equity_rows), Decimal('0'))

        return {
            'fiscal_year': fiscal_year,
            'period': period,
            'assets': {
                'rows': asset_rows,
                'total': total_assets,
            },
            'liabilities_equity': {
                'liabilities': liability_rows,
                'equity': equity_rows,
                'total_liabilities': total_liabilities,
                'total_equity': total_equity,
                'total': total_liabilities + total_equity,
            },
            'is_balanced': total_assets == total_liabilities + total_equity,
        }
```

`apps/reporting/services/__init__.py`:
```python
from .balance_sheet import BalanceSheetService
__all__ = ['BalanceSheetService']
```

Add `'apps.reporting',` to INSTALLED_APPS.

- [ ] **Step 4: Add view**

Add to `apps/ui_modern/views/report_views.py`:

```python
class BalanceSheetView(LoginRequiredMixin, TemplateView):
    template_name = 'modern/reporting/balance_sheet.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from datetime import date
        today = date.today()
        fiscal_year = int(self.request.GET.get('fiscal_year', today.year))
        period = int(self.request.GET.get('period', today.month))

        from apps.reporting.services import BalanceSheetService
        from apps.core.models import Company
        company = Company.objects.first()
        if company:
            data = BalanceSheetService(company=company).generate(fiscal_year, period)
            ctx.update(data)
        ctx['page_title'] = 'Báo cáo tình hình tài chính (B01-DN)'
        ctx['fiscal_year'] = fiscal_year
        ctx['period'] = period
        ctx['year_choices'] = [2024, 2025, 2026, 2027]
        ctx['period_choices'] = list(range(1, 13))
        return ctx
```

- [ ] **Step 5: Add URL + template + tests + commit**

```python
# urls.py
path('reports/balance-sheet/', BalanceSheetView.as_view(), name='balance_sheet'),
```

Template: `templates/modern/reporting/balance_sheet.html` — two-column table (Assets | Liabilities + Equity) with totals and balanced check.

```bash
.venv/bin/pytest tests/test_balance_sheet.py -v
.venv/bin/pytest -v
git add apps/reporting/ apps/ui_modern/ templates/modern/reporting/balance_sheet.html config/settings/base.py tests/test_balance_sheet.py
git commit -m "feat(reporting): Balance Sheet (B01a-DN) with balanced check

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: P&L Statement (B02a-DN)

**Files:**
- Create: `apps/reporting/services/pnl.py`
- Modify: `apps/reporting/services/__init__.py`
- Modify: `apps/ui_modern/views/report_views.py` (add PnLView)
- Create: `templates/modern/reporting/pnl.html`
- Modify: `apps/ui_modern/urls.py`
- Test: `tests/test_pnl.py`

- [ ] **Step 1: Write tests**

`tests/test_pnl.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.core.models import Company


@pytest.fixture
def company_with_pnl_data(db):
    company = Company.objects.create(code='TCO', name='Test')
    # Revenue: C5111 5000, C33311 500 (VAT)
    # Expense: N632 3000 (COGS), N642 1000 (Admin)
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC01', voucher_type='sales_invoice',
        voucher_date=date(2026, 6, 15), status=0,
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='131', debit_vnd=Decimal('5500'))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='5111', credit_vnd=Decimal('5000'))
    VoucherLine.objects.create(voucher=v, line_no=3, account_code='33311', credit_vnd=Decimal('500'))
    VoucherPostingService().post(v)

    v2 = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC02', voucher_type='journal',
        voucher_date=date(2026, 6, 16), status=0,
    )
    VoucherLine.objects.create(voucher=v2, line_no=1, account_code='632', debit_vnd=Decimal('3000'))
    VoucherLine.objects.create(voucher=v2, line_no=2, account_code='642', debit_vnd=Decimal('1000'))
    VoucherLine.objects.create(voucher=v2, line_no=3, account_code='111', credit_vnd=Decimal('4000'))
    VoucherPostingService().post(v2)
    return company


def test_pnl_revenue(company_with_pnl_data):
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['revenue'] == Decimal('5000')


def test_pnl_cogs(company_with_pnl_data):
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['cogs'] == Decimal('3000')


def test_pnl_gross_profit(company_with_pnl_data):
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    # Revenue 5000 - COGS 3000 = 2000
    assert result['gross_profit'] == Decimal('2000')


def test_pnl_admin_expense(company_with_pnl_data):
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['admin_expense'] == Decimal('1000')


def test_pnl_net_profit(company_with_pnl_data):
    """Gross 2000 - Admin 1000 = 1000 operating profit."""
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['operating_profit'] == Decimal('1000')
```

- [ ] **Step 2: Run to fail**

- [ ] **Step 3: Create apps/reporting/services/pnl.py**

```python
"""P&L Statement (B02a-DN) generator."""
from decimal import Decimal
from apps.ledger.models import AccountPeriodBalance


class PnLService:
    """Generate P&L data from AccountPeriodBalance period movements."""

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        balances = AccountPeriodBalance.objects.filter(
            company=self.company, fiscal_year=fiscal_year, period=period,
        )

        revenue = Decimal('0')
        cogs = Decimal('0')
        selling_expense = Decimal('0')
        admin_expense = Decimal('0')
        financial_income = Decimal('0')
        financial_expense = Decimal('0')
        other_income = Decimal('0')
        other_expense = Decimal('0')
        pit_expense = Decimal('0')

        for b in balances:
            code = b.account_code
            period_d = b.period_debit or 0
            period_c = b.period_credit or 0

            # Revenue: 5xx → credit side
            if code.startswith('5'):
                revenue += period_c - period_d
            # COGS: 632
            elif code.startswith('632'):
                cogs += period_d - period_c
            # Selling: 641
            elif code.startswith('641'):
                selling_expense += period_d - period_c
            # Admin: 642
            elif code.startswith('642'):
                admin_expense += period_d - period_c
            # Financial income: 515
            elif code.startswith('515'):
                financial_income += period_c - period_d
            # Financial expense: 635
            elif code.startswith('635'):
                financial_expense += period_d - period_c
            # Other income: 711
            elif code.startswith('711'):
                other_income += period_c - period_d
            # Other expense: 811
            elif code.startswith('811'):
                other_expense += period_d - period_c
            # PIT: 821
            elif code.startswith('821'):
                pit_expense += period_d - period_c

        revenue_net = revenue
        gross_profit = revenue_net - cogs
        operating_profit = (
            gross_profit
            + financial_income - financial_expense
            - selling_expense - admin_expense
        )
        other_profit = other_income - other_expense
        profit_before_tax = operating_profit + other_profit
        profit_after_tax = profit_before_tax - pit_expense

        return {
            'fiscal_year': fiscal_year,
            'period': period,
            'revenue': revenue,
            'revenue_net': revenue_net,
            'cogs': cogs,
            'gross_profit': gross_profit,
            'selling_expense': selling_expense,
            'admin_expense': admin_expense,
            'financial_income': financial_income,
            'financial_expense': financial_expense,
            'operating_profit': operating_profit,
            'other_income': other_income,
            'other_expense': other_expense,
            'other_profit': other_profit,
            'profit_before_tax': profit_before_tax,
            'pit_expense': pit_expense,
            'profit_after_tax': profit_after_tax,
        }
```

- [ ] **Step 4: Update services/__init__.py, add view + template + URL + tests + commit**

```python
# apps/reporting/services/__init__.py
from .balance_sheet import BalanceSheetService
from .pnl import PnLService
__all__ = ['BalanceSheetService', 'PnLService']
```

Add `PnLView` to report_views.py, add URL `/reports/pnl/`, create template `templates/modern/reporting/pnl.html`.

```bash
.venv/bin/pytest tests/test_pnl.py -v
.venv/bin/pytest -v
git add apps/reporting/ apps/ui_modern/ templates/modern/reporting/pnl.html tests/test_pnl.py
git commit -m "feat(reporting): P&L Statement (B02a-DN) with gross/net profit calc

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: VAT Return (01/GTGT)

**Files:**
- Create: `apps/reporting/services/vat_return.py`
- Modify: `apps/reporting/services/__init__.py`
- Modify: `apps/ui_modern/views/report_views.py`
- Create: `templates/modern/reporting/vat_return.html`
- Modify: `apps/ui_modern/urls.py`
- Test: `tests/test_vat_return.py`

- [ ] **Step 1: Write tests**

`tests/test_vat_return.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from apps.sales.models import SalesInvoice
from apps.sales.services import SalesInvoiceService
from apps.purchasing.models import PurchaseInvoice
from apps.purchasing.services import PurchaseInvoiceService
from apps.master_data.models import Customer, Vendor, Product
from apps.core.models import Company


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    cust = Customer.objects.create(company=company, code='KH01', name='C')
    vend = Vendor.objects.create(company=company, code='NCC01', name='V')
    prod = Product.objects.create(
        company=company, code='SP01', name='P',
        product_type='goods', unit_id='CAI',
        gl_account_inv='156', gl_account_cogs='632', gl_account_revenue='5111',
    )
    return company, cust, vend, prod


def test_vat_return_output(setup):
    """Output VAT from sales invoices."""
    company, cust, vend, prod = setup
    SalesInvoiceService(company=company).create({
        'invoice_no': 'BC01', 'invoice_date': date(2026, 6, 10),
        'customer_id': cust.id,
        'lines': [{'product_id': prod.id, 'quantity': 10,
                   'unit_price': 100000, 'vat_rate': 0.10}],
        'post': True,
    })

    from apps.reporting.services import VATReturnService
    svc = VATReturnService(company=company)
    result = svc.generate(fiscal_year=2026, period=6)
    # Output: 1M revenue * 10% = 100k VAT
    assert result['vat_output'] == Decimal('100000')


def test_vat_return_input(setup):
    """Input VAT from purchase invoices."""
    company, cust, vend, prod = setup
    PurchaseInvoiceService(company=company).create({
        'invoice_no': 'PN01', 'invoice_date': date(2026, 6, 5),
        'vendor_id': vend.id,
        'lines': [{'product_id': prod.id, 'quantity': 5,
                   'unit_price': 100000, 'vat_rate': 0.10}],
        'post': True,
    })

    from apps.reporting.services import VATReturnService
    svc = VATReturnService(company=company)
    result = svc.generate(fiscal_year=2026, period=6)
    # Input: 500k * 10% = 50k VAT
    assert result['vat_input_credit'] == Decimal('50000')


def test_vat_return_payable(setup):
    """VAT payable = output - input."""
    company, cust, vend, prod = setup
    SalesInvoiceService(company=company).create({
        'invoice_no': 'BC01', 'invoice_date': date(2026, 6, 10),
        'customer_id': cust.id,
        'lines': [{'product_id': prod.id, 'quantity': 10,
                   'unit_price': 100000, 'vat_rate': 0.10}],
        'post': True,
    })
    PurchaseInvoiceService(company=company).create({
        'invoice_no': 'PN01', 'invoice_date': date(2026, 6, 5),
        'vendor_id': vend.id,
        'lines': [{'product_id': prod.id, 'quantity': 5,
                   'unit_price': 100000, 'vat_rate': 0.10}],
        'post': True,
    })

    from apps.reporting.services import VATReturnService
    svc = VATReturnService(company=company)
    result = svc.generate(fiscal_year=2026, period=6)
    # 100k output - 50k input = 50k payable
    assert result['vat_payable'] == Decimal('50000')


def test_vat_return_view_loads(db):
    from django.test import Client
    from apps.identity.models import User
    user = User.objects.create_user(username='alice', password='Secret123')
    c = Client()
    c.force_login(user)
    response = c.get('/modern/reports/vat-return/')
    assert response.status_code == 200
```

- [ ] **Step 2: Run to fail**

- [ ] **Step 3: Create apps/reporting/services/vat_return.py**

```python
"""VAT Return (01/GTGT) generator."""
from decimal import Decimal
from apps.ledger.models import AccountPeriodBalance


class VATReturnService:
    """Generate VAT return data from AccountPeriodBalance.

    Reads from the posted vouchers:
    - VAT output (TK 33311 credit) = total output VAT
    - VAT input (TK 1331 debit) = total input VAT credit
    """

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        balances = AccountPeriodBalance.objects.filter(
            company=self.company, fiscal_year=fiscal_year, period=period,
        )

        # VAT output: TK 33311 (credit side = output VAT)
        vat_output = Decimal('0')
        # VAT input: TK 1331 (debit side = input VAT)
        vat_input = Decimal('0')

        for b in balances:
            if b.account_code.startswith('33311'):
                vat_output += b.period_credit or 0
            elif b.account_code.startswith('1331'):
                vat_input += b.period_debit or 0

        vat_payable = vat_output - vat_input if vat_output > vat_input else Decimal('0')
        vat_credit = vat_input - vat_output if vat_input > vat_output else Decimal('0')

        return {
            'fiscal_year': fiscal_year,
            'period': period,
            'vat_output': vat_output,
            'vat_input_credit': vat_input,
            'vat_payable': vat_payable,
            'vat_credit': vat_credit,
            'is_payable': vat_output > vat_input,
        }
```

- [ ] **Step 4: Update __init__.py + add view + URL + template + tests + commit**

```python
# apps/reporting/services/__init__.py
from .balance_sheet import BalanceSheetService
from .pnl import PnLService
from .vat_return import VATReturnService
__all__ = ['BalanceSheetService', 'PnLService', 'VATReturnService']
```

Add `VATReturnView` to report_views.py, URL `/reports/vat-return/`, template `templates/modern/reporting/vat_return.html`.

```bash
.venv/bin/pytest tests/test_vat_return.py -v
.venv/bin/pytest -v
git add apps/reporting/ apps/ui_modern/ templates/modern/reporting/vat_return.html tests/test_vat_return.py
git commit -m "feat(reporting): VAT Return (01/GTGT) with payable/credit calc

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Update sidebar + final verify + tag

- [ ] **Step 1: Update sidebar**

In `templates/modern/base/layout.html`, replace the existing "Báo cáo" section:

```html
<div class="nav-section">
    <div class="nav-section-title">Báo cáo</div>
    <a href="{% url 'ui_modern:trial_balance' %}" class="nav-item">
        <i class="bi bi-bar-chart"></i> BCĐ tài khoản
    </a>
    <a href="{% url 'ui_modern:balance_sheet' %}" class="nav-item">
        <i class="bi bi-file-earmark-bar-graph"></i> BCTH tài chính (B01)
    </a>
    <a href="{% url 'ui_modern:pnl' %}" class="nav-item">
        <i class="bi bi-graph-up"></i> KQ HĐKD (B02)
    </a>
    <a href="{% url 'ui_modern:vat_return' %}" class="nav-item">
        <i class="bi bi-receipt"></i> Tờ khai GTGT (01)
    </a>
</div>
```

- [ ] **Step 2: Final test + lint + check + tag**

```bash
.venv/bin/pytest -v
.venv/bin/ruff check apps/ --fix && .venv/bin/ruff format apps/
.venv/bin/python manage.py check

git add -A
git commit -m "feat: sidebar report links (B01/B02/VAT) + reporting app

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git tag v0.6.0-phase5
```

---

## Phase 5 Acceptance Criteria

- [ ] All tests pass (target: 185+)
- [ ] Balance Sheet: A = L + E (balanced)
- [ ] P&L: Revenue - COGS = Gross; Gross - Expenses = Operating Profit
- [ ] VAT Return: Output - Input = Payable
- [ ] Sidebar links work
- [ ] Lint clean, Django check clean

---

**Plan complete.** 4 tasks.
