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
