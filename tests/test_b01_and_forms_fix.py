"""Tests for bug #8 fix (empty FX/banking/bidding forms) and bug #10 fix (B01).

#8: The /fx/rates/new/ form's "Ngoại tệ" dropdown was empty because the
    Currency table had no rows. seed_currencies provides the missing data.
    The banking and bidding forms already had all their input fields.

#10: B01 BCTC used gross period-debit instead of net closing balance for
    accounts split across multiple object_code rows (e.g. TK 131 with
    separate invoice + payment rows). The fix nets debit vs credit
    across rows for the same account pattern.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.core.models import Company
from apps.fx.models import Currency
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.reporting.services.formula_parser import ReportEngine

# ---------------------------------------------------------------------------
# Bug #8: seed_currencies populates the FX rate form dropdown
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_currencies_creates_rows():
    """seed_currencies populates Currency with at least the major currencies."""
    call_command("seed_currencies")
    assert Currency.objects.count() >= 10
    for code in ("USD", "EUR", "JPY", "GBP", "CNY", "SGD"):
        assert Currency.objects.filter(code=code, is_active=True).exists(), (
            f"Currency {code} should be seeded"
        )


@pytest.mark.django_db
def test_seed_currencies_excludes_vnd_by_default():
    """VND is the local currency — should NOT be in the FX dropdown by default."""
    call_command("seed_currencies")
    assert not Currency.objects.filter(code="VND").exists()


@pytest.mark.django_db
def test_seed_currencies_includes_vnd_when_flagged():
    call_command("seed_currencies", include_vnd=True)
    assert Currency.objects.filter(code="VND").exists()


@pytest.mark.django_db
def test_seed_currencies_is_idempotent():
    call_command("seed_currencies")
    count1 = Currency.objects.count()
    call_command("seed_currencies")
    count2 = Currency.objects.count()
    assert count1 == count2


@pytest.mark.django_db
def test_fx_rate_form_dropdown_not_empty(client):
    """The FX rate form's currency dropdown shows at least one option."""
    call_command("seed_currencies")
    user = User.objects.create_superuser(
        username="admin", password="Secret123", email="a@b.c"
    )
    company = Company.objects.create(code="TCO", name="Test Co")
    client.force_login(user)
    session = client.session
    session["current_company_id"] = company.id
    session.save()

    response = client.get("/modern/fx/rates/")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "USD" in html, "USD option should appear in the currency dropdown"


# ---------------------------------------------------------------------------
# Bug #10: B01 uses net closing balance across object_code rows
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded_reports(db):
    """Seed FinancialReportLine rows for B01-DN."""
    call_command("seed_financial_report_lines")


@pytest.fixture
def ar_ap_company(db):
    """Company with TK 131 split across two object_codes.

    Simulates the PKM bug #10 scenario:
    - Row 1 (object_code="INV01"): closing_debit = 100 (invoice issued)
    - Row 2 (object_code="PAYMENT"): closing_credit = 60 (payment received)
    - Net for the asset line should be 100 - 60 = 40.
    """
    company = Company.objects.create(code="B10TCO", name="B10 Test Co")

    # Invoice row: full invoice amount on TK 1311 with object_code INV01
    v_inv = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="INV001",
        voucher_type="journal",
        voucher_date=date(2026, 6, 15),
        status=0,
    )
    VoucherLine.objects.create(
        voucher=v_inv, line_no=1, account_code="1311",
        object_code="INV01", debit_vnd=Decimal("100"),
    )
    VoucherLine.objects.create(
        voucher=v_inv, line_no=2, account_code="4111", credit_vnd=Decimal("100"),
    )
    VoucherPostingService().post(v_inv)

    # Payment row: payment for TK 1311 with a different object_code (the bug)
    v_pay = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="PAY001",
        voucher_type="cash_receipt",
        voucher_date=date(2026, 6, 20),
        status=0,
    )
    VoucherLine.objects.create(
        voucher=v_pay, line_no=1, account_code="1111", debit_vnd=Decimal("60"),
    )
    VoucherLine.objects.create(
        voucher=v_pay, line_no=2, account_code="1311",
        object_code="",  # ← the bug: payment didn't set object_code
        credit_vnd=Decimal("60"),
    )
    VoucherPostingService().post(v_pay)

    return company


@pytest.mark.django_db
def test_aggregate_closing_nets_across_object_codes(ar_ap_company):
    """#10 fix: TK 131 net closing balance = 40 (not 100, not 60).

    Before fix, _aggregate_closing('131*','debit') returned 100 (gross
    sum of closing_debit across the invoice row only). With the netting
    fix, it returns max(0, 100 - 60) = 40.
    """
    engine = ReportEngine(ar_ap_company, 2026, 6)
    debit = engine._aggregate_closing("131*", "debit")
    credit = engine._aggregate_closing("131*", "credit")
    assert debit == Decimal("40"), (
        f"Net closing_debit for 131* should be 40 (100 invoice - 60 payment), got {debit}"
    )
    assert credit == Decimal("0"), (
        f"Net closing_credit for 131* should be 0 (debt side wins), got {credit}"
    )


@pytest.mark.django_db
def test_aggregate_closing_pure_asset_no_credit(seded_reports, db):
    """Sanity: an account with only debit activity reports correctly."""
    company = Company.objects.create(code="SANITY", name="Sanity Co")
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        account_code="1111",
        period_debit=Decimal("500"),
        closing_debit=Decimal("500"),
    )
    engine = ReportEngine(company, 2026, 6)
    assert engine._aggregate_closing("1111*", "debit") == Decimal("500")
    assert engine._aggregate_closing("1111*", "credit") == Decimal("0")


@pytest.fixture
def seded_reports(db):
    """Alias fixture to avoid name collision in pure-asset test."""
    call_command("seed_financial_report_lines")
