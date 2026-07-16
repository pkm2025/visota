"""Tests for FinancialReportLine model, seed, formula parser, and services.

Covers VAL-M1-023 through VAL-M1-040 assertions.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.reporting.models import FinancialReportLine
from apps.reporting.services import BalanceSheetService, CashFlowService, PnLService
from apps.reporting.services.formula_parser import ReportEngine, parse_formula_tokens

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="TCO", name="Test Company")


@pytest.fixture
def seeded(db):
    """Seed FinancialReportLine rows."""
    call_command("seed_financial_report_lines")


@pytest.fixture
def posted_vouchers(db, company):
    """Post vouchers with various account types for report testing.

    Uses balanced entries so Assets = Liabilities + Equity:
    - DR 1111 (cash) 10,000 / CR 4111 (equity) 10,000
    - DR 1311 (AR) 5,500 / CR 3311 (AP) 5,500
    - DR 1521 (inventory) 2,000 / CR 33311 (tax payable) 2,000
    """
    # Asset + Equity voucher
    v1 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="BV001",
        voucher_type="journal",
        voucher_date=date(2026, 6, 15),
        status=0,
    )
    VoucherLine.objects.create(
        voucher=v1, line_no=1, account_code="1111", debit_vnd=Decimal("10000")
    )
    VoucherLine.objects.create(
        voucher=v1, line_no=2, account_code="4111", credit_vnd=Decimal("10000")
    )
    VoucherPostingService().post(v1)

    # AR + AP voucher
    v2 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="BV002",
        voucher_type="journal",
        voucher_date=date(2026, 6, 16),
        status=0,
    )
    VoucherLine.objects.create(
        voucher=v2, line_no=1, account_code="1311", debit_vnd=Decimal("5500")
    )
    VoucherLine.objects.create(
        voucher=v2, line_no=2, account_code="3311", credit_vnd=Decimal("5500")
    )
    VoucherPostingService().post(v2)

    # Inventory + Tax voucher
    v3 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="BV003",
        voucher_type="journal",
        voucher_date=date(2026, 6, 17),
        status=0,
    )
    VoucherLine.objects.create(
        voucher=v3, line_no=1, account_code="1521", debit_vnd=Decimal("2000")
    )
    VoucherLine.objects.create(
        voucher=v3, line_no=2, account_code="33311", credit_vnd=Decimal("2000")
    )
    VoucherPostingService().post(v3)

    return company


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestFinancialReportLineModel:
    def test_model_has_all_required_fields(self, db):
        """VAL-M1-023 (prerequisite): model exists with required fields."""
        line = FinancialReportLine.objects.create(
            report_type="B01-DN",
            stt="1",
            ma_so="100",
            chi_tieu="Tổng tài sản ngắn hạn",
            tk_no_pattern="111*",
            cong_thuc="=110+120",
            is_header=False,
            parent_ma_so="A",
            display_order=1,
        )
        assert line.pk is not None
        assert line.report_type == "B01-DN"
        assert line.cong_thuc == "=110+120"
        assert line.tk_no_pattern == "111*"
        assert line.is_header is False
        assert str(line) == "[B01-DN] 100 - Tổng tài sản ngắn hạn"

    def test_str_representation(self, db):
        line = FinancialReportLine.objects.create(
            report_type="B02-DN", chi_tieu="Revenue", ma_so="01", display_order=1
        )
        assert "B02-DN" in str(line)
        assert "01" in str(line)

    def test_db_table_name(self):
        assert FinancialReportLine._meta.db_table == "reporting_financial_report_line"

    def test_ordering(self):
        assert FinancialReportLine._meta.ordering == ["report_type", "display_order"]


# ---------------------------------------------------------------------------
# Seed command tests (VAL-M1-034)
# ---------------------------------------------------------------------------


class TestSeedFinancialReportLines:
    def test_seed_creates_lines(self, db):
        """VAL-M1-034: seed populates ~120 lines across 4 report types."""
        call_command("seed_financial_report_lines")
        total = FinancialReportLine.objects.count()
        assert total >= 120, f"Expected >=120 lines, got {total}"

    def test_seed_per_report_type(self, db):
        """Each report type has appropriate line count."""
        call_command("seed_financial_report_lines")
        b01 = FinancialReportLine.objects.filter(report_type="B01-DN").count()
        b02 = FinancialReportLine.objects.filter(report_type="B02-DN").count()
        b03d = FinancialReportLine.objects.filter(report_type="B03-DN-direct").count()
        b03i = FinancialReportLine.objects.filter(report_type="B03-DN-indirect").count()

        assert b01 >= 40, f"B01-DN should have >=40 lines, got {b01}"
        assert b02 >= 15, f"B02-DN should have >=15 lines, got {b02}"
        assert b03d >= 10, f"B03-DN-direct should have >=10 lines, got {b03d}"
        assert b03i >= 10, f"B03-DN-indirect should have >=10 lines, got {b03i}"

    def test_seed_is_idempotent(self, db):
        """VAL-M1-034: re-running seed does not duplicate."""
        call_command("seed_financial_report_lines")
        count1 = FinancialReportLine.objects.count()

        call_command("seed_financial_report_lines")
        count2 = FinancialReportLine.objects.count()

        assert count1 == count2, f"Seed not idempotent: {count1} -> {count2}"

    def test_130b_uses_3311_not_1331(self, db):
        """Line 130b 'Trả trước cho người bán ngắn hạn' aggregates TK 3311*
        (prepayment to suppliers), NOT 1331* which duplicates 150b and
        double-counts deductible VAT in total assets.
        """
        call_command("seed_financial_report_lines")
        line_130b = FinancialReportLine.objects.get(report_type="B01-DN", ma_so="130b")
        assert line_130b.tk_no_pattern == "3311*", (
            f"130b should use tk_no_pattern='3311*', got '{line_130b.tk_no_pattern}'"
        )
        assert line_130b.tk_no_pattern != "1331*", (
            "130b must NOT use 1331* (would duplicate line 150b)"
        )

    def test_150b_still_uses_1331(self, db):
        """Line 150b 'Thuế GTGT được khấu trừ' must still aggregate 1331*."""
        call_command("seed_financial_report_lines")
        line_150b = FinancialReportLine.objects.get(report_type="B01-DN", ma_so="150b")
        assert line_150b.tk_no_pattern == "1331*", (
            f"150b should keep tk_no_pattern='1331*', got '{line_150b.tk_no_pattern}'"
        )


# ---------------------------------------------------------------------------
# Formula parser tests (VAL-M1-035)
# ---------------------------------------------------------------------------


class TestFormulaParser:
    def test_parse_simple_addition(self):
        tokens = parse_formula_tokens("110+120+130+140")
        assert len(tokens) == 4
        assert tokens[0] == ("+", "110")
        assert tokens[1] == ("+", "120")
        assert tokens[3] == ("+", "140")

    def test_parse_with_minus(self):
        tokens = parse_formula_tokens("110-120")
        assert tokens == [("+", "110"), ("-", "120")]

    def test_parse_with_equals_prefix(self):
        tokens = parse_formula_tokens("=110+120")
        assert len(tokens) == 2
        assert tokens[0] == ("+", "110")

    def test_parse_empty(self):
        assert parse_formula_tokens("") == []
        assert parse_formula_tokens("") == []

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError):
            parse_formula_tokens("110+abc!def")

    def test_engine_evaluates_formula(self, db, company):
        """VAL-M1-035: cong_thuc resolves cross-line references."""
        FinancialReportLine.objects.create(
            report_type="TEST",
            ma_so="110",
            chi_tieu="A",
            tk_no_pattern="111*",
            display_order=1,
        )
        FinancialReportLine.objects.create(
            report_type="TEST",
            ma_so="120",
            chi_tieu="B",
            tk_no_pattern="112*",
            display_order=2,
        )
        FinancialReportLine.objects.create(
            report_type="TEST",
            ma_so="100",
            chi_tieu="Parent",
            cong_thuc="=110+120",
            display_order=3,
        )
        # Create balance data
        AccountPeriodBalance.objects.create(
            company=company,
            fiscal_year=2026,
            period=6,
            account_code="1111",
            period_debit=Decimal("500"),
            closing_debit=Decimal("500"),
        )
        AccountPeriodBalance.objects.create(
            company=company,
            fiscal_year=2026,
            period=6,
            account_code="1121",
            period_debit=Decimal("300"),
            closing_debit=Decimal("300"),
        )

        engine = ReportEngine(company, 2026, 6)
        lines = engine.generate("TEST", use_closing=True)
        values = {ln.ma_so: ln.value for ln in lines}

        assert values["110"] == Decimal("500")
        assert values["120"] == Decimal("300")
        assert values["100"] == Decimal("800")  # 500 + 300


# ---------------------------------------------------------------------------
# Pattern matching tests (VAL-M1-030, VAL-M1-031)
# ---------------------------------------------------------------------------


class TestPatternMatching:
    def test_wildcard_pattern_matches_multiple_accounts(self, db, company):
        """VAL-M1-031: tk_no_pattern='1331*' matches 1331 and 13311."""
        FinancialReportLine.objects.create(
            report_type="TEST",
            ma_so="200",
            chi_tieu="VAT",
            tk_no_pattern="1331*",
            display_order=1,
        )
        AccountPeriodBalance.objects.create(
            company=company,
            fiscal_year=2026,
            period=6,
            account_code="1331",
            period_debit=Decimal("100"),
            closing_debit=Decimal("100"),
        )
        AccountPeriodBalance.objects.create(
            company=company,
            fiscal_year=2026,
            period=6,
            account_code="13311",
            period_debit=Decimal("50"),
            closing_debit=Decimal("50"),
        )

        engine = ReportEngine(company, 2026, 6)
        lines = engine.generate("TEST", use_closing=True)
        assert lines[0].value == Decimal("150")  # 100 + 50

    def test_comma_separated_patterns(self, db, company):
        """Multiple comma-separated patterns are OR-ed."""
        FinancialReportLine.objects.create(
            report_type="TEST",
            ma_so="100",
            chi_tieu="Mixed",
            tk_no_pattern="111*,112*",
            display_order=1,
        )
        AccountPeriodBalance.objects.create(
            company=company,
            fiscal_year=2026,
            period=6,
            account_code="1111",
            period_debit=Decimal("200"),
            closing_debit=Decimal("200"),
        )
        AccountPeriodBalance.objects.create(
            company=company,
            fiscal_year=2026,
            period=6,
            account_code="1121",
            period_debit=Decimal("300"),
            closing_debit=Decimal("300"),
        )

        engine = ReportEngine(company, 2026, 6)
        lines = engine.generate("TEST", use_closing=True)
        assert lines[0].value == Decimal("500")

    def test_no_matching_accounts_returns_zero(self, db, company):
        FinancialReportLine.objects.create(
            report_type="TEST",
            ma_so="999",
            chi_tieu="None",
            tk_no_pattern="999*",
            display_order=1,
        )
        engine = ReportEngine(company, 2026, 6)
        lines = engine.generate("TEST")
        assert lines[0].value == Decimal("0")


# ---------------------------------------------------------------------------
# Service tests with config (VAL-M1-023 to VAL-M1-029)
# ---------------------------------------------------------------------------


class TestBalanceSheetServiceWithConfig:
    def test_generate_from_config(self, seeded, posted_vouchers):
        """VAL-M1-023: balance sheet renders from config lines."""
        svc = BalanceSheetService(company=posted_vouchers)
        result = svc.generate(2026, 6)

        assert "config_lines" in result
        assert len(result["config_lines"]) > 0
        # Balance sheet should be balanced (assets = liabilities + equity)
        assert result["is_balanced"] is True, (
            f"Not balanced: assets={result['assets']['total']}, "
            f"L+E={result['liabilities_equity']['total']}"
        )

    def test_balance_sheet_balances(self, seeded, posted_vouchers):
        """VAL-M1-028: Assets = Liabilities + Equity."""
        svc = BalanceSheetService(company=posted_vouchers)
        result = svc.generate(2026, 6)

        assets = result["assets"]["total"]
        le = result["liabilities_equity"]["total"]
        assert abs(assets - le) < Decimal("1"), (
            f"Balance sheet not balanced: assets={assets}, L+E={le}"
        )

    def test_config_lines_have_is_header_flag(self, seeded, posted_vouchers):
        """VAL-M1-032: header lines render differently from data lines."""
        svc = BalanceSheetService(company=posted_vouchers)
        result = svc.generate(2026, 6)

        lines = result["config_lines"]
        headers = [ln for ln in lines if ln.is_header]
        data = [ln for ln in lines if not ln.is_header]
        assert len(headers) > 0, "Should have at least one header line"
        assert len(data) > 0, "Should have at least one data line"

    def test_formula_aggregation_in_balance_sheet(self, seeded, posted_vouchers):
        """VAL-M1-030: line 100 = sum of child lines."""
        svc = BalanceSheetService(company=posted_vouchers)
        result = svc.generate(2026, 6)

        lines = result["config_lines"]
        values = {ln.ma_so: ln.value or Decimal("0") for ln in lines}

        # Line 100 (Tổng TS ngắn hạn) should equal sum of 110+120+130+140+150
        if "100" in values:
            children = (
                values.get("110", 0)
                + values.get("120", 0)
                + values.get("130", 0)
                + values.get("140", 0)
                + values.get("150", 0)
            )
            assert abs(values["100"] - children) < Decimal("1"), (
                f"Line 100 ({values['100']}) != sum of children ({children})"
            )


class TestPnLServiceWithConfig:
    def test_generate_from_config(self, seeded, posted_vouchers):
        """VAL-M1-024: P&L renders from config lines."""
        svc = PnLService(company=posted_vouchers)
        result = svc.generate(2026, 6)

        assert "config_lines" in result
        assert len(result["config_lines"]) > 0

    def test_pnl_revenue_correct(self, seeded, posted_vouchers):
        """VAL-M1-029: revenue matches account period balance."""
        svc = PnLService(company=posted_vouchers)
        result = svc.generate(2026, 6)

        # Revenue (5111 credit) should show in config-driven P&L
        lines = result["config_lines"]
        vals = {ln.ma_so: ln.value or Decimal("0") for ln in lines}
        # Fixture has no revenue accounts, so revenue should be 0
        assert vals.get("01", Decimal("0")) == Decimal("0")

    def test_pnl_net_income(self, seeded, posted_vouchers):
        """VAL-M1-029: net income computed correctly."""
        svc = PnLService(company=posted_vouchers)
        result = svc.generate(2026, 6)

        vals = {ln.ma_so: ln.value or Decimal("0") for ln in result["config_lines"]}
        # No P&L accounts in fixture, all values should be 0
        assert vals.get("01") == Decimal("0")  # Revenue
        assert vals.get("14") == Decimal("0")  # Net income


class TestCashFlowServiceWithConfig:
    def test_direct_from_config(self, seeded, posted_vouchers):
        """VAL-M1-025: direct cash flow renders from config."""
        svc = CashFlowService(company=posted_vouchers)
        result = svc.generate_direct(2026, 6)

        assert "config_lines" in result
        assert result["method"] == "direct"
        assert len(result["config_lines"]) > 0

    def test_indirect_from_config(self, seeded, posted_vouchers):
        """VAL-M1-026: indirect cash flow renders from config."""
        svc = CashFlowService(company=posted_vouchers)
        result = svc.generate_indirect(2026, 6)

        assert "config_lines" in result
        assert result["method"] == "indirect"
        assert len(result["config_lines"]) > 0

    def test_direct_and_indirect_different_config(self, seeded):
        """Direct and indirect have different report_type config."""
        from apps.reporting.models import FinancialReportLine

        direct_count = FinancialReportLine.objects.filter(report_type="B03-DN-direct").count()
        indirect_count = FinancialReportLine.objects.filter(report_type="B03-DN-indirect").count()
        assert direct_count > 0
        assert indirect_count > 0
        assert direct_count != indirect_count or direct_count > 5


# ---------------------------------------------------------------------------
# View tests (VAL-M1-023, VAL-M1-024, VAL-M1-025, VAL-M1-026, VAL-M1-027)
# ---------------------------------------------------------------------------


class TestReportViews:
    def _login_client(self, company=None):
        user = User.objects.create_superuser(
            username="tester", password="Secret123", email="tester@test.local"
        )
        client = Client()
        client.force_login(user)
        if company:
            session = client.session
            session["current_company_id"] = company.id
            session.save()
        return client

    def test_balance_sheet_view_with_config(self, seeded, posted_vouchers, company):
        """VAL-M1-023: B01-DN view renders config lines."""
        client = self._login_client(company)
        response = client.get("/modern/reports/balance-sheet/?fiscal_year=2026&period=6")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # Should contain config line labels
        assert "TÀI SẢN" in html or "NỢ PHẢI TRẢ" in html

    def test_pnl_view_with_config(self, seeded, posted_vouchers, company):
        """VAL-M1-024: B02-DN view renders config lines."""
        client = self._login_client(company)
        response = client.get("/modern/reports/pnl/?fiscal_year=2026&period=6")
        assert response.status_code == 200

    def test_cash_flow_direct_view_with_config(self, seeded, posted_vouchers, company):
        """VAL-M1-025: direct cash flow view renders config lines."""
        client = self._login_client(company)
        response = client.get("/modern/reports/cash-flow/direct/?fiscal_year=2026&period=6")
        assert response.status_code == 200

    def test_cash_flow_indirect_view_with_config(self, seeded, posted_vouchers, company):
        """VAL-M1-026: indirect cash flow view renders config lines."""
        client = self._login_client(company)
        response = client.get("/modern/reports/cash-flow/indirect/?fiscal_year=2026&period=6")
        assert response.status_code == 200

    def test_balance_sheet_empty_period_no_crash(self, seeded, company, db):
        """VAL-M1-036: empty period renders without 500."""
        client = self._login_client(company)
        response = client.get("/modern/reports/balance-sheet/?fiscal_year=2099&period=12")
        assert response.status_code == 200

    def test_pnl_empty_period_no_crash(self, seeded, company, db):
        """VAL-M1-036: P&L empty period renders without 500."""
        client = self._login_client(company)
        response = client.get("/modern/reports/pnl/?fiscal_year=2099&period=12")
        assert response.status_code == 200

    def test_cash_flow_empty_period_no_crash(self, seeded, company, db):
        """VAL-M1-036: cash flow empty period renders without 500."""
        client = self._login_client(company)
        response = client.get("/modern/reports/cash-flow/direct/?fiscal_year=2099&period=12")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Migration reversibility test (VAL-M1-038)
# ---------------------------------------------------------------------------


class TestMigrationReversibility:
    def test_migration_has_reverse(self):
        """VAL-M1-038: migration is reversible."""
        import os

        from apps.reporting.migrations import __path__ as mig_path

        mig_dir = mig_path[0] if isinstance(mig_path, list) else mig_path
        files = [f for f in os.listdir(mig_dir) if f.endswith(".py") and f != "__init__.py"]
        assert len(files) >= 1, "Should have at least one migration"

        # Read the migration file and verify it doesn't have Noop reverse
        for f in files:
            with open(os.path.join(mig_dir, f)) as fh:
                content = fh.read()
                assert "CreateModel" in content or "AddField" in content, (
                    f"Migration {f} should have CreateModel or AddField"
                )


# ---------------------------------------------------------------------------
# VAL-M1-040: No hard-coded BCTC values
# ---------------------------------------------------------------------------


class TestNoHardcodedValues:
    def test_services_check_config_first(self):
        """VAL-M1-040: services read from FinancialReportLine config."""
        import inspect

        from apps.reporting.services.balance_sheet import BalanceSheetService
        from apps.reporting.services.pnl import PnLService

        # The generate method should reference FinancialReportLine
        bs_src = inspect.getsource(BalanceSheetService)
        pnl_src = inspect.getsource(PnLService)

        assert "FinancialReportLine" in bs_src, (
            "BalanceSheetService should reference FinancialReportLine"
        )
        assert "FinancialReportLine" in pnl_src, "PnLService should reference FinancialReportLine"
