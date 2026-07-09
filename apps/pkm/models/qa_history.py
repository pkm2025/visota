"""QAHistory model for storing Q&A interactions.

Each Q&A interaction is persisted so the user can review past questions and
answers. Records are scoped per-user and per-company for isolation.
"""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class QAHistory(CompanyOwnedModel):
    """A single Q&A interaction with the RAG-powered assistant.

    Stores the user's question, the generated answer, and a JSON-serialisable
    list of source references (chunk/document metadata) used to build the
    answer context.
    """

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="pkm_qa_history",
    )
    question = models.TextField(help_text="The user's question")
    answer = models.TextField(blank=True, default="", help_text="The generated answer")
    sources = models.JSONField(
        default=list,
        blank=True,
        help_text="List of source references (chunk_id, document_title, preview)",
    )
    context_used = models.JSONField(
        default=list,
        blank=True,
        help_text="List of context chunks/notes used to build the prompt",
    )
    interaction_context = models.TextField(
        blank=True,
        default="",
        help_text="Summary of the user's recent activity (from interaction_service)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = "pkm_qa_history"
        indexes = [
            models.Index(fields=["user", "company"]),
            models.Index(fields=["user", "company", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"QA({self.user.username}): {self.question[:50]}"
