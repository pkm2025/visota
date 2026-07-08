"""E2E cross-area integration tests for PKM module.

Verifies complete integration flows across multiple PKM subsystems:

    VAL-CROSS-003 - Complete RAG flow (upload doc, process, ask Q&A, get answer with citations)
    VAL-CROSS-004 - Multi-user isolation (two users in same company, separate data)
    VAL-CROSS-005 - Multi-tenant isolation (users in different companies)
    VAL-CROSS-009 - Provider switching (OpenAI -> Anthropic, Q&A still works)
    VAL-CROSS-012 - Document reprocess preserves note references

All LLM/embedding calls are **mocked**. MariaDB VECTOR operations use the
real database.
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
    KnowledgeNote,
    PKMDocument,
    QAHistory,
    UserLLMConfig,
)
from apps.pkm.services.encryption_service import encrypt
from apps.pkm.services.vector_store import store_embedding

EMBEDDING_DIM = 1536


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_embedding_response(texts: list[str]) -> Any:
    data = [SimpleNamespace(embedding=[0.01] * EMBEDDING_DIM) for _ in range(len(texts))]
    return SimpleNamespace(data=data)


def _mock_completion_response(answer: str = "Mocked answer.") -> Any:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=answer))]
    )


def _create_processed_doc(
    user,
    company,
    title: str = "Test Doc",
    contents: list[str] | None = None,
) -> tuple[PKMDocument, list[DocumentChunk]]:
    """Create a PKMDocument (status=processed) with chunks and embeddings."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title=title,
        file=SimpleUploadedFile("cross_test.txt", b"test data", content_type="text/plain"),
        file_type="txt",
        file_size=9,
        status=PKMDocument.Status.PROCESSED,
    )
    if contents is None:
        contents = ["TT133 la quy chuan ke toan hanh chinh nha nuoc Viet Nam."]
    chunks: list[DocumentChunk] = []
    for i, content in enumerate(contents):
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


def _create_llm_config(user, company, provider="openai", is_active=True) -> UserLLMConfig:
    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider=provider,
        api_key_encrypted=encrypt(f"sk-{provider}-dummy-key"),
        default_model="gpt-4o-mini" if provider == "openai" else "claude-sonnet-4-20250514",
        default_embedding_model="text-embedding-3-small",
        is_active=is_active,
    )


def _client_for(user, company=None) -> Client:
    c = Client()
    c.force_login(user)
    if company:
        session = c.session
        session["current_company_id"] = company.id
        session.save()
    return c


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company_a(db):
    return Company.objects.create(code="CROSS_CA", name="Cross Area Co A")


@pytest.fixture
def company_b(db):
    return Company.objects.create(code="CROSS_CB", name="Cross Area Co B")


@pytest.fixture
def user_a(db, company_a):
    """Superuser to bypass permission checks for UI views."""
    return User.objects.create_superuser(
        username="cross_user_a", password="Test1234", email="a@cross.test"
    )


@pytest.fixture
def user_b(db, company_a):
    """User B in the same company as User A (superuser for UI access)."""
    return User.objects.create_superuser(
        username="cross_user_b", password="Test1234", email="b@cross.test"
    )


@pytest.fixture
def user_c(db, company_b):
    """User C in a different company (superuser for UI access)."""
    return User.objects.create_superuser(
        username="cross_user_c", password="Test1234", email="c@cross.test"
    )


# ===========================================================================
# VAL-CROSS-003: Complete RAG flow
# ===========================================================================


@pytest.mark.django_db
def test_complete_rag_flow(user_a, company_a):
    """VAL-CROSS-003: Upload doc, process, ask question, get answer with citations.

    Steps:
        1. Create a processed document with chunks + embeddings
        2. Configure LLM provider
        3. Ask a question via API
        4. Verify answer includes source citations
    """
    _create_processed_doc(
        user_a,
        company_a,
        title="TT133 Reference",
        contents=["TT133 la Thong tu ke toan so 133/2016/TT-BTC."],
    )
    _create_llm_config(user_a, company_a)

    c = _client_for(user_a, company_a)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("TT133 la thong tu ke toan."),
        ),
    ):
        response = c.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "TT133 la gi?"},
            content_type="application/json",
        )

    assert response.status_code == 200, response.content
    data = response.json()
    assert data["answer"] == "TT133 la thong tu ke toan."
    assert len(data["sources"]) >= 1
    # Source should reference the document
    src = data["sources"][0]
    assert src["document_title"] == "TT133 Reference"
    assert src["source_type"] == "document_chunk"

    # Verify Q&A history was saved
    assert QAHistory.objects.filter(user=user_a, company=company_a).count() == 1


@pytest.mark.django_db
def test_rag_flow_returns_answer_in_ui(user_a, company_a):
    """VAL-CROSS-003: Complete RAG flow via the UI (server-rendered)."""
    _create_processed_doc(
        user_a,
        company_a,
        title="Accounting Guide",
        contents=["Phan mem ke toan can tuan thu TT133."],
    )
    _create_llm_config(user_a, company_a)

    c = _client_for(user_a, company_a)

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Phan mem can tuan thu TT133."),
        ),
    ):
        response = c.post(
            "/modern/knowledge/qa/",
            data={"question": "Phan mem can lam gi?"},
        )

    assert response.status_code == 200
    assert b"Phan mem can tuan thu TT133." in response.content
    assert b"source-citations" in response.content
    assert b"Accounting Guide" in response.content


# ===========================================================================
# VAL-CROSS-004: Multi-user isolation
# ===========================================================================


@pytest.mark.django_db
def test_multi_user_isolation_notes(user_a, user_b, company_a):
    """VAL-CROSS-004: User A's notes are not visible to User B."""
    KnowledgeNote.objects.create(
        user=user_a,
        company=company_a,
        title="User A private note",
        content="Secret content",
    )

    # User B queries notes
    c_b = _client_for(user_b, company_a)
    response = c_b.get("/api/v1/pkm/notes/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 0


@pytest.mark.django_db
def test_multi_user_isolation_documents(user_a, user_b, company_a):
    """VAL-CROSS-004: User A's documents are not visible to User B."""
    _create_processed_doc(user_a, company_a, title="User A Doc")

    c_b = _client_for(user_b, company_a)
    response = c_b.get("/api/v1/pkm/documents/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 0


@pytest.mark.django_db
def test_multi_user_isolation_qa_history(user_a, user_b, company_a):
    """VAL-CROSS-004: User A's Q&A history is not visible to User B."""
    QAHistory.objects.create(
        user=user_a,
        company=company_a,
        question="User A question",
        answer="answer",
        sources=[],
    )

    c_b = _client_for(user_b, company_a)
    response = c_b.get("/api/v1/pkm/qa/history/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 0


@pytest.mark.django_db
def test_multi_user_isolation_llm_config(user_a, user_b, company_a):
    """VAL-CROSS-004: User A's LLM configs are not visible to User B."""
    _create_llm_config(user_a, company_a)

    c_b = _client_for(user_b, company_a)
    response = c_b.get("/api/v1/pkm/llm-configs/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@pytest.mark.django_db
def test_multi_user_isolation_qa_retrieval(user_a, user_b, company_a):
    """VAL-CROSS-004: Q&A for User B does not retrieve User A's documents."""
    _create_processed_doc(
        user_a,
        company_a,
        title="User A confidential doc",
        contents=["This is user A's confidential information about taxes."],
    )
    # User B also has a config + a doc
    _create_processed_doc(
        user_b,
        company_a,
        title="User B doc",
        contents=["User B's content about inventory."],
    )
    _create_llm_config(user_b, company_a)

    c_b = _client_for(user_b, company_a)
    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("User B answer."),
        ),
    ):
        response = c_b.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "What do I have?"},
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    all_previews = " ".join(s.get("content_preview", "") for s in data["sources"])
    assert "User A" not in all_previews
    assert "confidential" not in all_previews


# ===========================================================================
# VAL-CROSS-005: Multi-tenant isolation
# ===========================================================================


@pytest.mark.django_db
def test_multi_tenant_isolation_notes(user_a, user_c, company_a, company_b):
    """VAL-CROSS-005: Users in different companies have separate notes."""
    KnowledgeNote.objects.create(
        user=user_a,
        company=company_a,
        title="Company A note",
        content="content A",
    )
    KnowledgeNote.objects.create(
        user=user_a,
        company=company_b,
        title="Company B note",
        content="content B",
    )

    # User C in Company B should only see Company B notes
    c_c = _client_for(user_c, company_b)
    response = c_c.get("/api/v1/pkm/notes/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 0  # User C has no notes at all


@pytest.mark.django_db
def test_multi_tenant_isolation_qa_history(user_a, company_a, company_b):
    """VAL-CROSS-005: Q&A history is scoped by company."""
    QAHistory.objects.create(
        user=user_a,
        company=company_a,
        question="Question in Company A",
        answer="answer A",
        sources=[],
    )
    QAHistory.objects.create(
        user=user_a,
        company=company_b,
        question="Question in Company B",
        answer="answer B",
        sources=[],
    )

    c_a = _client_for(user_a, company_a)
    response_a = c_a.get("/api/v1/pkm/qa/history/")
    data_a = response_a.json()
    items_a = data_a if isinstance(data_a, list) else data_a.get("items", [])
    assert len(items_a) == 1
    assert items_a[0]["question"] == "Question in Company A"

    c_b = _client_for(user_a, company_b)
    response_b = c_b.get("/api/v1/pkm/qa/history/")
    data_b = response_b.json()
    items_b = data_b if isinstance(data_b, list) else data_b.get("items", [])
    assert len(items_b) == 1
    assert items_b[0]["question"] == "Question in Company B"


@pytest.mark.django_db
def test_multi_tenant_isolation_documents(user_a, user_c, company_a, company_b):
    """VAL-CROSS-005: Documents are scoped by company."""
    _create_processed_doc(user_a, company_a, title="Doc in Company A")
    _create_processed_doc(user_c, company_b, title="Doc in Company B")

    # User A querying Company A should see only Company A doc
    c_a = _client_for(user_a, company_a)
    response_a = c_a.get("/api/v1/pkm/documents/")
    data_a = response_a.json()
    items_a = data_a if isinstance(data_a, list) else data_a.get("items", [])
    assert len(items_a) == 1
    assert items_a[0]["title"] == "Doc in Company A"

    # User C querying Company B should see only Company B doc
    c_c = _client_for(user_c, company_b)
    response_c = c_c.get("/api/v1/pkm/documents/")
    data_c = response_c.json()
    items_c = data_c if isinstance(data_c, list) else data_c.get("items", [])
    assert len(items_c) == 1
    assert items_c[0]["title"] == "Doc in Company B"


# ===========================================================================
# VAL-CROSS-009: Provider switching
# ===========================================================================


@pytest.mark.django_db
def test_provider_switching(user_a, company_a):
    """VAL-CROSS-009: Configure OpenAI, ask Q&A, switch to Anthropic, Q&A works.

    Steps:
        1. Create OpenAI config (active)
        2. Ask a question (mocked) — should work
        3. Deactivate OpenAI, activate Anthropic
        4. Ask again — should still work
    """
    _create_processed_doc(
        user_a,
        company_a,
        title="Provider Switch Doc",
        contents=["Content for provider switching test."],
    )

    # Step 1: OpenAI active
    openai_config = UserLLMConfig.objects.create(
        user=user_a,
        company=company_a,
        provider="openai",
        api_key_encrypted=encrypt("sk-openai-key"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )

    c = _client_for(user_a, company_a)

    # Step 2: Ask with OpenAI
    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("OpenAI answer."),
        ),
    ):
        response = c.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "Question 1?"},
            content_type="application/json",
        )
    assert response.status_code == 200
    assert response.json()["answer"] == "OpenAI answer."

    # Step 3: Switch to Anthropic
    openai_config.is_active = False
    openai_config.save(update_fields=["is_active"])
    anthropic_config = UserLLMConfig.objects.create(
        user=user_a,
        company=company_a,
        provider="anthropic",
        api_key_encrypted=encrypt("sk-ant-key"),
        default_model="claude-sonnet-4-20250514",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )

    # Step 4: Ask again with Anthropic
    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Anthropic answer."),
        ),
    ):
        response = c.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "Question 2?"},
            content_type="application/json",
        )
    assert response.status_code == 200
    assert response.json()["answer"] == "Anthropic answer."

    # Verify both configs exist, only Anthropic is active
    configs = UserLLMConfig.objects.filter(user=user_a, company=company_a)
    assert configs.count() == 2
    assert configs.filter(is_active=True).count() == 1
    assert configs.get(is_active=True).provider == "anthropic"
    assert anthropic_config.is_active


@pytest.mark.django_db
def test_provider_switching_qa_still_works_after_switch(user_a, company_a):
    """VAL-CROSS-009: After switching provider, the UI Q&A page still works."""
    _create_processed_doc(user_a, company_a)

    # Start with OpenAI
    openai_config = _create_llm_config(user_a, company_a, provider="openai")

    c = _client_for(user_a, company_a)

    # Switch: deactivate openai, activate anthropic
    openai_config.is_active = False
    openai_config.save(update_fields=["is_active"])
    _create_llm_config(user_a, company_a, provider="anthropic")

    # UI should detect active config and allow asking
    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("Switched provider answer."),
        ),
    ):
        response = c.post(
            "/modern/knowledge/qa/",
            data={"question": "Does this work?"},
        )
    assert response.status_code == 200
    assert b"Switched provider answer." in response.content


# ===========================================================================
# VAL-CROSS-012: Document reprocess preserves note references
# ===========================================================================


@pytest.mark.django_db
def test_reprocess_preserves_note_references(user_a, company_a):
    """VAL-CROSS-012: After reprocessing a document, note references remain valid.

    A note may reference a document by title or contain content from it.
    After reprocessing (which deletes and recreates chunks/embeddings),
    the note should still be accessible and the document should still exist.
    """
    doc, chunks = _create_processed_doc(
        user_a,
        company_a,
        title="Important Policy",
        contents=["The vacation policy allows 12 days per year."],
    )

    # Create a note that references the document
    note = KnowledgeNote.objects.create(
        user=user_a,
        company=company_a,
        title="Vacation Policy Notes",
        content=f"See 'Important Policy' document (ID: {doc.id}) for details.",
    )

    original_chunk_count = DocumentChunk.objects.filter(document=doc).count()
    assert original_chunk_count > 0

    # Reprocess the document (reset to pending + re-queue)
    c = _client_for(user_a, company_a)
    with patch("apps.pkm.services.rag_pipeline.schedule_reprocessing"):
        response = c.post(f"/api/v1/pkm/documents/{doc.id}/reprocess/")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    # Verify the note still exists and references are valid
    note.refresh_from_db()
    assert note.title == "Vacation Policy Notes"
    assert str(doc.id) in note.content

    # Verify the document still exists
    doc.refresh_from_db()
    assert doc.title == "Important Policy"
    assert doc.status == PKMDocument.Status.PENDING

    # Note is still accessible via API
    response = c.get(f"/api/v1/pkm/notes/{note.id}/")
    assert response.status_code == 200
    assert response.json()["title"] == "Vacation Policy Notes"


@pytest.mark.django_db
def test_reprocess_preserves_document_record(user_a, company_a):
    """VAL-CROSS-012: Reprocessing doesn't delete the document record."""
    doc, _ = _create_processed_doc(
        user_a,
        company_a,
        title="Reprocess Test Doc",
        contents=["Content that will be reprocessed."],
    )
    doc_id = doc.id

    c = _client_for(user_a, company_a)
    with patch("apps.pkm.services.rag_pipeline.schedule_reprocessing"):
        response = c.post(f"/api/v1/pkm/documents/{doc_id}/reprocess/")
    assert response.status_code == 200

    # Document still exists
    assert PKMDocument.objects.filter(id=doc_id).exists()
    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.PENDING


@pytest.mark.django_db
def test_note_document_reference_after_reprocess_via_qa(user_a, company_a):
    """VAL-CROSS-012: After reprocessing, Q&A can still find the note referencing the doc."""
    doc, _ = _create_processed_doc(
        user_a,
        company_a,
        title="HR Manual",
        contents=["Annual leave entitlement is 12 days."],
    )

    # Note referencing the doc topic
    KnowledgeNote.objects.create(
        user=user_a,
        company=company_a,
        title="Leave Notes",
        content="Annual leave is mentioned in the HR Manual.",
    )

    _create_llm_config(user_a, company_a)
    c = _client_for(user_a, company_a)

    # Reprocess the document first
    with patch("apps.pkm.services.rag_pipeline.schedule_reprocessing"):
        c.post(f"/api/v1/pkm/documents/{doc.id}/reprocess/")

    # Manually re-add chunks+embeddings (simulating reprocess completion)
    # since the async pipeline doesn't run in tests
    content = "Annual leave entitlement is 12 days."
    chunk = DocumentChunk.objects.create(
        document=doc,
        chunk_index=0,
        content=content,
        token_count=len(content.split()),
    )
    store_embedding(
        chunk_id=chunk.id,
        user_id=user_a.id,
        company_id=company_a.id,
        content=content,
        embedding_vector=[0.01] * EMBEDDING_DIM,
        model_name="text-embedding-3-small",
    )

    # Q&A should still find both the document chunk and the note
    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(["q"]),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response("12 days of annual leave."),
        ),
    ):
        response = c.post(
            "/api/v1/pkm/qa/ask/",
            data={"question": "How many leave days?"},
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    # The note "Leave Notes" should appear in sources
    source_titles = [s.get("document_title", "") for s in data["sources"]]
    assert "Leave Notes" in source_titles
