"""Balance Sheet (B01-DN) generator - config-driven.

Reads ``FinancialReportLine`` config rows for ``report_type='B01-DN'``
and evaluates each line via the shared ``ReportEngine``.  Falls back to
the legacy first-digit grouping when no config rows exist (e.g. during
tests that don't run the seed command).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from apps.reporting.models import FinancialReportLine
from apps.reporting.services.formula_parser import ReportEngine, ReportLine

if TYPE_CHECKING:
    from apps.core.models import Company


class BalanceSheetService:
    """Generate Balance Sheet data from ``FinancialReportLine`` config.

    When config rows exist for ``B01-DN`` the service evaluates them via
    ``ReportEngine`` (closing balances for the balance sheet).  When no
    config is present it falls back to the legacy first-digit grouping so
    existing tests continue to pass.
    """

    REPORT_TYPE = "B01-DN"

    def __init__(self, company: Company | None):
        self.company = company

    # -- config-driven path ----------------------------------------------

    def _split_asset_vs_le(self, lines: list[ReportLine]) -> tuple[...]:
        """Split rendered lines into asset / liability / equity groups.

        Lines whose ``parent_ma_so`` starts with ``A`` are assets; those
        starting with ``L`` are liabilities; ``E`` are equity.  This
        matches the ``parent_ma_so`` convention used in the seed.
        """
        asset_lines: list[ReportLine] = []
        liability_lines: list[ReportLine] = []
        equity_lines: list[ReportLine] = []

        for ln in lines:
            parent = ln.parent_ma_so.upper()
            if parent.startswith("L"):
                liability_lines.append(ln)
            elif parent.startswith("E"):
                equity_lines.append(ln)
            else:
                asset_lines.append(ln)

        return asset_lines, liability_lines, equity_lines

    def _line_total(self, lines: list[ReportLine]) -> Decimal:
        """Return the value of the total line (the last line with a formula)."""
        for ln in reversed(lines):
            # Total lines have a formula (e.g. "=100+200") even if is_header.
            if ln.raw_config and ln.raw_config.cong_thuc.strip() and ln.value is not None:
                return ln.value
        # Fallback: last non-header line with a value.
        for ln in reversed(lines):
            if ln.value is not None and not ln.is_header:
                return ln.value
        return Decimal("0")

    def generate(self, fiscal_year: int, period: int) -> dict:
        has_config = FinancialReportLine.objects.filter(report_type=self.REPORT_TYPE).exists()

        if has_config:
            return self._generate_from_config(fiscal_year, period)
        return self._generate_legacy(fiscal_year, period)

    def _generate_from_config(self, fiscal_year: int, period: int) -> dict:
        engine = ReportEngine(self.company, fiscal_year, period)
        lines = engine.generate(self.REPORT_TYPE, use_closing=True)

        asset_lines, liability_lines, equity_lines = self._split_asset_vs_le(lines)

        # Build a ma_so -> value lookup for formula resolution.
        all_vals = {ln.ma_so: ln.value or Decimal("0") for ln in lines if ln.ma_so}

        # Total assets = line 270 (formula =100+200); fall back to sum of
        # section sub-totals (100+200).
        total_assets = all_vals.get("270") or (
            all_vals.get("100", Decimal("0")) + all_vals.get("200", Decimal("0"))
        )

        # Total LE = line 700 (formula =300+400+500+600).
        total_le = all_vals.get("700") or (
            all_vals.get("300", Decimal("0"))
            + all_vals.get("400", Decimal("0"))
            + all_vals.get("500", Decimal("0"))
            + all_vals.get("600", Decimal("0"))
        )

        # Liabilities = 300 + 400; Equity = 500 + 600.
        total_liabilities = all_vals.get("300", Decimal("0")) + all_vals.get("400", Decimal("0"))
        total_equity = all_vals.get("500", Decimal("0")) + all_vals.get("600", Decimal("0"))

        return {
            "fiscal_year": fiscal_year,
            "period": period,
            "config_lines": lines,
            "assets": {
                "rows": [
                    {
                        "ma_so": ln.ma_so,
                        "chi_tieu": ln.chi_tieu,
                        "amount": ln.value or Decimal("0"),
                    }
                    for ln in asset_lines
                    if not ln.is_header
                ],
                "lines": asset_lines,
                "total": total_assets,
            },
            "liabilities_equity": {
                "liabilities": [
                    {
                        "ma_so": ln.ma_so,
                        "chi_tieu": ln.chi_tieu,
                        "amount": ln.value or Decimal("0"),
                    }
                    for ln in liability_lines
                    if not ln.is_header
                ],
                "equity": [
                    {
                        "ma_so": ln.ma_so,
                        "chi_tieu": ln.chi_tieu,
                        "amount": ln.value or Decimal("0"),
                    }
                    for ln in equity_lines
                    if not ln.is_header
                ],
                "liability_lines": liability_lines,
                "equity_lines": equity_lines,
                "total_liabilities": total_liabilities,
                "total_equity": total_equity,
                "total": total_le,
            },
            "is_balanced": abs(total_assets - total_le) < Decimal("1"),
        }

    # -- legacy fallback -------------------------------------------------

    def _generate_legacy(self, fiscal_year: int, period: int) -> dict:
        from apps.ledger.services import YtdBalanceService

        rows = YtdBalanceService(
            company=self.company, fiscal_year=fiscal_year, period=period
        ).fetch()

        asset_rows: list[dict] = []
        liability_rows: list[dict] = []
        equity_rows: list[dict] = []

        for r in rows:
            closing = max(r.closing_debit, r.closing_credit)
            if closing == 0:
                continue

            first_digit = r.account_code[0] if r.account_code else "0"
            row = {"account_code": r.account_code, "amount": closing}

            if first_digit in ("1", "2"):
                asset_rows.append(row)
            elif first_digit == "3":
                liability_rows.append(row)
            elif first_digit == "4":
                equity_rows.append(row)

        total_assets = sum((r["amount"] for r in asset_rows), Decimal("0"))
        total_liabilities = sum((r["amount"] for r in liability_rows), Decimal("0"))
        total_equity = sum((r["amount"] for r in equity_rows), Decimal("0"))

        return {
            "fiscal_year": fiscal_year,
            "period": period,
            "config_lines": [],
            "assets": {
                "rows": asset_rows,
                "lines": [],
                "total": total_assets,
            },
            "liabilities_equity": {
                "liabilities": liability_rows,
                "equity": equity_rows,
                "liability_lines": [],
                "equity_lines": [],
                "total_liabilities": total_liabilities,
                "total_equity": total_equity,
                "total": total_liabilities + total_equity,
            },
            "is_balanced": total_assets == total_liabilities + total_equity,
        }
