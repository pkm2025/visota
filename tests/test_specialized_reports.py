"""Tests for specialized journals (S03a1/a2/a3/a4-DN) + T-account + sub-ledger books + cash flow."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, VoucherLine


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="SJ", name="SJ Test Co")
    user = User.objects.create_superuser(
        username="sjadmin", password="Secret123", email="sj@test.local"
    )
    # Cash receipt: debit 111 (cash inflow)
    v1 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="PT001",
        voucher_type="cash_receipt",
        voucher_date=date(2026, 6, 10),
        currency_code="VND",
        exchange_rate=Decimal("1"),
        total_vnd=Decimal("500000"),
        status=AccountingVoucher.Status.LEDGER,
        description="Thu tien KH",
    )
    VoucherLine.objects.create(
        voucher=v1, line_no=1, account_code="111", debit_vnd=Decimal("500000")
    )
    VoucherLine.objects.create(
        voucher=v1, line_no=2, account_code="131", credit_vnd=Decimal("500000")
    )

    # Cash payment: credit 112 (bank outflow)
    v2 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="PC001",
        voucher_type="cash_payment",
        voucher_date=date(2026, 6, 15),
        currency_code="VND",
        exchange_rate=Decimal("1"),
        total_vnd=Decimal("300000"),
        status=AccountingVoucher.Status.LEDGER,
        description="Chi tra NCC",
    )
    VoucherLine.objects.create(
        voucher=v2, line_no=1, account_code="331", debit_vnd=Decimal("300000")
    )
    VoucherLine.objects.create(
        voucher=v2, line_no=2, account_code="112", credit_vnd=Decimal("300000")
    )

    # Sales: credit 511 (revenue)
    v3 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="BH001",
        voucher_type="sales_invoice",
        voucher_date=date(2026, 6, 20),
        currency_code="VND",
        exchange_rate=Decimal("1"),
        total_vnd=Decimal("1000000"),
        status=AccountingVoucher.Status.LEDGER,
        description="Ban hang",
    )
    VoucherLine.objects.create(
        voucher=v3, line_no=1, account_code="131", debit_vnd=Decimal("1000000")
    )
    VoucherLine.objects.create(
        voucher=v3, line_no=2, account_code="511", credit_vnd=Decimal("1000000")
    )

    return company, user


# --- Specialized journals ---


@pytest.mark.django_db
def test_cash_receipt_journal_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/journal/cash-receipt/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert r.context["total_amount"] == Decimal("500000")
    assert "PT001" in r.content.decode()


@pytest.mark.django_db
def test_cash_payment_journal_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/journal/cash-payment/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert r.context["total_amount"] == Decimal("300000")
    assert "PC001" in r.content.decode()


@pytest.mark.django_db
def test_sales_journal_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/journal/sales/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert r.context["total_amount"] == Decimal("1000000")


@pytest.mark.django_db
def test_purchase_journal_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/journal/purchase/?fiscal_year=2026&period=6")
    assert r.status_code == 200


@pytest.mark.django_db
def test_t_account_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/t-account/?fiscal_year=2026&period=6&account_code=111")
    assert r.status_code == 200
    assert "111" in r.context["accounts"]


@pytest.mark.django_db
def test_specialized_journal_requires_login(db):
    c = Client()
    r = c.get("/modern/reports/journal/cash-receipt/")
    assert r.status_code == 302
    assert "/auth/login/" in r.url


# --- Sub-ledger books ---


@pytest.mark.django_db
def test_cash_book_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert r.context["total_debit"] == Decimal("500000")


@pytest.mark.django_db
def test_bank_book_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/bank-book/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert r.context["total_credit"] == Decimal("300000")


@pytest.mark.django_db
def test_sales_detail_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/sales-detail/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert r.context["total_revenue"] == Decimal("1000000")


# --- Cash flow statements ---


@pytest.mark.django_db
def test_cash_flow_direct_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/cash-flow/direct/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert r.context["method"] == "direct"


@pytest.mark.django_db
def test_cash_flow_indirect_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/cash-flow/indirect/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert r.context["method"] == "indirect"


# --- Tools ---


@pytest.mark.django_db
def test_period_allocation_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/tools/period-allocation/?fiscal_year=2026&period=6")
    assert r.status_code == 200


@pytest.mark.django_db
def test_closing_entry_declaration_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/tools/closing-entry-declaration/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert len(r.context["entries"]) == 8


@pytest.mark.django_db
def test_voucher_renumber_get_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/tools/voucher-renumber/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert len(r.context["rows"]) == 3


@pytest.mark.django_db
def test_year_end_carry_forward_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/tools/year-end-carry-forward/?fiscal_year=2026")
    assert r.status_code == 200


@pytest.mark.django_db
def test_opening_balances_load(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/tools/opening-balances/customers/?fiscal_year=2026")
    assert r.status_code == 200
    r2 = c.get("/modern/tools/opening-balances/invoices/?fiscal_year=2026")
    assert r2.status_code == 200


# --- CTGS workflow ---


@pytest.mark.django_db
def test_ctgs_create_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/ctgs/create/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert len(r.context["rows"]) == 3


@pytest.mark.django_db
def test_ctgs_register_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/ctgs/register/?fiscal_year=2026&period=6")
    assert r.status_code == 200


@pytest.mark.django_db
def test_ctgs_check_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/ctgs/check/?fiscal_year=2026&period=6")
    assert r.status_code == 200
    assert r.context["all_ok"] is True


@pytest.mark.django_db
def test_ctgs_schedule_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/ctgs/schedule/?fiscal_year=2026&period=6")
    assert r.status_code == 200


# --- Department master ---


@pytest.mark.django_db
def test_department_master_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/departments/?fiscal_year=2026&period=6")
    assert r.status_code == 200
