"""Tests for m3-running-balance-db feature (VAL-M3-001 .. VAL-M3-007)."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="RBCO", name="Running Balance Co", fiscal_year_start_month=1)


def _make_voucher(
    company,
    voucher_no,
    debit_lines,
    credit_lines,
    voucher_date=date(2026, 6, 15),
    period=6,
    status=AccountingVoucher.Status.DRAFT,
):
    """Create a voucher with the given debit/credit lines.

    Each line is a tuple (account_code, amount).
    """
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=period,
        voucher_no=voucher_no,
        voucher_type="journal",
        voucher_date=voucher_date,
        status=status,
    )
    line_no = 1
    for acc, amt in debit_lines:
        VoucherLine.objects.create(
            voucher=v,
            line_no=line_no,
            account_code=acc,
            debit_vnd=Decimal(str(amt)),
            credit_vnd=Decimal("0"),
        )
        line_no += 1
    for acc, amt in credit_lines:
        VoucherLine.objects.create(
            voucher=v,
            line_no=line_no,
            account_code=acc,
            debit_vnd=Decimal("0"),
            credit_vnd=Decimal(str(amt)),
        )
        line_no += 1
    return v


# ---------------------------------------------------------------------------
# VAL-M3-001 — VoucherLine has running_balance_debit / running_balance_credit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_voucherline_has_running_balance_fields():
    """The model exposes the two running-balance DecimalFields."""
    field_debit = VoucherLine._meta.get_field("running_balance_debit")
    field_credit = VoucherLine._meta.get_field("running_balance_credit")
    assert field_debit is not None
    assert field_credit is not None
    assert field_debit.max_digits == 20
    assert field_debit.decimal_places == 4
    assert field_credit.max_digits == 20
    assert field_credit.decimal_places == 4


@pytest.mark.django_db
def test_running_balance_migration_applied():
    """The migration file exists (VAL-M3-001 evidence 3)."""
    import os

    mig_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "apps",
        "ledger",
        "migrations",
    )
    files = os.listdir(mig_dir)
    assert any("running_balance" in f for f in files), (
        "Expected a migration mentioning running_balance in ledger/migrations/"
    )


# ---------------------------------------------------------------------------
# VAL-M3-002 — Running balance computed on post
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_computes_running_balance_single_voucher(company):
    """Two lines on the same account_code accumulate a cumulative balance."""
    v = _make_voucher(
        company,
        "RB-001",
        debit_lines=[("1111", 1000), ("1111", 500)],
        credit_lines=[("5111", 1500)],
    )
    VoucherPostingService().post(v)

    lines = list(VoucherLine.objects.filter(account_code="1111").order_by("line_no"))
    assert len(lines) == 2
    assert lines[0].running_balance_debit == Decimal("1000")
    assert lines[1].running_balance_debit == Decimal("1500")
    # No credit side on these lines
    assert lines[0].running_balance_credit == Decimal("0")
    assert lines[1].running_balance_credit == Decimal("0")


@pytest.mark.django_db
def test_post_cumulative_across_vouchers_different_dates(company):
    """V2 posted on a later date than V1: V2's running balance includes V1."""
    v1 = _make_voucher(
        company,
        "RB-V1",
        debit_lines=[("1111", 700)],
        credit_lines=[("5111", 700)],
        voucher_date=date(2026, 6, 10),
    )
    v2 = _make_voucher(
        company,
        "RB-V2",
        debit_lines=[("1111", 300)],
        credit_lines=[("5111", 300)],
        voucher_date=date(2026, 6, 20),
    )
    VoucherPostingService().post(v1)
    VoucherPostingService().post(v2)

    v1_line = VoucherLine.objects.get(voucher=v1, account_code="1111")
    v2_line = VoucherLine.objects.get(voucher=v2, account_code="1111")
    assert v1_line.running_balance_debit == Decimal("700")
    assert v2_line.running_balance_debit == Decimal("1000")  # 700 + 300 cumulative


# ---------------------------------------------------------------------------
# VAL-M3-006 — Unposting recomputes running balances
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unpost_recomputes_remaining_balances(company):
    """Post A then B on same account; unpost A; B's balance now equals B alone."""
    a = _make_voucher(
        company,
        "RB-A",
        debit_lines=[("1111", 400)],
        credit_lines=[("5111", 400)],
        voucher_date=date(2026, 6, 5),
    )
    b = _make_voucher(
        company,
        "RB-B",
        debit_lines=[("1111", 600)],
        credit_lines=[("5111", 600)],
        voucher_date=date(2026, 6, 10),
    )
    service = VoucherPostingService()
    service.post(a)
    service.post(b)

    b_line = VoucherLine.objects.get(voucher=b, account_code="1111")
    assert b_line.running_balance_debit == Decimal("1000")

    service.unpost(a)

    b_line.refresh_from_db()
    a_line = VoucherLine.objects.get(voucher=a, account_code="1111")
    assert a_line.running_balance_debit == Decimal("0")
    assert a_line.running_balance_credit == Decimal("0")
    assert b_line.running_balance_debit == Decimal("600")


# ---------------------------------------------------------------------------
# VAL-M3-007 — Cumulative across multiple vouchers in same period
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cumulative_across_three_vouchers(company):
    """Post 3 vouchers on successive dates for account 1111."""
    v1 = _make_voucher(
        company,
        "RB-C1",
        debit_lines=[("1111", 100)],
        credit_lines=[("5111", 100)],
        voucher_date=date(2026, 6, 1),
    )
    v2 = _make_voucher(
        company,
        "RB-C2",
        debit_lines=[("1111", 200)],
        credit_lines=[("5111", 200)],
        voucher_date=date(2026, 6, 2),
    )
    v3 = _make_voucher(
        company,
        "RB-C3",
        debit_lines=[("1111", 300)],
        credit_lines=[("5111", 300)],
        voucher_date=date(2026, 6, 3),
    )
    service = VoucherPostingService()
    service.post(v1)
    service.post(v2)
    service.post(v3)

    l1 = VoucherLine.objects.get(voucher=v1, account_code="1111")
    l2 = VoucherLine.objects.get(voucher=v2, account_code="1111")
    l3 = VoucherLine.objects.get(voucher=v3, account_code="1111")
    assert l1.running_balance_debit == Decimal("100")
    assert l2.running_balance_debit == Decimal("300")
    assert l3.running_balance_debit == Decimal("600")


# ---------------------------------------------------------------------------
# VAL-M3-002 — Credit side running balance
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_running_balance_credit_side(company):
    """Credit postings accumulate running_balance_credit."""
    v1 = _make_voucher(
        company,
        "RB-CD1",
        debit_lines=[("5111", 400)],
        credit_lines=[("1111", 400)],
        voucher_date=date(2026, 6, 1),
    )
    v2 = _make_voucher(
        company,
        "RB-CD2",
        debit_lines=[("5111", 600)],
        credit_lines=[("1111", 600)],
        voucher_date=date(2026, 6, 2),
    )
    VoucherPostingService().post(v1)
    VoucherPostingService().post(v2)

    l1 = VoucherLine.objects.get(voucher=v1, account_code="1111")
    l2 = VoucherLine.objects.get(voucher=v2, account_code="1111")
    assert l1.running_balance_credit == Decimal("400")
    assert l2.running_balance_credit == Decimal("1000")


# ---------------------------------------------------------------------------
# VAL-M3-003 / VAL-M3-004 — CashBookView and BankBookView read from line
# ---------------------------------------------------------------------------


@pytest.fixture
def cash_book_setup(db):
    company = Company.objects.create(code="CBCO", name="CB Co")
    user = User.objects.create_superuser(
        username="cbadmin", password="Secret123", email="cb@test.local"
    )
    v = _make_voucher(
        company,
        "CB-001",
        debit_lines=[("111", 500000)],
        credit_lines=[("131", 500000)],
    )
    VoucherPostingService().post(v)
    return company, user, v


@pytest.fixture
def bank_book_setup(db):
    company = Company.objects.create(code="BBCO", name="BB Co")
    user = User.objects.create_superuser(
        username="bbadmin", password="Secret123", email="bb@test.local"
    )
    v = _make_voucher(
        company,
        "BB-001",
        debit_lines=[("331", 300000)],
        credit_lines=[("112", 300000)],
    )
    VoucherPostingService().post(v)
    return company, user, v


@pytest.mark.django_db
def test_cash_book_view_reads_running_balance_from_line(cash_book_setup):
    """S07 cash book reads running balance from VoucherLine, not view-computed."""
    _, user, v = cash_book_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    # The displayed "running" value equals the stored running balance
    line = VoucherLine.objects.get(voucher=v, account_code="111")
    expected_running = line.running_balance_debit - line.running_balance_credit
    assert r.context["rows"][0]["running"] == expected_running


@pytest.mark.django_db
def test_bank_book_view_reads_running_balance_from_line(bank_book_setup):
    """S08 bank book reads running balance from VoucherLine."""
    _, user, v = bank_book_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/bank-book/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    line = VoucherLine.objects.get(voucher=v, account_code="112")
    expected_running = line.running_balance_debit - line.running_balance_credit
    assert r.context["rows"][0]["running"] == expected_running


@pytest.mark.django_db
def test_cash_book_displays_so_to_column(cash_book_setup):
    """VAL-M3-005: cash book has a 'Số dư' / 'Số tồn' column header."""
    _, user, _ = cash_book_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6")
    body = r.content.decode()
    assert "Số dư" in body or "Số tồn" in body
