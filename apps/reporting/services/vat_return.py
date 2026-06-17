"""VAT Return (01/GTGT) generator."""

from decimal import Decimal

from apps.ledger.models import AccountPeriodBalance


class VATReturnService:
    """Generate VAT return data from AccountPeriodBalance.

    Reads from the posted vouchers:
      - VAT output (TK 33311 credit) = total output VAT collected from sales
      - VAT input  (TK 1331  debit) = total input VAT paid to vendors

    VAT payable = output - input  (when output > input)
    VAT credit  = input  - output (when input  > output)
    """

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        balances = AccountPeriodBalance.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
        )

        vat_output = Decimal("0")
        vat_input = Decimal("0")

        for b in balances:
            code = b.account_code or ""
            if code.startswith("33311"):
                vat_output += b.period_credit or 0
            elif code.startswith("1331"):
                vat_input += b.period_debit or 0

        if vat_output > vat_input:
            vat_payable = vat_output - vat_input
            vat_credit = Decimal("0")
            is_payable = True
        else:
            vat_payable = Decimal("0")
            vat_credit = vat_input - vat_output
            is_payable = False

        return {
            "fiscal_year": fiscal_year,
            "period": period,
            "vat_output": vat_output,
            "vat_input_credit": vat_input,
            "vat_payable": vat_payable,
            "vat_credit": vat_credit,
            "is_payable": is_payable,
        }
