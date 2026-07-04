"""Cash flow statement (B03-DN) generators - direct and indirect methods.

Config-driven: reads ``FinancialReportLine`` rows for the direct and
indirect report types and evaluates them via ``ReportEngine``.  Falls
back to the legacy hard-coded logic when no config rows exist.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Q, Sum

from apps.ledger.models import AccountPeriodBalance, VoucherLine
from apps.reporting.models import FinancialReportLine
from apps.reporting.services.formula_parser import ReportEngine

if TYPE_CHECKING:
    from apps.core.models import Company


class CashFlowService:
    """Generate cash flow statement data (B03-DN) using direct or indirect method."""

    INVESTING_PREFIXES = ["211", "212", "221", "222", "228"]
    FINANCING_PREFIXES = ["341", "343", "411"]

    DIRECT_TYPE = "B03-DN-direct"
    INDIRECT_TYPE = "B03-DN-indirect"

    def __init__(self, company: Company | None):
        self.company = company

    # ====================================================================
    # Direct method
    # ====================================================================

    def generate_direct(self, fiscal_year: int, period: int) -> dict:
        has_config = FinancialReportLine.objects.filter(report_type=self.DIRECT_TYPE).exists()

        if has_config:
            return self._generate_from_config(self.DIRECT_TYPE, fiscal_year, period, "direct")
        return self._generate_direct_legacy(fiscal_year, period)

    def _generate_from_config(
        self, report_type: str, fiscal_year: int, period: int, method: str
    ) -> dict:
        engine = ReportEngine(self.company, fiscal_year, period)
        lines = engine.generate(report_type, use_closing=False)
        vals: dict[str, Decimal] = {}
        for ln in lines:
            if ln.ma_so:
                vals[ln.ma_so] = ln.value or Decimal("0")

        def _g(key: str) -> Decimal:
            return vals.get(key, Decimal("0"))

        # Direct method well-known ma_so mapping (matches seed)
        if method == "direct":
            result = {
                "method": "direct",
                "config_lines": lines,
                "fiscal_year": fiscal_year,
                "period": period,
                "operating_in": _g("01"),
                "operating_out": _g("02"),
                "net_operating": _g("03"),
                "investing_in": _g("04"),
                "investing_out": _g("05"),
                "net_investing": _g("06"),
                "financing_in": _g("07"),
                "financing_out": _g("08"),
                "net_financing": _g("09"),
                "net_change": _g("10"),
            }
        else:
            result = {
                "method": "indirect",
                "config_lines": lines,
                "fiscal_year": fiscal_year,
                "period": period,
                "net_income": _g("01"),
                "dep_exp": _g("02"),
                "delta_ar": _g("03"),
                "delta_ap": _g("04"),
                "delta_inv": _g("05"),
                "delta_prepaid": _g("06"),
                "net_operating": _g("07"),
                "net_investing": _g("08"),
                "net_financing": _g("09"),
                "net_change": _g("10"),
            }

        # Compute opening / closing cash from raw voucher data
        opening_cash = self._compute_opening_cash(fiscal_year, period)
        result["opening_cash"] = opening_cash
        result["closing_cash"] = opening_cash + (result.get("net_change") or Decimal("0"))
        return result

    def _compute_opening_cash(self, fiscal_year: int, period: int) -> Decimal:
        cash_q = Q(account_code__startswith="111") | Q(account_code__startswith="112")
        prior = VoucherLine.objects.filter(
            voucher__fiscal_year=fiscal_year,
            voucher__period__lt=period,
            voucher__status__gte=2,
        ).filter(cash_q)
        if self.company is not None:
            prior = prior.filter(voucher__company=self.company)
        prior_totals = prior.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
        return (prior_totals["d"] or Decimal("0")) - (prior_totals["c"] or Decimal("0"))

    # ====================================================================
    # Indirect method
    # ====================================================================

    def generate_indirect(self, fiscal_year: int, period: int) -> dict:
        has_config = FinancialReportLine.objects.filter(report_type=self.INDIRECT_TYPE).exists()

        if has_config:
            return self._generate_from_config(self.INDIRECT_TYPE, fiscal_year, period, "indirect")
        return self._generate_indirect_legacy(fiscal_year, period)

    # ====================================================================
    # Legacy implementations (used when no config rows seeded)
    # ====================================================================

    def _generate_direct_legacy(self, fiscal_year: int, period: int) -> dict:
        cash_prefixes = ["111", "112"]

        cash_q = Q()
        for prefix in cash_prefixes:
            cash_q |= Q(account_code__startswith=prefix)

        lines = VoucherLine.objects.filter(
            voucher__fiscal_year=fiscal_year,
            voucher__period=period,
            voucher__status__gte=2,
        ).select_related("voucher")
        if self.company is not None:
            lines = lines.filter(voucher__company=self.company)

        cash_lines = lines.filter(cash_q)

        operating_in = Decimal("0")
        operating_out = Decimal("0")
        investing_in = Decimal("0")
        investing_out = Decimal("0")
        financing_in = Decimal("0")
        financing_out = Decimal("0")

        for cl in cash_lines:
            offsets = lines.filter(voucher_id=cl.voucher_id).exclude(pk=cl.pk)
            offset_codes = [o.account_code for o in offsets]

            amount = cl.debit_vnd or cl.credit_vnd or Decimal("0")
            is_inflow = (cl.debit_vnd or 0) > 0

            category = "operating"
            for code in offset_codes:
                if any(code.startswith(p) for p in self.INVESTING_PREFIXES):
                    category = "investing"
                    break
                if any(code.startswith(p) for p in self.FINANCING_PREFIXES):
                    category = "financing"
                    break

            if category == "operating":
                if is_inflow:
                    operating_in += amount
                else:
                    operating_out += amount
            elif category == "investing":
                if is_inflow:
                    investing_in += amount
                else:
                    investing_out += amount
            elif category == "financing":
                if is_inflow:
                    financing_in += amount
                else:
                    financing_out += amount

        net_operating = operating_in - operating_out
        net_investing = investing_in - investing_out
        net_financing = financing_in - financing_out
        net_change = net_operating + net_investing + net_financing

        opening_cash = self._compute_opening_cash(fiscal_year, period)

        return {
            "method": "direct",
            "config_lines": [],
            "fiscal_year": fiscal_year,
            "period": period,
            "operating_in": operating_in,
            "operating_out": operating_out,
            "net_operating": net_operating,
            "investing_in": investing_in,
            "investing_out": investing_out,
            "net_investing": net_investing,
            "financing_in": financing_in,
            "financing_out": financing_out,
            "net_financing": net_financing,
            "net_change": net_change,
            "opening_cash": opening_cash,
            "closing_cash": opening_cash + net_change,
        }

    def _generate_indirect_legacy(self, fiscal_year: int, period: int) -> dict:
        balances = AccountPeriodBalance.objects.filter(
            fiscal_year=fiscal_year,
            period=period,
        )
        if self.company is not None:
            balances = balances.filter(company=self.company)

        def get_period_amount(prefix):
            r = balances.filter(account_code__startswith=prefix).aggregate(
                d=Sum("period_debit"), c=Sum("period_credit")
            )
            return (r["d"] or Decimal("0")), (r["c"] or Decimal("0"))

        rev_d, rev_c = get_period_amount("511")
        revenue = rev_c
        cogs_d, _ = get_period_amount("632")
        sell_d, _ = get_period_amount("641")
        admin_d, _ = get_period_amount("642")
        fin_d, _ = get_period_amount("635")
        other_inc_d, other_inc_c = get_period_amount("711")
        fin_inc_d, fin_inc_c = get_period_amount("515")
        other_exp_d, _ = get_period_amount("811")
        tax_d, _ = get_period_amount("821")

        net_income = (
            revenue
            + (fin_inc_c - fin_inc_d)
            + (other_inc_c - other_inc_d)
            - cogs_d
            - sell_d
            - admin_d
            - fin_d
            - other_exp_d
            - tax_d
        )

        dep_d, _ = get_period_amount("214")
        dep_exp = dep_d
        ar_d, ar_c = get_period_amount("131")
        ap_d, ap_c = get_period_amount("331")
        inv_d, inv_c = get_period_amount("152")
        prepaid_d, prepaid_c = get_period_amount("242")

        delta_ar = ar_d - ar_c
        delta_ap = ap_c - ap_d
        delta_inv = inv_d - inv_c
        delta_prepaid = prepaid_d - prepaid_c

        net_operating = net_income + dep_exp - delta_ar + delta_ap - delta_inv - delta_prepaid

        capex_d, _ = get_period_amount("211")
        net_investing = -(capex_d)

        loan_d, loan_c = get_period_amount("341")
        equity_d, equity_c = get_period_amount("411")
        net_financing = (loan_c - loan_d) + (equity_c - equity_d)

        div_d, _ = get_period_amount("421")
        net_financing -= div_d

        net_change = net_operating + net_investing + net_financing

        opening_cash = self._compute_opening_cash(fiscal_year, period)

        return {
            "method": "indirect",
            "config_lines": [],
            "fiscal_year": fiscal_year,
            "period": period,
            "net_income": net_income,
            "dep_exp": dep_exp,
            "delta_ar": delta_ar,
            "delta_ap": delta_ap,
            "delta_inv": delta_inv,
            "delta_prepaid": delta_prepaid,
            "net_operating": net_operating,
            "net_investing": net_investing,
            "net_financing": net_financing,
            "net_change": net_change,
            "opening_cash": opening_cash,
            "closing_cash": opening_cash + net_change,
        }
