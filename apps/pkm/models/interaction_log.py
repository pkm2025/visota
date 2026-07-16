"""UserInteractionLog model for passive user behaviour capture.

Each significant user action (page view, search, create operations) is logged
so that the smart-context service can build a recent-activity summary for
Q&A prompts. Records are scoped per-user and per-company for isolation.
"""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class UserInteractionLog(CompanyOwnedModel):
    """A single captured user interaction within the Visota ERP.

    Stores the interaction type, the module it occurred in, an optional
    reference to the affected entity, and a free-form JSON metadata payload
    (e.g. search query, page URL, or create payload summary).
    """

    class InteractionType(models.TextChoices):
        PAGE_VIEW = "page_view", "Page View"
        SEARCH = "search", "Search"
        NOTE_CREATE = "note_create", "Note Create"
        DOCUMENT_CREATE = "document_create", "Document Create"
        VOUCHER_CREATE = "voucher_create", "Voucher Create"
        INVOICE_CREATE = "invoice_create", "Invoice Create"
        DNSN_VOUCHER_CREATE = "dnsn_voucher_create", "DNSN Voucher Create"
        PERIOD_CLOSE = "period_close", "Period Close"
        EINVOICE_ISSUE = "einvoice_issue", "E-Invoice Issue"

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="pkm_interaction_logs",
        null=True,
        blank=True,
    )
    interaction_type = models.CharField(
        max_length=30,
        choices=InteractionType.choices,
    )
    module = models.CharField(
        max_length=50,
        help_text="Which Visota module the interaction occurred in (e.g. 'ledger', 'pkm')",
    )
    entity_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional entity type (e.g. 'note', 'document', 'voucher')",
    )
    entity_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional entity identifier as a string",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Free-form JSON metadata (search query, page URL, etc.)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = "pkm_user_interaction_log"
        indexes = [
            models.Index(fields=["user", "company"]),
            models.Index(fields=["user", "company", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        username = self.user.username if self.user_id else "system"
        return f"{username} - {self.interaction_type} ({self.module})"
