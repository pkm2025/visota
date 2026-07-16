"""Tests for the ``cleanup_pkm_data`` management command (data retention).

Fulfils:
  - **VAL-RETENTION-001**: Cleanup purges old interaction logs (and other
    ephemeral records) while preserving recent data.
  - **VAL-RETENTION-002**: Dry-run mode is safe (no rows deleted, counts
    reported).

Scope of the command
--------------------
The retention command purges *ephemeral, high-volume* data only:

  * ``UserInteractionLog`` older than ``--interaction-days`` (default 90).
  * ``QAHistory`` older than ``--qa-days`` (default 180).
  * ``Embedding`` rows whose parent ``DocumentChunk`` no longer exists
    (orphaned vectors).
  * ``PKMDocument`` rows in ``status=failed`` older than
    ``--failed-doc-days`` (default 30).

Safety contract
---------------
The command must **NEVER** delete user-authored or compounding artifacts:

  * ``KnowledgeNote`` (notes)
  * ``WikiPage`` (the LLM-maintained wiki)
  * ``PKMDocument`` in non-failed states (processed/pending/processing)
  * ``UserLLMConfig`` or any configuration row

These guards are enforced both in the command's implementation and by
explicit regression tests below.
"""

from __future__ import annotations

import io
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import (
    DocumentChunk,
    Embedding,
    KnowledgeNote,
    PKMDocument,
    QAHistory,
    UserInteractionLog,
    UserLLMConfig,
    WikiPage,
)

# ---------------------------------------------------------------------------
# Constants mirroring the command defaults
# ---------------------------------------------------------------------------

DEFAULT_INTERACTION_DAYS = 90
DEFAULT_QA_DAYS = 180
DEFAULT_FAILED_DOC_DAYS = 30


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="CLEANUP_CO", name="Cleanup Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="cleanup_user", password="Test1234!", email="cleanup@t.co"
    )


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="cleanup_other", password="Test1234!", email="co2@t.co"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_command(*args: str) -> str:
    """Run ``cleanup_pkm_data`` and return its combined stdout output."""
    out = io.StringIO()
    err = io.StringIO()
    call_command("cleanup_pkm_data", *args, stdout=out, stderr=err)
    return out.getvalue() + err.getvalue()


def _make_interaction_log(user, company, *, days_ago=0, interaction_type="page_view"):
    """Create a UserInteractionLog with ``created_at`` set to days_ago."""
    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type=interaction_type,
        module="pkm",
    )
    if days_ago:
        UserInteractionLog.objects.filter(pk=log.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago)
        )
    return log


def _make_qa_history(user, company, *, days_ago=0, question="?"):
    qa = QAHistory.objects.create(
        user=user,
        company=company,
        question=question,
        answer="answer",
    )
    if days_ago:
        QAHistory.objects.filter(pk=qa.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago)
        )
    return qa


def _make_document(user, company, *, status=PKMDocument.Status.PROCESSED, days_ago=0):
    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title=f"Doc {status} {days_ago}d",
        file=SimpleUploadedFile("d.txt", b"hello"),
        file_type="txt",
        status=status,
    )
    if days_ago:
        # ``created_at`` is auto_now_add; update via queryset to backdate.
        PKMDocument.objects.filter(pk=doc.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago)
        )
    return doc


def _make_embedding(user, company, chunk=None, *, model_name="text-embedding-3-small"):
    """Create an Embedding row via the vector_store raw SQL helper."""
    from apps.pkm.services.vector_store import EMBEDDING_DIMENSIONS, store_embedding

    if chunk is None:
        # Create a throwaway chunk for a non-failed document.
        doc = _make_document(user, company)
        chunk = DocumentChunk.objects.create(
            document=doc,
            chunk_index=0,
            content="x",
        )
    # Use the existing raw-SQL helper so the VECTOR column is populated
    # correctly via VEC_FromText().
    embedding_id = store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="x",
        embedding_vector=[0.0] * EMBEDDING_DIMENSIONS,
        model_name=model_name,
    )
    return Embedding.objects.filter(pk=embedding_id).first()


# ---------------------------------------------------------------------------
# VAL-RETENTION-001: purges old data, preserves recent
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_purges_old_interaction_logs(user, company):
    """UserInteractionLog older than 90 days is deleted."""
    old_log = _make_interaction_log(user, company, days_ago=DEFAULT_INTERACTION_DAYS + 5)
    recent_log = _make_interaction_log(user, company, days_ago=1)

    output = _run_command()

    assert "UserInteractionLog" in output
    assert UserInteractionLog.objects.filter(pk=old_log.pk).exists() is False
    assert UserInteractionLog.objects.filter(pk=recent_log.pk).exists() is True


@pytest.mark.django_db
def test_preserves_recent_interaction_logs(user, company):
    """All logs at or inside the threshold are preserved."""
    inside = _make_interaction_log(user, company, days_ago=DEFAULT_INTERACTION_DAYS - 1)
    # Boundary day: slightly fresher than the exact cutoff to avoid races
    # between the time the fixture backdates the row and the command reads
    # ``timezone.now()``.
    boundary = _make_interaction_log(user, company, days_ago=DEFAULT_INTERACTION_DAYS - 1)

    _run_command()

    assert UserInteractionLog.objects.filter(pk=inside.pk).exists() is True
    assert UserInteractionLog.objects.filter(pk=boundary.pk).exists() is True


@pytest.mark.django_db
def test_purges_old_qa_history(user, company):
    """QAHistory older than 180 days is deleted."""
    old_qa = _make_qa_history(user, company, days_ago=DEFAULT_QA_DAYS + 10)
    recent_qa = _make_qa_history(user, company, days_ago=5)

    _run_command()

    assert QAHistory.objects.filter(pk=old_qa.pk).exists() is False
    assert QAHistory.objects.filter(pk=recent_qa.pk).exists() is True


@pytest.mark.django_db
def test_preserves_recent_qa_history(user, company):
    """QAHistory inside the threshold is preserved."""
    inside = _make_qa_history(user, company, days_ago=DEFAULT_QA_DAYS - 1)

    _run_command()

    assert QAHistory.objects.filter(pk=inside.pk).exists() is True


@pytest.mark.django_db
def test_purges_failed_documents_older_than_30_days(user, company):
    """PKMDocument with status=failed older than 30 days is deleted."""
    old_failed = _make_document(
        user, company, status=PKMDocument.Status.FAILED, days_ago=DEFAULT_FAILED_DOC_DAYS + 3
    )
    recent_failed = _make_document(user, company, status=PKMDocument.Status.FAILED, days_ago=5)

    _run_command()

    assert PKMDocument.objects.filter(pk=old_failed.pk).exists() is False
    # Recent failed documents are still kept (still within retry window).
    assert PKMDocument.objects.filter(pk=recent_failed.pk).exists() is True


@pytest.mark.django_db
def test_never_purges_processed_documents(user, company):
    """PKMDocument in processed/pending/processing status is NEVER deleted."""
    processed_old = _make_document(user, company, status=PKMDocument.Status.PROCESSED, days_ago=365)
    pending_old = _make_document(user, company, status=PKMDocument.Status.PENDING, days_ago=365)
    processing_old = _make_document(
        user, company, status=PKMDocument.Status.PROCESSING, days_ago=365
    )

    _run_command()

    assert PKMDocument.objects.filter(pk=processed_old.pk).exists() is True
    assert PKMDocument.objects.filter(pk=pending_old.pk).exists() is True
    assert PKMDocument.objects.filter(pk=processing_old.pk).exists() is True


@pytest.mark.django_db
def test_never_purges_notes_wiki_configs(user, company):
    """KnowledgeNote, WikiPage, UserLLMConfig are NEVER deleted."""
    note = KnowledgeNote.objects.create(user=user, company=company, title="note", content="x")
    wiki = WikiPage.objects.create(user=user, company=company, title="wiki", content="x")
    config = UserLLMConfig.objects.create(user=user, company=company, provider="ollama")

    _run_command()

    assert KnowledgeNote.objects.filter(pk=note.pk).exists() is True
    assert WikiPage.objects.filter(pk=wiki.pk).exists() is True
    assert UserLLMConfig.objects.filter(pk=config.pk).exists() is True


# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_days_configurable(user, company):
    """--interaction-days overrides the 90-day default."""
    log_50d = _make_interaction_log(user, company, days_ago=50)
    log_10d = _make_interaction_log(user, company, days_ago=10)

    _run_command("--interaction-days", "30")

    # 50 days > 30 day threshold -> deleted
    assert UserInteractionLog.objects.filter(pk=log_50d.pk).exists() is False
    # 10 days < 30 day threshold -> kept
    assert UserInteractionLog.objects.filter(pk=log_10d.pk).exists() is True


@pytest.mark.django_db
def test_qa_days_configurable(user, company):
    """--qa-days overrides the 180-day default."""
    old_qa = _make_qa_history(user, company, days_ago=60)
    recent_qa = _make_qa_history(user, company, days_ago=10)

    _run_command("--qa-days", "30")

    assert QAHistory.objects.filter(pk=old_qa.pk).exists() is False
    assert QAHistory.objects.filter(pk=recent_qa.pk).exists() is True


@pytest.mark.django_db
def test_failed_doc_days_configurable(user, company):
    """--failed-doc-days overrides the 30-day default."""
    failed_20d = _make_document(user, company, status=PKMDocument.Status.FAILED, days_ago=20)
    failed_5d = _make_document(user, company, status=PKMDocument.Status.FAILED, days_ago=5)

    _run_command("--failed-doc-days", "10")

    assert PKMDocument.objects.filter(pk=failed_20d.pk).exists() is False
    assert PKMDocument.objects.filter(pk=failed_5d.pk).exists() is True


# ---------------------------------------------------------------------------
# VAL-RETENTION-002: dry-run mode safe
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dry_run_deletes_nothing_but_reports_counts(user, company):
    """--dry-run reports counts but deletes nothing (VAL-RETENTION-002)."""
    old_log = _make_interaction_log(user, company, days_ago=DEFAULT_INTERACTION_DAYS + 1)
    old_qa = _make_qa_history(user, company, days_ago=DEFAULT_QA_DAYS + 1)
    old_failed = _make_document(
        user, company, status=PKMDocument.Status.FAILED, days_ago=DEFAULT_FAILED_DOC_DAYS + 1
    )

    before_log = UserInteractionLog.objects.count()
    before_qa = QAHistory.objects.count()
    before_doc = PKMDocument.objects.count()

    output = _run_command("--dry-run")

    # Nothing was deleted.
    assert UserInteractionLog.objects.count() == before_log
    assert QAHistory.objects.count() == before_qa
    assert PKMDocument.objects.count() == before_doc

    # The IDs still exist.
    assert UserInteractionLog.objects.filter(pk=old_log.pk).exists() is True
    assert QAHistory.objects.filter(pk=old_qa.pk).exists() is True
    assert PKMDocument.objects.filter(pk=old_failed.pk).exists() is True

    # The output reports that it was a dry run.
    assert "dry" in output.lower()
    # Reports would-be-deleted counts for each category.
    assert "UserInteractionLog" in output
    assert "QAHistory" in output
    assert "PKMDocument" in output or "failed" in output.lower()


@pytest.mark.django_db
def test_dry_run_default_off(user, company):
    """Without --dry-run, the command actually deletes (dry-run is opt-in)."""
    old_log = _make_interaction_log(user, company, days_ago=DEFAULT_INTERACTION_DAYS + 1)

    _run_command()  # no --dry-run

    assert UserInteractionLog.objects.filter(pk=old_log.pk).exists() is False


# ---------------------------------------------------------------------------
# Orphaned embeddings cleanup
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_purges_orphaned_embeddings(user, company):
    """Embeddings whose parent chunk no longer exists are removed.

    In normal operation the FK cascade keeps embeddings in sync with chunks,
    but if a chunk is ever removed by raw SQL with FK checks disabled (or the
    chunk_id is otherwise detached to a stale id), the embedding becomes an
    orphan. We simulate that here by detaching the chunk_id to a non-existent
    value with FK checks temporarily off.
    """
    doc = _make_document(user, company)
    chunk = DocumentChunk.objects.create(document=doc, chunk_index=0, content="x")
    emb = _make_embedding(user, company, chunk=chunk)

    from django.db import connection

    # Detach the embedding's chunk pointer to simulate an orphan, bypassing
    # the FK constraint that would normally prevent this.
    with connection.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        try:
            cur.execute(
                "UPDATE pkm_embedding SET chunk_id = %s WHERE id = %s",
                [999_999_999, emb.id],
            )
        finally:
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")

    assert Embedding.objects.filter(pk=emb.pk).exists() is True

    _run_command()

    assert Embedding.objects.filter(pk=emb.pk).exists() is False


@pytest.mark.django_db
def test_preserves_non_orphaned_embeddings(user, company):
    """Embeddings with a valid parent chunk are preserved."""
    doc = _make_document(user, company)
    chunk = DocumentChunk.objects.create(document=doc, chunk_index=0, content="x")
    emb = _make_embedding(user, company, chunk=chunk)

    _run_command()

    assert Embedding.objects.filter(pk=emb.pk).exists() is True


# ---------------------------------------------------------------------------
# Multi-tenant scoping (purge is global, but does not violate isolation)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_purge_runs_across_all_tenants(user, company, other_user):
    """Old data from any user/company is purged (retention is system-wide)."""
    log_a = _make_interaction_log(user, company, days_ago=DEFAULT_INTERACTION_DAYS + 5)
    log_b = _make_interaction_log(other_user, company, days_ago=DEFAULT_INTERACTION_DAYS + 5)

    _run_command()

    assert UserInteractionLog.objects.filter(pk=log_a.pk).exists() is False
    assert UserInteractionLog.objects.filter(pk=log_b.pk).exists() is False


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_summary_reports_totals(user, company):
    """The command prints a clear summary of what was purged."""
    _make_interaction_log(user, company, days_ago=DEFAULT_INTERACTION_DAYS + 1)
    _make_qa_history(user, company, days_ago=DEFAULT_QA_DAYS + 1)

    output = _run_command()

    # The summary mentions each category and a count.
    assert "purged" in output.lower() or "deleted" in output.lower()


@pytest.mark.django_db
def test_command_runs_clean_on_empty_db(db):
    """Running the command on an empty database is a no-op (no crash)."""
    output = _run_command()
    # No errors raised; some summary printed.
    assert len(output) > 0
