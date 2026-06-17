"""Balance Sheet (B01a-DN) generator."""

from decimal import Decimal

from apps.ledger.models import AccountPeriodBalance


class BalanceSheetService:
    """Generate Balance Sheet data from AccountPeriodBalance.

    Groups account balances by first-digit code prefix per TT133:
      - 1, 2 = Assets (Tài sản)
      - 3    = Liabilities (Nợ phải trả)
      - 4    = Equity (Vốn chủ sở hữu)
    Computes totals and verifies Assets = Liabilities + Equity.
    """

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        balances = AccountPeriodBalance.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
        ).select_related("company")

        asset_rows = []
        liability_rows = []
        equity_rows = []

        for b in balances.order_by("account_code"):
            closing = max(b.closing_debit or 0, b.closing_credit or 0)
            if closing == 0:
                continue

            first_digit = b.account_code[0] if b.account_code else "0"
            row = {"account_code": b.account_code, "amount": closing}

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
            "assets": {
                "rows": asset_rows,
                "total": total_assets,
            },
            "liabilities_equity": {
                "liabilities": liability_rows,
                "equity": equity_rows,
                "total_liabilities": total_liabilities,
                "total_equity": total_equity,
                "total": total_liabilities + total_equity,
            },
            "is_balanced": total_assets == total_liabilities + total_equity,
        }
