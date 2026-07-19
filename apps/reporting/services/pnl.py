"""P&L Statement (B02-DN) generator - config-driven.

Reads ``FinancialReportLine`` config rows for ``report_type='B02-DN'``
and evaluates each line via the shared ``ReportEngine`` using period
debit/credit movements.  Falls back to the legacy hard-coded account-
prefix logic when no config rows exist.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from apps.reporting.models import FinancialReportLine
from apps.reporting.services.formula_parser import ReportEngine, ReportLine

if TYPE_CHECKING:
    from apps.core.models import Company


class PnLService:
    """Generate P&L data from ``FinancialReportLine`` config or legacy logic."""

    REPORT_TYPE = "B02-DN"

    def __init__(self, company: Company | None):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        has_config = FinancialReportLine.objects.filter(report_type=self.REPORT_TYPE).exists()

        if has_config:
            return self._generate_from_config(fiscal_year, period)
        return self._generate_legacy(fiscal_year, period)

    # -- config-driven path ----------------------------------------------

    def _values_by_ma_so(self, lines: list[ReportLine]) -> dict[str, Decimal]:
        """Map ma_so -> computed Decimal value for formula lookup."""
        out: dict[str, Decimal] = {}
        for ln in lines:
            if ln.ma_so:
                out[ln.ma_so] = ln.value or Decimal("0")
        return out

    def _generate_from_config(self, fiscal_year: int, period: int) -> dict:
        engine = ReportEngine(self.company, fiscal_year, period)
        lines = engine.generate(self.REPORT_TYPE, use_closing=False)
        vals = self._values_by_ma_so(lines)

        # Provide backward-compatible named keys by reading well-known
        # ma_so codes from the config.  If the seed uses different codes
        # the template relies on ``config_lines`` instead.
        def _g(key: str) -> Decimal:
            return vals.get(key, Decimal("0"))

        return {
            "fiscal_year": fiscal_year,
            "period": period,
            "config_lines": lines,
            "revenue": _g("01"),
            "revenue_net": _g("01"),
            "cogs": _g("02"),
            "gross_profit": _g("03"),
            "financial_income": _g("04"),
            "financial_expense": _g("05"),
            "selling_expense": _g("06"),
            "admin_expense": _g("07"),
            "operating_profit": _g("08"),
            "other_income": _g("09"),
            "other_expense": _g("10"),
            "other_profit": _g("11"),
            "profit_before_tax": _g("12"),
            "pit_expense": _g("13"),
            "profit_after_tax": _g("14"),
        }

    # -- legacy fallback -------------------------------------------------

    def _generate_legacy(self, fiscal_year: int, period: int) -> dict:
        from apps.ledger.services import YtdBalanceService

        rows = YtdBalanceService(
            company=self.company, fiscal_year=fiscal_year, period=period
        ).fetch()

        revenue = Decimal("0")
        cogs = Decimal("0")
        selling_expense = Decimal("0")
        admin_expense = Decimal("0")
        financial_income = Decimal("0")
        financial_expense = Decimal("0")
        other_income = Decimal("0")
        other_expense = Decimal("0")
        pit_expense = Decimal("0")

        for r in rows:
            code = r.account_code or ""
            # YTD period movements (Jan..N): revenue/expenses accumulate.
            period_d = r.period_debit_ytd
            period_c = r.period_credit_ytd

            if code.startswith("515"):
                financial_income += period_c - period_d
            elif code.startswith("5"):
                revenue += period_c - period_d
            elif code.startswith("632"):
                cogs += period_d - period_c
            elif code.startswith("641"):
                selling_expense += period_d - period_c
            elif code.startswith("642"):
                admin_expense += period_d - period_c
            elif code.startswith("635"):
                financial_expense += period_d - period_c
            elif code.startswith("711"):
                other_income += period_c - period_d
            elif code.startswith("811"):
                other_expense += period_d - period_c
            elif code.startswith("821"):
                pit_expense += period_d - period_c

        gross_profit = revenue - cogs
        operating_profit = (
            gross_profit + financial_income - financial_expense - selling_expense - admin_expense
        )
        other_profit = other_income - other_expense
        profit_before_tax = operating_profit + other_profit
        profit_after_tax = profit_before_tax - pit_expense

        return {
            "fiscal_year": fiscal_year,
            "period": period,
            "config_lines": [],
            "revenue": revenue,
            "revenue_net": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "selling_expense": selling_expense,
            "admin_expense": admin_expense,
            "financial_income": financial_income,
            "financial_expense": financial_expense,
            "operating_profit": operating_profit,
            "other_income": other_income,
            "other_expense": other_expense,
            "other_profit": other_profit,
            "profit_before_tax": profit_before_tax,
            "pit_expense": pit_expense,
            "profit_after_tax": profit_after_tax,
        }
