"""InputInvoice model — hóa đơn đầu vào từ NCC."""

from django.conf import settings
from django.db import models

from apps.core.managers import CompanyOwnedModel


class InputInvoice(CompanyOwnedModel):
    """Hóa đơn đầu vào — received from vendor, processed, then matched to a PI."""

    class ExtractionStatus(models.TextChoices):
        PENDING = "pending", "Chờ xử lý"
        EXTRACTED = "extracted", "Đã trích xuất"
        MATCHED = "matched", "Đã khớp"
        EXCLUDED = "excluded", "Loại trừ"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="input_invoices",
        db_index=True,
    )
    invoice_no = models.CharField(max_length=50, blank=True, default="")
    invoice_date = models.DateField(null=True, blank=True)

    # Seller (vendor) info — extracted
    seller_tax_code = models.CharField(max_length=20, blank=True, default="", db_index=True)
    seller_name = models.CharField(max_length=255, blank=True, default="")
    seller_address = models.TextField(blank=True, default="")

    # Amounts — extracted
    amount_before_vat = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    vat_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    vat_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency_code = models.CharField(max_length=3, default="VND")

    # Linking to PurchaseInvoice once matched
    purchase_invoice = models.ForeignKey(
        "purchasing.PurchaseInvoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="input_sources",
    )

    # Raw uploaded content
    scanned_file = models.FileField(upload_to="input_invoices/", null=True, blank=True)
    einvoice_xml = models.TextField(blank=True, default="")

    # Processing state
    extraction_status = models.CharField(
        max_length=20,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.PENDING,
        db_index=True,
    )
    extracted_data = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_input_invoices",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "input_invoice"
        verbose_name = "Hóa đơn đầu vào"
        verbose_name_plural = "Hóa đơn đầu vào"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["company", "extraction_status"]),
            models.Index(fields=["seller_tax_code"]),
        ]

    def __str__(self):
        return f"InputInvoice({self.invoice_no or 'pending'}) [{self.extraction_status}]"
