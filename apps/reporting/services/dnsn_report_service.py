"""DnsnReportService — TT58/2026/TT-BTC financial report generator.

Generates two simplified financial reports for DNSN (Doanh nghiệp siêu nhỏ):

**B01-DNSN — Báo cáo tình hình tài chính (Balance Sheet)**
Aggregates from DnsnLedgerBalance:
- Tiền (cash + bank) from S2d
- Công nợ phải thu from S4a (receivables portion)
- Hàng tồn kho from S2c
- TSCĐ from S4b
- Công nợ phải trả from S4a (payables portion)
- Thuế khác from S4c
- Vốn CSH from S4d

**B02-DNSN — Báo cáo kết quả hoạt động kinh doanh (P&L)**
Aggregates from DnsnLedgerBalance:
- Doanh thu from revenue ledgers (S1, S2a, S2b, S3a)
- Chi phí from S2b
- Thuế TNDN
- Lợi nhuận

Also provides BCTC (Báo cáo tài chính) mandatory check for period close:
- Groups 2 and 4 (tndn_method=tinh_thue): BCTC mandatory
- Groups 1 and 3 (tndn_method=ty_le_phan_tram): BCTC optional
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from apps.ledger.models import DnsnLedgerBalance

if TYPE_CHECKING:
    from apps.core.models import Company


class DnsnReportService:
    """Generate B01-DNSN and B02-DNSN reports from DnsnLedgerBalance data.

    All methods accept (company, fiscal_year, period) and return a dict
    suitable for template rendering.
    """

    def __init__(self, company: Company):
        self.company = company

    # ------------------------------------------------------------------
    # B01-DNSN — Báo cáo tình hình tài chính
    # ------------------------------------------------------------------

    def generate_b01_dnsn(self, fiscal_year: int, period: int) -> dict:
        """Generate B01-DNSN: simplified balance sheet for DNSN.

        Aggregates asset and liability+equity balances from
        DnsnLedgerBalance rows for the given period.

        Returns dict with keys:
            - assets: list of {label, amount} rows
            - total_assets
            - liabilities: list of {label, amount} rows
            - total_liabilities
            - equity: list of {label, amount} rows
            - total_equity
            - total_liabilities_equity
            - is_balanced: bool (total_assets == total_liabilities_equity)
            - fiscal_year, period
        """
        balances = self._get_balances(fiscal_year, period)

        # --- Assets ---
        cash = self._get_balance_value(balances, "s2d", "closing_cash")
        receivables = self._get_balance_value(balances, "s4a", "closing_cash")
        inventory = self._get_balance_value(balances, "s2c", "closing_revenue")
        fixed_assets = self._get_balance_value(balances, "s4b", "closing_cash")

        asset_rows = [
            {"stt": "1", "label": "Tiền", "amount": cash},
            {"stt": "2", "label": "Công nợ phải thu", "amount": receivables},
            {"stt": "3", "label": "Hàng tồn kho", "amount": inventory},
            {"stt": "4", "label": "Tài sản cố định", "amount": fixed_assets},
        ]
        total_assets = sum((r["amount"] for r in asset_rows), Decimal("0"))

        # --- Liabilities ---
        payables = self._get_balance_value(balances, "s4a", "closing_cost")
        other_taxes = self._get_balance_value(balances, "s4c", "closing_cash")

        liability_rows = [
            {"stt": "1", "label": "Công nợ phải trả", "amount": payables},
            {"stt": "2", "label": "Thuế khác phải nộp", "amount": other_taxes},
        ]
        total_liabilities = sum((r["amount"] for r in liability_rows), Decimal("0"))

        # --- Equity ---
        owner_capital = self._get_balance_value(balances, "s4d", "closing_cash")
        retained_earnings = self._get_balance_value(balances, "s4d", "closing_revenue")

        equity_rows = [
            {"stt": "1", "label": "Vốn góp của chủ sở hữu", "amount": owner_capital},
            {"stt": "2", "label": "Lợi nhuận chưa phân phối", "amount": retained_earnings},
        ]
        total_equity = sum((r["amount"] for r in equity_rows), Decimal("0"))

        total_le = total_liabilities + total_equity
        is_balanced = abs(total_assets - total_le) < Decimal("1")

        return {
            "report_type": "B01-DNSN",
            "report_title": "Báo cáo tình hình tài chính (B01-DNSN)",
            "fiscal_year": fiscal_year,
            "period": period,
            "company": self.company,
            "company_name": self.company.name,
            "assets": asset_rows,
            "total_assets": total_assets,
            "liabilities": liability_rows,
            "total_liabilities": total_liabilities,
            "equity": equity_rows,
            "total_equity": total_equity,
            "total_liabilities_equity": total_le,
            "is_balanced": is_balanced,
        }

    # ------------------------------------------------------------------
    # B02-DNSN — Báo cáo kết quả hoạt động kinh doanh
    # ------------------------------------------------------------------

    def generate_b02_dnsn(self, fiscal_year: int, period: int) -> dict:
        """Generate B02-DNSN: simplified P&L for DNSN.

        Aggregates revenue and cost from DnsnLedgerBalance rows.

        Returns dict with keys:
            - revenue: total revenue for the period
            - cost: total cost for the period
            - gross_profit: revenue - cost
            - tndn_tax: TNDN tax amount
            - net_profit: gross_profit - tndn_tax
            - fiscal_year, period
            - rows: list of {stt, label, amount} for display
        """
        balances = self._get_balances(fiscal_year, period)

        # Sum revenue from all revenue ledgers (S1, S2a, S2b, S3a)
        revenue = Decimal("0")
        for lt in ("s1", "s2a", "s2b", "s3a"):
            revenue += self._get_balance_value(balances, lt, "closing_revenue")

        # Sum cost from S2b
        cost = self._get_balance_value(balances, "s2b", "closing_cost")

        # TNDN tax: stored in S4c closing_vat (or closing_cost as fallback)
        tndn_tax = self._get_balance_value(balances, "s4c", "closing_vat")

        gross_profit = revenue - cost
        net_profit = gross_profit - tndn_tax

        rows = [
            {"stt": "1", "label": "Doanh thu bán hàng hóa, dịch vụ", "amount": revenue},
            {"stt": "2", "label": "Chi phí hoạt động kinh doanh", "amount": cost},
            {"stt": "3", "label": "Lợi nhuận trước thuế", "amount": gross_profit},
            {"stt": "4", "label": "Thuế thu nhập doanh nghiệp", "amount": tndn_tax},
            {"stt": "5", "label": "Lợi nhuận sau thuế", "amount": net_profit},
        ]

        return {
            "report_type": "B02-DNSN",
            "report_title": "Báo cáo kết quả hoạt động kinh doanh (B02-DNSN)",
            "fiscal_year": fiscal_year,
            "period": period,
            "company": self.company,
            "company_name": self.company.name,
            "revenue": revenue,
            "cost": cost,
            "gross_profit": gross_profit,
            "profit_before_tax": gross_profit,
            "tndn_tax": tndn_tax,
            "pit_expense": tndn_tax,
            "net_profit": net_profit,
            "profit_after_tax": net_profit,
            "rows": rows,
        }

    # ------------------------------------------------------------------
    # BCTC Mandatory Check
    # ------------------------------------------------------------------

    def is_bctc_mandatory(self) -> bool:
        """Check if BCTC (Báo cáo tài chính) is mandatory for this company.

        Per TT58/2026/TT-BTC:
        - Groups 2 and 4 (tndn_method=tinh_thue): BCTC mandatory
        - Groups 1 and 3 (tndn_method=ty_le_phan_tram): BCTC optional

        Returns True if BCTC is mandatory, False if optional.
        """
        if self.company.accounting_regime != "tt58":
            return False
        group = self.company.tax_method_group
        # Groups 2 and 4 have tndn_method=tinh_thue
        return group in (2, 4)

    def has_bctc_for_period(self, fiscal_year: int, period: int) -> bool:
        """Check if a BCTC has been generated for the given period.

        A BCTC is considered generated if there are DnsnLedgerBalance
        records for the period, which indicates the ledger has been
        posted and report data is available.

        For year-end close, period=12 (or the final period) is checked.
        """
        return DnsnLedgerBalance.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
        ).exists()

    def check_bctc_for_period_close(self, fiscal_year: int, period: int) -> dict:
        """Check BCTC status for period close.

        Returns dict with:
            - mandatory: bool — whether BCTC is required
            - has_bctc: bool — whether BCTC data exists
            - can_close: bool — True if close is allowed
            - message: str — human-readable status message
        """
        mandatory = self.is_bctc_mandatory()
        has_bctc = self.has_bctc_for_period(fiscal_year, period)

        if mandatory and not has_bctc:
            can_close = False
            message = (
                "BCTC bắt buộc phải lập cho nhóm thuế tính thuế. "
                "Vui lòng lập B01-DNSN và B02-DNSN trước khi kết chuyển."
            )
        elif mandatory and has_bctc:
            can_close = True
            message = "BCTC đã lập. Có thể kết chuyển kỳ."
        else:
            # Optional for groups 1 and 3
            can_close = True
            message = "BCTC tùy chọn cho nhóm thuế tỷ lệ %. Có thể kết chuyển kỳ."

        return {
            "mandatory": mandatory,
            "has_bctc": has_bctc,
            "can_close": can_close,
            "message": message,
            "tax_method_group": self.company.tax_method_group,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_balances(self, fiscal_year: int, period: int) -> dict[str, DnsnLedgerBalance]:
        """Get all DnsnLedgerBalance rows for the period, keyed by ledger_type."""
        qs = DnsnLedgerBalance.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
        )
        return {b.ledger_type: b for b in qs}

    @staticmethod
    def _get_balance_value(
        balances: dict[str, DnsnLedgerBalance],
        ledger_type: str,
        field: str,
    ) -> Decimal:
        """Extract a Decimal value from a balance dict safely.

        Args:
            balances: dict keyed by ledger_type
            ledger_type: e.g. "s2d"
            field: balance field name, e.g. "closing_cash"
        """
        balance = balances.get(ledger_type)
        if balance is None:
            return Decimal("0")
        value = getattr(balance, field, None)
        if value is None:
            return Decimal("0")
        return Decimal(str(value))

    # ------------------------------------------------------------------
    # Export data extraction
    # ------------------------------------------------------------------

    def get_b01_export_rows(
        self, fiscal_year: int, period: int
    ) -> tuple[list[str], list[list[str]]]:
        """Get B01-DNSN data as (headers, rows) for PDF/Excel export."""
        data = self.generate_b01_dnsn(fiscal_year, period)
        headers = ["STT", "Chỉ tiêu", "Số tiền"]
        rows: list[list[str]] = []

        # Assets section
        rows.append(["", "I. TÀI SẢN", "", ""])
        for r in data["assets"]:
            rows.append([r["stt"], r["label"], "", self._fmt_vnd(r["amount"])])
        rows.append(["", "TỔNG CỘNG TÀI SẢN", "", self._fmt_vnd(data["total_assets"])])

        # Liabilities section
        rows.append(["", "II. NỢ PHẢI TRẢ", "", ""])
        for r in data["liabilities"]:
            rows.append([r["stt"], r["label"], "", self._fmt_vnd(r["amount"])])
        rows.append(["", "TỔNG NỢ PHẢI TRẢ", "", self._fmt_vnd(data["total_liabilities"])])

        # Equity section
        rows.append(["", "III. VỐN CHỦ SỞ HỮU", "", ""])
        for r in data["equity"]:
            rows.append([r["stt"], r["label"], "", self._fmt_vnd(r["amount"])])
        rows.append(["", "TỔNG VỐN CSH", "", self._fmt_vnd(data["total_equity"])])

        rows.append(
            [
                "",
                "TỔNG NỢ PHẢI TRẢ + VỐN CSH",
                "",
                self._fmt_vnd(data["total_liabilities_equity"]),
            ]
        )

        return headers, rows

    def get_b02_export_rows(
        self, fiscal_year: int, period: int
    ) -> tuple[list[str], list[list[str]]]:
        """Get B02-DNSN data as (headers, rows) for PDF/Excel export."""
        data = self.generate_b02_dnsn(fiscal_year, period)
        headers = ["STT", "Chỉ tiêu", "Mã số", "Kỳ này"]
        rows: list[list[str]] = []
        for r in data["rows"]:
            rows.append([r["stt"], r["label"], "", self._fmt_vnd(r["amount"])])
        return headers, rows

    @staticmethod
    def _fmt_vnd(value) -> str:
        """Format a Decimal as Vietnamese integer string with thousands separators."""
        if value is None:
            return ""
        try:
            d = Decimal(str(value)).quantize(Decimal("1"))
            return f"{int(d):,}".replace(",", ".")
        except Exception:
            return str(value)
