"""RAG pipeline orchestration for the PKM module.

This module ties together the individual services (document parsing, text
chunking, LLM embedding generation, and MariaDB vector storage) into a single
end-to-end pipeline that can be executed asynchronously via django-q2.

Pipeline stages::

    process_document(document_id)
        1.  Set PKMDocument.status = "processing"
        2.  Extract text from the uploaded file  (doc_parser)
        3.  Split text into chunks               (chunking_service)
        4.  Resolve the user's active LLM config  (for embedding model + key)
        5.  Generate embeddings                   (llm_service.get_embedding)
        6.  Persist DocumentChunk + Embedding rows (vector_store)
        7.  Set PKMDocument.status = "processed"

Any exception during steps 2-7 is caught, the document status is set to
``"failed"`` with an ``error_message``, and the exception is re-raised so
django-q2's retry mechanism can handle it.

Helper functions
----------------
- ``reprocess_document(document_id)`` - delete old chunks/embeddings then re-run
- ``delete_document_data(document_id)`` - cascade delete chunks + embeddings
- ``schedule_document_processing(document_id)`` - enqueue via django-q2 ``async_task``
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from apps.pkm.models import DocumentChunk, PKMDocument, UserLLMConfig
from apps.pkm.services.chunking_service import count_tokens, split_text
from apps.pkm.services.doc_parser import extract_text
from apps.pkm.services.llm_service import get_embedding
from apps.pkm.services.vector_store import delete_embeddings, store_embedding

logger = logging.getLogger(__name__)

#: Task configuration passed to ``django_q.tasks.async_task``.
TASK_TIMEOUT: int = 300
TASK_MAX_ATTEMPTS: int = 3

#: Default chunk size (characters) used by the pipeline.
DEFAULT_CHUNK_SIZE: int = 1000
#: Default chunk overlap (characters) used by the pipeline.
DEFAULT_CHUNK_OVERLAP: int = 200

__all__ = [
    "process_document",
    "reprocess_document",
    "delete_document_data",
    "schedule_document_processing",
    "TASK_TIMEOUT",
    "TASK_MAX_ATTEMPTS",
]


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------


def _get_embedding_config(document: PKMDocument) -> UserLLMConfig:
    """Return the active LLM config for the document owner.

    Selects the user's active config within the same company (multi-tenant
    scoped). Raises ``ValueError`` if no active config exists.
    """
    config = UserLLMConfig.objects.filter(
        user=document.user,
        company=document.company,
        is_active=True,
    ).first()
    if config is None:
        raise ValueError(
            f"No active LLM configuration found for user "
            f"{document.user_id} in company {document.company_id}. "
            "Configure an embedding provider before processing documents."
        )
    return config


def _extract_embedding_vectors(response: Any, expected_count: int) -> list[list[float]]:
    """Extract embedding vectors from a litellm embedding response.

    litellm's ``embedding()`` returns an object with a ``.data`` list, where
    each element has an ``.embedding`` attribute (a list of floats). This
    helper normalises different response shapes into ``list[list[float]]``.
    """
    vectors: list[list[float]] = []

    # Standard litellm response: response.data is a list of EmbeddingResponse
    if hasattr(response, "data") and response.data:
        for item in response.data:
            emb = getattr(item, "embedding", None) or (
                item.get("embedding") if isinstance(item, dict) else None
            )
            if emb:
                vectors.append(list(emb))
    elif isinstance(response, dict) and "data" in response:
        for item in response["data"]:
            emb = item.get("embedding") if isinstance(item, dict) else None
            if emb:
                vectors.append(list(emb))

    if len(vectors) != expected_count:
        raise ValueError(
            f"Embedding count mismatch: expected {expected_count} embeddings, got {len(vectors)}."
        )
    return vectors


def _store_chunks_and_embeddings(
    document: PKMDocument,
    chunks: list[str],
    embedding_config: UserLLMConfig,
    embeddings: list[list[float]],
    model_name: str,
) -> None:
    """Persist DocumentChunk rows and corresponding Embedding vectors.

    Each chunk is stored via the Django ORM, then its vector is inserted
    via raw SQL (vector_store.store_embedding) because Django's ORM cannot
    express MariaDB's VECTOR type.
    """
    for index, (chunk_text, vector) in enumerate(zip(chunks, embeddings, strict=True)):
        chunk = DocumentChunk.objects.create(
            document=document,
            chunk_index=index,
            content=chunk_text,
            token_count=count_tokens(chunk_text),
        )
        store_embedding(
            chunk_id=chunk.id,
            user_id=document.user_id,
            company_id=document.company_id,
            content=chunk_text,
            embedding_vector=vector,
            model_name=model_name,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def process_document(document_id: int) -> None:
    """Run the full RAG processing pipeline for a single document.

    This function is designed to be called by django-q2 as an async task.
    It updates the document status through the pipeline stages::

        pending -> processing -> processed
                          |-> failed (on error)

    Steps:
        1.  Load the document and set status to ``"processing"``.
        2.  Extract text from the file (supports PDF, DOCX, TXT, MD, XLSX).
        3.  Split text into chunks (default 1000 chars, 200 overlap).
        4.  Resolve the user's active LLM config for embedding.
        5.  Generate embeddings via ``llm_service.get_embedding``.
        6.  Store DocumentChunk + Embedding records.
        7.  Set status to ``"processed"``.

    On any error, the document status is set to ``"failed"`` with the error
    message, and the exception is re-raised so django-q2 can retry.

    Args:
        document_id: Primary key of the PKMDocument to process.
    """
    try:
        document = PKMDocument.objects.get(pk=document_id)
    except PKMDocument.DoesNotExist:
        logger.error("process_document: PKMDocument %s not found", document_id)
        raise

    # Step 1: Mark as processing
    document.status = PKMDocument.Status.PROCESSING
    document.error_message = ""
    document.save(update_fields=["status", "error_message", "updated_at"])

    try:
        # Step 2: Extract text from the file
        file_path = document.file.path
        text = extract_text(file_path)
        if not text:
            raise ValueError(f"No text could be extracted from document {document_id}.")

        # Step 3: Split into chunks
        chunks = split_text(
            text,
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        )
        if not chunks:
            raise ValueError(f"Chunking produced no chunks for document {document_id}.")

        # Step 4: Get user's active LLM config for embedding
        embedding_config = _get_embedding_config(document)
        embed_model = embedding_config.default_embedding_model or "text-embedding-3-small"

        # Step 5: Generate embeddings (batch via llm_service)
        response = get_embedding(embedding_config, chunks, model=embed_model)
        embeddings = _extract_embedding_vectors(response, expected_count=len(chunks))

        # Step 6: Store chunks + embeddings
        with transaction.atomic():
            _store_chunks_and_embeddings(
                document=document,
                chunks=chunks,
                embedding_config=embedding_config,
                embeddings=embeddings,
                model_name=embed_model,
            )

        # Step 7: Mark as processed
        document.status = PKMDocument.Status.PROCESSED
        document.error_message = ""
        document.save(update_fields=["status", "error_message", "updated_at"])

        logger.info(
            "process_document: document %s processed successfully (%d chunks, %d embeddings)",
            document_id,
            len(chunks),
            len(embeddings),
        )

    except Exception as exc:
        # Set status to failed with the error message
        error_msg = str(exc) if str(exc) else exc.__class__.__name__
        document.status = PKMDocument.Status.FAILED
        document.error_message = error_msg[:5000]
        document.save(update_fields=["status", "error_message", "updated_at"])
        logger.error("process_document: document %s failed: %s", document_id, error_msg)
        raise


def reprocess_document(document_id: int) -> None:
    """Delete existing chunks/embeddings for a document and re-run the pipeline.

    This is used when a user wants to retry processing a failed document or
    re-process with updated settings. Old data is deleted first to avoid
    duplicate chunks/embeddings.

    Args:
        document_id: Primary key of the PKMDocument to reprocess.
    """
    delete_document_data(document_id)
    process_document(document_id)


def delete_document_data(document_id: int) -> int:
    """Delete all chunks and embeddings for a document.

    Embeddings are deleted first (raw SQL), then DocumentChunk rows are
    removed via the ORM (cascade would also handle embeddings, but explicit
    deletion ensures the raw-SQL rows are cleaned even if the ORM cascade
    doesn't target the VECTOR table).

    Args:
        document_id: Primary key of the PKMDocument.

    Returns:
        Total number of chunk rows deleted (embeddings are cascade-deleted).
    """
    # Delete embeddings via raw SQL (VECTOR table rows)
    delete_embeddings(document_id=document_id)

    # Delete chunks via ORM (cascade handles any remaining embedding rows)
    deleted_count, _ = DocumentChunk.objects.filter(document_id=document_id).delete()

    logger.info(
        "delete_document_data: removed data for document %s (%d references deleted)",
        document_id,
        deleted_count,
    )
    return deleted_count


def schedule_document_processing(document_id: int) -> Any:
    """Enqueue ``process_document`` as a django-q2 async task.

    Uses ``async_task`` with ``timeout=300``. The ``max_attempts=3`` retry
    limit is configured at the cluster level via ``Q_CLUSTER`` in Django
    settings (django-q2 does not accept ``max_attempts`` as a per-task kwarg).

    In test mode (``Q_CLUSTER = {"sync": True}``), the task executes
    synchronously.

    Args:
        document_id: Primary key of the PKMDocument to process.

    Returns:
        The result of ``async_task`` (task id or sync result).
    """
    from django_q.tasks import async_task

    return async_task(
        "apps.pkm.services.rag_pipeline.process_document",
        document_id,
        timeout=TASK_TIMEOUT,
    )
