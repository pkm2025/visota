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
