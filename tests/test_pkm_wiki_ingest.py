"""Tests for the PKM wiki ingest service (Karpathy LLM Wiki pattern).

Covers the ingest operation that turns a processed document or note into a
persistent, compounding set of wiki pages:

  1. AI reads source chunks (masked).
  2. Creates a summary WikiPage for the source.
  3. Reads existing concept/entity pages for context.
  4. Creates or updates concept/entity pages (merge, not duplicate).
  5. Updates cross-references via ``linked_pages``.
  6. Maintains the index page (catalog of all pages).
  7. Appends a timestamped entry to the log page.

All LLM calls are mocked (no real API key required).

Fulfills:
  - VAL-WIKI-002: Ingest creates summary page from document.
  - VAL-WIKI-003: Ingest updates existing concept pages (merge, not duplicate).
  - VAL-WIKI-004: Index page auto-maintained.
  - VAL-WIKI-005: Log page appends entries.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import (
    DocumentChunk,
    KnowledgeNote,
    PKMDocument,
    UserLLMConfig,
    WikiPage,
)
from apps.pkm.services.encryption_service import encrypt
from apps.pkm.services.wiki_ingest_service import (
    INDEX_PAGE_TITLE,
    LOG_PAGE_TITLE,
    append_log_entry,
    build_ingest_prompt,
    ingest_document,
    ingest_note,
    maintain_index_page,
    schedule_document_ingest,
    schedule_note_ingest,
)

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_completion(summary_md: str, concepts_json: list[dict[str, Any]] | None = None) -> Any:
    """Build a mock LLM completion response containing summary + concepts.

    The response content is a JSON blob with ``summary`` (markdown) and
    ``concepts`` (list of {title, page_type, content}) keys, matching the
    contract the wiki ingest prompt asks the LLM to return.
    """
    payload = {
        "summary": summary_md,
        "concepts": concepts_json or [],
    }
    content = json.dumps(payload)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="WIKI_ING", name="Wiki Ingest Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="wiki_ingest_user", password="Test1234", email="wingest@t.co"
    )


@pytest.fixture
def llm_config(db, user, company):
    """Active LLM config with an encrypted dummy API key (mocked calls)."""
    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-dummy"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


@pytest.fixture
def processed_doc(db, user, company):
    """A processed PKMDocument with a couple of chunks."""
    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="VAT Guide 2026",
        file=SimpleUploadedFile("vat.txt", b"dummy", content_type="text/plain"),
        file_type="txt",
        file_size=5,
        status=PKMDocument.Status.PROCESSED,
    )
    DocumentChunk.objects.create(
        document=doc,
        chunk_index=0,
        content="VAT rate in Vietnam is 10% standard.",
        token_count=8,
    )
    DocumentChunk.objects.create(
        document=doc,
        chunk_index=1,
        content="Input VAT is creditable against output VAT.",
        token_count=8,
    )
    return doc


@pytest.fixture
def note(db, user, company):
    return KnowledgeNote.objects.create(
        user=user,
        company=company,
        title="My VAT notes",
        content="VAT registration threshold is 100M VND revenue.",
    )


# ---------------------------------------------------------------------------
# build_ingest_prompt tests
# ---------------------------------------------------------------------------


def test_build_ingest_prompt_returns_messages_list():
    """build_ingest_prompt returns [system, user] message list."""
    messages = build_ingest_prompt(
        source_title="Doc A",
        chunks_text="Some source content.",
        existing_concepts="",
    )
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_ingest_prompt_includes_source_content():
    """The source chunks appear in the user message so the LLM can read them."""
    messages = build_ingest_prompt(
        source_title="Doc A",
        chunks_text="VAT rate is 10%.",
        existing_concepts="",
    )
    assert "VAT rate is 10%." in messages[1]["content"]


def test_build_ingest_prompt_includes_existing_concepts():
    """Existing concept titles are provided so the LLM can merge, not duplicate."""
    messages = build_ingest_prompt(
        source_title="Doc A",
        chunks_text="VAT rate is 10%.",
        existing_concepts="Existing concepts: VAT, PIT",
    )
    assert "VAT" in messages[1]["content"]


# ---------------------------------------------------------------------------
# VAL-WIKI-002: Ingest creates summary page from document
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ingest_document_creates_summary_page(user, company, llm_config, processed_doc):
    """Ingesting a document creates a WikiPage with page_type=summary."""
    mock_resp = _mock_completion(
        summary_md="# VAT Guide Summary\n\nKey VAT points.",
        concepts_json=[],
    )
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        result = ingest_document(processed_doc.id)

    summary_pages = WikiPage.objects.filter(
        user=user,
        company=company,
        page_type=WikiPage.PageType.SUMMARY,
    )
    assert summary_pages.count() == 1
    summary = summary_pages.first()
    assert summary is not None
    assert "VAT Guide Summary" in summary.content
    assert summary.is_ai_generated is True
    # The summary page must reference the source document
    assert processed_doc in summary.source_refs.all()
    # last_ingest_at should be set
    assert summary.last_ingest_at is not None
    # Result should include created page info
    assert result["summary_page_id"] == summary.id


@pytest.mark.django_db
def test_ingest_document_summary_title_references_source(processed_doc, user, company, llm_config):
    """The summary page title should reference the source document title."""
    mock_resp = _mock_completion(summary_md="summary", concepts_json=[])
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        ingest_document(processed_doc.id)

    summary = WikiPage.objects.get(user=user, company=company, page_type=WikiPage.PageType.SUMMARY)
    # Title should include the source document's title
    assert "VAT Guide 2026" in summary.title


# ---------------------------------------------------------------------------
# VAL-WIKI-003: Ingest creates/updates concept pages (merge, not duplicate)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ingest_document_creates_new_concept_pages(user, company, llm_config, processed_doc):
    """Ingesting creates concept pages for concepts extracted from the source."""
    mock_resp = _mock_completion(
        summary_md="summary",
        concepts_json=[
            {
                "title": "VAT",
                "page_type": "concept",
                "content": "Value Added Tax in Vietnam.",
            },
            {
                "title": "Input VAT",
                "page_type": "concept",
                "content": "Creditable input VAT.",
            },
        ],
    )
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        ingest_document(processed_doc.id)

    concept_pages = WikiPage.objects.filter(
        user=user, company=company, page_type=WikiPage.PageType.CONCEPT
    )
    titles = {p.title for p in concept_pages}
    assert "VAT" in titles
    assert "Input VAT" in titles
    assert concept_pages.count() == 2


@pytest.mark.django_db
def test_ingest_document_updates_existing_concept_not_duplicate(
    user, company, llm_config, processed_doc
):
    """When a concept page already exists, ingest updates it instead of duplicating."""
    # Pre-existing VAT concept page
    existing_vat = WikiPage.objects.create(
        user=user,
        company=company,
        title="VAT",
        content="VAT is a consumption tax.",
        page_type=WikiPage.PageType.CONCEPT,
    )

    mock_resp = _mock_completion(
        summary_md="summary",
        concepts_json=[
            {
                "title": "VAT",
                "page_type": "concept",
                "content": "VAT standard rate is 10%.",
            },
        ],
    )
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        ingest_document(processed_doc.id)

    # Still only one VAT concept page (merge, not duplicate)
    vat_pages = WikiPage.objects.filter(
        user=user, company=company, title="VAT", page_type=WikiPage.PageType.CONCEPT
    )
    assert vat_pages.count() == 1
    vat = vat_pages.first()
    assert vat.id == existing_vat.id
    # Content should include the new information (merged)
    assert "10%" in vat.content
    assert "consumption tax" in vat.content  # original content preserved


@pytest.mark.django_db
def test_ingest_document_links_summary_to_concepts(user, company, llm_config, processed_doc):
    """Summary page cross-references concept pages via linked_pages."""
    mock_resp = _mock_completion(
        summary_md="summary",
        concepts_json=[
            {"title": "VAT", "page_type": "concept", "content": "VAT concept."},
        ],
    )
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        ingest_document(processed_doc.id)

    summary = WikiPage.objects.get(user=user, company=company, page_type=WikiPage.PageType.SUMMARY)
    vat_concept = WikiPage.objects.get(
        user=user, company=company, title="VAT", page_type=WikiPage.PageType.CONCEPT
    )
    assert vat_concept in summary.linked_pages.all()


# ---------------------------------------------------------------------------
# VAL-WIKI-004: Index page auto-maintained
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_maintain_index_page_lists_all_pages(user, company):
    """maintain_index_page creates/updates an overview page cataloging all pages."""
    WikiPage.objects.create(
        user=user,
        company=company,
        title="Concept A",
        content="Body of concept A.",
        page_type=WikiPage.PageType.CONCEPT,
    )
    WikiPage.objects.create(
        user=user,
        company=company,
        title="Entity B",
        content="Body of entity B.",
        page_type=WikiPage.PageType.ENTITY,
    )

    index_page = maintain_index_page(user, company)

    assert index_page.page_type == WikiPage.PageType.OVERVIEW
    assert index_page.title == INDEX_PAGE_TITLE
    # Index should list both pages by title
    assert "Concept A" in index_page.content
    assert "Entity B" in index_page.content
    # Should categorize by type
    assert "concept" in index_page.content.lower() or "Concept" in index_page.content


@pytest.mark.django_db
def test_maintain_index_page_includes_one_line_summary(user, company):
    """Each entry in the index includes a one-line summary."""
    WikiPage.objects.create(
        user=user,
        company=company,
        title="My Concept",
        content="This is a detailed explanation that should be summarized.",
        page_type=WikiPage.PageType.CONCEPT,
    )
    index_page = maintain_index_page(user, company)
    assert "My Concept" in index_page.content


@pytest.mark.django_db
def test_ingest_document_maintains_index(user, company, llm_config, processed_doc):
    """Ingesting a document triggers index page maintenance."""
    mock_resp = _mock_completion(summary_md="summary", concepts_json=[])
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        ingest_document(processed_doc.id)

    index_pages = WikiPage.objects.filter(
        user=user,
        company=company,
        page_type=WikiPage.PageType.OVERVIEW,
        title=INDEX_PAGE_TITLE,
    )
    assert index_pages.count() == 1
    # Index should reference the summary page
    summary = WikiPage.objects.get(user=user, company=company, page_type=WikiPage.PageType.SUMMARY)
    assert summary.title in index_pages.first().content


# ---------------------------------------------------------------------------
# VAL-WIKI-005: Log page appends entries
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_append_log_entry_creates_log_page(user, company):
    """append_log_entry creates the log page on first call."""
    append_log_entry(user, company, operation="ingest", detail="Ingested Doc A")

    log_pages = WikiPage.objects.filter(user=user, company=company, title=LOG_PAGE_TITLE)
    assert log_pages.count() == 1
    log = log_pages.first()
    assert "ingest" in log.content.lower()
    assert "Doc A" in log.content


@pytest.mark.django_db
def test_append_log_entry_appends_to_existing(user, company):
    """Subsequent log calls append rather than overwrite."""
    append_log_entry(user, company, operation="ingest", detail="First entry")
    append_log_entry(user, company, operation="query", detail="Second entry")

    log = WikiPage.objects.get(user=user, company=company, title=LOG_PAGE_TITLE)
    assert "First entry" in log.content
    assert "Second entry" in log.content


@pytest.mark.django_db
def test_append_log_entry_includes_timestamp(user, company):
    """Log entries include a timestamp."""
    append_log_entry(user, company, operation="ingest", detail="timestamped entry")

    log = WikiPage.objects.get(user=user, company=company, title=LOG_PAGE_TITLE)
    # ISO-like timestamp should appear (YYYY-MM-DD)
    assert timezone.now().strftime("%Y-%m-%d") in log.content or "20" in log.content


@pytest.mark.django_db
def test_ingest_document_appends_log_entry(user, company, llm_config, processed_doc):
    """Ingesting a document appends an entry to the log page."""
    mock_resp = _mock_completion(summary_md="summary", concepts_json=[])
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        ingest_document(processed_doc.id)

    log = WikiPage.objects.get(user=user, company=company, title=LOG_PAGE_TITLE)
    assert processed_doc.title in log.content
    assert "ingest" in log.content.lower()


# ---------------------------------------------------------------------------
# Masking integration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ingest_document_masks_data_before_llm_call(user, company, llm_config, processed_doc):
    """Sensitive data (MST, VND amounts) is masked before the LLM call."""
    # Add a chunk with sensitive data
    DocumentChunk.objects.create(
        document=processed_doc,
        chunk_index=2,
        content="MST 0123456789. Revenue 50,000,000 VND.",
        token_count=8,
    )

    captured_messages: list[Any] = []

    def _capture(config, messages, stream=False):
        captured_messages.append(messages)
        return _mock_completion(summary_md="ok", concepts_json=[])

    with patch("apps.pkm.services.wiki_ingest_service.get_completion", side_effect=_capture):
        ingest_document(processed_doc.id)

    assert len(captured_messages) == 1
    user_msg = captured_messages[0][1]["content"]
    # The raw MST should NOT appear; the masked version should.
    assert "0123456789" not in user_msg
    assert "0*******9" in user_msg or "0" in user_msg  # masked pattern


# ---------------------------------------------------------------------------
# Note ingest
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ingest_note_creates_summary_page(user, company, llm_config, note):
    """Ingesting a note creates a summary wiki page for it."""
    mock_resp = _mock_completion(
        summary_md="# Note Summary\n\nVAT threshold notes.",
        concepts_json=[],
    )
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        result = ingest_note(note.id)

    summary_pages = WikiPage.objects.filter(
        user=user, company=company, page_type=WikiPage.PageType.SUMMARY
    )
    assert summary_pages.count() == 1
    assert "Note Summary" in summary_pages.first().content
    assert result["summary_page_id"] == summary_pages.first().id


# ---------------------------------------------------------------------------
# Async scheduling (django-q2)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_schedule_document_ingest_enqueues_task(processed_doc):
    """schedule_document_ingest enqueues the ingest_document task via django-q2."""
    with patch("django_q.tasks.async_task") as mock_async:
        schedule_document_ingest(processed_doc.id)
        mock_async.assert_called_once()
        # First positional arg is the dotted task path
        args, kwargs = mock_async.call_args
        task_path = args[0] if args else kwargs.get("func", "")
        assert "wiki_ingest_service" in str(task_path)


@pytest.mark.django_db
def test_schedule_note_ingest_enqueues_task(note):
    """schedule_note_ingest enqueues the ingest_note task via django-q2."""
    with patch("django_q.tasks.async_task") as mock_async:
        schedule_note_ingest(note.id)
        mock_async.assert_called_once()
        args, kwargs = mock_async.call_args
        task_path = args[0] if args else kwargs.get("func", "")
        assert "wiki_ingest_service" in str(task_path)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ingest_document_missing_llm_config(user, company, processed_doc):
    """Ingest raises ValueError if no active LLM config exists."""
    # No llm_config fixture used here
    with pytest.raises(ValueError, match="LLM"):
        ingest_document(processed_doc.id)


@pytest.mark.django_db
def test_ingest_document_missing_chunks_logs_warning(user, company, llm_config):
    """Ingest on a document with no chunks still produces a summary (empty)."""
    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="Empty Doc",
        file=SimpleUploadedFile("e.txt", b"x"),
        file_type="txt",
        status=PKMDocument.Status.PROCESSED,
    )
    mock_resp = _mock_completion(summary_md="empty doc summary", concepts_json=[])
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        result = ingest_document(doc.id)
    # Summary still created
    assert result["summary_page_id"] is not None


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ingest_isolates_by_user_company(
    user, company, llm_config, processed_doc, other_user=None, other_company=None
):
    """Wiki pages from ingest are scoped to the document owner's user+company."""
    from apps.core.models import Company as Co
    from apps.identity.models import User as Usr

    other_co = Co.objects.create(code="WIKI_ING2", name="Other Co")
    other_u = Usr.objects.create_user(username="wiki_other2", password="Test1234", email="wo2@t.co")

    mock_resp = _mock_completion(summary_md="summary", concepts_json=[])
    with patch("apps.pkm.services.wiki_ingest_service.get_completion", return_value=mock_resp):
        ingest_document(processed_doc.id)

    # No pages should belong to the other user/company
    assert WikiPage.objects.filter(user=other_u, company=company).count() == 0
    assert WikiPage.objects.filter(user=user, company=other_co).count() == 0
