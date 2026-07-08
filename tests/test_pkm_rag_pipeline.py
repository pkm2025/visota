"""Integration tests for the PKM RAG pipeline.

These tests verify the end-to-end ``process_document`` pipeline:
  - Status transitions: pending -> processing -> processed
  - Chunks and embeddings are stored correctly
  - Errors during processing set status=failed with error_message
  - reprocess_document clears old data and re-runs
  - delete_document_data removes all related records

All LLM/embedding calls are **mocked** (no real API key required). MariaDB
VECTOR operations use the real database (verified working).

Fulfills:
  - VAL-RAG-007: Processing status transitions
  - VAL-RAG-008: Failed processing shows error and allows retry
  - VAL-RAG-009: Deleting a document removes all embeddings
  - VAL-RAG-010: Async task enqueued via django-q2
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import DocumentChunk, PKMDocument, UserLLMConfig
from apps.pkm.services.encryption_service import encrypt
from apps.pkm.services.rag_pipeline import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    TASK_MAX_ATTEMPTS,
    TASK_TIMEOUT,
    delete_document_data,
    process_document,
    reprocess_document,
    schedule_document_processing,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMBEDDING_DIM = 1536


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_RAG_CO", name="PKM RAG Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(username="pkm_rag_user", password="Test1234", email="rag@t.co")


@pytest.fixture
def llm_config(db, user, company):
    """Create an active LLM config with an encrypted dummy API key."""
    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-dummy-key-for-mocking"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


def _create_document_with_file(
    user,
    company,
    content=b"Hello world. This is a test document for the RAG pipeline.",
    filename="test_doc.txt",
):
    """Create a PKMDocument with a real temporary file (so file.path works)."""
    upload = SimpleUploadedFile(filename, content, content_type="text/plain")
    return PKMDocument.objects.create(
        user=user,
        company=company,
        title=filename,
        file=upload,
        file_type="txt",
        file_size=len(content),
        status=PKMDocument.Status.PENDING,
    )


def _create_mock_embedding_response(texts: list[str]) -> Any:
    """Build a mock litellm embedding response object.

    litellm returns an object with a ``.data`` list, each element having an
    ``.embedding`` attribute. We return a simple namespace to match that shape.
    """
    from types import SimpleNamespace

    data = [SimpleNamespace(embedding=[0.01 * (i + 1)] * EMBEDDING_DIM) for i in range(len(texts))]
    return SimpleNamespace(data=data)


# ---------------------------------------------------------------------------
# process_document: success path (VAL-RAG-007)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_process_document_success_status_transitions(user, company, llm_config):
    """Document transitions pending -> processing -> processed."""
    doc = _create_document_with_file(user, company)
    assert doc.status == PKMDocument.Status.PENDING

    mock_response = _create_mock_embedding_response(["dummy"])

    with patch(
        "apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response
    ) as mock_get_emb:
        process_document(doc.id)

        # Verify get_embedding was called
        assert mock_get_emb.called

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.PROCESSED
    assert doc.error_message == ""


@pytest.mark.django_db
def test_process_document_creates_chunks(user, company, llm_config):
    """DocumentChunk records are created with correct content and indices."""
    # Create a document with enough text to produce multiple chunks
    long_text = "This is paragraph one. " * 200
    doc = _create_document_with_file(
        user,
        company,
        content=long_text.encode("utf-8"),
        filename="long_doc.txt",
    )

    # Predict chunk count by splitting the same text
    from apps.pkm.services.chunking_service import split_text

    expected_chunks = split_text(long_text, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)

    mock_response = _create_mock_embedding_response(expected_chunks)

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        process_document(doc.id)

    chunks = DocumentChunk.objects.filter(document=doc).order_by("chunk_index")
    assert chunks.count() == len(expected_chunks)
    assert chunks.count() > 1  # verify multi-chunk document

    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert chunk.content != ""
        assert chunk.token_count > 0

    # Verify all chunk content joined roughly equals the original text
    all_content = "".join(c.content for c in chunks)
    assert "paragraph one" in all_content


@pytest.mark.django_db
def test_process_document_creates_embeddings(user, company, llm_config):
    """Embedding records are created in the pkm_embedding table."""
    doc = _create_document_with_file(user, company)

    # Determine how many chunks we'll produce
    from apps.pkm.services.chunking_service import split_text
    from apps.pkm.services.doc_parser import extract_text

    text = extract_text(doc.file.path)
    expected_chunks = split_text(text, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)

    mock_response = _create_mock_embedding_response(expected_chunks)

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        process_document(doc.id)

    # Verify embeddings exist in DB via raw SQL
    chunk_ids = list(DocumentChunk.objects.filter(document=doc).values_list("id", flat=True))
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pkm_embedding WHERE chunk_id IN (%s)"
            % ",".join(["%s"] * len(chunk_ids)),
            chunk_ids,
        )
        embedding_count = cursor.fetchone()[0]

    assert embedding_count == len(expected_chunks)


@pytest.mark.django_db
def test_process_document_embedding_vector_populated(user, company, llm_config):
    """The VECTOR column is populated (distance to same vector is near-zero)."""
    doc = _create_document_with_file(user, company)
    mock_response = _create_mock_embedding_response(["dummy"])

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        process_document(doc.id)

    chunk = DocumentChunk.objects.get(document=doc)
    import json

    expected_vec = json.dumps([0.01] * EMBEDDING_DIM)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT VEC_DISTANCE_COSINE(embedding, VEC_FromText(%s)) "
            "FROM pkm_embedding WHERE chunk_id = %s",
            [expected_vec, chunk.id],
        )
        distance = cursor.fetchone()[0]

    assert distance < 0.001


@pytest.mark.django_db
def test_process_document_uses_user_llm_config(user, company, llm_config):
    """The pipeline retrieves the user's active LLM config."""
    doc = _create_document_with_file(user, company)
    mock_response = _create_mock_embedding_response(["dummy"])

    with patch(
        "apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response
    ) as mock_get_emb:
        process_document(doc.id)
        # Check the config was passed to get_embedding
        call_args = mock_get_emb.call_args
        passed_config = call_args[0][0]  # first positional arg
        assert passed_config.user_id == user.id
        assert passed_config.company_id == company.id
        assert passed_config.is_active is True


@pytest.mark.django_db
def test_process_document_model_name_stored(user, company, llm_config):
    """The embedding model_name is stored correctly."""
    doc = _create_document_with_file(user, company)
    mock_response = _create_mock_embedding_response(["dummy"])

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        process_document(doc.id)

    chunk = DocumentChunk.objects.get(document=doc)
    with connection.cursor() as cursor:
        cursor.execute("SELECT model_name FROM pkm_embedding WHERE chunk_id = %s", [chunk.id])
        model_name = cursor.fetchone()[0]

    assert model_name == "text-embedding-3-small"


# ---------------------------------------------------------------------------
# process_document: error handling (VAL-RAG-008)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_process_document_error_sets_failed_status(user, company, llm_config):
    """When embedding fails, status becomes 'failed' with error_message."""
    doc = _create_document_with_file(user, company)

    with (
        patch(
            "apps.pkm.services.rag_pipeline.get_embedding",
            side_effect=RuntimeError("Embedding API is down"),
        ),
        pytest.raises(RuntimeError, match="Embedding API is down"),
    ):
        process_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.FAILED
    assert "Embedding API is down" in doc.error_message


@pytest.mark.django_db
def test_process_document_error_no_active_config(user, company):
    """Without an active LLM config, processing fails with a clear message."""
    doc = _create_document_with_file(user, company)

    # No llm_config fixture -> no active config
    with pytest.raises(ValueError, match="No active LLM configuration"):
        process_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.FAILED
    assert "No active LLM configuration" in doc.error_message


@pytest.mark.django_db
def test_process_document_empty_text_fails(user, company, llm_config):
    """Empty text extraction results in 'failed' status."""
    doc = _create_document_with_file(user, company, content=b"", filename="empty.txt")

    with pytest.raises(ValueError, match="No text could be extracted"):
        process_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.FAILED
    assert doc.error_message != ""


@pytest.mark.django_db
def test_process_document_embedding_count_mismatch(user, company, llm_config):
    """Mismatched embedding count causes failure."""
    doc = _create_document_with_file(
        user,
        company,
        content=b"This is a test document. " * 100,
        filename="multi_chunk.txt",
    )

    # Return fewer embeddings than chunks
    mock_response = _create_mock_embedding_response(["only_one"])

    with (
        patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response),
        pytest.raises(ValueError, match="Embedding count mismatch"),
    ):
        process_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.FAILED


@pytest.mark.django_db
def test_process_document_no_chunks_created_on_error(user, company, llm_config):
    """When embedding fails, no chunks/embeddings are left behind."""
    doc = _create_document_with_file(user, company)

    with (
        patch(
            "apps.pkm.services.rag_pipeline.get_embedding",
            side_effect=RuntimeError("API error"),
        ),
        pytest.raises(RuntimeError),
    ):
        process_document(doc.id)

    assert DocumentChunk.objects.filter(document=doc).count() == 0
    # Check no embeddings
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM pkm_embedding WHERE user_id = %s", [user.id])
        count = cursor.fetchone()[0]
    assert count == 0


@pytest.mark.django_db
def test_process_document_nonexistent_id_raises():
    """Processing a non-existent document_id raises DoesNotExist."""
    with pytest.raises(PKMDocument.DoesNotExist):
        process_document(99999999)


# ---------------------------------------------------------------------------
# reprocess_document (VAL-RAG-008 retry)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reprocess_document_clears_old_and_reruns(user, company, llm_config):
    """reprocess_document deletes old chunks/embeddings and re-runs pipeline."""
    doc = _create_document_with_file(user, company)
    mock_response = _create_mock_embedding_response(["dummy"])

    # First: process successfully
    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        process_document(doc.id)

    old_chunk_ids = set(DocumentChunk.objects.filter(document=doc).values_list("id", flat=True))
    assert len(old_chunk_ids) > 0

    # Second: reprocess
    mock_response2 = _create_mock_embedding_response(["dummy"])
    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response2):
        reprocess_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.PROCESSED

    # Old chunks should be gone, new chunks present
    new_chunk_ids = set(DocumentChunk.objects.filter(document=doc).values_list("id", flat=True))
    assert old_chunk_ids.isdisjoint(new_chunk_ids)
    assert len(new_chunk_ids) > 0


@pytest.mark.django_db
def test_reprocess_document_from_failed_state(user, company, llm_config):
    """Reprocessing a failed document succeeds after fixing the error."""
    doc = _create_document_with_file(user, company)

    # First attempt: fail
    with (
        patch(
            "apps.pkm.services.rag_pipeline.get_embedding",
            side_effect=RuntimeError("First attempt fails"),
        ),
        pytest.raises(RuntimeError),
    ):
        process_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.FAILED

    # Reprocess: succeed
    mock_response = _create_mock_embedding_response(["dummy"])
    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        reprocess_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.PROCESSED
    assert DocumentChunk.objects.filter(document=doc).count() > 0


# ---------------------------------------------------------------------------
# delete_document_data (VAL-RAG-009)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_document_data_removes_chunks(user, company, llm_config):
    """delete_document_data removes all DocumentChunk rows."""
    doc = _create_document_with_file(user, company)
    mock_response = _create_mock_embedding_response(["dummy"])

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        process_document(doc.id)

    assert DocumentChunk.objects.filter(document=doc).count() > 0

    delete_document_data(doc.id)

    assert DocumentChunk.objects.filter(document=doc).count() == 0


@pytest.mark.django_db
def test_delete_document_data_removes_embeddings(user, company, llm_config):
    """delete_document_data removes all embedding rows from the DB."""
    doc = _create_document_with_file(user, company)
    mock_response = _create_mock_embedding_response(["dummy"])

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        process_document(doc.id)

    # Verify embeddings exist
    chunk_ids = list(DocumentChunk.objects.filter(document=doc).values_list("id", flat=True))
    with connection.cursor() as cursor:
        ph = ",".join(["%s"] * len(chunk_ids))
        cursor.execute(
            f"SELECT COUNT(*) FROM pkm_embedding WHERE chunk_id IN ({ph})",
            chunk_ids,
        )
        assert cursor.fetchone()[0] > 0

    delete_document_data(doc.id)

    # Verify all embeddings gone
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pkm_embedding WHERE user_id = %s AND company_id = %s",
            [user.id, company.id],
        )
        count = cursor.fetchone()[0]
    assert count == 0


@pytest.mark.django_db
def test_delete_document_data_does_not_affect_other_docs(user, company, llm_config):
    """Deleting one document's data does not affect another document."""
    doc1 = _create_document_with_file(
        user, company, content=b"Document one content here.", filename="doc1.txt"
    )
    doc2 = _create_document_with_file(
        user, company, content=b"Document two content here.", filename="doc2.txt"
    )

    mock_resp1 = _create_mock_embedding_response(["d1"])
    mock_resp2 = _create_mock_embedding_response(["d2"])

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_resp1):
        process_document(doc1.id)
    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_resp2):
        process_document(doc2.id)

    assert DocumentChunk.objects.filter(document=doc2).count() > 0

    delete_document_data(doc1.id)

    assert DocumentChunk.objects.filter(document=doc1).count() == 0
    assert DocumentChunk.objects.filter(document=doc2).count() > 0


@pytest.mark.django_db
def test_delete_document_data_nonexistent_doc():
    """Deleting data for a non-existent document does not raise."""
    # Should not raise
    result = delete_document_data(99999999)
    # Returns 0 deleted references (or small number from cascade)
    assert result == 0


# ---------------------------------------------------------------------------
# schedule_document_processing (VAL-RAG-010)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_schedule_document_processing_enqueues_task(user, company, llm_config):
    """schedule_document_processing enqueues a django-q2 async_task.

    In test mode, Q_CLUSTER sync=True means the task runs synchronously.
    We mock get_embedding so the pipeline completes successfully.
    """
    doc = _create_document_with_file(user, company)
    mock_response = _create_mock_embedding_response(["dummy"])

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        schedule_document_processing(doc.id)

    # In sync mode, async_task returns the task result
    # The document should be processed
    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.PROCESSED


@pytest.mark.django_db
def test_schedule_document_processing_uses_correct_task_config(user, company, llm_config):
    """async_task is called with timeout=300 and the correct task path."""
    doc = _create_document_with_file(user, company)

    with patch("django_q.tasks.async_task") as mock_async:
        mock_async.return_value = "task-id"
        schedule_document_processing(doc.id)

        assert mock_async.called
        call_args, call_kwargs = mock_async.call_args

        # First positional arg is the task path string
        assert call_args[0] == "apps.pkm.services.rag_pipeline.process_document"
        # Second positional arg is document_id
        assert call_args[1] == doc.id
        # timeout is a recognized django-q2 per-task option
        assert call_kwargs["timeout"] == TASK_TIMEOUT


@pytest.mark.django_db
def test_task_config_constants():
    """Task config constants have correct values."""
    assert TASK_TIMEOUT == 300
    assert TASK_MAX_ATTEMPTS == 3


# ---------------------------------------------------------------------------
# Per-user isolation in pipeline
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_process_document_per_user_isolation(user, company, llm_config):
    """Embeddings are stored with the correct user_id/company_id."""
    doc = _create_document_with_file(user, company)
    mock_response = _create_mock_embedding_response(["dummy"])

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        process_document(doc.id)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT user_id, company_id FROM pkm_embedding WHERE chunk_id IN "
            "(SELECT id FROM pkm_documentchunk WHERE document_id = %s)",
            [doc.id],
        )
        row = cursor.fetchone()

    assert row is not None
    assert row[0] == user.id
    assert row[1] == company.id


@pytest.mark.django_db
def test_process_document_multi_chunk_consistency(user, company, llm_config):
    """A multi-chunk document has consistent chunk indices and embeddings."""
    # Create a document large enough for multiple chunks
    long_text = "This is a paragraph with content. " * 300
    doc = _create_document_with_file(
        user,
        company,
        content=long_text.encode("utf-8"),
        filename="multi.txt",
    )

    from apps.pkm.services.chunking_service import split_text

    expected_chunks = split_text(long_text, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)
    mock_response = _create_mock_embedding_response(expected_chunks)

    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        process_document(doc.id)

    chunks = list(DocumentChunk.objects.filter(document=doc).order_by("chunk_index"))
    assert len(chunks) == len(expected_chunks)
    assert len(chunks) > 1  # ensure multi-chunk

    # Verify each chunk has an embedding
    for chunk in chunks:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM pkm_embedding WHERE chunk_id = %s", [chunk.id])
            count = cursor.fetchone()[0]
        assert count == 1

    # Verify chunk indices are sequential 0..N-1
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_process_document_error_truncates_long_message(user, company, llm_config):
    """Very long error messages are truncated to fit the TextField."""
    doc = _create_document_with_file(user, company)

    long_error = "x" * 10000
    with (
        patch(
            "apps.pkm.services.rag_pipeline.get_embedding",
            side_effect=RuntimeError(long_error),
        ),
        pytest.raises(RuntimeError),
    ):
        process_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.FAILED
    # Error message should be truncated to 5000 chars
    assert len(doc.error_message) <= 5000


@pytest.mark.django_db
def test_process_document_clears_previous_error_on_retry(user, company, llm_config):
    """Reprocessing clears the error_message from a previous failure."""
    doc = _create_document_with_file(user, company)

    # First: fail
    with (
        patch(
            "apps.pkm.services.rag_pipeline.get_embedding",
            side_effect=RuntimeError("First error"),
        ),
        pytest.raises(RuntimeError),
    ):
        process_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.FAILED
    assert doc.error_message != ""

    # Reprocess: succeed
    mock_response = _create_mock_embedding_response(["dummy"])
    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_response):
        reprocess_document(doc.id)

    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.PROCESSED
    assert doc.error_message == ""


@pytest.mark.django_db
def test_process_document_status_set_to_processing_first(user, company, llm_config):
    """The document status is set to 'processing' before any work."""
    doc = _create_document_with_file(user, company)
    mock_response = _create_mock_embedding_response(["dummy"])

    captured_statuses = []

    def spy_extract(file_path):
        # At this point, the document should be in 'processing' status
        doc.refresh_from_db()
        captured_statuses.append(doc.status)
        from apps.pkm.services.doc_parser import extract_text as real_extract

        return real_extract(file_path)

    with (
        patch("apps.pkm.services.rag_pipeline.extract_text", side_effect=spy_extract),
        patch(
            "apps.pkm.services.rag_pipeline.get_embedding",
            return_value=mock_response,
        ),
    ):
        process_document(doc.id)

    assert PKMDocument.Status.PROCESSING in captured_statuses
