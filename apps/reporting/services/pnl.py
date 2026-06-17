"""P&L Statement (B02a-DN) generator."""

from decimal import Decimal

from apps.ledger.models import AccountPeriodBalance


class PnLService:
    """Generate P&L data from AccountPeriodBalance period movements.

    Account mapping per TT133:
      - 5xx  → Revenue (515 financial income is a 5xx; handled below as financial income)
      - 632  → COGS (Giá vốn hàng bán)
      - 641  → Selling expense (Chi phí bán hàng)
      - 642  → Admin expense (Chi phí quản lý DN)
      - 515  → Financial income (Doanh thu hoạt động tài chính)
      - 635  → Financial expense (Chi phí tài chính)
      - 711  → Other income (Thu nhập khác)
      - 811  → Other expense (Chi phí khác)
      - 821  → PIT (Chi phí thuế TNDN)
    """

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        balances = AccountPeriodBalance.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
        )

        revenue = Decimal("0")
        cogs = Decimal("0")
        selling_expense = Decimal("0")
        admin_expense = Decimal("0")
        financial_income = Decimal("0")
        financial_expense = Decimal("0")
        other_income = Decimal("0")
        other_expense = Decimal("0")
        pit_expense = Decimal("0")

        for b in balances:
            code = b.account_code or ""
            period_d = b.period_debit or 0
            period_c = b.period_credit or 0

            # Financial income: 515 (subset of 5xx — check first)
            if code.startswith("515"):
                financial_income += period_c - period_d
            # Revenue: 5xx except 515 (511, 512, etc.)
            elif code.startswith("5"):
                revenue += period_c - period_d
            # COGS: 632
            elif code.startswith("632"):
                cogs += period_d - period_c
            # Selling: 641
            elif code.startswith("641"):
                selling_expense += period_d - period_c
            # Admin: 642
            elif code.startswith("642"):
                admin_expense += period_d - period_c
            # Financial expense: 635
            elif code.startswith("635"):
                financial_expense += period_d - period_c
            # Other income: 711
            elif code.startswith("711"):
                other_income += period_c - period_d
            # Other expense: 811
            elif code.startswith("811"):
                other_expense += period_d - period_c
            # PIT: 821
            elif code.startswith("821"):
                pit_expense += period_d - period_c

        revenue_net = revenue
        gross_profit = revenue_net - cogs
        operating_profit = (
            gross_profit
            + financial_income
            - financial_expense
            - selling_expense
            - admin_expense
        )
        other_profit = other_income - other_expense
        profit_before_tax = operating_profit + other_profit
        profit_after_tax = profit_before_tax - pit_expense

        return {
            "fiscal_year": fiscal_year,
            "period": period,
            "revenue": revenue,
            "revenue_net": revenue_net,
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
