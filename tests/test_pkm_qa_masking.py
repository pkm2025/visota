"""Integration tests for PII masking in the PKM Q&A pipeline.

These tests verify that:

  - VAL-MASK-003: When ``qa_service.build_prompt`` constructs the LLM prompt,
    MST tax IDs, VND amounts, phone numbers and emails in chunks, notes,
    interaction context and the question itself are masked before the text
    reaches the LLM.
  - VAL-MASK-004: When ``UserLLMConfig.disable_masking=True`` (e.g. for a
    local Ollama model), masking is bypassed and the raw text is sent to the
    LLM unchanged.

All LLM calls are mocked; no real API key is required.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import UserLLMConfig
from apps.pkm.services.encryption_service import encrypt
from apps.pkm.services.qa_service import _build_wiki_prompt, answer_question, build_prompt

# ---------------------------------------------------------------------------
# build_prompt masking integration  (VAL-MASK-003)
# ---------------------------------------------------------------------------


class TestBuildPromptMasking:
    def test_build_prompt_masks_mst_in_chunks_by_default(self):
        """By default MST in chunk content is masked before reaching the prompt."""
        chunks = [
            {
                "content": "MST cua cong ty la 0123456789.",
                "document_title": "Doc",
                "chunk_id": 1,
            }
        ]
        messages = build_prompt(chunks, [], "question")
        user_content = messages[1]["content"]
        assert "0123456789" not in user_content
        assert "0*******9" in user_content or "*" in user_content

    def test_build_prompt_masks_vnd_in_chunks_by_default(self):
        """VND amounts in chunk content are masked to magnitude."""
        chunks = [
            {
                "content": "Doanh thu 50,000,000 VND nam 2026.",
                "document_title": "Doc",
                "chunk_id": 1,
            }
        ]
        messages = build_prompt(chunks, [], "question")
        user_content = messages[1]["content"]
        assert "50,000,000" not in user_content
        assert "50M" in user_content

    def test_build_prompt_masks_phone_in_chunks_by_default(self):
        """Phone numbers in chunk content are masked."""
        chunks = [
            {
                "content": "Lien he 0901234567.",
                "document_title": "Doc",
                "chunk_id": 1,
            }
        ]
        messages = build_prompt(chunks, [], "question")
        assert "0901234567" not in messages[1]["content"]

    def test_build_prompt_masks_email_in_chunks_by_default(self):
        """Emails in chunk content are masked."""
        chunks = [
            {
                "content": "Email user@example.com.",
                "document_title": "Doc",
                "chunk_id": 1,
            }
        ]
        messages = build_prompt(chunks, [], "question")
        assert "user@example.com" not in messages[1]["content"]
        assert "example.com" in messages[1]["content"]

    def test_build_prompt_masks_question(self):
        """The user's question itself is masked before reaching the LLM."""
        question = "MST 0123456789 la cua ai?"
        messages = build_prompt([], [], question)
        assert "0123456789" not in messages[1]["content"]

    def test_build_prompt_masks_note_content(self):
        """Note title and content preview are masked."""
        notes = [
            {
                "id": 1,
                "title": "Note MST 0123456789",
                "content_preview": "Doanh thu 50,000,000 VND.",
            }
        ]
        messages = build_prompt([], notes, "question")
        user_content = messages[1]["content"]
        assert "0123456789" not in user_content
        assert "50,000,000" not in user_content

    def test_build_prompt_masks_interaction_context(self):
        """Interaction context is masked before being inlined."""
        interaction = "Khach hang MST 0123456789 mua hang 50,000,000 VND."
        messages = build_prompt([], [], "question", interaction)
        user_content = messages[1]["content"]
        assert "0123456789" not in user_content
        assert "50,000,000" not in user_content

    def test_build_prompt_mask_false_passes_through(self):
        """When mask=False, raw PII is preserved (for Ollama/local)."""
        chunks = [
            {
                "content": "MST 0123456789 doanh thu 50,000,000 VND.",
                "document_title": "Doc",
                "chunk_id": 1,
            }
        ]
        messages = build_prompt(chunks, [], "MST 0123456789?", mask=False)
        user_content = messages[1]["content"]
        assert "0123456789" in user_content
        assert "50,000,000" in user_content


# ---------------------------------------------------------------------------
# _build_wiki_prompt masking
# ---------------------------------------------------------------------------


class TestBuildWikiPromptMasking:
    def test_wiki_prompt_masks_page_content_by_default(self):
        """Wiki page content is masked by default."""
        wiki_pages = [
            {
                "id": 1,
                "title": "VAT Page",
                "content": "MST 0123456789, doanh thu 50,000,000 VND.",
                "page_type": "concept",
            }
        ]
        messages = _build_wiki_prompt(wiki_pages, "question")
        user_content = messages[1]["content"]
        assert "0123456789" not in user_content
        assert "50,000,000" not in user_content

    def test_wiki_prompt_masks_question_by_default(self):
        wiki_pages = [{"id": 1, "title": "X", "content": "no pii", "page_type": "concept"}]
        messages = _build_wiki_prompt(wiki_pages, "MST 0123456789?")
        assert "0123456789" not in messages[1]["content"]

    def test_wiki_prompt_mask_false_passes_through(self):
        wiki_pages = [
            {
                "id": 1,
                "title": "X",
                "content": "MST 0123456789",
                "page_type": "concept",
            }
        ]
        messages = _build_wiki_prompt(wiki_pages, "MST 0123456789?", mask=False)
        assert "0123456789" in messages[1]["content"]


# ---------------------------------------------------------------------------
# answer_question + disable_masking flag  (VAL-MASK-003, VAL-MASK-004)
# ---------------------------------------------------------------------------


def _mock_completion(answer: str = "ok") -> Any:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=answer))])


def _mock_embedding() -> Any:
    return SimpleNamespace(data=[SimpleNamespace(embedding=[0.01] * 1536)])


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_MASK_CO", name="Mask Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="pkm_mask_user", password="Test1234", email="mask@t.co"
    )


@pytest.fixture
def llm_config(db, user, company):
    """Active LLM config with masking ON (default)."""
    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-mask-dummy"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


@pytest.fixture
def llm_config_no_mask(db, user, company):
    """Active LLM config with disable_masking=True (e.g. local Ollama)."""
    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="ollama",
        api_key_encrypted="",
        api_base="http://localhost:11434",
        default_model="llama3",
        default_embedding_model="nomic-embed-text",
        is_active=False,  # set active below per-test
        disable_masking=True,
    )


@pytest.mark.django_db
def test_answer_question_masks_pii_before_llm_call(user, company, llm_config):
    """VAL-MASK-003: PII is masked before the LLM completion call.

    We force the wiki path off (no wiki pages) and check the captured prompt
    that ``get_completion`` received does NOT contain the raw MST.
    """
    captured: list[Any] = []

    def _capture_completion(config, messages, stream=False):
        captured.append(messages)
        return _mock_completion()

    with (
        patch(
            "apps.pkm.services.qa_service.get_context_summary",
            return_value="",
        ),
        patch(
            "apps.pkm.services.qa_service.query_wiki",
            return_value=[],
        ),
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding(),
        ),
        patch(
            "apps.pkm.services.qa_service.search_similar",
            return_value=[],
        ),
        patch(
            "apps.pkm.services.qa_service._search_notes",
            return_value=[],
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            side_effect=_capture_completion,
        ),
        patch("apps.pkm.services.qa_service.append_log_entry", return_value=None),
    ):
        answer_question(
            user,
            company,
            "MST 0123456789 la cua cong ty nao?",
        )

    assert len(captured) == 1
    user_msg = captured[0][1]["content"]
    assert "0123456789" not in user_msg


@pytest.mark.django_db
def test_answer_question_disable_masking_passes_through(user, company, llm_config_no_mask):
    """VAL-MASK-004: When disable_masking=True, no masking applied."""
    # Activate the no-mask config (the default fixture keeps it inactive).
    UserLLMConfig.objects.filter(id=llm_config_no_mask.id).update(is_active=True)
    # Deactivate the masking-on config so the no-mask one is the active one.
    UserLLMConfig.objects.filter(user=user, company=company, provider="openai").update(
        is_active=False
    )

    captured: list[Any] = []

    def _capture_completion(config, messages, stream=False):
        captured.append(messages)
        return _mock_completion()

    with (
        patch(
            "apps.pkm.services.qa_service.get_context_summary",
            return_value="",
        ),
        patch(
            "apps.pkm.services.qa_service.query_wiki",
            return_value=[],
        ),
        patch(
            "apps.pkm.services.qa_service.get_embedding",
            return_value=_mock_embedding(),
        ),
        patch(
            "apps.pkm.services.qa_service.search_similar",
            return_value=[],
        ),
        patch(
            "apps.pkm.services.qa_service._search_notes",
            return_value=[],
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            side_effect=_capture_completion,
        ),
        patch("apps.pkm.services.qa_service.append_log_entry", return_value=None),
    ):
        answer_question(
            user,
            company,
            "MST 0123456789 la cua cong ty nao?",
        )

    assert len(captured) == 1
    user_msg = captured[0][1]["content"]
    # Raw MST preserved because disable_masking=True
    assert "0123456789" in user_msg


@pytest.mark.django_db
def test_answer_question_masks_pii_in_wiki_path(user, company, llm_config):
    """Masking is applied on the wiki-grounded Q&A path too."""
    wiki_pages = [
        {
            "id": 1,
            "title": "VAT",
            "content": "MST 0123456789, doanh thu 50,000,000 VND.",
            "page_type": "concept",
        }
    ]
    captured: list[Any] = []

    def _capture_completion(config, messages, stream=False):
        captured.append(messages)
        return _mock_completion()

    with (
        patch(
            "apps.pkm.services.qa_service.get_context_summary",
            return_value="",
        ),
        patch(
            "apps.pkm.services.qa_service.query_wiki",
            return_value=wiki_pages,
        ),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            side_effect=_capture_completion,
        ),
        patch("apps.pkm.services.qa_service.append_log_entry", return_value=None),
    ):
        answer_question(user, company, "MST 0123456789?")

    assert len(captured) == 1
    user_msg = captured[0][1]["content"]
    assert "0123456789" not in user_msg
    assert "50,000,000" not in user_msg
