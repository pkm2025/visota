"""PKMDocument model for uploaded files in the RAG pipeline."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class PKMDocument(CompanyOwnedModel):
    """Source document uploaded by a user for RAG processing.

    Each document belongs to a specific user within a company (multi-tenant).
    The file is stored under ``pkm/docs/%Y/%m/`` and processing status is
    tracked through pending -> processing -> processed/failed.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="pkm_documents",
    )
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to="pkm/docs/%Y/%m/",
        help_text="Uploaded document file for RAG processing",
    )
    file_type = models.CharField(
        max_length=20,
        help_text="File extension/type (e.g. pdf, docx, txt, md)",
    )
    file_size = models.PositiveIntegerField(
        default=0,
        help_text="File size in bytes",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    checksum = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 checksum for deduplication",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error details if processing failed",
    )
    is_system = models.BooleanField(
        default=False,
        help_text=(
            "If True, this document is a system-seeded regulation or reference "
            "shared across tenants (e.g. TT58, PIT rates, TT133 overview)."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "pkm_document"
        indexes = [
            models.Index(fields=["user", "company"]),
            models.Index(fields=["user", "company", "status"]),
            models.Index(fields=["checksum"]),
            models.Index(fields=["is_system"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
