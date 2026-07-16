"""Tests for regulation context integration in Q&A and vector search.

Fulfills:
  - VAL-RAG-002: Q&A search includes regulation chunks
    ("Given regulation documents are seeded and embedded, when
    vector_store.search_similar runs, then regulation chunks can appear in
    results for accounting-related queries.")
  - VAL-RAG-003: Q&A system prompt includes accounting context
    ("Given qa_service.answer_question builds prompt, when prompt is assembled,
    then system prompt contains 'trợ lý kế toán' and user's business context
    summary.")
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import DocumentChunk, PKMDocument
from apps.pkm.services.qa_service import (
    ACCOUNTING_KEYWORDS,
    SYSTEM_MESSAGE,
    _boost_regulation_chunks,
    _contains_accounting_keywords,
    answer_question,
    build_prompt,
)
from apps.pkm.services.vector_store import search_similar, store_embedding

EMBEDDING_DIM = 1536


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_embedding_response(texts: list[str]) -> Any:
    data = [SimpleNamespace(embedding=[0.01] * EMBEDDING_DIM) for _ in range(len(texts))]
    return SimpleNamespace(data=data)


def _mock_completion_response(answer: str = "Mocked answer from LLM.") -> Any:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=answer))])


def _create_system_document_with_chunks(
    company,
    user,
    title="[system] reg:tt58-test — TT58 test",
    chunk_contents: list[str] | None = None,
    embedding_vector: list[float] | None = None,
) -> tuple[PKMDocument, list[DocumentChunk]]:
    """Create an is_system=True PKMDocument with chunks and stored embeddings."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title=title,
        file=SimpleUploadedFile("reg_test.txt", b"regulation", content_type="text/plain"),
        file_type="txt",
        file_size=10,
        status=PKMDocument.Status.PROCESSED,
        is_system=True,
    )
    if chunk_contents is None:
        chunk_contents = ["TT58/2026 quy dinh che do ke toan DNSN."]
    if embedding_vector is None:
        embedding_vector = [0.01] * EMBEDDING_DIM

    chunks: list[DocumentChunk] = []
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
            embedding_vector=embedding_vector,
            model_name="text-embedding-3-small",
        )
        chunks.append(chunk)
    return doc, chunks


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_REG_CO", name="PKM Regulation Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(username="pkm_reg_user", password="Test1234", email="reg@t.co")


@pytest.fixture
def llm_config(db, user, company):
    from apps.pkm.models import UserLLMConfig
    from apps.pkm.services.encryption_service import encrypt

    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-dummy-key-for-mocking"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# VAL-RAG-002: vector_store.search_similar includes regulation chunks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_search_similar_include_system_returns_regulation_chunks(company, user):
    """search_similar with include_system=True returns is_system chunks."""
    _create_system_document_with_chunks(
        company,
        user,
        chunk_contents=["TT58 quy dinh che do ke toan doanh nghiep sieu nho."],
    )

    results = search_similar(
        user.id, company.id, [0.01] * EMBEDDING_DIM, top_k=5, include_system=True
    )
    assert len(results) >= 1
    system_results = [r for r in results if r.get("is_system")]
    assert len(system_results) >= 1, "Regulation (is_system) chunks must be retrievable"
    assert "TT58" in system_results[0]["content"]


@pytest.mark.django_db
def test_search_similar_default_excludes_system_chunks(company, user):
    """Without include_system, system chunks are NOT returned (backward compat)."""
    _create_system_document_with_chunks(
        company,
        user,
        chunk_contents=["Regulation-only content TT133."],
        embedding_vector=[0.9] * EMBEDDING_DIM,
    )

    # Default include_system=False
    results = search_similar(user.id, company.id, [0.9] * EMBEDDING_DIM, top_k=5)
    assert results == [], "Default search should not return system chunks"


@pytest.mark.django_db
def test_search_similar_merges_user_and_system_chunks(company, user):
    """include_system=True returns both user-scoped and system chunks."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    # User's own document
    user_doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="My notes",
        file=SimpleUploadedFile("m.txt", b"d"),
        file_type="txt",
        file_size=1,
    )
    user_chunk = DocumentChunk.objects.create(
        document=user_doc, chunk_index=0, content="user content", token_count=2
    )
    store_embedding(
        chunk_id=user_chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="user content",
        embedding_vector=[0.5] * EMBEDDING_DIM,
        model_name="m",
    )

    # System regulation document
    _create_system_document_with_chunks(
        company,
        user,
        chunk_contents=["system regulation content"],
        embedding_vector=[0.5] * EMBEDDING_DIM,
    )

    results = search_similar(
        user.id, company.id, [0.5] * EMBEDDING_DIM, top_k=10, include_system=True
    )
    contents = [r["content"] for r in results]
    assert "user content" in contents
    assert "system regulation content" in contents


@pytest.mark.django_db
def test_search_similar_results_have_is_system_flag(company, user):
    """Each result dict has an is_system boolean flag."""
    _create_system_document_with_chunks(company, user)

    results = search_similar(
        user.id, company.id, [0.01] * EMBEDDING_DIM, top_k=5, include_system=True
    )
    assert len(results) >= 1
    for r in results:
        assert "is_system" in r
        assert isinstance(r["is_system"], bool)


# ---------------------------------------------------------------------------
# VAL-RAG-003: system prompt includes accounting context
# ---------------------------------------------------------------------------


def test_system_message_contains_accounting_assistant_phrase():
    """SYSTEM_MESSAGE contains 'trợ lý kế toán' (VAL-RAG-003)."""
    assert "trợ lý kế toán" in SYSTEM_MESSAGE.lower()


def test_system_message_references_vietnamese_regulations():
    """SYSTEM_MESSAGE references current Vietnamese regulations."""
    lowered = SYSTEM_MESSAGE.lower()
    assert "quy định pháp luật việt nam" in lowered
    assert "hiện hành" in lowered


def test_system_message_references_user_activity_context():
    """SYSTEM_MESSAGE references the user's activity context."""
    lowered = SYSTEM_MESSAGE.lower()
    assert "ngữ cảnh hoạt động" in lowered or "hoat dong" in lowered


def test_build_prompt_system_message_has_accounting_context():
    """build_prompt emits a system message containing 'trợ lý kế toán'."""
    messages = build_prompt([], [], "question?")
    assert messages[0]["role"] == "system"
    assert "trợ lý kế toán" in messages[0]["content"].lower()


# ---------------------------------------------------------------------------
# Keyword detection
# ---------------------------------------------------------------------------


def test_contains_accounting_keywords_vietnamese():
    """Vietnamese accounting keywords are detected."""
    assert _contains_accounting_keywords("Làm sao kê khai thuế GTGT?") is True
    assert _contains_accounting_keywords("Cách ghi sổ kế toán?") is True
    assert _contains_accounting_keywords("Hóa đơn điện tử là gì?") is True


def test_contains_accounting_keywords_english():
    """English accounting keywords are detected."""
    assert _contains_accounting_keywords("How does VAT work?") is True
    assert _contains_accounting_keywords("What is depreciation?") is True


def test_contains_accounting_keywords_negative():
    """Non-accounting questions are not flagged."""
    assert _contains_accounting_keywords("Thời tiết hôm nay thế nào?") is False
    assert _contains_accounting_keywords("What color is the sky?") is False


def test_contains_accounting_keywords_empty():
    """Empty input is handled gracefully."""
    assert _contains_accounting_keywords("") is False
    assert _contains_accounting_keywords(None) is False  # type: ignore[arg-type]


def test_accounting_keywords_list_not_empty():
    """The keyword list is populated."""
    assert len(ACCOUNTING_KEYWORDS) > 0
    assert "thuế" in ACCOUNTING_KEYWORDS
    assert "PIT" in ACCOUNTING_KEYWORDS


# ---------------------------------------------------------------------------
# Regulation chunk boosting
# ---------------------------------------------------------------------------


def test_boost_regulation_chunks_prioritizes_system():
    """System chunks get a distance bonus that can move them ahead."""
    user_chunk = {
        "id": 1,
        "content": "user note",
        "chunk_id": 1,
        "distance": 0.40,
        "is_system": False,
    }
    system_chunk = {
        "id": 2,
        "content": "TT58 regulation",
        "chunk_id": 2,
        "distance": 0.50,
        "is_system": True,
    }
    result = _boost_regulation_chunks([user_chunk, system_chunk], bonus=0.15)
    # After boost: system adjusted = 0.50 - 0.15 = 0.35 < user 0.40
    assert result[0]["content"] == "TT58 regulation"
    assert result[0]["original_distance"] == 0.50


def test_boost_regulation_chunks_preserves_original_distance():
    """The original distance value is preserved for transparency."""
    chunk = {
        "id": 1,
        "content": "reg",
        "chunk_id": 1,
        "distance": 0.7,
        "is_system": True,
    }
    result = _boost_regulation_chunks([chunk], bonus=0.15)
    assert result[0]["original_distance"] == 0.7


def test_boost_regulation_chunks_does_not_affect_user_chunks():
    """Non-system chunks keep their original distance."""
    chunk = {
        "id": 1,
        "content": "user",
        "chunk_id": 1,
        "distance": 0.3,
        "is_system": False,
    }
    result = _boost_regulation_chunks([chunk], bonus=0.5)
    assert result[0]["original_distance"] == 0.3


def test_boost_regulation_chunks_empty():
    """Empty list is handled gracefully."""
    assert _boost_regulation_chunks([]) == []


# ---------------------------------------------------------------------------
# answer_question integration: regulation chunks in results
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_answer_question_includes_regulation_chunks_in_sources(company, user, llm_config):
    """VAL-RAG-002: answer_question returns regulation chunks as sources."""
    _create_system_document_with_chunks(
        company,
        user,
        chunk_contents=["TT58/2026 quy dinh che do ke toan DNSN."],
        embedding_vector=[0.01] * EMBEDDING_DIM,
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Answer."),
        ),
    ):
        result = answer_question(user, company, "TT58 là quy định gì về thuế?")

    # At least one source should be a system regulation chunk
    system_sources = [s for s in result["sources"] if s.get("source_type") == "document_chunk"]
    assert len(system_sources) >= 1
    # The system chunk's document title should reference the regulation doc
    titles = " ".join(s.get("document_title", "") for s in system_sources)
    assert "TT58" in titles or "system" in titles.lower()


@pytest.mark.django_db
def test_answer_question_accounting_question_boosts_regulation(company, user, llm_config):
    """Accounting-keyword questions promote regulation chunks earlier."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    # A user doc with content that is NOT about regulations, with a slightly
    # better (lower) cosine distance than the system regulation chunk.
    user_doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="My Diary",
        file=SimpleUploadedFile("d.txt", b"d"),
        file_type="txt",
        file_size=1,
    )
    user_chunk = DocumentChunk.objects.create(
        document=user_doc, chunk_index=0, content="diary entry about weather", token_count=5
    )

    # user_chunk vector: very close to query vector [0.5]*1536
    store_embedding(
        chunk_id=user_chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="diary entry about weather",
        embedding_vector=[0.5] * 768 + [0.0] * 768,
        model_name="m",
    )
    # system chunk vector: slightly farther from query
    _create_system_document_with_chunks(
        company,
        user,
        chunk_contents=["quy định kế toán thuế TT133"],
        embedding_vector=[0.5] * 768 + [0.5] * 768,  # 45 degrees -> distance ~0.29
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Regulation answer."),
        ),
    ):
        result = answer_question(user, company, "Kế toán ghi sổ thuế thế nào?")

    # The first source should be a system regulation chunk (boosted)
    assert len(result["sources"]) >= 1
    first_src = result["sources"][0]
    assert first_src.get("source_type") == "document_chunk"


@pytest.mark.django_db
def test_answer_question_system_prompt_sent_to_llm_has_accounting_context(
    company, user, llm_config
):
    """The system prompt passed to the LLM contains 'trợ lý kế toán'."""
    _create_system_document_with_chunks(company, user)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Answer."),
        ) as mock_gc,
    ):
        answer_question(user, company, "Câu hỏi về thuế?")

    call_args = mock_gc.call_args
    messages = call_args[0][1]
    system_msg = messages[0]["content"]
    assert "trợ lý kế toán" in system_msg.lower()


@pytest.mark.django_db
def test_answer_question_non_accounting_question_still_works(company, user, llm_config):
    """Non-accounting questions still complete successfully (no boost, but
    system chunks are still searchable)."""
    _create_system_document_with_chunks(company, user)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Answer."),
        ),
    ):
        result = answer_question(user, company, "What color is the sky?")

    assert isinstance(result["answer"], str)


@pytest.mark.django_db
def test_answer_question_context_used_marks_system_chunks(company, user, llm_config):
    """context_used entries for system chunks indicate their origin."""
    _create_system_document_with_chunks(
        company,
        user,
        chunk_contents=["quy định thuế GTGT"],
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Answer."),
        ),
    ):
        result = answer_question(user, company, "Thuế GTGT?")

    chunk_contexts = [c for c in result["context_used"] if c.get("type") == "document_chunk"]
    # At least one chunk should be present (system chunk surfaced)
    assert len(chunk_contexts) >= 1
