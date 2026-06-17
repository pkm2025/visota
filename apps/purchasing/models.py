"""Purchase invoice models."""
from django.db import models
from apps.core.managers import CompanyOwnedModel


class PurchaseInvoice(CompanyOwnedModel):
    """Purchase invoice — hóa đơn mua hàng."""

    class InvoiceType(models.TextChoices):
        GOODS = 'goods', 'Hàng hóa'
        SERVICE = 'service', 'Dịch vụ'
        IMPORT = 'import', 'Nhập khẩu'

    class PaymentStatus(models.IntegerChoices):
        UNPAID = 0, 'Chưa thanh toán'
        PARTIAL = 1, 'Thanh toán một phần'
        PAID = 2, 'Đã thanh toán'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='purchase_invoices',
        db_index=True,
    )
    invoice_no = models.CharField(max_length=50)
    invoice_date = models.DateField()
    invoice_type = models.CharField(
        max_length=20, choices=InvoiceType.choices, default=InvoiceType.GOODS,
    )
    vendor = models.ForeignKey(
        'master_data.Vendor', on_delete=models.PROTECT, related_name='invoices',
    )
    purchaser_code = models.CharField(max_length=50, blank=True, default='')
    currency_code = models.CharField(max_length=3, default='VND')
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=6, default=1)

    subtotal = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    discount_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    vat_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    paid_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    payment_status = models.PositiveSmallIntegerField(
        choices=PaymentStatus.choices, default=PaymentStatus.UNPAID,
    )

    gl_voucher = models.ForeignKey(
        'ledger.AccountingVoucher', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='purchase_invoices',
    )

    status = models.PositiveSmallIntegerField(default=2,
        help_text='0=Draft, 1=Subsidiary, 2=Ledger, 3=Locked')

    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'purchase_invoice'
        unique_together = [('company', 'invoice_type', 'invoice_no')]
        ordering = ['-invoice_date', '-id']
        indexes = [
            models.Index(fields=['company', 'invoice_date']),
            models.Index(fields=['vendor', 'invoice_date']),
        ]

    def __str__(self):
        return f'{self.invoice_no} ({self.invoice_date})'


class PurchaseInvoiceLine(models.Model):
    """Purchase invoice line item."""

    invoice = models.ForeignKey(
        PurchaseInvoice, on_delete=models.CASCADE, related_name='lines',
    )
    line_no = models.PositiveSmallIntegerField()
    product = models.ForeignKey(
        'master_data.Product', on_delete=models.PROTECT, related_name='purchase_lines',
    )
    description = models.CharField(max_length=500, blank=True, default='')
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_id = models.CharField(max_length=20, default='CAI')
    unit_price = models.DecimalField(max_digits=20, decimal_places=4)
    discount_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    discount_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    amount_before_vat = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    vat_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.10)
    vat_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    inventory_account = models.CharField(max_length=20, default='156')
    vat_account = models.CharField(max_length=20, default='1331')
    cost_account = models.CharField(max_length=20, default='632')

    class Meta:
        db_table = 'purchase_invoice_line'
        unique_together = [('invoice', 'line_no')]
        ordering = ['line_no']

    def __str__(self):
        return f'{self.invoice.invoice_no} line {self.line_no}'
