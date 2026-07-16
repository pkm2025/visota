"""Tests for the wiki-grounded Q&A pipeline (Karpathy LLM Wiki pattern).

These tests verify that ``qa_service.answer_question`` consults the
**persistent wiki** before falling back to vector search + notes:

  1. When relevant wiki pages exist, the wiki is read and its content is sent
     to the LLM as the primary context.
  2. The vector-search / note-search pipeline (the expensive fallback) is NOT
     invoked when the wiki already has a usable answer.
  3. When the wiki has no relevant pages, the existing RAG fallback
     (vector search + notes) runs as before.
  4. Valuable answers surface a ``suggest_file_to_wiki`` hint so the user can
     persist the synthesized answer back into the wiki.
  5. The wiki ``Log`` page records each query operation (append-only timeline).

All LLM/embedding calls are mocked (no real API key required).

Fulfills:
  - VAL-QA-001: Query reads wiki before vector search.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import (
    DocumentChunk,
    PKMDocument,
    QAHistory,
    UserLLMConfig,
    WikiPage,
)
from apps.pkm.services.encryption_service import encrypt
from apps.pkm.services.qa_service import answer_question
from apps.pkm.services.wiki_ingest_service import (
    LOG_PAGE_TITLE,
    maintain_index_page,
)

EMBEDDING_DIM = 1536

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_embedding_response(texts: list[str]) -> Any:
    data = [SimpleNamespace(embedding=[0.01] * EMBEDDING_DIM) for _ in range(len(texts))]
    return SimpleNamespace(data=data)


def _mock_completion_response(answer: str = "Mocked answer from LLM.") -> Any:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=answer))],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="WIKI_QA_CO", name="Wiki QA Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(username="wiki_qa_user", password="Test1234", email="wqa@t.co")


@pytest.fixture
def llm_config(db, user, company):
    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-dummy"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


def _create_document_with_chunks(
    user,
    company,
    title="Fallback Doc",
    chunk_contents: list[str] | None = None,
):
    """Create a PKMDocument with chunks + embeddings for the vector-search fallback."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title=title,
        file=SimpleUploadedFile("qa_test.txt", b"dummy", content_type="text/plain"),
        file_type="txt",
        file_size=5,
        status=PKMDocument.Status.PROCESSED,
    )
    if chunk_contents is None:
        chunk_contents = ["Fallback vector-search chunk about depreciation."]
    from apps.pkm.services.vector_store import store_embedding

    for i, content in enumerate(chunk_contents):
        chunk = DocumentChunk.objects.create(
            document=doc,
            chunk_index=i,
            content=content,
            token_count=len(content.split()),
        )
        store_embedding(
            chunk_id=chunk.id,
            user_id=user.id,
            company_id=company.id,
            content=content,
            embedding_vector=[0.01] * EMBEDDING_DIM,
            model_name="text-embedding-3-small",
        )
    return doc


def _seed_wiki_page(user, company, *, title, content, page_type=WikiPage.PageType.CONCEPT):
    """Create a wiki page for this tenant."""
    return WikiPage.objects.create(
        user=user,
        company=company,
        title=title,
        content=content,
        page_type=page_type,
        is_ai_generated=True,
    )


# ---------------------------------------------------------------------------
# VAL-QA-001: Wiki consulted before vector search
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_answer_question_reads_wiki_before_vector_search(user, company, llm_config):
    """When wiki has relevant content, vector search is NOT invoked.

    The wiki page about "VAT" should fully answer a VAT question, so the
    expensive embedding + vector-search path is skipped.
    """
    # Seed wiki with relevant content
    _seed_wiki_page(
        user,
        company,
        title="VAT",
        content="# VAT\n\nThe standard VAT rate in Vietnam is 10%.",
    )
    # Also seed the index page so the wiki is "real"
    maintain_index_page(user, company)
    # And a fallback doc that should NOT be consulted
    _create_document_with_chunks(
        user,
        company,
        chunk_contents=["Fallback depreciation content."],
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ) as mock_embed,
        patch(
            "apps.pkm.services.qa_service.search_similar",
            return_value=[],
        ) as mock_search,
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("VAT standard rate is 10%."),
        ) as mock_gc,
    ):
        result = answer_question(user, company, "What is the VAT rate?")

    # Wiki was consulted: vector search must NOT have run
    assert not mock_embed.called, "get_embedding should be skipped when wiki answers the question"
    assert not mock_search.called, "search_similar should be skipped when wiki answers the question"
    # Completion still called
    assert mock_gc.called

    # Result must flag that wiki was the source
    assert result["wiki_consulted"] is True
    # Sources should reference wiki pages
    wiki_sources = [s for s in result["sources"] if s.get("source_type") == "wiki_page"]
    assert len(wiki_sources) >= 1
    assert any("VAT" in s.get("document_title", "") for s in wiki_sources)


@pytest.mark.django_db
def test_answer_question_falls_back_to_vector_search_when_wiki_empty(user, company, llm_config):
    """When wiki has no relevant pages, vector search + notes run as fallback."""
    # No wiki pages exist; only a fallback document
    _create_document_with_chunks(
        user,
        company,
        chunk_contents=["Depreciation is recognized over useful life."],
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ) as mock_embed,
        patch(
            "apps.pkm.services.qa_service.search_similar",
            return_value=[],
        ) as mock_search,
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Depreciation answer."),
        ),
    ):
        result = answer_question(user, company, "How does depreciation work?")

    # Vector search fallback ran
    assert mock_embed.called
    assert mock_search.called
    # Wiki was consulted but yielded nothing useful
    assert result["wiki_consulted"] is False


@pytest.mark.django_db
def test_answer_question_falls_back_to_vector_search_when_wiki_no_match(user, company, llm_config):
    """Wiki exists but no pages match the question -> vector search fallback."""
    # Wiki exists but is about an unrelated topic
    _seed_wiki_page(
        user,
        company,
        title="Payroll",
        content="Payroll is processed monthly.",
    )
    maintain_index_page(user, company)
    _create_document_with_chunks(
        user,
        company,
        chunk_contents=["Depreciation rules for fixed assets."],
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ) as mock_embed,
        patch(
            "apps.pkm.services.qa_service.search_similar",
            return_value=[],
        ) as mock_search,
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Depreciation answer."),
        ),
    ):
        result = answer_question(user, company, "How does depreciation work?")

    # Wiki had no relevant page, so vector search ran
    assert mock_embed.called
    assert mock_search.called
    assert result["wiki_consulted"] is False


@pytest.mark.django_db
def test_answer_question_wiki_content_sent_to_llm(user, company, llm_config):
    """The wiki page content is included in the LLM prompt."""
    _seed_wiki_page(
        user,
        company,
        title="VAT",
        content="# VAT\n\nThe UNIQUE_WIKI_MARKER_42 appears here.",
    )
    maintain_index_page(user, company)

    with (
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Wiki-grounded answer."),
        ) as mock_gc,
    ):
        answer_question(user, company, "Tell me about VAT.")

    call_args = mock_gc.call_args
    messages = call_args[0][1]
    user_msg = messages[1]["content"]
    assert "UNIQUE_WIKI_MARKER_42" in user_msg


# ---------------------------------------------------------------------------
# Suggest filing valuable answers back to the wiki
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_answer_question_suggests_file_to_wiki_on_fallback(user, company, llm_config):
    """When answer comes from vector-search fallback, suggest_file_to_wiki=True."""
    _create_document_with_chunks(
        user,
        company,
        chunk_contents=["Useful depreciation rule that should be persisted."],
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.search_similar",
            return_value=[],
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("A useful synthesized answer."),
        ),
    ):
        result = answer_question(user, company, "Tell me about depreciation.")

    assert result["suggest_file_to_wiki"] is True


@pytest.mark.django_db
def test_answer_question_no_suggest_when_wiki_already_answered(user, company, llm_config):
    """When wiki already answers, no need to re-file the answer."""
    _seed_wiki_page(
        user,
        company,
        title="VAT",
        content="# VAT\n\nThe standard rate is 10%.",
    )
    maintain_index_page(user, company)

    with patch(
        "apps.pkm.services.qa_service.get_completion",
        return_value=_mock_completion_response("Wiki answer."),
    ):
        result = answer_question(user, company, "VAT rate?")

    assert result["wiki_consulted"] is True
    assert result["suggest_file_to_wiki"] is False


# ---------------------------------------------------------------------------
# Query logs to the wiki Log page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_answer_question_appends_query_to_wiki_log(user, company, llm_config):
    """Each query appends a 'query' entry to the wiki Log page."""
    _seed_wiki_page(
        user,
        company,
        title="VAT",
        content="VAT standard rate is 10%.",
    )
    maintain_index_page(user, company)

    with patch(
        "apps.pkm.services.qa_service.get_completion",
        return_value=_mock_completion_response("VAT is 10%."),
    ):
        answer_question(user, company, "What is the VAT rate?")

    log = WikiPage.objects.get(user=user, company=company, title=LOG_PAGE_TITLE)
    assert "query" in log.content.lower()
    # The question text should be referenced in the log
    assert "VAT rate" in log.content


# ---------------------------------------------------------------------------
# Wiki query result structure
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_answer_question_returns_wiki_pages_in_context(user, company, llm_config):
    """The context_used field lists the wiki pages consulted."""
    _seed_wiki_page(
        user,
        company,
        title="VAT",
        content="# VAT\n\nStandard rate is 10%.",
        page_type=WikiPage.PageType.CONCEPT,
    )
    maintain_index_page(user, company)

    with patch(
        "apps.pkm.services.qa_service.get_completion",
        return_value=_mock_completion_response("VAT answer."),
    ):
        result = answer_question(user, company, "VAT rate?")

    wiki_ctx = [c for c in result["context_used"] if c.get("type") == "wiki_page"]
    assert len(wiki_ctx) >= 1
    assert any(c.get("title") == "VAT" for c in wiki_ctx)


# ---------------------------------------------------------------------------
# Index page is read to find relevant pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_answer_question_uses_index_to_select_relevant_pages(user, company, llm_config):
    """The index page (catalog) is consulted to identify relevant wiki pages.

    Even if multiple pages exist, only pages whose title/summary appears
    related to the question should be selected.
    """
    _seed_wiki_page(
        user,
        company,
        title="VAT",
        content="# VAT\n\nStandard rate is 10%.",
    )
    _seed_wiki_page(
        user,
        company,
        title="Payroll",
        content="# Payroll\n\nPayroll runs monthly.",
    )
    maintain_index_page(user, company)

    with patch(
        "apps.pkm.services.qa_service.get_completion",
        return_value=_mock_completion_response("VAT answer."),
    ) as mock_gc:
        answer_question(user, company, "What is VAT?")

    call_args = mock_gc.call_args
    messages = call_args[0][1]
    user_msg = messages[1]["content"]
    # VAT page should be included
    assert "Standard rate is 10%" in user_msg
    # Payroll page should NOT be included (irrelevant)
    assert "Payroll runs monthly" not in user_msg


# ---------------------------------------------------------------------------
# Backward compatibility: existing pipeline still works
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_answer_question_result_structure_has_required_keys(user, company, llm_config):
    """Result retains the original keys plus the new wiki fields."""
    _create_document_with_chunks(user, company)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.search_similar",
            return_value=[],
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Answer."),
        ),
    ):
        result = answer_question(user, company, "Question?")

    # Original keys preserved
    assert "answer" in result
    assert "sources" in result
    assert "context_used" in result
    # New wiki keys
    assert "wiki_consulted" in result
    assert "suggest_file_to_wiki" in result


@pytest.mark.django_db
def test_answer_question_saves_qa_history_with_wiki_flag(user, company, llm_config):
    """QAHistory still saved when wiki is consulted."""
    _seed_wiki_page(
        user,
        company,
        title="VAT",
        content="VAT standard rate is 10%.",
    )
    maintain_index_page(user, company)

    with patch(
        "apps.pkm.services.qa_service.get_completion",
        return_value=_mock_completion_response("VAT answer."),
    ):
        answer_question(user, company, "VAT?")

    history = QAHistory.objects.filter(user=user, company=company)
    assert history.count() == 1
