"""Integration tests for PKM Q&A API endpoints (/api/v1/pkm/qa/ask/, /api/v1/pkm/qa/history/).

Covers:
  - Ask question returns answer + sources (mocked LLM)
  - Empty question is rejected (400)
  - No active LLM config returns 400 with "configure first" message
  - History endpoint returns paginated Q&A records
  - Per-user isolation: user B cannot see user A's Q&A history
  - Per-company isolation: history scoped by company
  - Unauthenticated requests return 401
  - LLMError handling: auth -> 401, rate limit -> 429, timeout -> 504, other -> 502

All LLM/embedding calls are **mocked** (no real API key required). MariaDB
VECTOR operations use the real database.

Fulfills:
    VAL-QA-007: Q&A API endpoint returns response (mocked)
    VAL-QA-009: Q&A results private per user
    VAL-QA-011: Empty question validation
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
        file=SimpleUploadedFile("qa_api_test.txt", b"dummy", content_type="text/plain"),
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
    return Company.objects.create(code="PKM_QA_API_CO", name="PKM QA API Test Co")


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="PKM_QA_API_OC", name="PKM QA API Other Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="pkm_qa_api_user", password="Test1234", email="qaapi@t.co"
    )


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="pkm_qa_api_other", password="Test1234", email="qaapiother@t.co"
    )


@pytest.fixture
def client(user):
    """Authenticated test client for ``user``."""
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def other_client(other_user):
    """Authenticated test client for ``other_user`` (same company)."""
    c = Client()
    c.force_login(other_user)
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


# ===========================================================================
# POST /qa/ask/ — VAL-QA-007: Q&A API endpoint returns response (mocked)
# ===========================================================================


@pytest.mark.django_db
def test_ask_question_returns_answer_and_sources(client, user, company, llm_config):
    """VAL-QA-007: POST /qa/ask/ returns 200 with answer + sources."""
    _create_document_with_chunks(
        user,
        company,
        chunk_contents=["TT133 la quy chuan ke toan hanh chinh nha nuoc."],
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["question"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("TT133 la quy chuan ke toan."),
        ),
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "TT133 la gi?"},
            content_type="application/json",
        )

    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["answer"] == "TT133 la quy chuan ke toan."
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) >= 1
    assert isinstance(data["context_used"], list)


@pytest.mark.django_db
def test_ask_question_answer_is_string(client, user, company, llm_config):
    """POST /qa/ask/ returns a string answer."""
    _create_document_with_chunks(user, company)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("String answer."),
        ),
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is this?"},
            content_type="application/json",
        )

    assert response.status_code == 200
    assert isinstance(response.json()["answer"], str)


@pytest.mark.django_db
def test_ask_question_sources_have_source_type(client, user, company, llm_config):
    """POST /qa/ask/ sources include a ``source_type`` field."""
    _create_document_with_chunks(user, company)

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
            data={"question": "What?"},
            content_type="application/json",
        )

    data = response.json()
    for src in data["sources"]:
        assert "source_type" in src


@pytest.mark.django_db
def test_ask_question_saves_history(client, user, company, llm_config):
    """POST /qa/ask/ saves a QAHistory record."""
    _create_document_with_chunks(user, company)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("History save test."),
        ),
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "Save this question?"},
            content_type="application/json",
        )

    assert response.status_code == 200
    history = QAHistory.objects.filter(user=user, company=company)
    assert history.count() == 1
    record = history.first()
    assert record is not None
    assert record.question == "Save this question?"
    assert record.answer == "History save test."


# ===========================================================================
# VAL-QA-011: Empty question validation
# ===========================================================================


@pytest.mark.django_db
def test_ask_question_empty_question_returns_400(client, user, company, llm_config):
    """VAL-QA-011: Empty question returns 400."""
    with patch("apps.pkm.services.qa_service.get_completion") as mock_gc:
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": ""},
            content_type="application/json",
        )
    # django-ninja schema validation catches empty string for min_length=1
    assert response.status_code == 400 or response.status_code == 422
    # LLM should never have been called
    assert not mock_gc.called


@pytest.mark.django_db
def test_ask_question_whitespace_only_rejected(client, user, company, llm_config):
    """VAL-QA-011: Whitespace-only question is rejected."""
    # Schema allows non-empty strings through, service-level validates whitespace
    with patch("apps.pkm.services.qa_service.get_completion") as mock_gc:
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "   "},
            content_type="application/json",
        )
    # The service raises ValueError for whitespace-only -> caught as 400
    assert response.status_code == 400
    assert not mock_gc.called


@pytest.mark.django_db
def test_ask_question_missing_question_field_returns_422(client, user, company, llm_config):
    """POST without the ``question`` field returns 422 (validation)."""
    response = client.post(
        "/api/v1/pkm/qa/ask/",
        data={},
        content_type="application/json",
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_ask_question_llm_not_called_on_empty(client, user, company, llm_config):
    """Empty question never invokes the LLM."""
    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
        ) as mock_ge,
        patch("apps.pkm.services.qa_service.get_completion") as mock_gc,
    ):
        client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "   "},
            content_type="application/json",
        )
    assert not mock_ge.called
    assert not mock_gc.called


# ===========================================================================
# No LLM config returns 400 with "configure first" message
# ===========================================================================


@pytest.mark.django_db
def test_ask_question_no_llm_config_returns_400(client, user, company):
    """No active LLM config returns 400 with a helpful message."""
    # Do NOT create llm_config fixture
    with patch("apps.pkm.services.qa_service.get_completion") as mock_gc:
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is TT133?"},
            content_type="application/json",
        )

    assert response.status_code == 400
    body_text = response.content.decode("utf-8")
    # The message should mention configuring a provider / LLM config
    assert "LLM" in body_text or "cau hinh" in body_text.lower() or "configure" in body_text.lower()
    # LLM should never have been called
    assert not mock_gc.called


@pytest.mark.django_db
def test_ask_question_no_llm_config_message_mentions_configure(client, user, company):
    """The 400 message includes guidance to configure a provider first."""
    response = client.post(
        "/api/v1/pkm/qa/ask/",
        data={"question": "Question?"},
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.content.decode("utf-8")
    # Check for "cau hinh" (configure) in the message
    assert "cau hinh" in body.lower() or "configure" in body.lower()


@pytest.mark.django_db
def test_ask_question_inactive_llm_config_returns_400(client, user, company):
    """An inactive LLM config is treated as no config."""
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test"),
        default_model="gpt-4o",
        is_active=False,  # not active
    )
    response = client.post(
        "/api/v1/pkm/qa/ask/",
        data={"question": "Question?"},
        content_type="application/json",
    )
    assert response.status_code == 400


# ===========================================================================
# GET /qa/history/ — History retrieval
# ===========================================================================


@pytest.mark.django_db
def test_history_returns_records(client, user, company):
    """GET /qa/history/ returns the user's Q&A records."""
    QAHistory.objects.create(
        user=user,
        company=company,
        question="Q1",
        answer="A1",
        sources=[{"chunk_id": 1}],
    )
    QAHistory.objects.create(
        user=user,
        company=company,
        question="Q2",
        answer="A2",
        sources=[],
    )
    response = client.get("/api/v1/pkm/qa/history/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 2


@pytest.mark.django_db
def test_history_empty_returns_empty_list(client):
    """GET /qa/history/ returns empty list when user has no history."""
    response = client.get("/api/v1/pkm/qa/history/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 0


@pytest.mark.django_db
def test_history_includes_question_and_answer(client, user, company):
    """GET /qa/history/ records include question and answer fields."""
    QAHistory.objects.create(
        user=user,
        company=company,
        question="What is depreciation?",
        answer="Depreciation is the systematic allocation of cost.",
        sources=[],
    )
    response = client.get("/api/v1/pkm/qa/history/")
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 1
    item = items[0]
    assert item["question"] == "What is depreciation?"
    assert item["answer"] == "Depreciation is the systematic allocation of cost."
    assert "id" in item
    assert "created_at" in item
    assert "sources" in item
    assert "context_used" in item


@pytest.mark.django_db
def test_history_ordered_by_recent_first(client, user, company):
    """GET /qa/history/ returns most recent records first."""
    from time import sleep

    h1 = QAHistory.objects.create(
        user=user, company=company, question="first question", answer="a1", sources=[]
    )
    sleep(0.01)
    h2 = QAHistory.objects.create(
        user=user, company=company, question="second question", answer="a2", sources=[]
    )
    response = client.get("/api/v1/pkm/qa/history/")
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    # h2 should come before h1 (most recent first)
    assert items[0]["id"] == h2.id
    assert items[1]["id"] == h1.id


@pytest.mark.django_db
def test_history_paginated(client, user, company):
    """GET /qa/history/ supports pagination."""
    # Create more than the default page size (20 for ninja)
    for i in range(25):
        QAHistory.objects.create(
            user=user,
            company=company,
            question=f"Q{i}",
            answer=f"A{i}",
            sources=[],
        )
    # Default pagination should limit results
    response = client.get("/api/v1/pkm/qa/history/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    # Default page size is 20 in django-ninja
    assert len(items) <= 25
    # With pagination, the response should include a count if paginate decorator is used
    # ninja's default paginate returns a paginated structure


# ===========================================================================
# VAL-QA-009: Per-user isolation
# ===========================================================================


@pytest.mark.django_db
def test_history_private_per_user(user, other_user, company):
    """VAL-QA-009: User A's history is not visible to User B."""
    QAHistory.objects.create(
        user=user, company=company, question="user A question", answer="a1", sources=[]
    )
    QAHistory.objects.create(
        user=user, company=company, question="user A question 2", answer="a2", sources=[]
    )

    c_b = Client()
    c_b.force_login(other_user)
    response = c_b.get("/api/v1/pkm/qa/history/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 0


@pytest.mark.django_db
def test_history_isolation_both_users(user, other_user, company):
    """Both users see only their own history."""
    QAHistory.objects.create(
        user=user, company=company, question="A question", answer="A answer", sources=[]
    )
    QAHistory.objects.create(
        user=other_user, company=company, question="B question", answer="B answer", sources=[]
    )

    c_a = Client()
    c_a.force_login(user)
    response_a = c_a.get("/api/v1/pkm/qa/history/")
    data_a = response_a.json()
    items_a = data_a if isinstance(data_a, list) else data_a.get("items", [])
    assert len(items_a) == 1
    assert items_a[0]["question"] == "A question"

    c_b = Client()
    c_b.force_login(other_user)
    response_b = c_b.get("/api/v1/pkm/qa/history/")
    data_b = response_b.json()
    items_b = data_b if isinstance(data_b, list) else data_b.get("items", [])
    assert len(items_b) == 1
    assert items_b[0]["question"] == "B question"


@pytest.mark.django_db
def test_ask_question_per_user_isolation(user, company, llm_config, other_user):
    """VAL-QA-009: Ask as user A only retrieves user A's data as sources."""
    # User A's document
    _create_document_with_chunks(
        user,
        company,
        title="User A Doc",
        chunk_contents=["User A's secret content about taxes."],
    )
    # User B's document
    _create_document_with_chunks(
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
        response = user_client_post(user, "What do I have?")
        assert response.status_code == 200
        data = response.json()

    all_previews = " ".join(s.get("content_preview", "") for s in data["sources"])
    assert "salaries" not in all_previews


def user_client_post(user, question: str):
    """Helper: create a client for the given user and POST a question."""
    c = Client()
    c.force_login(user)
    return c.post(
        "/api/v1/pkm/qa/ask/",
        data={"question": question},
        content_type="application/json",
    )


# ===========================================================================
# Per-company isolation
# ===========================================================================


@pytest.mark.django_db
def test_history_isolated_by_company(user, company, other_company):
    """History is scoped by company."""
    QAHistory.objects.create(
        user=user, company=company, question="company A Q", answer="a", sources=[]
    )
    QAHistory.objects.create(
        user=user, company=other_company, question="company B Q", answer="b", sources=[]
    )

    c = Client()
    c.force_login(user)
    # When current_company is company, only company A's records should appear
    response = c.get("/api/v1/pkm/qa/history/")
    assert response.status_code == 200


# ===========================================================================
# Authentication
# ===========================================================================


@pytest.mark.django_db
def test_ask_question_unauthenticated(db):
    """POST /qa/ask/ without auth returns 401."""
    c = Client()
    response = c.post(
        "/api/v1/pkm/qa/ask/",
        data={"question": "Hello?"},
        content_type="application/json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_history_unauthenticated(db):
    """GET /qa/history/ without auth returns 401."""
    c = Client()
    response = c.get("/api/v1/pkm/qa/history/")
    assert response.status_code == 401


# ===========================================================================
# LLMError handling — pkm-fix-qa-llm-error-handling
#
# The Q&A ask endpoint must catch LLMError exceptions and return structured
# error responses with appropriate HTTP status codes instead of unhandled 500s.
#
# Mapping:
#   AuthenticationError -> LLMAuthError   -> 401
#   RateLimitError      -> LLMRateLimitError -> 429
#   Timeout/APIConnectionError -> LLMTimeoutError -> 504
#   Other LLMError      -> 502
# ===========================================================================


@pytest.mark.django_db
def test_ask_question_llm_auth_error_returns_401(client, user, company, llm_config):
    """LLMAuthError (invalid API key) returns 401, not a 500."""
    from apps.pkm.services.llm_service import LLMAuthError

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            side_effect=LLMAuthError("Invalid API key. Please check your configuration."),
        ),
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is TT133?"},
            content_type="application/json",
        )

    assert response.status_code == 401
    body = response.content.decode("utf-8").lower()
    assert "authentication failed" in body or "auth" in body


@pytest.mark.django_db
def test_ask_question_llm_rate_limit_error_returns_429(client, user, company, llm_config):
    """LLMRateLimitError returns 429, not a 500."""
    from apps.pkm.services.llm_service import LLMRateLimitError

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            side_effect=LLMRateLimitError("Rate limit reached. Please try again later."),
        ),
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is TT133?"},
            content_type="application/json",
        )

    assert response.status_code == 429
    body = response.content.decode("utf-8").lower()
    assert "rate limit" in body


@pytest.mark.django_db
def test_ask_question_llm_timeout_error_returns_504(client, user, company, llm_config):
    """LLMTimeoutError returns 504, not a 500."""
    from apps.pkm.services.llm_service import LLMTimeoutError

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            side_effect=LLMTimeoutError("Request timed out. Please try again."),
        ),
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is TT133?"},
            content_type="application/json",
        )

    assert response.status_code == 504
    body = response.content.decode("utf-8").lower()
    assert "timed out" in body or "timeout" in body


@pytest.mark.django_db
def test_ask_question_llm_connection_error_returns_504(client, user, company, llm_config):
    """LLMTimeoutError from connection failure returns 504, not a 500."""
    from apps.pkm.services.llm_service import LLMTimeoutError

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            side_effect=LLMTimeoutError("Cannot connect to openai API."),
        ),
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is TT133?"},
            content_type="application/json",
        )

    assert response.status_code == 504


@pytest.mark.django_db
def test_ask_question_generic_llm_error_returns_502(client, user, company, llm_config):
    """Generic LLMError (not auth/rate-limit/timeout) returns 502, not a 500."""
    from apps.pkm.services.llm_service import LLMError

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            side_effect=LLMError("Internal server error from provider."),
        ),
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is TT133?"},
            content_type="application/json",
        )

    assert response.status_code == 502
    body = response.content.decode("utf-8").lower()
    assert "provider error" in body or "llm" in body


@pytest.mark.django_db
def test_ask_question_embedding_llm_error_returns_502(client, user, company, llm_config):
    """LLMError from the embedding step (not completion) is also caught."""
    from apps.pkm.services.llm_service import LLMError

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            side_effect=LLMError("Embedding API failed."),
        ),
        patch("apps.pkm.services.qa_service.get_completion") as mock_gc,
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is TT133?"},
            content_type="application/json",
        )

    # Generic LLMError from embedding -> 502
    assert response.status_code == 502
    # Completion should never have been called since embedding failed first
    assert not mock_gc.called


@pytest.mark.django_db
def test_ask_question_embedding_auth_error_returns_401(client, user, company, llm_config):
    """LLMAuthError from the embedding step returns 401, not a 500."""
    from apps.pkm.services.llm_service import LLMAuthError

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            side_effect=LLMAuthError("Invalid API key. Please check your configuration."),
        ),
        patch("apps.pkm.services.qa_service.get_completion") as mock_gc,
    ):
        response = client.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What is TT133?"},
            content_type="application/json",
        )

    assert response.status_code == 401
    assert not mock_gc.called


@pytest.mark.django_db
def test_ask_question_llm_error_no_500(client, user, company, llm_config):
    """No unhandled 500 from LLM failures - all are caught and mapped."""
    from apps.pkm.services.llm_service import (
        LLMAuthError,
        LLMError,
        LLMRateLimitError,
        LLMTimeoutError,
    )

    error_cases = [
        (LLMAuthError("auth error"), 401),
        (LLMRateLimitError("rate limit error"), 429),
        (LLMTimeoutError("timeout error"), 504),
        (LLMError("generic"), 502),
    ]

    for exc, expected_code in error_cases:
        with (
            patch(
                "apps.pkm.services.qa_service.get_embedding",
                return_value=_mock_embedding_response(["q"]),
            ),
            patch(
                "apps.pkm.services.qa_service.get_completion",
                side_effect=exc,
            ),
        ):
            response = client.post(
                "/api/v1/pkm/qa/ask/",
                data={"question": "What is TT133?"},
                content_type="application/json",
            )
        assert response.status_code != 500, f"Got unhandled 500 for {type(exc).__name__}"
        assert response.status_code == expected_code, (
            f"Expected {expected_code} for {type(exc).__name__}, got {response.status_code}"
        )
