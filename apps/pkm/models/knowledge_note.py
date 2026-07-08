"""KnowledgeNote model for personal notes with markdown content and tags."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class KnowledgeNote(CompanyOwnedModel):
    """Personal knowledge note with markdown content and optional tags.

    Each note belongs to a specific user within a company (multi-tenant).
    Notes support markdown rendering, pinning, and role-based context tagging.
    """

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="pkm_notes",
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, default="", help_text="Markdown content")
    tags = models.ManyToManyField(
        "pkm.Tag",
        blank=True,
        related_name="notes",
    )
    role_context = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional role tag for context filtering (e.g. 'accountant')",
    )
    is_pinned = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "pkm_knowledge_note"
        indexes = [
            models.Index(fields=["user", "company"]),
            models.Index(fields=["user", "company", "is_pinned"]),
        ]
        ordering = ["-is_pinned", "-updated_at"]

    def __str__(self) -> str:
        return self.title
