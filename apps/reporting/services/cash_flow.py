"""Cash flow statement (B03-DN) generators — direct and indirect methods.

Direct method: lists actual cash receipts and payments by category.
Indirect method: starts from net income and adjusts for non-cash items.

Account mapping (TT133):
  Operating activities:   TK 111, 112 (cash/bank) excluding investing/financing
  Investing activities:   TK 111/112 movements tied to 211, 212, 221, 222, 228
  Financing activities:   TK 111/112 movements tied to 341, 343, 411
"""

from decimal import Decimal

from django.db.models import Q, Sum

from apps.ledger.models import AccountPeriodBalance, VoucherLine


class CashFlowService:
    """Generate cash flow statement data (B03-DN) using direct or indirect method."""

    INVESTING_PREFIXES = ["211", "212", "221", "222", "228"]
    FINANCING_PREFIXES = ["341", "343", "411"]

    def __init__(self, company):
        self.company = company

    def generate_direct(self, fiscal_year: int, period: int) -> dict:
        """Direct method: cash receipts minus cash payments by activity."""
        cash_prefixes = ["111", "112"]

        # All cash lines in the period
        cash_q = Q()
        for prefix in cash_prefixes:
            cash_q |= Q(account_code__startswith=prefix)

        lines = VoucherLine.objects.filter(
            voucher__company=self.company,
            voucher__fiscal_year=fiscal_year,
            voucher__period=period,
            voucher__status__gte=2,
        ).select_related("voucher")

        cash_lines = lines.filter(cash_q)

        # Categorize: find offset account on same voucher
        operating_in = Decimal("0")
        operating_out = Decimal("0")
        investing_in = Decimal("0")
        investing_out = Decimal("0")
        financing_in = Decimal("0")
        financing_out = Decimal("0")

        for cl in cash_lines:
            # Determine the offset account from the same voucher
            offsets = lines.filter(voucher_id=cl.voucher_id).exclude(pk=cl.pk)
            offset_codes = [o.account_code for o in offsets]

            amount = cl.debit_vnd or cl.credit_vnd or Decimal("0")
            is_inflow = (cl.debit_vnd or 0) > 0  # debit to cash = inflow

            # Classify by offset account
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

        # Opening cash balance
        prior = VoucherLine.objects.filter(
            voucher__company=self.company,
            voucher__fiscal_year=fiscal_year,
            voucher__period__lt=period,
            voucher__status__gte=2,
        ).filter(cash_q)
        prior_totals = prior.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
        opening_cash = (prior_totals["d"] or Decimal("0")) - (prior_totals["c"] or Decimal("0"))

        return {
            "method": "direct",
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

    def generate_indirect(self, fiscal_year: int, period: int) -> dict:
        """Indirect method: net income adjusted for non-cash items."""
        balances = AccountPeriodBalance.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
        )

        def get_period_amount(prefix):
            r = balances.filter(account_code__startswith=prefix).aggregate(
                d=Sum("period_debit"), c=Sum("period_credit")
            )
            return (r["d"] or Decimal("0")), (r["c"] or Decimal("0"))

        # Net income: revenue (511) - expenses (632, 641, 642, 635, 811) + other income (711, 515)
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

        # Adjustments: depreciation (non-cash)
        dep_d, _ = get_period_amount("214")
        dep_exp = dep_d
        # Changes in working capital
        ar_d, ar_c = get_period_amount("131")
        ap_d, ap_c = get_period_amount("331")
        inv_d, inv_c = get_period_amount("152")
        prepaid_d, prepaid_c = get_period_amount("242")

        delta_ar = ar_d - ar_c
        delta_ap = ap_c - ap_d
        delta_inv = inv_d - inv_c
        delta_prepaid = prepaid_d - prepaid_c

        net_operating = net_income + dep_exp - delta_ar + delta_ap - delta_inv - delta_prepaid

        # Investing: capex (211 debit), investments
        capex_d, _ = get_period_amount("211")
        net_investing = -(capex_d)

        # Financing: loans (341), equity (411)
        loan_d, loan_c = get_period_amount("341")
        equity_d, equity_c = get_period_amount("411")
        net_financing = (loan_c - loan_d) + (equity_c - equity_d)

        # Dividends paid (421 debit)
        div_d, _ = get_period_amount("421")
        net_financing -= div_d

        net_change = net_operating + net_investing + net_financing

        # Opening cash
        cash_q = Q(account_code__startswith="111") | Q(account_code__startswith="112")
        prior = VoucherLine.objects.filter(
            voucher__company=self.company,
            voucher__fiscal_year=fiscal_year,
            voucher__period__lt=period,
            voucher__status__gte=2,
        ).filter(cash_q)
        prior_totals = prior.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
        opening_cash = (prior_totals["d"] or Decimal("0")) - (prior_totals["c"] or Decimal("0"))

        return {
            "method": "indirect",
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
