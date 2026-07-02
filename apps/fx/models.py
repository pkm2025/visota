"""Multi-currency models.

ExchangeRate: per currency × date (VCB cross-rates).
FxRevaluationBatch: period-end revaluation (KT007) — N635/C111/C112.
"""

from django.conf import settings
from django.db import models

from apps.core.managers import CompanyOwnedModel


class Currency(models.Model):
    """ISO 4217 currency master."""

    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10, blank=True, default="")
    decimals = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "currency"

    def __str__(self):
        return f"{self.code} — {self.name}"


class ExchangeRate(CompanyOwnedModel):
    """Daily exchange rate vs company's local currency (VND)."""

    from_currency = models.CharField(max_length=3)  # e.g., USD
    to_currency = models.CharField(max_length=3, default="VND")
    rate_date = models.DateField(db_index=True)
    rate = models.DecimalField(max_digits=18, decimal_places=6)  # 1 USD = rate VND
    rate_type = models.CharField(max_length=20, default="VCB")  # VCB / SBV / accounting
    source = models.CharField(max_length=100, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "exchange_rate"
        unique_together = [("company", "from_currency", "to_currency", "rate_date", "rate_type")]
        ordering = ["-rate_date"]

    def __str__(self):
        return f"1 {self.from_currency} = {self.rate:,.2f} {self.to_currency} ({self.rate_date})"


class FxRevaluationBatch(CompanyOwnedModel):
    """Period-end FX revaluation: restate foreign-currency balances at closing rate."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Dự thảo"
        POSTED = "posted", "Đã ghi sổ"
        REVERSED = "reversed", "Đã đảo ngược"

    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    valuation_date = models.DateField()
    reference_rate = models.JSONField(default=dict, blank=True)
    # {"USD": 24500, "EUR": 26800, ...}

    gl_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fx_revaluations",
    )
    reversal_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fx_reversals",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True, default="")

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fx_revaluation_batch"
        unique_together = [("company", "period_year", "period_month")]

    def __str__(self):
        return f"FX {self.period_month:02d}/{self.period_year} [{self.status}]"
