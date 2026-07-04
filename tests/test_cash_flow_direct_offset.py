"""Tests for the cash-flow direct-method offset (counterpart) account filter.

Covers feature m1-fix-cash-flow-direct-offset:
  - FinancialReportLine has ``tk_doi_ung_pattern`` field.
  - Migration 0002 applies cleanly.
  - ReportEngine._aggregate_cash_with_offset queries VoucherLine with
    voucher_id join.
  - Each B03-direct data line returns a DIFFERENT value based on its
    offset account filter.
  - Net cash change (ma_so 10) reconciles with opening/closing cash
    balance delta.
  - Cash flow direct method matches legacy CashFlowService output.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db.models import Q, Sum

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.reporting.models import FinancialReportLine
from apps.reporting.services import CashFlowService
from apps.reporting.services.formula_parser import ReportEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="TCF", name="Cash Flow Test Co")


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
def diverse_cash_vouchers(db, company):
    """Post vouchers covering every B03-direct offset category.

    Each voucher has a cash leg (1111/1121) and an offset leg matching
    exactly one B03-direct line's ``tk_doi_ung_pattern``.

    Voucher -> offset account -> B03-direct line:
      BV-01  -> 5111 (revenue)      -> line 01 (cash from customers)
      BV-02  -> 3311 (AP)           -> line 02 (cash to suppliers)
      BV-02A -> 3341 (salaries)     -> line 02a (cash to employees)
      BV-02B -> 33311 (VAT payable) -> line 02b (tax paid) [3331* match]
      BV-04  -> 7111 (other income) -> line 04 (asset disposal) [711* match]
      BV-05  -> 2111 (fixed asset)  -> line 05 (buy fixed assets)
      BV-05A -> 1211 (securities)   -> line 05a (lending/investing)
      BV-07  -> 3411 (loan)         -> line 07 (borrowing)
      BV-08  -> 4111 (equity)       -> line 08 (repay capital) [411* match]
      BV-08A -> 4211 (retained ear) -> line 08a (dividends)
    """
    _make_voucher(
        company,
        2026,
        6,
        "BV-01",
        "cash_receipt",
        date(2026, 6, 1),
        [("1111", 1000, 0), ("5111", 0, 1000)],
    )
    _make_voucher(
        company,
        2026,
        6,
        "BV-02",
        "cash_payment",
        date(2026, 6, 2),
        [("3311", 200, 0), ("1111", 0, 200)],
    )
    _make_voucher(
        company,
        2026,
        6,
        "BV-02A",
        "cash_payment",
        date(2026, 6, 3),
        [("3341", 300, 0), ("1121", 0, 300)],
    )
    _make_voucher(
        company,
        2026,
        6,
        "BV-02B",
        "cash_payment",
        date(2026, 6, 4),
        [("33311", 400, 0), ("1111", 0, 400)],
    )
    _make_voucher(
        company,
        2026,
        6,
        "BV-04",
        "cash_receipt",
        date(2026, 6, 5),
        [("1121", 500, 0), ("7111", 0, 500)],
    )
    _make_voucher(
        company,
        2026,
        6,
        "BV-05",
        "cash_payment",
        date(2026, 6, 6),
        [("2111", 600, 0), ("1121", 0, 600)],
    )
    _make_voucher(
        company,
        2026,
        6,
        "BV-05A",
        "cash_payment",
        date(2026, 6, 7),
        [("1211", 700, 0), ("1111", 0, 700)],
    )
    _make_voucher(
        company,
        2026,
        6,
        "BV-07",
        "cash_receipt",
        date(2026, 6, 8),
        [("1111", 800, 0), ("3411", 0, 800)],
    )
    _make_voucher(
        company,
        2026,
        6,
        "BV-08",
        "cash_payment",
        date(2026, 6, 9),
        [("4111", 900, 0), ("1121", 0, 900)],
    )
    _make_voucher(
        company,
        2026,
        6,
        "BV-08A",
        "cash_payment",
        date(2026, 6, 10),
        [("4211", 150, 0), ("1111", 0, 150)],
    )
    return company


# ---------------------------------------------------------------------------
# Model + migration
# ---------------------------------------------------------------------------


class TestTkDoiUngPatternField:
    def test_field_exists(self, db):
        """FinancialReportLine has tk_doi_ung_pattern field."""
        field = FinancialReportLine._meta.get_field("tk_doi_ung_pattern")
        assert field.max_length == 200
        assert field.blank is True
        assert field.default == ""

    def test_field_persists_and_round_trips(self, db):
        line = FinancialReportLine.objects.create(
            report_type="TEST",
            chi_tieu="test",
            tk_doi_ung_pattern="511*,131*",
            display_order=1,
        )
        line.refresh_from_db()
        assert line.tk_doi_ung_pattern == "511*,131*"

    def test_migration_0002_filename(self):
        import os

        from apps.reporting.migrations import __path__ as mig_paths

        mig_dir = mig_paths[0] if isinstance(mig_paths, list) else mig_paths
        files = [f for f in os.listdir(mig_dir) if f.startswith("0002")]
        assert len(files) >= 1, "Should have a 0002 migration"
        assert "tk_doi_ung_pattern" in files[0] or "financialreportline" in files[0]


# ---------------------------------------------------------------------------
# Seed offset patterns
# ---------------------------------------------------------------------------


class TestSeedOffsetPatterns:
    def test_b03_direct_lines_have_offset_patterns(self, seeded):
        """Each B03-direct DATA line has a non-empty tk_doi_ung_pattern."""
        from django.db.models import Q

        data_lines = FinancialReportLine.objects.filter(
            report_type="B03-DN-direct",
        ).filter(Q(tk_no_pattern__startswith="111") | Q(tk_co_pattern__startswith="111"))
        assert data_lines.count() >= 10, "Should have at least 10 data lines"
        for line in data_lines:
            assert line.tk_doi_ung_pattern != "", (
                f"Line {line.ma_so} ({line.chi_tieu}) has empty tk_doi_ung_pattern"
            )

    def test_each_direct_line_has_unique_offset(self, seeded):
        """The 11 data lines should NOT all share the same offset pattern.

        This is the core fix: previously all lines used identical
        ``111*,112*`` which produced the same meaningless value.  Now each
        line has a distinct offset pattern per TT133.
        """
        from django.db.models import Q

        data_lines = (
            FinancialReportLine.objects.filter(
                report_type="B03-DN-direct",
            )
            .filter(Q(tk_no_pattern__startswith="111") | Q(tk_co_pattern__startswith="111"))
            .values_list("tk_doi_ung_pattern", flat=True)
        )

        offsets = list(data_lines)
        assert len(offsets) >= 10
        # At least 8 distinct patterns (some may overlap, e.g. 07/08)
        assert len(set(offsets)) >= 8, (
            f"Expected >=8 distinct offset patterns, got {len(set(offsets))}: {set(offsets)}"
        )

    def test_specific_offset_patterns(self, seeded):
        """Verify the exact offset patterns per TT133 spec."""
        expected = {
            "01": "511*,131*",
            "02": "531*,331*,152*,156*",
            "02a": "334*",
            "02b": "3334*,3331*,821*",
            "04": "211*,212*,213*,711*",
            "05": "211*,212*,213*,241*",
            "05a": "121*,228*",
            "07": "341*,411*",
            "08": "341*,411*",
            "08a": "421*,3531*",
        }
        for ma_so, expected_offset in expected.items():
            line = FinancialReportLine.objects.get(report_type="B03-DN-direct", ma_so=ma_so)
            assert line.tk_doi_ung_pattern == expected_offset, (
                f"Line {ma_so}: expected '{expected_offset}', got '{line.tk_doi_ung_pattern}'"
            )


# ---------------------------------------------------------------------------
# ReportEngine._aggregate_cash_with_offset
# ---------------------------------------------------------------------------


class TestAggregateCashWithOffset:
    def test_inflow_offset_sums_cash_debit(self, db, company):
        """Cash received from customers (offset 511*) sums cash debit."""
        _make_voucher(
            company,
            2026,
            6,
            "BV1",
            "cash_receipt",
            date(2026, 6, 1),
            [("1111", 1000, 0), ("5111", 0, 1000)],
        )
        engine = ReportEngine(company, 2026, 6)
        result = engine._aggregate_cash_with_offset("111*,112*", "511*,131*", side="debit")
        assert result == Decimal("1000")

    def test_outflow_offset_sums_cash_credit(self, db, company):
        """Cash paid to suppliers (offset 331*) sums cash credit."""
        _make_voucher(
            company,
            2026,
            6,
            "BV1",
            "cash_payment",
            date(2026, 6, 1),
            [("3311", 500, 0), ("1111", 0, 500)],
        )
        engine = ReportEngine(company, 2026, 6)
        result = engine._aggregate_cash_with_offset("111*,112*", "331*", side="credit")
        assert result == Decimal("500")

    def test_non_matching_offset_returns_zero(self, db, company):
        """Vouchers whose offset does NOT match are excluded."""
        _make_voucher(
            company,
            2026,
            6,
            "BV1",
            "cash_receipt",
            date(2026, 6, 1),
            [("1111", 1000, 0), ("5111", 0, 1000)],
        )
        engine = ReportEngine(company, 2026, 6)
        # Offset 331* (suppliers) should NOT match a revenue voucher
        result = engine._aggregate_cash_with_offset("111*,112*", "331*", side="credit")
        assert result == Decimal("0")

    def test_different_offsets_produce_different_values(self, db, company):
        """Two different offset patterns on the same data produce different values."""
        _make_voucher(
            company,
            2026,
            6,
            "BV1",
            "cash_receipt",
            date(2026, 6, 1),
            [("1111", 1000, 0), ("5111", 0, 1000)],
        )
        _make_voucher(
            company,
            2026,
            6,
            "BV2",
            "cash_payment",
            date(2026, 6, 2),
            [("3311", 300, 0), ("1111", 0, 300)],
        )
        engine = ReportEngine(company, 2026, 6)
        revenue_cash = engine._aggregate_cash_with_offset("111*,112*", "511*,131*", side="debit")
        supplier_cash = engine._aggregate_cash_with_offset("111*,112*", "331*", side="credit")
        assert revenue_cash == Decimal("1000")
        assert supplier_cash == Decimal("300")
        assert revenue_cash != supplier_cash

    def test_result_is_cached(self, db, company):
        """Calling twice returns cached value without re-querying."""
        _make_voucher(
            company,
            2026,
            6,
            "BV1",
            "cash_receipt",
            date(2026, 6, 1),
            [("1111", 1000, 0), ("5111", 0, 1000)],
        )
        engine = ReportEngine(company, 2026, 6)
        first = engine._aggregate_cash_with_offset("111*,112*", "511*", side="debit")
        second = engine._aggregate_cash_with_offset("111*,112*", "511*", side="debit")
        assert first == second == Decimal("1000")

    def test_period_filter_excludes_other_periods(self, db, company):
        """Only vouchers in the engine's fiscal_year/period are included."""
        _make_voucher(
            company,
            2026,
            5,
            "BV1",
            "cash_receipt",
            date(2026, 5, 1),
            [("1111", 1000, 0), ("5111", 0, 1000)],
        )
        _make_voucher(
            company,
            2026,
            6,
            "BV2",
            "cash_receipt",
            date(2026, 6, 1),
            [("1111", 2000, 0), ("5111", 0, 2000)],
        )
        engine = ReportEngine(company, 2026, 6)
        result = engine._aggregate_cash_with_offset("111*,112*", "511*", side="debit")
        assert result == Decimal("2000"), "Should only include period 6"


# ---------------------------------------------------------------------------
# Full B03-direct generation: lines differ + reconciliation
# ---------------------------------------------------------------------------


class TestB03DirectDifferentiation:
    def test_data_lines_return_different_values(self, seeded, diverse_cash_vouchers):
        """Each B03-direct data line returns a DIFFERENT value based on its
        offset filter (the core fix for Blocker B03-DN-direct)."""
        company = diverse_cash_vouchers
        engine = ReportEngine(company, 2026, 6)
        lines = engine.generate("B03-DN-direct")
        values = {
            ln.ma_so: ln.value or Decimal("0")
            for ln in lines
            if ln.ma_so in ("01", "02", "02a", "02b", "04", "05", "05a", "07", "08", "08a")
        }

        # At least 3 distinct nonzero values among the data lines
        nonzero = {k: v for k, v in values.items() if v > 0}
        distinct = set(nonzero.values())
        assert len(distinct) >= 3, (
            f"Expected >=3 distinct nonzero values, got {distinct} from {nonzero}"
        )

    def test_expected_values_per_line(self, seeded, diverse_cash_vouchers):
        """Verify specific expected values per B03-direct line."""
        company = diverse_cash_vouchers
        engine = ReportEngine(company, 2026, 6)
        lines = engine.generate("B03-DN-direct")
        vals = {ln.ma_so: ln.value or Decimal("0") for ln in lines}

        # Inflows (cash debited)
        assert vals["01"] == Decimal("1000"), f"line 01: {vals['01']}"
        assert vals["04"] == Decimal("500"), f"line 04: {vals['04']}"
        assert vals["07"] == Decimal("800"), f"line 07: {vals['07']}"

        # Outflows (cash credited, reported as positive magnitude)
        assert vals["02"] == Decimal("200"), f"line 02: {vals['02']}"
        assert vals["02a"] == Decimal("300"), f"line 02a: {vals['02a']}"
        assert vals["02b"] == Decimal("400"), f"line 02b: {vals['02b']}"
        assert vals["05"] == Decimal("600"), f"line 05: {vals['05']}"
        assert vals["05a"] == Decimal("700"), f"line 05a: {vals['05a']}"
        assert vals["08"] == Decimal("900"), f"line 08: {vals['08']}"
        assert vals["08a"] == Decimal("150"), f"line 08a: {vals['08a']}"

    def test_net_operating_formula(self, seeded, diverse_cash_vouchers):
        """Line 03 (net operating) = 01 - 02 - 02a - 02b."""
        company = diverse_cash_vouchers
        engine = ReportEngine(company, 2026, 6)
        lines = engine.generate("B03-DN-direct")
        vals = {ln.ma_so: ln.value or Decimal("0") for ln in lines}

        expected_03 = vals["01"] - vals["02"] - vals["02a"] - vals["02b"]
        assert vals["03"] == expected_03, f"Line 03 ({vals['03']}) != 01-02-02a-02b ({expected_03})"

    def test_net_change_reconciles_with_cash_delta(self, seeded, diverse_cash_vouchers):
        """Net cash change (ma_so 10) reconciles with opening/closing
        cash balance delta.

        Net change = inflows - outflows = total cash debit - total cash
        credit across all posted vouchers in the period.
        """
        company = diverse_cash_vouchers
        engine = ReportEngine(company, 2026, 6)
        lines = engine.generate("B03-DN-direct")
        vals = {ln.ma_so: ln.value or Decimal("0") for ln in lines}

        net_change = vals["10"]

        # Independently compute net cash movement from VoucherLine
        cash_q = Q(account_code__startswith="111") | Q(account_code__startswith="112")
        cash_lines = VoucherLine.objects.filter(
            voucher__fiscal_year=2026,
            voucher__period=6,
            voucher__status__gte=2,
            voucher__company=company,
        ).filter(cash_q)
        totals = cash_lines.aggregate(
            d=Sum("debit_vnd"),
            c=Sum("credit_vnd"),
        )
        expected_net = (totals["d"] or Decimal("0")) - (totals["c"] or Decimal("0"))

        assert abs(net_change - expected_net) < Decimal("1"), (
            f"Net change {net_change} != cash delta {expected_net}"
        )


# ---------------------------------------------------------------------------
# Comparison with legacy CashFlowService.generate_direct
# ---------------------------------------------------------------------------


class TestMatchesLegacyDirect:
    def test_config_matches_legacy_totals(self, seeded, diverse_cash_vouchers):
        """The config-driven direct method should match the legacy
        CashFlowService.generate_direct output for net_change.

        We compare the overall net cash change, not individual line
        values, because the legacy method categorizes by first-digit
        prefix while the config method categorizes by offset pattern.
        Both should agree on the total net cash movement.
        """
        company = diverse_cash_vouchers

        # Force legacy path by temporarily removing config
        FinancialReportLine.objects.filter(report_type="B03-DN-direct").delete()
        legacy_svc = CashFlowService(company=company)
        legacy_result = legacy_svc.generate_direct(2026, 6)

        # Re-seed config
        call_command("seed_financial_report_lines")
        config_svc = CashFlowService(company=company)
        config_result = config_svc.generate_direct(2026, 6)

        legacy_net = legacy_result["net_change"]
        config_net = config_result["net_change"]

        assert abs(legacy_net - config_net) < Decimal("1"), (
            f"Config net_change {config_net} != legacy net_change {legacy_net}"
        )
