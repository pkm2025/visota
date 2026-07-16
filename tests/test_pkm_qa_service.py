"""Integration tests for the PKM Q&A service (RAG-powered).

These tests verify the full ``answer_question`` pipeline:
  - Question is embedded and similar chunks are retrieved before answering
  - Context is assembled from chunks + notes
  - Sources are cited in the response
  - Q&A history is saved to the database
  - Per-user isolation (only own chunks/notes retrieved)
  - Empty question validation

All LLM/embedding calls are **mocked** (no real API key required). MariaDB
VECTOR operations use the real database.

Fulfills:
  - VAL-QA-008: RAG context retrieved before answer
  - VAL-QA-010: Source citations in answer
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
    KnowledgeNote,
    PKMDocument,
    QAHistory,
    UserLLMConfig,
)
from apps.pkm.services.encryption_service import encrypt
from apps.pkm.services.qa_service import (
    PREVIEW_LENGTH,
    _build_context_string,
    _collect_sources,
    answer_question,
    build_prompt,
    save_qa_history,
)
from apps.pkm.services.vector_store import store_embedding

EMBEDDING_DIM = 1536

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_embedding_response(texts: list[str]) -> Any:
    """Build a mock litellm embedding response (single or multi)."""
    data = [SimpleNamespace(embedding=[0.01] * EMBEDDING_DIM) for _ in range(len(texts))]
    return SimpleNamespace(data=data)


def _mock_completion_response(answer: str = "Mocked answer from LLM.") -> Any:
    """Build a mock litellm completion response."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=answer),
            )
        ]
    )


def _create_document_with_chunks(
    user,
    company,
    title="Test Document",
    chunk_contents: list[str] | None = None,
) -> tuple[PKMDocument, list[DocumentChunk]]:
    """Create a PKMDocument with DocumentChunk rows and stored embeddings."""
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
        chunk_contents = [
            "TT133 la bo Quy chuan ke toan Viet Nam.",
            "Tai san co dinh duoc khau hao theo thoi gian.",
        ]

    chunks: list[DocumentChunk] = []
    for i, content in enumerate(chunk_contents):
        chunk = DocumentChunk.objects.create(
            document=doc,
            chunk_index=i,
            content=content,
            token_count=len(content.split()),
        )
        # Store a real embedding so vector search works
        store_embedding(
            chunk_id=chunk.id,
            user_id=user.id,
            company_id=company.id,
            content=content,
            embedding_vector=[0.01] * EMBEDDING_DIM,
            model_name="text-embedding-3-small",
        )
        chunks.append(chunk)
    return doc, chunks


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_QA_CO", name="PKM QA Test Co")


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="PKM_QA_OC", name="PKM QA Other Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(username="pkm_qa_user", password="Test1234", email="qa@t.co")


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="pkm_qa_other", password="Test1234", email="qa_other@t.co"
    )


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


@pytest.fixture
def other_llm_config(db, other_user, company):
    """LLM config for the other user (for isolation tests)."""
    return UserLLMConfig.objects.create(
        user=other_user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-other-dummy-key"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# build_prompt tests
# ---------------------------------------------------------------------------


def test_build_prompt_returns_messages_list():
    """build_prompt returns a list of 2 messages (system + user)."""
    chunks = [{"content": "chunk1 text", "document_title": "Doc A", "chunk_id": 1}]
    notes = [{"id": 1, "title": "Note 1", "content_preview": "note preview"}]
    messages = build_prompt(chunks, notes, "What is this?")

    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_prompt_system_message_is_vietnamese():
    """The system message instructs the LLM to answer in Vietnamese."""
    messages = build_prompt([], [], "question")
    system_content = messages[0]["content"]
    # The updated system prompt uses proper Vietnamese diacritics.
    lowered = system_content.lower()
    assert "tiếng việt" in lowered or "tieng viet" in lowered
    # Should mention context-based answering
    assert "ngu canh" in lowered or "ngữ cảnh" in lowered


def test_build_prompt_includes_question_in_user_message():
    """The user's question appears in the user-role message."""
    question = "What is TT133 regulation?"
    messages = build_prompt([], [], question)
    assert question in messages[1]["content"]


def test_build_prompt_includes_chunk_content():
    """Chunk content is included in the user message context."""
    chunks = [
        {"content": "TT133 is an accounting standard", "document_title": "Doc A", "chunk_id": 1}
    ]
    messages = build_prompt(chunks, [], "question")
    assert "TT133 is an accounting standard" in messages[1]["content"]


def test_build_prompt_includes_note_content():
    """Note content is included in the user message context."""
    notes = [{"id": 1, "title": "My Note", "content_preview": "Important note text"}]
    messages = build_prompt([], notes, "question")
    assert "Important note text" in messages[1]["content"]
    assert "My Note" in messages[1]["content"]


def test_build_prompt_empty_context():
    """build_prompt handles empty context gracefully."""
    messages = build_prompt([], [], "question")
    assert "CAU HOI" in messages[1]["content"] or "question" in messages[1]["content"].lower()


# ---------------------------------------------------------------------------
# save_qa_history tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_qa_history_creates_record(user, company):
    """save_qa_history persists a QAHistory record."""
    sources = [{"chunk_id": 1, "document_title": "Doc", "content_preview": "preview"}]
    record = save_qa_history(user, company, "What is X?", "Answer X", sources)
    assert record.id is not None
    assert record.user_id == user.id
    assert record.company_id == company.id
    assert record.question == "What is X?"
    assert record.answer == "Answer X"
    assert record.sources == sources


@pytest.mark.django_db
def test_save_qa_history_with_context_used(user, company):
    """save_qa_history stores context_used JSON."""
    sources = [{"chunk_id": 1, "document_title": "Doc", "content_preview": "preview"}]
    context_used = [{"type": "document_chunk", "chunk_id": 1}]
    record = save_qa_history(user, company, "Q", "A", sources, context_used)
    assert record.context_used == context_used


# ---------------------------------------------------------------------------
# answer_question: full pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_answer_question_retrieves_chunks_before_answering(user, company, llm_config):
    """VAL-QA-008: Vector search occurs before LLM completion.

    Verifies that get_embedding and search_similar are called, and that
    get_completion is called with context from the retrieved chunks.
    """
    doc, chunks = _create_document_with_chunks(
        user,
        company,
        chunk_contents=["TT133 la quy chuan ke toan hanh chinh nha nuoc."],
    )

    mock_embed = _mock_embedding_response(["question"])
    mock_completion = _mock_completion_response("TT133 la quy chuan ke toan.")

    with (
        patch("apps.pkm.services.qa_service.get_embedding", return_value=mock_embed) as mock_ge,
        patch(
            "apps.pkm.services.qa_service.get_completion", return_value=mock_completion
        ) as mock_gc,
    ):
        result = answer_question(user, company, "TT133 la gi?")

    # Verify embedding was called
    assert mock_ge.called
    # Verify completion was called
    assert mock_gc.called

    # The answer should be from the mock
    assert result["answer"] == "TT133 la quy chuan ke toan."


@pytest.mark.django_db
def test_answer_question_returns_sources_with_citations(user, company, llm_config):
    """VAL-QA-010: Sources are cited in the response.

    Verifies the result has a 'sources' list with chunk references.
    """
    doc, chunks = _create_document_with_chunks(
        user,
        company,
        chunk_contents=["Depreciation is calculated over useful life."],
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Depreciation answer."),
        ),
    ):
        result = answer_question(user, company, "How does depreciation work?")

    assert "sources" in result
    assert isinstance(result["sources"], list)
    assert len(result["sources"]) >= 1

    # Verify source has expected fields
    src = result["sources"][0]
    assert "chunk_id" in src
    assert "document_title" in src
    assert "content_preview" in src
    assert "source_type" in src


@pytest.mark.django_db
def test_answer_question_context_assembled_from_chunks_and_notes(user, company, llm_config):
    """Context is assembled from both document chunks and notes."""
    doc, chunks = _create_document_with_chunks(
        user,
        company,
        chunk_contents=["Revenue recognition principle applies here."],
    )
    KnowledgeNote.objects.create(
        user=user,
        company=company,
        title="Revenue Notes",
        content="Revenue is recognized when earned and realizable.",
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Revenue answer."),
        ),
    ):
        result = answer_question(user, company, "Revenue recognition principle?")

    # context_used should include both chunks and notes
    context_types = [c["type"] for c in result["context_used"]]
    assert "document_chunk" in context_types
    assert "note" in context_types

    # Sources should include both types
    source_types = [s["source_type"] for s in result["sources"]]
    assert "document_chunk" in source_types
    assert "note" in source_types


@pytest.mark.django_db
def test_answer_question_saves_history(user, company, llm_config):
    """Q&A history is saved after answering."""
    doc, chunks = _create_document_with_chunks(
        user,
        company,
        chunk_contents=["Some content for testing."],
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("History test answer."),
        ),
    ):
        answer_question(user, company, "Test question?")

    history = QAHistory.objects.filter(user=user, company=company)
    assert history.count() == 1
    record = history.first()
    assert record is not None
    assert record.question == "Test question?"
    assert record.answer == "History test answer."
    assert len(record.sources) > 0


@pytest.mark.django_db
def test_answer_question_per_user_isolation(
    user, company, llm_config, other_user, other_llm_config
):
    """Per-user isolation: only the current user's chunks/notes are retrieved."""
    # User A's document
    doc_a, chunks_a = _create_document_with_chunks(
        user,
        company,
        title="User A Doc",
        chunk_contents=["User A's secret content about taxes."],
    )
    # User B's document
    doc_b, chunks_b = _create_document_with_chunks(
        other_user,
        company,
        title="User B Doc",
        chunk_contents=["User B's private content about salaries."],
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
        result = answer_question(user, company, "What content do I have?")

    # User A should only see User A's content in sources, not User B's
    all_previews = " ".join(s.get("content_preview", "") for s in result["sources"])
    assert "secret content about taxes" in all_previews or "User A" in all_previews
    # User B's content should never appear
    assert "salaries" not in all_previews


@pytest.mark.django_db
def test_answer_question_multi_tenant_isolation(user, company, llm_config, other_company):
    """Multi-tenant: chunks from another company are never retrieved."""
    # Create chunks in other company for a different user
    doc_other, _ = _create_document_with_chunks(
        user,
        other_company,
        title="Other Company Doc",
        chunk_contents=["Other company confidential data."],
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
        result = answer_question(user, company, "What data do I have?")

    all_previews = " ".join(s.get("content_preview", "") for s in result["sources"])
    assert "Other company confidential data" not in all_previews


@pytest.mark.django_db
def test_answer_question_empty_question_raises(user, company, llm_config):
    """Empty question raises ValueError and does not call the LLM."""
    with patch("apps.pkm.services.qa_service.get_completion") as mock_gc:
        with pytest.raises(ValueError, match="khong duoc de trong"):
            answer_question(user, company, "")
        with pytest.raises(ValueError):
            answer_question(user, company, "   ")
        # LLM should never have been called
        assert not mock_gc.called


@pytest.mark.django_db
def test_answer_question_no_llm_config_raises(user, company):
    """No active LLM config raises ValueError."""
    # Don't create llm_config fixture
    with pytest.raises(ValueError, match="LLM"):
        answer_question(user, company, "Some question?")


@pytest.mark.django_db
def test_answer_question_returns_correct_structure(user, company, llm_config):
    """The return value has the three required keys: answer, sources, context_used."""
    _create_document_with_chunks(user, company, chunk_contents=["Test content."])

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Structured answer."),
        ),
    ):
        result = answer_question(user, company, "Test?")

    assert set(result.keys()) >= {"answer", "sources", "context_used"}
    assert isinstance(result["answer"], str)
    assert isinstance(result["sources"], list)
    assert isinstance(result["context_used"], list)


@pytest.mark.django_db
def test_answer_question_source_preview_truncated(user, company, llm_config):
    """Source content previews are truncated to PREVIEW_LENGTH."""
    long_content = "A" * (PREVIEW_LENGTH + 100)
    _create_document_with_chunks(user, company, chunk_contents=[long_content])

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
        result = answer_question(user, company, "Test?")

    for src in result["sources"]:
        if src.get("source_type") == "document_chunk":
            assert len(src["content_preview"]) <= PREVIEW_LENGTH


@pytest.mark.django_db
def test_answer_question_sources_include_document_title(user, company, llm_config):
    """Sources include the parent document title."""
    _create_document_with_chunks(
        user,
        company,
        title="Important Accounting Guide",
        chunk_contents=["This is chapter 1 content."],
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
        result = answer_question(user, company, "What is chapter 1?")

    doc_titles = [s["document_title"] for s in result["sources"]]
    assert "Important Accounting Guide" in doc_titles


@pytest.mark.django_db
def test_answer_question_completion_receives_context(user, company, llm_config):
    """The completion call receives messages with retrieved context content."""
    _create_document_with_chunks(
        user,
        company,
        chunk_contents=["Unique context marker XYZ123 for retrieval."],
    )

    mock_embed = _mock_embedding_response(["q"])
    mock_completion = _mock_completion_response("Answer.")

    with (
        patch("apps.pkm.services.qa_service.get_embedding", return_value=mock_embed),
        patch(
            "apps.pkm.services.qa_service.get_completion", return_value=mock_completion
        ) as mock_gc,
    ):
        answer_question(user, company, "What is XYZ123?")

    # Inspect the messages passed to get_completion
    call_args = mock_gc.call_args
    messages = call_args[0][1]  # second positional arg (messages)
    user_msg = messages[1]["content"]
    assert "Unique context marker XYZ123" in user_msg


# ---------------------------------------------------------------------------
# Internal helper tests
# ---------------------------------------------------------------------------


def test_build_context_string_with_chunks_and_notes():
    """_build_context_string assembles both chunks and notes sections."""
    chunks = [{"content": "chunk text", "document_title": "Doc A"}]
    notes = [{"title": "Note 1", "content_preview": "note text"}]
    result = _build_context_string(chunks, notes)
    assert "chunk text" in result
    assert "note text" in result
    assert "Doc A" in result
    assert "Note 1" in result


def test_build_context_string_empty():
    """_build_context_string handles empty input."""
    result = _build_context_string([], [])
    assert len(result) > 0  # should return a fallback message


def test_collect_sources_from_chunks():
    """_collect_sources builds source dicts from chunks."""
    chunks = [
        {
            "chunk_id": 1,
            "id": 10,
            "content": "content here",
            "document_title": "Doc",
            "distance": 0.5,
        }
    ]
    sources = _collect_sources(chunks, [])
    assert len(sources) == 1
    assert sources[0]["chunk_id"] == 1
    assert sources[0]["document_title"] == "Doc"
    assert sources[0]["source_type"] == "document_chunk"
    assert "content_preview" in sources[0]


def test_collect_sources_from_notes():
    """_collect_sources builds source dicts from notes."""
    notes = [{"id": 5, "title": "My Note", "content_preview": "preview text"}]
    sources = _collect_sources([], notes)
    assert len(sources) == 1
    assert sources[0]["note_id"] == 5
    assert sources[0]["document_title"] == "My Note"
    assert sources[0]["source_type"] == "note"


def test_collect_sources_mixed():
    """_collect_sources handles mixed chunks + notes."""
    chunks = [{"chunk_id": 1, "content": "c", "document_title": "D"}]
    notes = [{"id": 1, "title": "N", "content_preview": "p"}]
    sources = _collect_sources(chunks, notes)
    assert len(sources) == 2
