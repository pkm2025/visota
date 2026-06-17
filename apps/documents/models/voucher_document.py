"""Voucher document model — printed forms + scanned uploads."""

import os

from django.db import models

from apps.core.managers import CompanyOwnedModel


class VoucherDocument(CompanyOwnedModel):
    """Document linked to a voucher: printed PDF or scanned upload."""

    class DocumentType(models.TextChoices):
        PRINT_TEMPLATE = "print_template", "In từ hệ thống"
        SCANNED_UPLOAD = "scanned_upload", "Scan/Upload"
        EXTERNAL = "external", "File ngoài"
        SIGNED_CONTRACT = "signed_contract", "Hợp đồng đã ký"

    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        PRINTED = "printed", "Đã in"
        SIGNED = "signed", "Đã ký"
        SCANNED = "scanned", "Đã scan"
        ARCHIVED = "archived", "Lưu trữ"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
    )
    voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )

    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    title = models.CharField(max_length=500)
    file = models.FileField(upload_to="documents/%Y/%m/", null=True, blank=True)
    file_type = models.CharField(max_length=10, blank=True, default="")
    file_size = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    notes = models.TextField(blank=True, default="")
    uploaded_by = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "voucher_document"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "voucher"]),
            models.Index(fields=["company", "document_type"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.document_type})"

    def save(self, *args, **kwargs):
        if self.file:
            try:
                self.file_size = self.file.size
                ext = os.path.splitext(self.file.name)[1].lower().lstrip(".")
                self.file_type = ext
            except Exception:
                # File may not yet be saved (e.g. SimpleUploadedFile before commit)
                pass
        super().save(*args, **kwargs)
