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
    """Voucher with status=LEDGER (already posted) must not be re-posted.

    With the idempotency guard, post() returns early if the voucher is already
    posted. No balance entries should be created since the voucher was never
    actually posted through the service (it was manually set to LEDGER).
    """
    v = _make_voucher(
        company,
        debit_lines=[('111', 1000)],
        credit_lines=[('5111', 1000)],
        status=AccountingVoucher.Status.LEDGER,  # already posted
    )
    service = VoucherPostingService()
    # Should not raise; should not create balances (idempotent early-return)
    service.post(v)
    # No balance created because post() returned early
    assert not AccountPeriodBalance.objects.filter(
        company=company, fiscal_year=2026, period=6, account_code='111',
    ).exists()


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


# ---------------------------------------------------------------------------
# Regression: post() idempotency (VAL-POST-001)
# ---------------------------------------------------------------------------


def test_post_twice_does_not_double_count_balances(company):
    """VAL-POST-001: Calling post() twice must NOT double-count balances."""
    v = _make_voucher(
        company,
        debit_lines=[('111', 1000)],
        credit_lines=[('5111', 1000)],
    )
    service = VoucherPostingService()

    # First post — creates balances
    service.post(v)
    bal_111 = AccountPeriodBalance.objects.get(
        company=company, fiscal_year=2026, period=6, account_code='111',
    )
    first_debit = bal_111.period_debit
    first_credit_5111 = AccountPeriodBalance.objects.get(
        company=company, fiscal_year=2026, period=6, account_code='5111',
    ).period_credit
    assert first_debit == Decimal('1000')

    # Second post — should be a no-op (idempotent)
    service.post(v)

    bal_111.refresh_from_db()
    assert bal_111.period_debit == first_debit  # unchanged
    assert bal_111.transaction_count == 1  # not 2

    bal_5111 = AccountPeriodBalance.objects.get(
        company=company, fiscal_year=2026, period=6, account_code='5111',
    )
    assert bal_5111.period_credit == first_credit_5111  # unchanged


def test_post_twice_preserves_closing_balances(company):
    """VAL-POST-001: Closing balances must remain unchanged after second post()."""
    v = _make_voucher(
        company,
        debit_lines=[('111', 2000)],
        credit_lines=[('5111', 2000)],
    )
    service = VoucherPostingService()
    service.post(v)

    closing_before = AccountPeriodBalance.objects.get(
        company=company, fiscal_year=2026, period=6, account_code='111',
    ).closing_debit

    service.post(v)  # second call

    closing_after = AccountPeriodBalance.objects.get(
        company=company, fiscal_year=2026, period=6, account_code='111',
    ).closing_debit
    assert closing_before == closing_after == Decimal('2000')


# ---------------------------------------------------------------------------
# Regression: period lock check (VAL-POST-001)
# ---------------------------------------------------------------------------


def test_post_to_closed_period_raises(company):
    """Posting to a closed period must raise PeriodClosedError."""
    from apps.ledger.services.voucher_posting_service import PeriodClosedError

    # Mark period as closed by creating a closing voucher
    AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no='KC-CLOSED',
        voucher_type='closing',
        voucher_date=date(2026, 6, 30),
        source='closing',
        status=AccountingVoucher.Status.LEDGER,
    )

    v = _make_voucher(
        company,
        debit_lines=[('111', 1000)],
        credit_lines=[('5111', 1000)],
    )
    service = VoucherPostingService()
    with pytest.raises(PeriodClosedError):
        service.post(v)
