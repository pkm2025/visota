"""Universal attachment model — links a file to any entity via content_type."""

import contextlib
import os

from django.db import models


class Attachment(models.Model):
    """Universal file attachment — can link to any entity via content_type."""

    class AttachmentType(models.TextChoices):
        SPECIFICATION = "specification", "Thông số kỹ thuật"
        CONTRACT_SCAN = "contract_scan", "Hợp đồng scan"
        PROPOSAL = "proposal", "Báo giá/Proposal"
        REPORT = "report", "Báo cáo"
        CERTIFICATE = "certificate", "Chứng chỉ"
        PHOTO = "photo", "Ảnh/Hình"
        DELIVERABLE = "deliverable", "Sản phẩm bàn giao"
        SLA = "sla", "Thỏa thuận SLA"
        INVOICE_SCAN = "invoice_scan", "Hóa đơn scan"
        RECEIPT = "receipt", "Biên lai"
        OTHER = "other", "Khác"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Đã tải lên"
        VERIFIED = "verified", "Đã kiểm tra"
        ARCHIVED = "archived", "Lưu trữ"

    # Generic link using content_type
    content_type = models.ForeignKey("contenttypes.ContentType", on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()

    # File info
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    file = models.FileField(upload_to="attachments/%Y/%m/")
    file_type = models.CharField(max_length=10, blank=True, default="")
    file_size = models.BigIntegerField(default=0)

    # Metadata
    attachment_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
        default=AttachmentType.OTHER,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)

    # Ownership
    uploaded_by = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_attachments",
    )
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "attachment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.file_type})"

    def save(self, *args, **kwargs):
        if self.file:
            with contextlib.suppress(Exception):
                self.file_size = self.file.size
            ext = os.path.splitext(self.file.name)[1].lower().lstrip(".")
            if ext:
                self.file_type = ext
        super().save(*args, **kwargs)
