"""Account balance projections — pre-computed for fast reporting."""

from django.db import models


class AccountPeriodBalance(models.Model):
    """Period balance per account (+ optional object).

    Updated by VoucherPostingService on post/unpost.
    Rebuildable from voucher_line table.
    """

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="balances",
        db_index=True,
    )
    fiscal_year = models.SmallIntegerField()
    period = models.PositiveSmallIntegerField()
    account_code = models.CharField(max_length=20)
    object_type = models.CharField(max_length=20, blank=True, default="")
    object_code = models.CharField(max_length=50, blank=True, default="")

    opening_debit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    opening_credit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_debit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_credit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_debit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_credit = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    opening_debit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    opening_credit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_debit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_credit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_debit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_credit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    last_transaction_date = models.DateField(null=True, blank=True)
    transaction_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "account_period_balance"
        unique_together = [
            ("company", "fiscal_year", "period", "account_code", "object_type", "object_code"),
        ]
        indexes = [
            models.Index(fields=["company", "fiscal_year", "period"]),
            models.Index(fields=["account_code"]),
            models.Index(fields=["object_type", "object_code"]),
        ]

    def __str__(self):
        return f"{self.account_code} P{self.period}/{self.fiscal_year}"

    def recalculate_closing(self):
        """Compute closing from opening + period. Side with larger value wins."""
        d = self.opening_debit + self.period_debit
        c = self.opening_credit + self.period_credit
        if d >= c:
            self.closing_debit = d - c
            self.closing_credit = 0
        else:
            self.closing_credit = c - d
            self.closing_debit = 0
