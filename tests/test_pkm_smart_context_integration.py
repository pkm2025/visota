"""Integration tests for smart-context integration in the Q&A pipeline.

These tests verify VAL-CAP-008: the interaction context summary is included
in the Q&A prompt when the user asks a question.

Specifically:
  - ``answer_question`` calls ``interaction_service.get_context_summary``
  - The context summary is visible in the messages list passed to the LLM
  - The context summary appears as a 'Recent user activity' section prepended
    to the RAG context
  - The Q&A API response includes a 'context used' indicator
  - The interaction summary is persisted in Q&A history

All LLM/embedding calls are **mocked** (no real API key required).

Fulfills:
  - VAL-CAP-008: Activity summary included in Q&A context
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import (
    DocumentChunk,
    PKMDocument,
    QAHistory,
    UserLLMConfig,
)
from apps.pkm.services.encryption_service import encrypt
from apps.pkm.services.interaction_service import log_interaction
from apps.pkm.services.qa_service import (
    _build_context_string,
    answer_question,
    build_prompt,
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
        file=SimpleUploadedFile("ctx_test.txt", b"dummy", content_type="text/plain"),
        file_type="txt",
        file_size=5,
        status=PKMDocument.Status.PROCESSED,
    )
    if chunk_contents is None:
        chunk_contents = [
            "TT133 la bo Quy chuan ke toan Viet Nam.",
        ]

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
    return Company.objects.create(
        code="PKM_CTX_CO",
        name="PKM Context Test Co",
        tax_code="0105550001",
        accounting_regime="tt133",
    )


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="pkm_ctx_user", password="Test1234", email="ctx@t.co"
    )


@pytest.fixture
def client(user):
    """Authenticated test client for ``user``."""
    c = Client()
    c.force_login(user)
    return c


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
def interaction_logs(db, user, company):
    """Create some interaction logs for the user so get_context_summary has data."""
    with patch(
        "apps.pkm.services.interaction_service._django_q_available", return_value=False
    ):
        for _ in range(3):
            log_interaction(user, company, "page_view", "ledger")
        for _ in range(2):
            log_interaction(user, company, "note_create", "pkm")
        log_interaction(user, company, "document_create", "pkm")


# ===========================================================================
# VAL-CAP-008: answer_question calls get_context_summary
# ===========================================================================


@pytest.mark.django_db
def test_answer_question_calls_get_context_summary(user, company, llm_config):
    """VAL-CAP-008: answer_question calls interaction_service.get_context_summary."""
    _create_document_with_chunks(user, company, chunk_contents=["Test content."])

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Answer."),
        ),
        patch(
            "apps.pkm.services.qa_service.get_context_summary",
            return_value="Recently: viewed 3 ledger pages, created 2 notes.",
        ) as mock_ctx,
    ):
        answer_question(user, company, "What is this?")

    # get_context_summary must have been called with user and company
    assert mock_ctx.called
    call_args = mock_ctx.call_args
    # Verify it was called with the right user and company
    assert call_args[0][0] == user or call_args.kwargs.get("user") == user
    assert call_args[0][1] == company or call_args.kwargs.get("company") == company


@pytest.mark.django_db
def test_answer_question_includes_interaction_context_in_messages(
    user, company, llm_config, interaction_logs
):
    """VAL-CAP-008: The interaction context summary appears in the messages passed to the LLM."""
    _create_document_with_chunks(user, company, chunk_contents=["Test content for retrieval."])

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
        answer_question(user, company, "What is this?")

    # Inspect the messages passed to get_completion
    assert mock_gc.called
    call_args = mock_gc.call_args
    # Second positional arg is the messages list
    messages = call_args[0][1]
    assert isinstance(messages, list)
    assert len(messages) == 2

    # The user message should contain the interaction context summary
    user_message = messages[1]["content"]
    # The user had interaction logs (3 page views, 2 notes, 1 document)
    # The summary should mention these counts
    assert "3" in user_message  # 3 page views
    assert "2" in user_message  # 2 notes


@pytest.mark.django_db
def test_answer_question_includes_recent_activity_label(
    user, company, llm_config, interaction_logs
):
    """The prompt includes a 'Recent user activity' section label."""
    _create_document_with_chunks(user, company, chunk_contents=["Content."])

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
        answer_question(user, company, "Question?")

    messages = mock_gc.call_args[0][1]
    user_message = messages[1]["content"]
    # The 'Recent user activity' label should be present
    assert "Recent user activity" in user_message or "HOAT DONG" in user_message


@pytest.mark.django_db
def test_answer_question_interaction_context_prepended_before_rag(
    user, company, llm_config, interaction_logs
):
    """The interaction context section appears BEFORE the document chunks section."""
    _create_document_with_chunks(
        user,
        company,
        chunk_contents=["UNIQUE_CHUNK_MARKER_12345 for ordering test."],
    )

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
        answer_question(user, company, "Question?")

    messages = mock_gc.call_args[0][1]
    user_message = messages[1]["content"]

    # The interaction context section should come before the chunk content
    activity_pos = user_message.find("HOAT DONG")
    if activity_pos == -1:
        activity_pos = user_message.find("Recent user activity")
    chunk_pos = user_message.find("UNIQUE_CHUNK_MARKER_12345")

    assert activity_pos != -1, "Interaction context section not found in message"
    assert chunk_pos != -1, "Chunk content not found in message"
    assert activity_pos < chunk_pos, "Interaction context should appear before RAG chunks"


@pytest.mark.django_db
def test_answer_question_returns_interaction_context_in_result(
    user, company, llm_config, interaction_logs
):
    """The answer_question result dict includes the interaction_context field."""
    _create_document_with_chunks(user, company, chunk_contents=["Content."])

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
        result = answer_question(user, company, "Question?")

    assert "interaction_context" in result
    assert isinstance(result["interaction_context"], str)
    assert len(result["interaction_context"]) > 0


@pytest.mark.django_db
def test_answer_question_saves_interaction_context_in_history(
    user, company, llm_config, interaction_logs
):
    """The interaction context summary is persisted in QAHistory."""
    _create_document_with_chunks(user, company, chunk_contents=["Content."])

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
        answer_question(user, company, "Question?")

    record = QAHistory.objects.filter(user=user, company=company).first()
    assert record is not None
    assert record.interaction_context  # should be non-empty
    assert "3" in record.interaction_context or "Recently" in record.interaction_context


@pytest.mark.django_db
def test_answer_question_works_without_interaction_logs(user, company, llm_config):
    """answer_question still works when there are no interaction logs (empty summary)."""
    _create_document_with_chunks(user, company, chunk_contents=["Content."])

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
        result = answer_question(user, company, "Question?")

    # Should still return a valid result even with no interaction logs
    assert result["answer"] == "Answer."
    assert "interaction_context" in result
    # Summary will indicate no recent activity, but it's still a string
    assert isinstance(result["interaction_context"], str)


# ===========================================================================
# build_prompt with interaction context
# ===========================================================================


def test_build_prompt_with_interaction_context():
    """build_prompt includes interaction context in the user message."""
    chunks = [{"content": "chunk text", "document_title": "Doc", "chunk_id": 1}]
    notes = [{"id": 1, "title": "Note", "content_preview": "preview"}]
    interaction_ctx = "Recently: viewed 3 ledger pages, created 2 notes."

    messages = build_prompt(chunks, notes, "question", interaction_ctx)

    user_msg = messages[1]["content"]
    assert "Recently: viewed 3 ledger pages" in user_msg
    assert "chunk text" in user_msg
    assert "preview" in user_msg


def test_build_prompt_without_interaction_context():
    """build_prompt works without interaction context (backward compatible)."""
    chunks = [{"content": "chunk text", "document_title": "Doc", "chunk_id": 1}]
    messages = build_prompt(chunks, [], "question")
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert "chunk text" in messages[1]["content"]


def test_build_prompt_interaction_context_prepended():
    """Interaction context appears at the start of the context, before chunks."""
    chunks = [{"content": "CHUNK_MARKER", "document_title": "Doc", "chunk_id": 1}]
    interaction_ctx = "ACTIVITY_MARKER"

    messages = build_prompt(chunks, [], "question", interaction_ctx)
    user_msg = messages[1]["content"]

    activity_pos = user_msg.find("ACTIVITY_MARKER")
    chunk_pos = user_msg.find("CHUNK_MARKER")
    assert activity_pos < chunk_pos


def test_build_context_string_with_interaction_context():
    """_build_context_string includes the interaction context section."""
    chunks = [{"content": "chunk text", "document_title": "Doc"}]
    result = _build_context_string(chunks, [], "Activity summary text")

    assert "Activity summary text" in result
    assert "chunk text" in result
    # The 'Recent user activity' label should be present
    assert "Recent user activity" in result or "HOAT DONG" in result


def test_build_context_string_without_interaction_context():
    """_build_context_string works without interaction context."""
    chunks = [{"content": "chunk text", "document_title": "Doc"}]
    result = _build_context_string(chunks, [], None)
    assert "chunk text" in result


# ===========================================================================
# API endpoint: context used indicator
# ===========================================================================


@pytest.mark.django_db
def test_api_ask_includes_context_used_indicator(client, user, company, llm_config):
    """POST /api/v1/pkm/qa/ask/ response includes context_used_indicator."""
    _create_document_with_chunks(user, company, chunk_contents=["Test content."])

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
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is this?"},
            content_type="application/json",
        )

    assert response.status_code == 200, response.json()
    data = response.json()
    # The response should include the context_used_indicator field
    assert "context_used_indicator" in data
    assert data["context_used_indicator"] is True


@pytest.mark.django_db
def test_api_ask_includes_interaction_context(client, user, company, llm_config, interaction_logs):
    """POST /api/v1/pkm/qa/ask/ response includes the interaction_context field."""
    _create_document_with_chunks(user, company, chunk_contents=["Content."])

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
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "Question?"},
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    assert "interaction_context" in data
    assert isinstance(data["interaction_context"], str)


@pytest.mark.django_db
def test_api_ask_context_indicator_true_with_only_interaction(
    client, user, company, llm_config, interaction_logs
):
    """context_used_indicator is True even when only interaction context is available."""
    # No documents, no notes - but interaction logs exist
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
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "Question?"},
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    # Even without chunks/notes, the interaction context is present
    assert data["context_used_indicator"] is True
    assert len(data["interaction_context"]) > 0
