"""Tests for the disable_masking flag integration in the wiki ingest service.

Verifies that:
  - By default (``disable_masking=False``) ingest masks PII before the LLM call.
  - When ``UserLLMConfig.disable_masking=True`` (e.g. local Ollama), the raw
    source text is passed through unmasked.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import DocumentChunk, PKMDocument, UserLLMConfig
from apps.pkm.services.encryption_service import encrypt
from apps.pkm.services.wiki_ingest_service import build_ingest_prompt, ingest_document


def _mock_completion(summary_md: str = "ok", concepts: list | None = None) -> Any:
    payload = {"summary": summary_md, "concepts": concepts or []}
    content = json.dumps(payload)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )


@pytest.fixture
def company(db):
    return Company.objects.create(code="WIKI_MSK_CO", name="Wiki Mask Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(username="wiki_mask_user", password="Test1234", email="wm@t.co")


@pytest.fixture
def llm_config(db, user, company):
    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-wiki-mask"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


@pytest.fixture
def llm_config_no_mask(db, user, company):
    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="ollama",
        api_key_encrypted="",
        api_base="http://localhost:11434",
        default_model="llama3",
        default_embedding_model="nomic-embed-text",
        is_active=True,
        disable_masking=True,
    )


@pytest.fixture
def doc_with_pii(db, user, company):
    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="Source with PII",
        file=SimpleUploadedFile("p.txt", b"dummy"),
        file_type="txt",
        file_size=5,
        status=PKMDocument.Status.PROCESSED,
    )
    DocumentChunk.objects.create(
        document=doc,
        chunk_index=0,
        content="MST 0123456789, doanh thu 50,000,000 VND.",
        token_count=8,
    )
    return doc


# ---------------------------------------------------------------------------
# build_ingest_prompt mask flag
# ---------------------------------------------------------------------------


def test_build_ingest_prompt_masks_by_default():
    messages = build_ingest_prompt(
        source_title="Doc",
        chunks_text="MST 0123456789.",
        existing_concepts="",
    )
    assert "0123456789" not in messages[1]["content"]


def test_build_ingest_prompt_mask_false_passes_through():
    messages = build_ingest_prompt(
        source_title="Doc",
        chunks_text="MST 0123456789.",
        existing_concepts="",
        mask=False,
    )
    assert "0123456789" in messages[1]["content"]


# ---------------------------------------------------------------------------
# ingest_document respects disable_masking
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ingest_document_masks_pii_by_default(user, company, llm_config, doc_with_pii):
    captured: list[Any] = []

    def _capture(config, messages, stream=False):
        captured.append(messages)
        return _mock_completion()

    with patch("apps.pkm.services.wiki_ingest_service.get_completion", side_effect=_capture):
        ingest_document(doc_with_pii.id)

    assert len(captured) == 1
    user_msg = captured[0][1]["content"]
    assert "0123456789" not in user_msg
    assert "50,000,000" not in user_msg


@pytest.mark.django_db
def test_ingest_document_no_mask_when_disable_masking(
    user, company, llm_config_no_mask, doc_with_pii
):
    """VAL-MASK-004: disable_masking=True bypasses masking in ingest."""
    # Ensure the openai (mask-on) config is inactive so the no-mask config wins.
    UserLLMConfig.objects.filter(user=user, company=company, provider="openai").update(
        is_active=False
    )

    captured: list[Any] = []

    def _capture(config, messages, stream=False):
        captured.append(messages)
        return _mock_completion()

    with patch("apps.pkm.services.wiki_ingest_service.get_completion", side_effect=_capture):
        ingest_document(doc_with_pii.id)

    assert len(captured) == 1
    user_msg = captured[0][1]["content"]
    # disable_masking=True -> raw MST preserved.
    assert "0123456789" in user_msg
