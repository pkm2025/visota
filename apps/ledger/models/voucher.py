"""Accounting voucher (phiếu kế toán) and bút toán (voucher line) models."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class AccountingVoucher(CompanyOwnedModel):
    """Accounting voucher (phiếu kế toán) — header for a set of bút toán."""

    class VoucherType(models.TextChoices):
        JOURNAL = "journal", "Phiếu kế toán"
        CASH_RECEIPT = "cash_receipt", "Phiếu thu"
        CASH_PAYMENT = "cash_payment", "Phiếu chi"
        SALES_INVOICE = "sales_invoice", "Hóa đơn bán"
        PURCHASE_INVOICE = "purchase_invoice", "Phiếu nhập mua"
        STOCK_VOUCHER = "stock_voucher", "Phiếu nhập xuất"
        DEPRECIATION = "depreciation", "Khấu hao"
        ALLOCATION = "allocation", "Phân bổ"
        CLOSING = "closing", "Kết chuyển"

    class Status(models.IntegerChoices):
        DRAFT = 0, "Lưu tạm"
        SUBSIDIARY = 1, "Ghi sổ phụ"
        LEDGER = 2, "Ghi sổ cái"
        LOCKED = 3, "Đã khóa"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="vouchers",
        db_index=True,
    )
    fiscal_year = models.SmallIntegerField()
    period = models.PositiveSmallIntegerField()
    voucher_no = models.CharField(max_length=50)
    voucher_type = models.CharField(max_length=30, choices=VoucherType.choices)
    voucher_date = models.DateField()
    posting_date = models.DateField(null=True, blank=True)
    book_code = models.CharField(max_length=20, blank=True)
    status = models.PositiveSmallIntegerField(
        choices=Status.choices,
        default=Status.LEDGER,
    )
    currency_code = models.CharField(max_length=3, default="VND")
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=6, default=1)
    total_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_vnd = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=20, default="manual")
    source_reference_id = models.BigIntegerField(null=True, blank=True)
    is_reversed = models.BooleanField(default=False)
    reversal_voucher = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversals",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vouchers_created",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vouchers_updated",
    )

    objects = models.Manager()

    class Meta:
        db_table = "accounting_voucher"
        unique_together = [
            ("company", "fiscal_year", "voucher_type", "voucher_no"),
        ]
        indexes = [
            models.Index(fields=["company", "voucher_date"]),
            models.Index(fields=["company", "fiscal_year", "period", "status"]),
            models.Index(fields=["company", "voucher_type", "voucher_date"]),
        ]
        ordering = ["-voucher_date", "-id"]

    def __str__(self):
        return f"{self.voucher_no} ({self.voucher_date})"

    @property
    def is_posted(self):
        return self.status >= self.Status.LEDGER

    @property
    def is_locked(self):
        return self.status == self.Status.LOCKED


class VoucherLine(models.Model):
    """Bút toán — single debit or credit entry in a voucher."""

    class ObjectType(models.TextChoices):
        NONE = "", "—"
        CUSTOMER = "customer", "Khách hàng"
        VENDOR = "vendor", "Nhà cung cấp"
        EMPLOYEE = "employee", "Nhân viên"
        BANK = "bank", "Ngân hàng"
        OTHER = "other", "Khác"

    voucher = models.ForeignKey(
        AccountingVoucher,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_no = models.PositiveSmallIntegerField()
    account_code = models.CharField(max_length=20)
    object_type = models.CharField(
        max_length=20,
        choices=ObjectType.choices,
        blank=True,
        default="",
    )
    object_code = models.CharField(max_length=50, blank=True, default="")
    object_name = models.CharField(max_length=255, blank=True, default="")
    debit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    credit_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    debit_vnd = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    credit_vnd = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    description = models.TextField(blank=True, default="")
    cost_center_code = models.CharField(max_length=50, blank=True, default="")
    project_code = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "voucher_line"
        unique_together = [("voucher", "line_no")]
        indexes = [
            models.Index(fields=["account_code"]),
            models.Index(fields=["object_type", "object_code"]),
        ]
        ordering = ["line_no"]

    def __str__(self):
        side = "Nợ" if self.debit_vnd > 0 else "Có"
        amount = self.debit_vnd or self.credit_vnd
        return f"{self.line_no}. {self.account_code} {side} {amount}"
