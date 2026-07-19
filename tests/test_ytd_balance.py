"""Regression tests for the YTD-balance bug (BCTC không cộng dồn YTD).

Before the fix, ``TrialBalanceView`` / ``BalanceSheetService`` /
``PnLService`` read only the single-period ``AccountPeriodBalance`` row,
which dropped everything from prior periods of the same fiscal year.
These tests post vouchers across two periods and assert that period 2
shows the cumulative year-to-date balance.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine
from apps.ledger.services import VoucherPostingService, YtdBalanceService
from apps.reporting.services import BalanceSheetService, PnLService


@pytest.fixture
def company(db):
    return Company.objects.create(code="YTD", name="YTD Test")


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(
        username="ytdadmin", password="Secret123", email="ytd@test.local"
    )


def _post(company, voucher_no, period, day, lines):
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=period,
        voucher_no=voucher_no,
        voucher_type="journal",
        voucher_date=date(2026, day.month, day.day),
        status=AccountingVoucher.Status.DRAFT,
    )
    for i, (acc, debit, credit) in enumerate(lines, 1):
        VoucherLine.objects.create(
            voucher=v,
            line_no=i,
            account_code=acc,
            debit_vnd=Decimal(debit),
            credit_vnd=Decimal(credit),
        )
    VoucherPostingService().post(v)
    return v


@pytest.mark.django_db
def test_ytd_service_aggregates_opening_and_period(company):
    """Period 2 closing must include period 1 movement + period 2 movement."""
    # Period 1: +1000 on TK 111
    _post(company, "P1", 1, date(2026, 1, 10), [("111", "1000", "0"), ("411", "0", "1000")])
    # Period 2: +500 on TK 111
    _post(company, "P2", 2, date(2026, 2, 10), [("111", "500", "0"), ("411", "0", "500")])

    rows = YtdBalanceService(company=company, fiscal_year=2026, period=2).fetch()
    by_code = {r.account_code: r for r in rows}

    # TK 111 (asset, debit-natured): opening=1000, period=500, closing=1500.
    assert by_code["111"].opening_debit == Decimal("1000")
    assert by_code["111"].period_debit == Decimal("500")
    assert by_code["111"].closing_debit == Decimal("1500")

    # TK 411 (equity, credit-natured): opening=1000, period=500, closing=1500.
    assert by_code["411"].opening_credit == Decimal("1000")
    assert by_code["411"].period_credit == Decimal("500")
    assert by_code["411"].closing_credit == Decimal("1500")


@pytest.mark.django_db
def test_ytd_service_period1_opening_is_period0(company):
    """Period 1 opening must equal the period-0 opening balance row."""
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=0,
        account_code="111",
        opening_debit=Decimal("700"),
        opening_credit=Decimal("0"),
        closing_debit=Decimal("700"),
        closing_credit=Decimal("0"),
    )
    _post(company, "P1", 1, date(2026, 1, 15), [("111", "300", "0"), ("411", "0", "300")])

    rows = YtdBalanceService(company=company, fiscal_year=2026, period=1).fetch()
    by_code = {r.account_code: r for r in rows}
    # Period 0 opening (700) flows into period 1 opening.
    assert by_code["111"].opening_debit == Decimal("700")
    assert by_code["111"].period_debit == Decimal("300")
    assert by_code["111"].closing_debit == Decimal("1000")


@pytest.mark.django_db
def test_ytd_service_pnl_accounts_drop_period0_opening(company):
    """P&L accounts (5/6/7/8) start the year at zero even if period 0 has data."""
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=0,
        account_code="511",
        opening_credit=Decimal("999"),  # bogus period-0 entry
    )
    _post(
        company,
        "P1",
        1,
        date(2026, 1, 20),
        [("111", "200", "0"), ("511", "0", "200")],
    )

    rows = YtdBalanceService(company=company, fiscal_year=2026, period=1).fetch()
    by_code = {r.account_code: r for r in rows}
    # P&L opening must be 0 — not the bogus 999.
    assert by_code["511"].opening_credit == Decimal("0")
    assert by_code["511"].period_credit == Decimal("200")
    assert by_code["511"].closing_credit == Decimal("200")


@pytest.mark.django_db
def test_trial_balance_view_ytd(company, admin):
    """Trial balance at period 2 must show cumulative closing across periods 1-2."""
    _post(company, "P1", 1, date(2026, 1, 10), [("111", "1000", "0"), ("411", "0", "1000")])
    _post(company, "P2", 2, date(2026, 2, 10), [("111", "500", "0"), ("411", "0", "500")])

    client = Client()
    client.force_login(admin)
    session = client.session
    session["current_company_id"] = company.id
    session.save()

    response = client.get("/modern/reports/trial-balance/?fiscal_year=2026&period=2")
    assert response.status_code == 200
    # Closing totals must reflect cumulative YTD = 1500.
    assert response.context["total_closing_debit"] == Decimal("1500")
    assert response.context["total_closing_credit"] == Decimal("1500")
    # Period column = period 2 only.
    assert response.context["total_period_debit"] == Decimal("500")
    # Opening column = period 1 movement.
    assert response.context["total_opening_debit"] == Decimal("1000")


@pytest.mark.django_db
def test_balance_sheet_service_ytd(company):
    """Balance sheet at period 2 must equal cumulative activity of periods 1-2."""
    _post(company, "P1", 1, date(2026, 1, 10), [("111", "1000", "0"), ("411", "0", "1000")])
    _post(company, "P2", 2, date(2026, 2, 10), [("111", "500", "0"), ("411", "0", "500")])

    result = BalanceSheetService(company=company).generate(fiscal_year=2026, period=2)
    assert result["assets"]["total"] == Decimal("1500")
    assert result["liabilities_equity"]["total"] == Decimal("1500")
    assert result["is_balanced"]


@pytest.mark.django_db
def test_pnl_service_legacy_ytd(company):
    """P&L legacy path at period 2 must sum periods 1-2."""
    # Period 1: revenue 1000
    _post(company, "R1", 1, date(2026, 1, 10), [("111", "1000", "0"), ("511", "0", "1000")])
    # Period 2: revenue 500
    _post(company, "R2", 2, date(2026, 2, 10), [("111", "500", "0"), ("511", "0", "500")])

    # Force the legacy path: no FinancialReportLine config rows for B02-DN.
    from apps.reporting.models import FinancialReportLine

    FinancialReportLine.objects.filter(report_type="B02-DN").delete()

    result = PnLService(company=company).generate(fiscal_year=2026, period=2)
    assert result["revenue"] == Decimal("1500"), "P&L revenue must be YTD"
