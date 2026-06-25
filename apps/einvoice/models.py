"""E-invoice models per TT78/2021/TT-BTC.

EInvoiceConfig: per-company provider settings (MISA, VNPT, eHoadon, BKAV, manual).
EInvoice: a single issued invoice with XML/JSON/PDF storage + transaction code.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.core.managers import CompanyOwnedModel


class EInvoiceProvider(models.TextChoices):
    MANUAL = "manual", "Ký thủ công (file PDF)"
    MISA = "misa", "MISA"
    VNPT = "vnpt", "VNPT-Invoice"
    EHOADON = "ehoadon", "eHoadon (VNPT)"
    BKAV = "bkav", "BKAV"
    VIETTEL = "viettel", "Viettel-Invoice"


class EInvoiceConfig(CompanyOwnedModel):
    """Per-company e-invoice provider configuration."""

    provider = models.CharField(
        max_length=20,
        choices=EInvoiceProvider.choices,
        default=EInvoiceProvider.MANUAL,
    )
    # Tax authority registration
    pattern = models.CharField(max_length=50, default="1C26T")  # 1C22T, 1C26T etc
    serial = models.CharField(max_length=20, default="")  # AA/26E etc
    form_symbol = models.CharField(max_length=10, default="01GTKT")  # 01GTKT-DFS-Form
    issue_place = models.CharField(max_length=100, blank=True, default="")

    # API credentials (encrypted in real prod)
    api_url = models.CharField(max_length=500, blank=True, default="")
    api_username = models.CharField(max_length=100, blank=True, default="")
    api_password = models.CharField(max_length=200, blank=True, default="")
    api_token = models.CharField(max_length=500, blank=True, default="")

    # Default for the company's tax branch (MST + donvi)
    tax_branch_code = models.CharField(max_length=50, blank=True, default="")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "einvoice_config"
        verbose_name = "Cấu hình hóa đơn điện tử"

    def __str__(self):
        return f"{self.company.name} — {self.get_provider_display()} ({self.pattern})"


class EInvoice(CompanyOwnedModel):
    """A single issued e-invoice with files + status tracking."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Dự thảo"
        ISSUED = "issued", "Đã phát hành"
        ADJUSTED = "adjusted", "Đã điều chỉnh"
        REPLACED = "replaced", "Đã thay thế"
        CANCELLED = "cancelled", "Đã hủy"

    # Key identification
    invoice_no = models.CharField(max_length=50, blank=True, default="")
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False)
    pattern = models.CharField(max_length=50, default="1C26T")
    serial = models.CharField(max_length=20, default="")

    # Link to SalesInvoice (1-1 optional)
    sales_invoice = models.ForeignKey(
        "sales.SalesInvoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="einvoices",
    )

    # Parties (snapshot — denormalized from sales invoice for resilience)
    buyer_name = models.CharField(max_length=255, blank=True, default="")
    buyer_tax_code = models.CharField(max_length=20, blank=True, default="")
    buyer_address = models.TextField(blank=True, default="")
    buyer_bank_account = models.CharField(max_length=50, blank=True, default="")
    seller_name = models.CharField(max_length=255, blank=True, default="")
    seller_tax_code = models.CharField(max_length=20, blank=True, default="")
    seller_address = models.TextField(blank=True, default="")

    # Money
    subtotal = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    vat_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.10)
    vat_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_in_words = models.TextField(blank=True, default="")

    # Notes
    payment_method = models.CharField(max_length=100, blank=True, default="")
    note = models.TextField(blank=True, default="")
    # ISO 8601 of issue (per TT78 spec)
    issue_date = models.DateTimeField(null=True, blank=True)

    # Files — XML (per TT78 schema), JSON (provider-specific), signed PDF
    xml_file = models.FileField(upload_to="einvoice/xml/", null=True, blank=True)
    json_file = models.FileField(upload_to="einvoice/json/", null=True, blank=True)
    pdf_file = models.FileField(upload_to="einvoice/pdf/", null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    # Adjustment reference (if this is an adjusting/replacing invoice)
    replaces_invoice = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaced_by",
    )
    adjustment_type = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="adjust=Điều chỉnh, replace=Thay thế, cancel=Hủy",
    )

    # Provider response
    provider_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="einvoices_issued",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "einvoice"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "issue_date"]),
            models.Index(fields=["sales_invoice"]),
        ]

    def __str__(self):
        return f"{self.invoice_no or self.transaction_id} [{self.status}]"


class EInvoiceReportBatch(CompanyOwnedModel):
    """Monthly BC01 / BC26 report submission to tax authority."""

    class ReportType(models.TextChoices):
        BC01 = "bc01", "BC01 — Báo cáo tình hình sử dụng HĐĐT"
        BC26 = "bc26", "BC26 — Báo cáo HĐĐT định kỳ"
        TB04 = "tb04", "TB04 — Thông báo phát hành"

    report_type = models.CharField(max_length=10, choices=ReportType.choices)
    period_month = models.PositiveSmallIntegerField()
    period_year = models.PositiveSmallIntegerField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    xml_file = models.FileField(upload_to="einvoice/reports/", null=True, blank=True)
    invoice_count = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    status = models.CharField(max_length=20, default="pending")
    note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "einvoice_report_batch"
        ordering = ["-period_year", "-period_month"]

    def __str__(self):
        return f"{self.report_type.upper()} {self.period_month:02d}/{self.period_year}"
