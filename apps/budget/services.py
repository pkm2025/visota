"""Budget + Cash flow services."""

from datetime import date
from decimal import Decimal

from django.db.models import Sum

from .models import Budget, BudgetLine, CashFlowProjection


class BudgetVarianceService:
    """Compute actuals vs plan and refresh variance analysis."""

    @classmethod
    def refresh_actuals(cls, budget):
        """Pull actual amounts from ledger (AccountPeriodBalance) for each line."""
        from apps.ledger.models import AccountPeriodBalance

        for line in budget.lines.all():
            # Map account_group to a range of account codes
            range_map = {
                "revenue": ("511", "51"),  # 511x
                "cogs": ("632", "63"),  # 632
                "opex": ("641", "64"),  # 641-642
                "salaries": ("6221", "62"),  # 622
                "marketing": ("6411", "6411"),  # marketing subset
                "capex": ("211", "21"),  # TSCĐ
            }
            prefix, _ = range_map.get(line.account_group, ("", ""))
            if not prefix:
                continue

            qs = AccountPeriodBalance.objects.filter(
                company=budget.company,
                fiscal_year=budget.fiscal_year,
                period=line.period_month,
                account_code__startswith=prefix,
            )
            if line.direction == "debit":
                # Expense
                total = qs.aggregate(s=Sum("period_debit"))["s"] or Decimal("0")
            else:
                # Revenue
                total = qs.aggregate(s=Sum("period_credit"))["s"] or Decimal("0")
            line.actual_amount = total
            line.save(update_fields=["actual_amount"])

    @classmethod
    def generate_default_template(cls, company, fiscal_year):
        """Create a default budget with 12 monthly periods × N account groups."""
        budget, created = Budget.objects.get_or_create(
            company=company,
            fiscal_year=fiscal_year,
            scenario=Budget.Scenario.PLANNED,
            defaults={"name": f"Ngân sách {fiscal_year}"},
        )
        if not created:
            return budget

        GROUPS = [
            ("revenue", "credit"),
            ("cogs", "debit"),
            ("opex", "debit"),
            ("salaries", "debit"),
            ("marketing", "debit"),
        ]
        for month in range(1, 13):
            for grp, direction in GROUPS:
                BudgetLine.objects.create(
                    budget=budget,
                    period_month=month,
                    account_group=grp,
                    direction=direction,
                )
        return budget


class CashFlowService:
    """Generate cash flow projections from AR/AP due dates."""

    @classmethod
    def generate_for_period(cls, company, year, month):
        """Compute expected inflow/outflow for given month based on outstanding AR/AP."""
        from datetime import timedelta

        from apps.ledger.models import VoucherLine

        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year, 12, 31)
        else:
            period_end = date(year, month + 1, 1) - timedelta(days=1)

        # AR outstanding: sum of debit_vnd - credit_vnd on 131 lines
        # (For demo, we just sum period_debit on account 131 for this month + outstanding from prev)
        ar_qs = VoucherLine.objects.filter(
            voucher__company=company,
            account_code__startswith="131",
            voucher__voucher_date__lte=period_end,
        )
        ar_total = sum(
            ((l.debit_vnd or 0) - (l.credit_vnd or 0) for l in ar_qs),
            Decimal("0"),
        )
        # Assume 60% of outstanding AR gets collected this month (rough heuristic)
        expected_ar = ar_total * Decimal("0.6") if ar_total > 0 else Decimal("0")

        # AP outstanding: sum of credit_vnd - debit_vnd on 331
        ap_qs = VoucherLine.objects.filter(
            voucher__company=company,
            account_code__startswith="331",
            voucher__voucher_date__lte=period_end,
        )
        ap_total = sum(
            ((l.credit_vnd or 0) - (l.debit_vnd or 0) for l in ap_qs),
            Decimal("0"),
        )
        expected_ap = ap_total * Decimal("0.7") if ap_total > 0 else Decimal("0")

        # Payroll estimate from 334 lines this month
        payroll_qs = VoucherLine.objects.filter(
            voucher__company=company,
            account_code__startswith="334",
            voucher__voucher_date__range=(period_start, period_end),
        )
        expected_payroll = sum((l.debit_vnd or 0 for l in payroll_qs), Decimal("0"))

        # Tax estimate from 333 lines this month
        tax_qs = VoucherLine.objects.filter(
            voucher__company=company,
            account_code__startswith="333",
            voucher__voucher_date__range=(period_start, period_end),
        )
        expected_tax = sum((l.debit_vnd or 0 for l in tax_qs), Decimal("0"))

        # Cash on hand start of month (TK 1111 + 1121 debit balance up to start)
        cash_qs = VoucherLine.objects.filter(
            voucher__company=company,
            account_code__in=["1111", "1121"],
            voucher__voucher_date__lt=period_start,
        )
        opening = sum(
            ((l.debit_vnd or 0) - (l.credit_vnd or 0) for l in cash_qs),
            Decimal("0"),
        )

        proj, _ = CashFlowProjection.objects.update_or_create(
            company=company,
            period_year=year,
            period_month=month,
            defaults={
                "expected_ar_collection": expected_ar,
                "expected_ap_payment": expected_ap,
                "expected_payroll": expected_payroll,
                "expected_tax": expected_tax,
                "opening_balance": opening,
            },
        )
        return proj
