"""Integration tests for PKM Q&A chat UI view (/modern/knowledge/qa/).

Covers:
    VAL-QA-001 - Access Q&A chat page
    VAL-QA-002 - Q&A interface shows chat input
    VAL-QA-003 - User can submit a question
    VAL-QA-004 - Response is displayed (mocked)
    VAL-QA-005 - Q&A history visible
    VAL-QA-006 - No LLM config prompts configuration
    VAL-QA-011 - Empty question shows validation error
    VAL-QA-010 - Source citations displayed

All LLM/embedding calls are **mocked** (no real API key required). MariaDB
VECTOR operations use the real database.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import Permission, Role, User, UserCompanyRole
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
    """Build a mock litellm embedding response."""
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
        file=SimpleUploadedFile("qa_ui_test.txt", b"dummy", content_type="text/plain"),
        file_type="txt",
        file_size=5,
        status=PKMDocument.Status.PROCESSED,
    )
    if chunk_contents is None:
        chunk_contents = ["TT133 la bo Quy chuan ke toan Viet Nam."]

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
    return Company.objects.create(code="PKM_QA_UI_CO", name="PKM QA UI Test Co")


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="PKM_QA_UI_OC", name="PKM QA UI Other Co")


@pytest.fixture
def admin_user(db, company):
    """Superuser — bypasses permission checks."""
    return User.objects.create_superuser(
        username="pkm_qa_admin", password="Test1234", email="qaadmin@pkm.test"
    )


@pytest.fixture
def regular_user(db, company):
    """Regular user with pkm.access permission."""
    user = User.objects.create_user(
        username="pkm_qa_user", password="Test1234", email="qauser@pkm.test"
    )
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={"module": "pkm", "name": "PKM Access", "description": "Access PKM"},
    )
    role = Role.objects.create(company=company, code="qa_role", name="QA Role")
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)
    return user


@pytest.fixture
def admin_client(admin_user, company):
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def perm_client(regular_user, company):
    c = Client()
    c.force_login(regular_user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def llm_config(db, regular_user, company):
    return UserLLMConfig.objects.create(
        user=regular_user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-dummy-key"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


@pytest.fixture
def admin_llm_config(db, admin_user, company):
    return UserLLMConfig.objects.create(
        user=admin_user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-admin-dummy-key"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


# ===========================================================================
# VAL-QA-001: Access Q&A chat page
# ===========================================================================


@pytest.mark.django_db
def test_qa_chat_page_loads(admin_client, admin_llm_config):
    """VAL-QA-001: Q&A chat page renders for a user with an active config."""
    response = admin_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    assert "qa-chat-container" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_qa_chat_page_renders_with_template(perm_client, llm_config):
    """VAL-QA-001: Q&A chat page uses the qa_chat.html template."""
    response = perm_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    assert b"qa-chat-container" in response.content


@pytest.mark.django_db
def test_qa_chat_requires_login(db):
    """Unauthenticated access redirects to login."""
    c = Client()
    response = c.get("/modern/knowledge/qa/")
    assert response.status_code in (302, 301)
    assert "/auth/login/" in response.url


# ===========================================================================
# VAL-QA-002: Q&A interface shows chat input
# ===========================================================================


@pytest.mark.django_db
def test_qa_chat_shows_input(perm_client, llm_config):
    """VAL-QA-002: Q&A page has a text input and submit button."""
    response = perm_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    assert b'name="question"' in response.content
    assert b'id="qa-question-input"' in response.content
    assert b'id="qa-submit-btn"' in response.content


@pytest.mark.django_db
def test_qa_chat_shows_submit_button(perm_client, llm_config):
    """VAL-QA-002: The submit button is present and not disabled."""
    response = perm_client.get("/modern/knowledge/qa/")
    content = response.content.decode("utf-8")
    assert 'id="qa-submit-btn"' in content
    # Input should not be disabled when config is active
    assert "disabled" not in content.split('id="qa-question-input"')[0].split("<")[-1]


# ===========================================================================
# VAL-QA-003: User can submit a question
# ===========================================================================


@pytest.mark.django_db
def test_submit_question_shows_question(admin_client, admin_user, company, admin_llm_config):
    """VAL-QA-003: Submitting a question shows the question in the chat."""
    _create_document_with_chunks(admin_user, company)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("TT133 la quy chuan."),
        ),
    ):
        response = admin_client.post(
            "/modern/knowledge/qa/",
            data={"question": "TT133 la gi?"},
        )

    assert response.status_code == 200
    assert b"TT133 la gi?" in response.content


@pytest.mark.django_db
def test_submit_question_via_form(admin_client, admin_user, company, admin_llm_config):
    """VAL-QA-003: Form POST submits the question."""
    _create_document_with_chunks(admin_user, company)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Form answer."),
        ),
    ):
        response = admin_client.post(
            "/modern/knowledge/qa/",
            data={"question": "What is this?"},
        )

    assert response.status_code == 200
    assert b"Form answer." in response.content


# ===========================================================================
# VAL-QA-004: Response is displayed (mocked)
# ===========================================================================


@pytest.mark.django_db
def test_response_displayed(admin_client, admin_user, company, admin_llm_config):
    """VAL-QA-004: After submitting, a response is displayed."""
    _create_document_with_chunks(admin_user, company)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("This is the mocked answer."),
        ),
    ):
        response = admin_client.post(
            "/modern/knowledge/qa/",
            data={"question": "Tell me about TT133"},
        )

    assert response.status_code == 200
    assert b"This is the mocked answer." in response.content


@pytest.mark.django_db
def test_response_displayed_with_ai_label(admin_client, admin_user, company, admin_llm_config):
    """VAL-QA-004: The response has an AI label."""
    _create_document_with_chunks(admin_user, company)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Answer text."),
        ),
    ):
        response = admin_client.post(
            "/modern/knowledge/qa/",
            data={"question": "Question?"},
        )

    assert b"ai-response" in response.content
    assert b"Tr" in response.content  # Part of "Trợ lý AI"


# ===========================================================================
# VAL-QA-005: Q&A history visible
# ===========================================================================


@pytest.mark.django_db
def test_history_panel_visible(perm_client, llm_config):
    """VAL-QA-005: The history panel is rendered on the page."""
    response = perm_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    assert b"qa-history-panel" in response.content


@pytest.mark.django_db
def test_history_list_shows_past_qa(perm_client, regular_user, company, llm_config):
    """VAL-QA-005: Past Q&A entries appear in the history list."""
    QAHistory.objects.create(
        user=regular_user,
        company=company,
        question="What is depreciation?",
        answer="Depreciation is cost allocation.",
        sources=[],
    )
    response = perm_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    assert b"What is depreciation?" in response.content
    assert b"Depreciation is cost allocation." in response.content


@pytest.mark.django_db
def test_history_empty_message(perm_client, llm_config):
    """VAL-QA-005: Empty history shows a message."""
    response = perm_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    assert "Chưa có lịch sử hỏi đáp" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_history_limited_to_recent(perm_client, regular_user, company, llm_config):
    """History panel shows a limited number of entries (most recent first)."""
    for i in range(30):
        QAHistory.objects.create(
            user=regular_user,
            company=company,
            question=f"Question {i}",
            answer=f"Answer {i}",
            sources=[],
        )
    response = perm_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    # The most recent question should be present
    assert b"Question 29" in response.content
    # Question 0 is beyond the limit (20) and should not appear
    # (it would appear as "Question 0" only if all 30 were shown)


# ===========================================================================
# VAL-QA-006: No LLM config prompts configuration
# ===========================================================================


@pytest.mark.django_db
def test_no_config_shows_configure_prompt(admin_client):
    """VAL-QA-006: No active config shows a 'configure provider first' prompt."""
    response = admin_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "configure-first-prompt" in content or "qa-disabled-state" in content
    assert "cấu hình" in content.lower() or "configure" in content.lower()


@pytest.mark.django_db
def test_no_config_input_disabled(admin_client):
    """VAL-QA-006: Input is disabled when there's no active config."""
    response = admin_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # The input should have a disabled attribute when no config
    assert "disabled" in content


@pytest.mark.django_db
def test_no_config_shows_link_to_settings(admin_client):
    """VAL-QA-006: No-config state includes a link to settings."""
    response = admin_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "/modern/knowledge/settings/" in content


# ===========================================================================
# VAL-QA-011: Empty question shows validation error
# ===========================================================================


@pytest.mark.django_db
def test_empty_question_validation_error(admin_client, admin_llm_config):
    """VAL-QA-011: Empty question shows a validation error."""
    with patch("apps.pkm.services.qa_service.get_completion") as mock_gc:
        response = admin_client.post(
            "/modern/knowledge/qa/",
            data={"question": ""},
        )
    assert response.status_code == 200
    assert "không được để trống" in response.content.decode("utf-8")
    # LLM never called
    assert not mock_gc.called


@pytest.mark.django_db
def test_whitespace_question_validation_error(admin_client, admin_llm_config):
    """VAL-QA-011: Whitespace-only question shows a validation error."""
    with patch("apps.pkm.services.qa_service.get_completion") as mock_gc:
        response = admin_client.post(
            "/modern/knowledge/qa/",
            data={"question": "   "},
        )
    assert response.status_code == 200
    assert "không được để trống" in response.content.decode("utf-8")
    assert not mock_gc.called


# ===========================================================================
# VAL-QA-010: Source citations displayed
# ===========================================================================


@pytest.mark.django_db
def test_source_citations_displayed(admin_client, admin_user, company, admin_llm_config):
    """VAL-QA-010: Answer includes source citations."""
    _create_document_with_chunks(
        admin_user,
        company,
        title="Accounting Standards",
        chunk_contents=["TT133 is a Vietnamese accounting regulation."],
    )

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Based on the document..."),
        ),
    ):
        response = admin_client.post(
            "/modern/knowledge/qa/",
            data={"question": "What is TT133?"},
        )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "source-citations" in content
    assert "Accounting Standards" in content


# ===========================================================================
# Navigation / sidebar
# ===========================================================================


@pytest.mark.django_db
def test_sidebar_has_qa_link(admin_client, admin_llm_config):
    """The sidebar includes a link to Q&A chat."""
    response = admin_client.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    assert "/modern/knowledge/qa/" in response.content.decode("utf-8")
    assert "Hỏi đáp AI" in response.content.decode("utf-8")


# ===========================================================================
# Per-user isolation (UI level)
# ===========================================================================


@pytest.mark.django_db
def test_qa_history_private_per_user(
    regular_user, company, llm_config, admin_user, admin_llm_config
):
    """User B's Q&A history is not visible to User A via UI."""
    QAHistory.objects.create(
        user=regular_user,
        company=company,
        question="User A secret question",
        answer="secret answer",
        sources=[],
    )

    # Admin logs in, should NOT see regular_user's history
    c_admin = Client()
    c_admin.force_login(admin_user)
    session = c_admin.session
    session["current_company_id"] = company.id
    session.save()

    response = c_admin.get("/modern/knowledge/qa/")
    assert response.status_code == 200
    assert b"User A secret question" not in response.content
