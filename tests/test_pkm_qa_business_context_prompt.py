"""Tests for the business-context-aware Q&A system prompt (qa_service).

Verifies that the ``SYSTEM_MESSAGE`` in ``qa_service``:

  1. Includes a placeholder / instruction referencing the company business
     context (regime, entity type, tax group, industry) that
     ``interaction_service.get_context_summary`` produces, so the LLM is
     aware of the user's accounting regime when answering.
  2. Contains the explicit regime-aware instruction telling the model to
     consider the user's accounting regime and tax method when answering
     accounting / tax questions.

Fulfills:
  - VAL-QA-001: System prompt includes company context
  - VAL-QA-002: System prompt instructs regime-aware answers
"""

from __future__ import annotations

import pytest

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import (
    DocumentChunk,
    PKMDocument,
    UserLLMConfig,
)
from apps.pkm.services.encryption_service import encrypt
from apps.pkm.services.interaction_service import _format_company_context
from apps.pkm.services.qa_service import (
    SYSTEM_MESSAGE,
    answer_question,
    build_prompt,
)
from apps.pkm.services.vector_store import store_embedding

EMBEDDING_DIM = 1536

# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

#: Exact Vietnamese instruction that must appear verbatim in the system
#: prompt. The feature description specifies this sentence.
REGIME_AWARE_INSTRUCTION = (
    "Khi trả lời câu hỏi kế toán/thuế, hãy xem xét chế độ kế toán và "
    "phương pháp nộp thuế của doanh nghiệp người dùng."
)


def _mock_embedding_response():
    from types import SimpleNamespace

    return SimpleNamespace(data=[SimpleNamespace(embedding=[0.01] * EMBEDDING_DIM)])


def _mock_completion_response(answer: str = "Mocked answer."):
    from types import SimpleNamespace

    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=answer))])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tt58_company(db):
    return Company.objects.create(
        code="QA_BC_TT58",
        name="QA BC TT58 Co",
        tax_code="0105550101",
        accounting_regime="tt58",
        entity_type="doanh_nghiep_sieu_nho",
        vat_method="ty_le_phan_tram",
        tndn_method="tinh_thue",
        industry="Thương mại - Công nghệ",
    )


@pytest.fixture
def tt133_company(db):
    return Company.objects.create(
        code="QA_BC_TT133",
        name="QA BC TT133 Co",
        tax_code="0105550102",
        accounting_regime="tt133",
        entity_type="doanh_nghiep_sieu_nho",
        vat_method="khau_tru",
        tndn_method="tinh_thue",
        industry="Dịch vụ - bán lẻ",
    )


@pytest.fixture
def user(db, tt58_company):
    return User.objects.create_user(
        username="qa_bc_user",
        password="Test1234",
        email="qa_bc@t.co",
    )


@pytest.fixture
def llm_config(db, user, tt58_company):
    return UserLLMConfig.objects.create(
        user=user,
        company=tt58_company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-dummy-key-for-mocking"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


def _create_document_with_chunks(user, company, chunk_contents):
    """Create a PKMDocument with chunks + stored embeddings (for RAG)."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="QA BC Doc",
        file=SimpleUploadedFile("qa_bc.txt", b"dummy", content_type="text/plain"),
        file_type="txt",
        file_size=5,
        status=PKMDocument.Status.PROCESSED,
    )
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


# ---------------------------------------------------------------------------
# VAL-QA-001: System prompt includes company context reference
# ---------------------------------------------------------------------------


def test_system_message_references_company_context():
    """VAL-QA-001: SYSTEM_MESSAGE references the company business context.

    The system prompt must mention the company context section (which contains
    regime, entity type, tax group, industry from ``get_context_summary``).
    """
    lowered = SYSTEM_MESSAGE.lower()
    # Must reference "company context" / "bối cảnh doanh nghiệp" / "ngữ cảnh"
    # that carries regime + entity type text.
    assert (
        "bối cảnh doanh nghiệp" in lowered
        or "company context" in lowered
        or "ngữ cảnh doanh nghiệp" in lowered
        or "doanh nghiệp" in lowered
    ), "SYSTEM_MESSAGE must reference the company context section"


def test_system_message_mentions_regime_or_accounting_regime():
    """VAL-QA-001: SYSTEM_MESSAGE explicitly mentions the accounting regime.

    The regime text ('chế độ kế toán') is what the company context provides,
    and the system prompt must instruct the model to use it.
    """
    lowered = SYSTEM_MESSAGE.lower()
    assert "chế độ kế toán" in lowered or "accounting regime" in lowered


def test_build_prompt_system_message_contains_regime_instruction():
    """VAL-QA-001/002: build_prompt embeds SYSTEM_MESSAGE as the system role."""
    messages = build_prompt([], [], "question?")
    system_content = messages[0]["content"]
    assert REGIME_AWARE_INSTRUCTION in system_content


@pytest.mark.django_db
def test_answer_question_system_prompt_carries_company_context_tt58(user, tt58_company, llm_config):
    """VAL-QA-001: When answering, the system prompt sent to the LLM includes
    the company context text produced by ``_format_company_context`` (regime,
    entity type). The company context is injected via the interaction summary,
    so the assembled user message must carry it.
    """
    _create_document_with_chunks(
        user, tt58_company, ["TT58 quy che do ke toan danh cho doanh nghiep sieu nho."]
    )

    company_context = _format_company_context(user, tt58_company)
    assert "TT58" in company_context
    assert "Doanh nghiệp siêu nhỏ" in company_context

    from unittest.mock import patch

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response(),
        ) as mock_gc,
    ):
        answer_question(user, tt58_company, "Cách tính thuế GTGT?")

    assert mock_gc.called
    messages = mock_gc.call_args[0][1]
    # The company context (regime + entity type) must be carried in the prompt.
    all_content = " ".join(m["content"] for m in messages)
    assert "TT58" in all_content
    assert "Doanh nghiệp siêu nhỏ" in all_content


# ---------------------------------------------------------------------------
# VAL-QA-002: System prompt instructs regime-aware answers
# ---------------------------------------------------------------------------


def test_system_message_contains_regime_aware_instruction():
    """VAL-QA-002: SYSTEM_MESSAGE contains the exact regime-aware instruction."""
    assert REGIME_AWARE_INSTRUCTION in SYSTEM_MESSAGE


def test_system_message_instructs_to_consider_accounting_regime():
    """VAL-QA-002: SYSTEM_MESSAGE instructs the model to consider the
    user's accounting regime / tax method when answering.
    """
    lowered = SYSTEM_MESSAGE.lower()
    assert "kế toán/thuế" in lowered or "kế toán / thuế" in lowered
    assert "chế độ kế toán" in lowered
    assert "phương pháp nộp thuế" in lowered or "phuong phap nop thue" in lowered


@pytest.mark.django_db
def test_answer_question_system_prompt_has_instruction(user, tt58_company, llm_config):
    """VAL-QA-002: The instruction survives into the messages sent to the LLM."""
    _create_document_with_chunks(user, tt58_company, ["Some content."])

    from unittest.mock import patch

    with (
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding_response(),
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=_mock_completion_response(),
        ) as mock_gc,
    ):
        answer_question(user, tt58_company, "Tax question?")

    messages = mock_gc.call_args[0][1]
    system_content = messages[0]["content"]
    assert REGIME_AWARE_INSTRUCTION in system_content
