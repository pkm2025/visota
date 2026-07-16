"""Tests for cash-flow direct-method company isolation (VAL-CF-001).

Verifies that ``ReportEngine._aggregate_cash_with_offset`` filters by
company, preventing cross-tenant data leakage in the cash flow direct
method report.

Scenario:
  - Create two companies (A and B).
  - Post vouchers in the SAME fiscal_year/period for both companies.
  - Generate the cash flow direct method report for company A.
  - Assert that only company A's voucher lines appear in the result.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.reporting.services.formula_parser import ReportEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company_a(db):
    return Company.objects.create(code="CFA", name="Company A")


@pytest.fixture
def company_b(db):
    return Company.objects.create(code="CFB", name="Company B")


@pytest.fixture
def seeded(db):
    """Seed FinancialReportLine rows (including B03-direct offsets)."""
    call_command("seed_financial_report_lines")


def _make_voucher(company, fy, period, vno, vtype, vdate, lines):
    """Helper: create a voucher + lines, post it, return the voucher."""
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=fy,
        period=period,
        voucher_no=vno,
        voucher_type=vtype,
        voucher_date=vdate,
        status=0,
    )
    for idx, (acc, debit, credit) in enumerate(lines, 1):
        VoucherLine.objects.create(
            voucher=v,
            line_no=idx,
            account_code=acc,
            debit_vnd=Decimal(str(debit)),
            credit_vnd=Decimal(str(credit)),
        )
    VoucherPostingService().post(v)
    return v


@pytest.fixture
def two_company_vouchers(db, company_a, company_b):
    """Post identical cash-receipt vouchers for two companies.

    Company A: 1000 cash debit from revenue (5111).
    Company B: 5000 cash debit from revenue (5111).

    Both in the same fiscal_year (2026) and period (6).
    """
    _make_voucher(
        company_a,
        2026,
        6,
        "BV-A1",
        "cash_receipt",
        date(2026, 6, 1),
        [("1111", 1000, 0), ("5111", 0, 1000)],
    )
    _make_voucher(
        company_b,
        2026,
        6,
        "BV-B1",
        "cash_receipt",
        date(2026, 6, 1),
        [("1111", 5000, 0), ("5111", 0, 5000)],
    )
    return company_a, company_b


# ---------------------------------------------------------------------------
# _aggregate_cash_with_offset company isolation
# ---------------------------------------------------------------------------


class TestCashWithOffsetCompanyIsolation:
    """VAL-CF-001: _aggregate_cash_with_offset must filter by company."""

    def test_company_a_excludes_company_b_data(self, two_company_vouchers):
        """When company A generates cash flow, company B data must NOT appear."""
        company_a, company_b = two_company_vouchers

        engine = ReportEngine(company_a, 2026, 6)
        result = engine._aggregate_cash_with_offset("111*,112*", "511*,131*", side="debit")
        # Should be 1000 (company A only), NOT 6000 (both companies)
        assert result == Decimal("1000"), (
            f"Expected 1000 (company A only), got {result} - cross-company leak!"
        )

    def test_company_b_excludes_company_a_data(self, two_company_vouchers):
        """When company B generates cash flow, company A data must NOT appear."""
        company_a, company_b = two_company_vouchers

        engine = ReportEngine(company_b, 2026, 6)
        result = engine._aggregate_cash_with_offset("111*,112*", "511*,131*", side="debit")
        # Should be 5000 (company B only), NOT 6000 (both companies)
        assert result == Decimal("5000"), (
            f"Expected 5000 (company B only), got {result} - cross-company leak!"
        )

    def test_offset_voucher_ids_scoped_by_company(self, two_company_vouchers):
        """The offset_voucher_ids subquery must be scoped by company.

        This test verifies that vouchers from company B are NOT included
        in the offset_voucher_ids set when querying for company A, even
        if company B's voucher has a matching offset account line.
        """
        company_a, company_b = two_company_vouchers

        # Company A's vouchers in period 6 with offset 5111
        company_a_offset_vouchers = set(
            VoucherLine.objects.filter(
                voucher__fiscal_year=2026,
                voucher__period=6,
                voucher__status__gte=2,
                voucher__company=company_a,
                account_code__startswith="511",
            ).values_list("voucher_id", flat=True)
        )
        # Company B's vouchers should NOT be in company A's set
        company_b_voucher_ids = set(
            VoucherLine.objects.filter(
                voucher__fiscal_year=2026,
                voucher__period=6,
                voucher__status__gte=2,
                voucher__company=company_b,
            ).values_list("voucher_id", flat=True)
        )
        assert company_a_offset_vouchers.isdisjoint(company_b_voucher_ids)

    def test_no_company_filter_returns_all_data(self, two_company_vouchers):
        """When company is None (superuser/global), all data should appear.

        This verifies the company=None case still works (no filter applied),
        which is important for admin/superuser views.
        """
        company_a, company_b = two_company_vouchers

        engine = ReportEngine(None, 2026, 6)
        result = engine._aggregate_cash_with_offset("111*,112*", "511*,131*", side="debit")
        # Should be 6000 (both companies, since company=None means global)
        assert result == Decimal("6000"), f"Expected 6000 (all companies), got {result}"


# ---------------------------------------------------------------------------
# Full B03-direct report generation company isolation
# ---------------------------------------------------------------------------


class TestB03DirectCompanyIsolation:
    """VAL-CF-001: Full B03-DN-direct report must isolate by company."""

    def test_report_only_includes_current_company(self, seeded, two_company_vouchers):
        """The full B03-DN-direct report for company A must only show
        company A's data (1000), not company B's (5000)."""
        company_a, company_b = two_company_vouchers

        engine = ReportEngine(company_a, 2026, 6)
        lines = engine.generate("B03-DN-direct")
        vals = {ln.ma_so: ln.value or Decimal("0") for ln in lines}

        # Line 01 (cash from customers) should be 1000, NOT 6000
        assert vals["01"] == Decimal("1000"), (
            f"Line 01 expected 1000, got {vals['01']} - cross-company leak!"
        )

    def test_company_b_report_only_includes_b_data(self, seeded, two_company_vouchers):
        """The full B03-DN-direct report for company B must only show
        company B's data (5000)."""
        company_a, company_b = two_company_vouchers

        engine = ReportEngine(company_b, 2026, 6)
        lines = engine.generate("B03-DN-direct")
        vals = {ln.ma_so: ln.value or Decimal("0") for ln in lines}

        # Line 01 (cash from customers) should be 5000, NOT 6000
        assert vals["01"] == Decimal("5000"), (
            f"Line 01 expected 5000, got {vals['01']} - cross-company leak!"
        )
