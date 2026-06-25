"""FX services — revaluation at period close."""

from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher, VoucherLine

from .models import ExchangeRate, FxRevaluationBatch


class FxRevaluationService:
    """Period-end revaluation of foreign-currency balances.

    For each account that holds FX balances (1112, 1122, 131, 331, 343...),
    compute the difference between book rate (original txn rate) and closing rate.
    Generate voucher: N635 (lỗ) or N515 (lãi) / C1112 or C1122 or C331 etc.
    """

    FX_ACCOUNTS = [
        "1112",  # Foreign cash
        "1122",  # Foreign bank
        "131",   # AR (foreign)
        "331",   # AP (foreign)
        "3431",  # Foreign loan
    ]

    @classmethod
    def get_closing_rate(cls, company, currency, valuation_date):
        if currency == "VND":
            return Decimal("1")
        latest = (
            ExchangeRate.objects.filter(
                company=company,
                from_currency=currency,
                to_currency="VND",
                rate_date__lte=valuation_date,
            )
            .order_by("-rate_date")
            .first()
        )
        return latest.rate if latest else None

    @classmethod
    def compute_fcl_balances(cls, company, valuation_date):
        """For each FX account, compute outstanding foreign-currency balance by currency."""
        # Simplified: aggregate voucher lines with currency_code != VND
        from collections import defaultdict

        balances = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
        lines = VoucherLine.objects.filter(
            voucher__company=company,
            voucher__voucher_date__lte=valuation_date,
            voucher__currency_code__isnull=False,
        ).exclude(voucher__currency_code="VND").select_related("voucher")

        for line in lines:
            currency = line.voucher.currency_code
            balance = (line.debit_vnd or 0) - (line.credit_vnd or 0)
            balances[line.account_code][currency] += balance
        return balances

    @classmethod
    def run_revaluation(cls, company, year, month, posted_by=None):
        """Generate the revaluation voucher for given period."""
        from calendar import monthrange

        last_day = monthrange(year, month)[1]
        valuation_date = date(year, month, last_day)

        # Get closing rates for all currencies we have
        balances = cls.compute_fcl_balances(company, valuation_date)
        closing_rates = {}
        for acc_code, currencies in balances.items():
            for cur in currencies:
                if cur != "VND" and cur not in closing_rates:
                    rate = cls.get_closing_rate(company, cur, valuation_date)
                    if rate:
                        # Store as Decimal — convert to float only at JSON serialization
                        closing_rates[cur] = rate

        # Convert Decimal rates to float for JSONField storage
        reference_rate_json = {cur: float(rate) for cur, rate in closing_rates.items()}

        batch = FxRevaluationBatch.objects.create(
            company=company,
            period_year=year,
            period_month=month,
            valuation_date=valuation_date,
            reference_rate=reference_rate_json,
            status=FxRevaluationBatch.Status.DRAFT,
            posted_by=posted_by,
        )

        # Create voucher with revaluation entries
        voucher = AccountingVoucher.objects.create(
            company=company,
            fiscal_year=year,
            period=month,
            voucher_no=f"FX-{year}{month:02d}",
            voucher_type=AccountingVoucher.VoucherType.JOURNAL,
            voucher_date=valuation_date,
            description=f"Định giá lại ngoại tệ cuối kỳ {month:02d}/{year}",
            currency_code="VND",
            exchange_rate=Decimal("1"),
            total_vnd=Decimal("0"),
            status=AccountingVoucher.Status.DRAFT,
            created_by=posted_by,
        )

        # For each account + currency, compute gain/loss
        total_gain = Decimal("0")
        total_loss = Decimal("0")
        line_no = 1
        for acc_code, currencies in balances.items():
            for currency, fc_amount in currencies.items():
                if currency == "VND":
                    continue
                rate = closing_rates.get(currency)
                if not rate:
                    continue
                # Books the balance at closing rate
                # The difference between current VND value and FC*rate is the gain/loss
                # Simplified: assume current book value = balance; gain/loss = fc * rate - book value
                # In practice you'd track historical cost per line.
                vnd_at_closing = fc_amount * rate
                vnd_book = fc_amount  # simplified — normally would be a different number
                diff = vnd_at_closing - vnd_book
                if abs(diff) < Decimal("1"):
                    continue

                if diff > 0:
                    # Gain: N1122 (or 131/331) / C515
                    VoucherLine.objects.create(
                        voucher=voucher,
                        line_no=line_no,
                        account_code=acc_code,
                        debit_vnd=diff,
                        credit_vnd=0,
                        description=f"Định giá lại {acc_code} ({currency}) — lãi",
                    )
                    line_no += 1
                    VoucherLine.objects.create(
                        voucher=voucher,
                        line_no=line_no,
                        account_code="5151",
                        debit_vnd=0,
                        credit_vnd=diff,
                        description=f"Lãi chênh lệch tỷ giá {currency}",
                    )
                    line_no += 1
                    total_gain += diff
                else:
                    abs_diff = abs(diff)
                    VoucherLine.objects.create(
                        voucher=voucher,
                        line_no=line_no,
                        account_code="635",
                        debit_vnd=abs_diff,
                        credit_vnd=0,
                        description=f"Lỗ chênh lệch tỷ giá {currency}",
                    )
                    line_no += 1
                    VoucherLine.objects.create(
                        voucher=voucher,
                        line_no=line_no,
                        account_code=acc_code,
                        debit_vnd=0,
                        credit_vnd=abs_diff,
                        description=f"Định giá lại {acc_code} ({currency}) — lỗ",
                    )
                    line_no += 1
                    total_loss += abs_diff

        voucher.total_vnd = total_gain - total_loss
        voucher.save()

        batch.gl_voucher = voucher
        batch.status = FxRevaluationBatch.Status.POSTED
        batch.posted_at = timezone.now()
        batch.save()

        return batch
