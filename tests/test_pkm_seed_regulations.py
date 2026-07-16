"""Tests for the ``seed_pkm_regulations`` management command.

Fulfills VAL-RAG-001: "Given seed_pkm_regulations runs, when complete, then
PKMDocument records exist for TT58, PIT rates, VAT law with is_system=True."

Coverage:
  - Command creates system documents for all 4 regulations (TT58, rates,
    TT133 overview, ND254 e-invoice).
  - Each created document has ``is_system=True``.
  - Documents are chunked via the existing RAG pipeline helpers.
  - Idempotent: re-running updates existing documents instead of duplicating.
  - Documents are attached to an existing company + a real user.
  - ``--no-chunks`` skips chunk creation.
  - Fails cleanly with a helpful error when no user exists.
"""

from __future__ import annotations

import io

import pytest
from django.core.management import call_command

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import DocumentChunk, PKMDocument

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="SEED_REG_CO", name="Seed Regulation Co")


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="seed_admin", password="Test1234!", email="seed_admin@t.co"
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="seed_user", password="Test1234!", email="seed_user@t.co"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_command(*args: str) -> str:
    """Run seed_pkm_regulations and return stdout output."""
    out = io.StringIO()
    call_command("seed_pkm_regulations", *args, stdout=out, stderr=out)
    return out.getvalue()


# ---------------------------------------------------------------------------
# VAL-RAG-001: command creates the expected system documents
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_creates_system_documents_for_each_regulation(company, superuser):
    """All 4 regulations are seeded as is_system=True documents."""
    initial = PKMDocument.objects.filter(is_system=True).count()
    output = _run_command()
    assert "Seeded 4 regulation document(s)" in output

    docs = list(PKMDocument.objects.filter(is_system=True).order_by("title"))
    assert len(docs) == initial + 4

    # Title substrings prove each regulation is present.
    titles = " ".join(d.title for d in docs)
    assert "TT58" in titles
    assert "PIT/BHXH/CIT/VAT" in titles
    assert "TT133" in titles
    assert "254/2026" in titles
    for doc in docs:
        assert doc.is_system is True
        assert doc.status == PKMDocument.Status.PROCESSED
        assert doc.checksum  # populated


@pytest.mark.django_db
def test_seed_documents_have_chunks(company, superuser):
    """Each seeded system document has DocumentChunk rows."""
    _run_command()
    docs = PKMDocument.objects.filter(is_system=True)
    assert docs.count() == 4
    for doc in docs:
        assert doc.chunks.count() > 0, f"Document {doc.title!r} has no chunks"
        # Chunks should contain Vietnamese regulation text.
        chunk_text = " ".join(c.content for c in doc.chunks.all())
        assert len(chunk_text) > 0


@pytest.mark.django_db
def test_seed_documents_have_stored_md_file(company, superuser):
    """System documents store the regulation body as a markdown file."""
    _run_command()
    doc = PKMDocument.objects.filter(is_system=True).first()
    assert doc is not None
    assert doc.file_type == "md"
    assert doc.file.size > 0
    # The stored file should be readable back.
    doc.file.open("rb")
    try:
        content = doc.file.read().decode("utf-8")
    finally:
        doc.file.close()
    assert "TT" in content or "thuế" in content.lower() or "Tài khoản" in content


@pytest.mark.django_db
def test_seed_uses_existing_company_and_superuser(company, superuser):
    """System documents attach to the existing company + a superuser."""
    _run_command()
    doc = PKMDocument.objects.filter(is_system=True).first()
    assert doc is not None
    assert doc.company_id == company.id
    assert doc.user_id == superuser.id


@pytest.mark.django_db
def test_seed_falls_back_to_any_user_when_no_superuser(company, regular_user):
    """Without a superuser, the command uses the first available user."""
    assert not User.objects.filter(is_superuser=True).exists()
    _run_command()
    doc = PKMDocument.objects.filter(is_system=True).first()
    assert doc is not None
    assert doc.user_id == regular_user.id


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_is_idempotent(company, superuser):
    """Re-running the command updates existing docs instead of duplicating."""
    _run_command()
    docs_after_first = list(PKMDocument.objects.filter(is_system=True).order_by("title"))
    chunks_after_first = DocumentChunk.objects.filter(document__is_system=True).count()
    assert len(docs_after_first) == 4
    assert chunks_after_first > 0

    output = _run_command()
    # Second run reports 0 new, 4 updated.
    assert "0 new, 4 updated" in output

    docs_after_second = list(PKMDocument.objects.filter(is_system=True).order_by("title"))
    chunks_after_second = DocumentChunk.objects.filter(document__is_system=True).count()

    assert len(docs_after_second) == 4
    # Same PKs (not recreated).
    assert [d.id for d in docs_after_first] == [d.id for d in docs_after_second]
    # Chunks were replaced (count may differ slightly but should be > 0 and
    # bounded by the same source text).
    assert chunks_after_second > 0


@pytest.mark.django_db
def test_seed_updates_body_changes_chunks(company, superuser):
    """If the body text changes, re-running refreshes chunks."""
    _run_command()
    doc = PKMDocument.objects.filter(is_system=True).first()
    assert doc is not None
    original_checksum = doc.checksum
    original_chunk_count = doc.chunks.count()

    # Manually tamper with the chunks to prove they get regenerated.
    doc.chunks.all().delete()
    assert doc.chunks.count() == 0

    _run_command()
    doc.refresh_from_db()
    assert doc.checksum == original_checksum  # Same source -> same checksum.
    assert doc.chunks.count() == original_chunk_count  # Chunks restored.


# ---------------------------------------------------------------------------
# --no-chunks flag
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_no_chunks_flag(company, superuser):
    """--no-chunks creates documents but no chunks."""
    output = _run_command("--no-chunks")
    assert "chunks skipped" in output

    docs = PKMDocument.objects.filter(is_system=True)
    assert docs.count() == 4
    for doc in docs:
        assert doc.chunks.count() == 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_fails_when_no_user(company):
    """Command raises a helpful error when no user exists."""
    assert User.objects.count() == 0
    with pytest.raises(Exception) as exc_info:  # noqa: PT011 - CommandError is a SystemExit
        _run_command()
    # The management call_command raises CommandError.
    assert "user" in str(exc_info.value).lower() or "superuser" in str(exc_info.value).lower()


@pytest.mark.django_db
def test_seed_creates_sentinel_company_when_none_exists(superuser):
    """When no company exists, a sentinel SYSTEM company is created."""
    assert Company.objects.count() == 0
    _run_command()
    doc = PKMDocument.objects.filter(is_system=True).first()
    assert doc is not None
    assert doc.company.code == "SYSTEM"


# ---------------------------------------------------------------------------
# Module-level helpers (slug extraction)
# ---------------------------------------------------------------------------


def test_extract_slug_from_title_round_trip():
    """Slug embedded in title is recoverable (used for idempotency lookups)."""
    from apps.pkm.management.commands.seed_pkm_regulations import (
        _extract_slug_from_title,
        _system_title,
    )

    slug = "tt58-2026"
    title = "TT58/2026/TT-BTC — Chế độ kế toán DNSN"
    full = _system_title(slug, title)
    assert _extract_slug_from_title(full) == slug


def test_extract_slug_returns_none_for_non_system_title():
    from apps.pkm.management.commands.seed_pkm_regulations import (
        _extract_slug_from_title,
    )

    assert _extract_slug_from_title("My regular user document") is None
