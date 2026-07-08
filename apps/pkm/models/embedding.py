"""Embedding model for vector storage in MariaDB.

NOTE: The ``embedding`` column is a MariaDB-native ``VECTOR(1536)`` type that
Django's ORM cannot express natively. We use a custom ``VectorField`` that
returns ``VECTOR(1536)`` as its DB type, so Django's migration system manages
the column correctly. All reads and writes of the vector itself go through
raw SQL via the ``vector_store`` service (using ``VEC_FromText()``).
"""

from django.db import models

from apps.core.managers import CompanyOwnedModel
from apps.pkm.fields import VectorField


class Embedding(CompanyOwnedModel):
    """Vector embedding for a DocumentChunk, stored in MariaDB VECTOR(1536).

    The ``embedding`` column is a native VECTOR(1536) type. Values must be
    stored via raw SQL using ``VEC_FromText()`` (see vector_store service).
    """

    chunk = models.ForeignKey(
        "pkm.DocumentChunk",
        on_delete=models.CASCADE,
        related_name="embeddings",
    )
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="pkm_embeddings",
    )
    content = models.TextField(
        blank=True,
        default="",
        help_text="Cached text content that was embedded",
    )
    model_name = models.CharField(
        max_length=100,
        help_text="Name of the embedding model used (e.g. text-embedding-3-small)",
    )
    embedding = VectorField(
        dimensions=1536,
        help_text="1536-dim vector (stored via VEC_FromText raw SQL)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = "pkm_embedding"
        indexes = [
            models.Index(fields=["user", "company"]),
            models.Index(fields=["chunk"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Embedding(chunk={self.chunk_id}, model={self.model_name})"
