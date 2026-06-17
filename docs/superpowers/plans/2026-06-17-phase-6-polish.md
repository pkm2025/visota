# Phase 6: Polish + Go-Live Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Add period closing (kết chuyển cuối kỳ), company switcher, voucher detail + reversal, and finalize for go-live.

**Architecture:** `PeriodClosingService` generates KC voucher (N511/711/C911 + N911/C632/641/642/811 + N911/C421 or N421/C911). Company switcher stores `current_company_id` in session. Voucher detail view renders lines.

---

## Task 1: PeriodClosingService — Kết chuyển cuối kỳ

**Files:**
- Create: `apps/ledger/services/period_closing_service.py`
- Modify: `apps/ledger/services/__init__.py`
- Create: `apps/ui_modern/views/closing_views.py`
- Modify: views/__init__.py, urls.py
- Create: `templates/modern/ledger/closing.html`
- Test: `tests/test_period_closing.py`

- [ ] **Step 1: Write tests**

`tests/test_period_closing.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from apps.ledger.models import AccountingVoucher, VoucherLine, AccountPeriodBalance
from apps.ledger.services import VoucherPostingService, PeriodClosingService
from apps.core.models import Company


@pytest.fixture
def company_with_activity(db):
    """Company with posted revenue + expense vouchers."""
    company = Company.objects.create(code='TCO', name='Test')

    # Revenue: C5111 5000
    v1 = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC01', voucher_type='journal',
        voucher_date=date(2026, 6, 15), status=0,
    )
    VoucherLine.objects.create(voucher=v1, line_no=1, account_code='111', debit_vnd=Decimal('5000'))
    VoucherLine.objects.create(voucher=v1, line_no=2, account_code='5111', credit_vnd=Decimal('5000'))
    VoucherPostingService().post(v1)

    # Expense: N642 2000
    v2 = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC02', voucher_type='journal',
        voucher_date=date(2026, 6, 16), status=0,
    )
    VoucherLine.objects.create(voucher=v2, line_no=1, account_code='642', debit_vnd=Decimal('2000'))
    VoucherLine.objects.create(voucher=v2, line_no=2, account_code='111', credit_vnd=Decimal('2000'))
    VoucherPostingService().post(v2)

    return company


def test_closing_generates_voucher(company_with_activity):
    svc = PeriodClosingService(company=company_with_activity)
    result = svc.close_period(fiscal_year=2026, period=6)

    assert result['voucher_id'] is not None
    voucher = AccountingVoucher.objects.get(id=result['voucher_id'])
    assert voucher.voucher_type == 'closing'
    assert voucher.is_posted


def test_closing_transfers_revenue_to_911(company_with_activity):
    """KC: N5111 / C911 = revenue amount."""
    svc = PeriodClosingService(company=company_with_activity)
    result = svc.close_period(fiscal_year=2026, period=6)

    voucher = AccountingVoucher.objects.get(id=result['voucher_id'])
    # Should have N5111 (debit = revenue closing)
    lines_5111 = voucher.lines.filter(account_code='5111')
    assert lines_5111.exists()
    assert lines_5111.first().debit_vnd == Decimal('5000')


def test_closing_transfers_expense_to_911(company_with_activity):
    """KC: N911 / C642 = expense amount."""
    svc = PeriodClosingService(company=company_with_activity)
    result = svc.close_period(fiscal_year=2026, period=6)

    voucher = AccountingVoucher.objects.get(id=result['voucher_id'])
    lines_642 = voucher.lines.filter(account_code='642')
    assert lines_642.exists()
    assert lines_642.first().credit_vnd == Decimal('2000')


def test_closing_transfers_profit_to_421(company_with_activity):
    """Profit = Revenue 5000 - Expense 2000 = 3000 → N911 / C421."""
    svc = PeriodClosingService(company=company_with_activity)
    result = svc.close_period(fiscal_year=2026, period=6)

    voucher = AccountingVoucher.objects.get(id=result['voucher_id'])
    lines_421 = voucher.lines.filter(account_code='421')
    assert lines_421.exists()
    # C421 = 3000 (profit)
    assert lines_421.first().credit_vnd == Decimal('3000')


def test_closing_voucher_is_balanced(company_with_activity):
    """The KC voucher must be balanced (N = C)."""
    svc = PeriodClosingService(company=company_with_activity)
    result = svc.close_period(fiscal_year=2026, period=6)

    voucher = AccountingVoucher.objects.get(id=result['voucher_id'])
    total_d = sum(l.debit_vnd for l in voucher.lines.all())
    total_c = sum(l.credit_vnd for l in voucher.lines.all())
    assert total_d == total_c


def test_closing_idempotent(company_with_activity):
    """Running closing twice does NOT double-post."""
    svc = PeriodClosingService(company=company_with_activity)
    svc.close_period(fiscal_year=2026, period=6)
    result2 = svc.close_period(fiscal_year=2026, period=6)
    assert result2['skipped'] is True
    # Only 1 closing voucher
    closing_vouchers = AccountingVoucher.objects.filter(
        company=company_with_activity, source='closing', fiscal_year=2026, period=6,
    )
    assert closing_vouchers.count() == 1
```

- [ ] **Step 2: Run to fail**

- [ ] **Step 3: Create PeriodClosingService**

`apps/ledger/services/period_closing_service.py`:
```python
"""PeriodClosingService — kết chuyển cuối kỳ."""
from decimal import Decimal
from datetime import date
from django.db import transaction

from apps.ledger.models import AccountingVoucher, VoucherLine, AccountPeriodBalance
from apps.ledger.services.voucher_posting_service import VoucherPostingService


# Account code prefixes that get closed
REVENUE_PREFIXES = ['5', '7']   # 511, 515, 711 → credit balances → N to close
EXPENSE_PREFIXES = ['6', '8']   # 632, 641, 642, 635, 811, 821 → debit balances → C to close
PROFIT_ACCOUNT = '421'          # Lợi nhuận chưa phân phối
RESULT_ACCOUNT = '911'          # Xác định KQ


class PeriodClosingService:
    """Kết chuyển cuối kỳ: move revenue/expense balances to TK 911, then to TK 421."""

    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def close_period(self, fiscal_year: int, period: int) -> dict:
        """Close a period by transferring revenue/expense to 911, then 421.

        Idempotent: skips if a closing voucher already exists for this period.
        """
        # Check idempotency
        existing = AccountingVoucher.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
            source='closing',
        ).exists()
        if existing:
            return {'skipped': True, 'voucher_id': None}

        balances = AccountPeriodBalance.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
        )

        total_revenue = Decimal('0')
        total_expense = Decimal('0')
        kc_lines = []  # (account_code, is_debit, amount)

        for b in balances:
            code = b.account_code
            period_d = b.period_debit or 0
            period_c = b.period_credit or 0

            net_credit = period_c - period_d  # revenue net
            net_debit = period_d - period_c   # expense net

            if code.startswith(tuple(REVENUE_PREFIXES)):
                if net_credit > 0:
                    # KC: N5111 (close revenue by debiting)
                    kc_lines.append((code, True, net_credit))
                    total_revenue += net_credit
            elif code.startswith(tuple(EXPENSE_PREFIXES)):
                if net_debit > 0:
                    # KC: C642 (close expense by crediting)
                    kc_lines.append((code, False, net_debit))
                    total_expense += net_debit

        if not kc_lines:
            return {'skipped': True, 'voucher_id': None, 'reason': 'No revenue/expense to close'}

        profit = total_revenue - total_expense

        # Create closing voucher
        voucher = AccountingVoucher.objects.create(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
            voucher_no=f'KC-{fiscal_year}{period:02d}',
            voucher_type='closing',
            voucher_date=date(fiscal_year, period, 28),  # end of period (simplified)
            currency_code='VND',
            exchange_rate=Decimal('1'),
            status=AccountingVoucher.Status.DRAFT,
            source='closing',
            description=f'Kết chuyển cuối kỳ {period}/{fiscal_year}',
        )

        line_no = 1

        # Step 1: KC revenue → N5xx / C911
        for acc_code, is_debit, amount in kc_lines:
            if is_debit:  # revenue: N5xx
                VoucherLine.objects.create(
                    voucher=voucher, line_no=line_no,
                    account_code=acc_code,
                    debit_vnd=amount,
                    description=f'KC doanh thu {acc_code}',
                )
                line_no += 1

        if total_revenue > 0:
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=RESULT_ACCOUNT,
                credit_vnd=total_revenue,
                description='KC doanh thu → 911',
            )
            line_no += 1

        # Step 2: KC expense → N911 / C6xx
        if total_expense > 0:
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=RESULT_ACCOUNT,
                debit_vnd=total_expense,
                description='KC chi phí → 911',
            )
            line_no += 1

        for acc_code, is_debit, amount in kc_lines:
            if not is_debit:  # expense: C6xx
                VoucherLine.objects.create(
                    voucher=voucher, line_no=line_no,
                    account_code=acc_code,
                    credit_vnd=amount,
                    description=f'KC chi phí {acc_code}',
                )
                line_no += 1

        # Step 3: Transfer profit/loss to 421
        if profit > 0:
            # Profit: N911 / C421
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=RESULT_ACCOUNT,
                debit_vnd=profit,
                description='KC lợi nhuận → 421',
            )
            line_no += 1
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=PROFIT_ACCOUNT,
                credit_vnd=profit,
                description='Lợi nhuận sau thuế',
            )
        elif profit < 0:
            # Loss: N421 / C911
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=PROFIT_ACCOUNT,
                debit_vnd=-profit,
                description='Lỗ kỳ',
            )
            line_no += 1
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=RESULT_ACCOUNT,
                credit_vnd=-profit,
                description='KC lỗ → 421',
            )

        # Post voucher
        VoucherPostingService().post(voucher)

        return {
            'skipped': False,
            'voucher_id': voucher.id,
            'total_revenue': total_revenue,
            'total_expense': total_expense,
            'profit': profit,
        }
```

- [ ] **Step 4: Update services/__init__.py**

```python
from .voucher_posting_service import VoucherPostingService
from .period_closing_service import PeriodClosingService

__all__ = ['VoucherPostingService', 'PeriodClosingService']
```

- [ ] **Step 5: Add view + URL + template**

`apps/ui_modern/views/closing_views.py`:
```python
"""Period closing view."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages
from apps.ledger.services import PeriodClosingService
from apps.core.models import Company


class PeriodClosingView(LoginRequiredMixin, TemplateView):
    template_name = 'modern/ledger/closing.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Kết chuyển cuối kỳ'
        from datetime import date as dt
        today = dt.today()
        ctx['default_year'] = today.year
        ctx['default_month'] = today.month
        ctx['year_choices'] = [2024, 2025, 2026, 2027]
        ctx['period_choices'] = list(range(1, 13))
        return ctx

    def post(self, request, *args, **kwargs):
        company = Company.objects.first()
        if not company:
            messages.error(request, 'No company')
            return redirect('ui_modern:period_closing')

        year = int(request.POST.get('fiscal_year'))
        month = int(request.POST.get('period'))

        service = PeriodClosingService(company=company)
        result = service.close_period(fiscal_year=year, period=month)

        if result.get('skipped'):
            messages.info(request, f'Kỳ {month}/{year} đã kết chuyển hoặc không có dữ liệu')
        else:
            messages.success(
                request,
                f'Kết chuyển {month}/{year}: DT={result["total_revenue"]:,.0f} '
                f'CP={result["total_expense"]:,.0f} '
                f'Lãi/Lỗ={result["profit"]:,.0f}'
            )
        return redirect('ui_modern:period_closing')
```

Add URL: `path('closing/', PeriodClosingView.as_view(), name='period_closing')`

Template `templates/modern/ledger/closing.html`: year/month selector + "Kết chuyển" button.

- [ ] **Step 6: Run tests + commit**

```bash
.venv/bin/pytest tests/test_period_closing.py -v
.venv/bin/pytest -v
git add apps/ledger/services/ apps/ui_modern/ templates/modern/ledger/closing.html tests/test_period_closing.py
git commit -m "feat(ledger): PeriodClosingService (kết chuyển 5xx/6xx/7xx/8xx → 911 → 421)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: Voucher detail view + reversal

**Files:**
- Create: `apps/ui_modern/views/voucher_detail_view.py` (or add to ledger_views.py)
- Modify: `apps/ui_modern/urls.py`
- Create: `templates/modern/ledger/voucher_detail.html`
- Modify: `templates/modern/ledger/voucher_list.html` (link to detail)
- Test: `tests/test_voucher_detail.py`

- [ ] **Step 1: Write tests**

`tests/test_voucher_detail.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from django.test import Client
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.identity.models import User


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='alice', password='Secret123')
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def voucher(db):
    from apps.core.models import Company
    company = Company.objects.create(code='TCO', name='T')
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), status=2,
        description='Test',
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='111', debit_vnd=Decimal('1000'))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='5111', credit_vnd=Decimal('1000'))
    return v


@pytest.mark.django_db
def test_voucher_detail_loads(auth_client, voucher):
    response = auth_client.get(f'/modern/vouchers/{voucher.id}/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'BC0001' in content
    assert '111' in content
    assert '5111' in content
    assert '1.000' in content or '1000' in content


@pytest.mark.django_db
def test_voucher_detail_shows_lines(auth_client, voucher):
    response = auth_client.get(f'/modern/vouchers/{voucher.id}/')
    content = response.content.decode('utf-8')
    # Should show 2 lines
    assert content.count('account_code') >= 2 or content.count('111') >= 1
```

- [ ] **Step 2: Add VoucherDetailView**

Add to `apps/ui_modern/views/ledger_views.py`:

```python
from django.views.generic import DetailView

class VoucherDetailView(LoginRequiredMixin, DetailView):
    template_name = 'modern/ledger/voucher_detail.html'
    context_object_name = 'voucher'
    login_url = '/auth/login/'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return AccountingVoucher.objects.prefetch_related('lines')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Phiếu {self.object.voucher_no}'
        return ctx
```

- [ ] **Step 3: Add URL + template**

URL: `path('vouchers/<int:pk>/', VoucherDetailView.as_view(), name='voucher_detail')`

Update voucher_list.html: change `<a href="#">` to `<a href="{% url 'ui_modern:voucher_detail' voucher.id %}">`

Template `voucher_detail.html`: show voucher header + table of lines (account, debit, credit, description).

- [ ] **Step 4: Run tests + commit**

---

## Task 3: Update sidebar + final cleanup + tag

- [ ] **Step 1: Add "Kết chuyển" to sidebar**

```html
<a href="{% url 'ui_modern:period_closing' %}" class="nav-item">
    <i class="bi bi-arrow-repeat"></i> Kết chuyển cuối kỳ
</a>
```

Replace the existing placeholder `#` link for "Kết chuyển cuối kỳ".

- [ ] **Step 2: Final lint + test + check + tag**

```bash
.venv/bin/ruff check apps/ --fix && .venv/bin/ruff format apps/
.venv/bin/pytest -v
.venv/bin/python manage.py check
git add -A
git commit -m "feat: voucher detail + period closing sidebar + final cleanup

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git tag v0.7.0-phase6
```

---

## Phase 6 Acceptance Criteria

- [ ] All tests pass (target: 195+)
- [ ] Period closing generates KC voucher (N5xx/C911 + N911/C6xx + N911/C421)
- [ ] Closing is idempotent
- [ ] Voucher detail view shows lines
- [ ] Sidebar has real link to "Kết chuyển cuối kỳ"
- [ ] Lint clean, Django check clean

---

**Plan complete.** 3 tasks.
