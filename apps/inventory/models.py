"""Stock voucher + ledger models."""

from decimal import Decimal

from django.db import models

from apps.core.managers import CompanyOwnedModel


class StockVoucher(CompanyOwnedModel):
    """Stock movement voucher — receipt/issue/transfer."""

    class VoucherType(models.TextChoices):
        RECEIPT = "receipt", "Phiếu nhập"
        ISSUE = "issue", "Phiếu xuất"
        TRANSFER = "transfer", "Phiếu chuyển"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="stock_vouchers",
        db_index=True,
    )
    voucher_type = models.CharField(max_length=20, choices=VoucherType.choices)
    voucher_no = models.CharField(max_length=50)
    voucher_date = models.DateField()

    warehouse = models.ForeignKey(
        "master_data.Warehouse",
        on_delete=models.PROTECT,
        related_name="stock_vouchers",
        help_text=("Source warehouse for receipt/issue; from-warehouse for transfer."),
    )
    to_warehouse = models.ForeignKey(
        "master_data.Warehouse",
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        null=True,
        blank=True,
        help_text="Destination warehouse for transfer only.",
    )

    reason = models.CharField(max_length=500, blank=True, default="")
    status = models.PositiveSmallIntegerField(default=2)

    gl_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_vouchers",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "stock_voucher"
        unique_together = [("company", "voucher_type", "voucher_no")]
        ordering = ["-voucher_date", "-id"]

    def __str__(self):
        return f"{self.voucher_no} ({self.voucher_type})"


class StockVoucherLine(models.Model):
    """Line in a stock voucher."""

    voucher = models.ForeignKey(
        StockVoucher,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_no = models.PositiveSmallIntegerField()
    product = models.ForeignKey(
        "master_data.Product",
        on_delete=models.PROTECT,
        related_name="stock_lines",
    )
    description = models.CharField(max_length=500, blank=True, default="")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_id = models.CharField(max_length=20, default="CAI")
    unit_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    class Meta:
        db_table = "stock_voucher_line"
        unique_together = [("voucher", "line_no")]
        ordering = ["line_no"]

    def __str__(self):
        return f"{self.voucher.voucher_no} line {self.line_no}"


class StockLedger(models.Model):
    """Current stock level per product + warehouse. Single row per combo."""

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="stock_ledger",
        db_index=True,
    )
    product = models.ForeignKey(
        "master_data.Product",
        on_delete=models.CASCADE,
        related_name="stock_ledger",
    )
    warehouse = models.ForeignKey(
        "master_data.Warehouse",
        on_delete=models.CASCADE,
        related_name="stock_ledger",
    )

    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    avg_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    last_transaction_date = models.DateField(null=True, blank=True)
    transaction_count = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "stock_ledger"
        unique_together = [("company", "product", "warehouse")]
        indexes = [
            models.Index(fields=["product", "warehouse"]),
        ]

    def __str__(self):
        return f"{self.product.code} @ {self.warehouse.code}: {self.quantity}"

    def recalculate_avg_cost(self):
        """Update avg_cost from quantity + amount."""
        if self.quantity != 0:
            self.avg_cost = (self.amount / self.quantity).quantize(Decimal("0.0001"))
        else:
            self.avg_cost = 0
