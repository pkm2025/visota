"""DocumentChunk model for text chunks extracted from PKMDocuments."""

from django.db import models


class DocumentChunk(models.Model):
    """A text chunk produced by splitting a PKMDocument for embedding.

    Each chunk belongs to exactly one document (cascade delete). Chunks are
    ordered by ``chunk_index`` within the parent document.
    """

    document = models.ForeignKey(
        "pkm.PKMDocument",
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.IntegerField(
        help_text="Zero-based ordinal position within the document",
    )
    content = models.TextField(
        help_text="The extracted text content for this chunk",
    )
    token_count = models.IntegerField(
        default=0,
        help_text="Number of tokens in this chunk",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = "pkm_documentchunk"
        indexes = [
            models.Index(fields=["document"]),
            models.Index(fields=["document", "chunk_index"]),
        ]
        ordering = ["document", "chunk_index"]

    def __str__(self) -> str:
        return f"Chunk {self.chunk_index} of {self.document_id}"
