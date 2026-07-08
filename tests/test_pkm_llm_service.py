"""Unit tests for apps.pkm.services.llm_service.

All LLM/embedding calls are mocked. We never make real API calls.
These tests cover:
  - get_completion with provider prefix formatting and per-call api_key
  - get_embedding with provider prefix formatting and per-call api_key
  - get_available_providers returns all 6 supported providers
  - get_provider_models returns suggested models per provider
  - validate_api_key returns True on success, False on auth errors
  - Error handling: AuthenticationError, RateLimitError, Timeout, APIConnectionError
  - API key never appears in logs
  - Model prefix formatting for each provider
"""

from __future__ import annotations

import contextlib
import logging
from unittest.mock import MagicMock, patch

import pytest

from apps.pkm.services import llm_service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    from apps.core.models import Company

    return Company.objects.create(code="PKM_LLM", name="PKM LLM Test Co")


@pytest.fixture
def user(db, company):
    from apps.identity.models import User

    return User.objects.create_user(username="llm_user", password="Test1234", email="llm@t.co")


@pytest.fixture
def openai_config(company, user):
    """A UserLLMConfig with encrypted OpenAI key."""
    from apps.pkm.models import UserLLMConfig
    from apps.pkm.services.encryption_service import encrypt

    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-openai-key"),
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


@pytest.fixture
def anthropic_config(company, user):
    """A UserLLMConfig with encrypted Anthropic key."""
    from apps.pkm.models import UserLLMConfig
    from apps.pkm.services.encryption_service import encrypt

    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="anthropic",
        api_key_encrypted=encrypt("sk-ant-test-key"),
        default_model="claude-sonnet-4-20250514",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


@pytest.fixture
def ollama_config(company, user):
    """A UserLLMConfig for Ollama (no API key, uses api_base)."""
    from apps.pkm.models import UserLLMConfig

    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="ollama",
        api_key_encrypted="",
        api_base="http://localhost:11434",
        default_model="llama3",
        default_embedding_model="nomic-embed-text",
        is_active=True,
    )


def _mock_completion_response(text: str = "Mocked answer") -> MagicMock:
    """Build a mock litellm completion response object."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=text))]
    return mock_resp


def _mock_embedding_response(vectors=None) -> MagicMock:
    """Build a mock litellm embedding response object."""
    mock_resp = MagicMock()
    if vectors is None:
        vectors = [[0.1] * 1536]
    mock_resp.data = [MagicMock(embedding=v) for v in vectors]
    return mock_resp


# ---------------------------------------------------------------------------
# get_completion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_completion_calls_litellm_completion(openai_config):
    """get_completion delegates to litellm.completion."""
    mock_resp = _mock_completion_response("Hello!")
    with patch("apps.pkm.services.llm_service.completion", return_value=mock_resp) as mock_fn:
        result = llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])
    assert result is mock_resp
    mock_fn.assert_called_once()


@pytest.mark.django_db
def test_get_completion_uses_provider_prefix(openai_config):
    """The model passed to litellm uses 'openai/' prefix format."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])
    _, kwargs = mock_fn.call_args
    assert kwargs["model"] == "openai/gpt-4o"


@pytest.mark.django_db
def test_get_completion_anthropic_prefix(anthropic_config):
    """Anthropic uses 'anthropic/' prefix."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(anthropic_config, [{"role": "user", "content": "Hi"}])
    _, kwargs = mock_fn.call_args
    assert kwargs["model"] == "anthropic/claude-sonnet-4-20250514"


@pytest.mark.django_db
def test_get_completion_ollama_prefix(ollama_config):
    """Ollama uses 'ollama/' prefix."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(ollama_config, [{"role": "user", "content": "Hi"}])
    _, kwargs = mock_fn.call_args
    assert kwargs["model"] == "ollama/llama3"


@pytest.mark.django_db
def test_get_completion_passes_decrypted_api_key_per_call(openai_config):
    """The decrypted API key is passed per-call, NOT set as a global env var."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])
    _, kwargs = mock_fn.call_args
    assert kwargs["api_key"] == "sk-test-openai-key"


@pytest.mark.django_db
def test_get_completion_no_api_key_for_empty_encrypted(ollama_config):
    """If api_key_encrypted is empty, api_key is not passed (or None)."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(ollama_config, [{"role": "user", "content": "Hi"}])
    _, kwargs = mock_fn.call_args
    # For Ollama, api_key should be None or not set (no key needed)
    assert kwargs.get("api_key") is None or kwargs.get("api_key") == ""


@pytest.mark.django_db
def test_get_completion_passes_api_base(openai_config):
    """api_base is forwarded to litellm when present."""
    openai_config.api_base = "https://custom.openai.endpoint.com"
    openai_config.save()
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])
    _, kwargs = mock_fn.call_args
    assert kwargs["api_base"] == "https://custom.openai.endpoint.com"


@pytest.mark.django_db
def test_get_completion_passes_messages(openai_config):
    """Messages are forwarded to litellm."""
    msgs = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "What is 2+2?"},
    ]
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(openai_config, msgs)
    _, kwargs = mock_fn.call_args
    assert kwargs["messages"] == msgs


@pytest.mark.django_db
def test_get_completion_stream_false(openai_config):
    """stream=False is forwarded."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}], stream=False)
    _, kwargs = mock_fn.call_args
    assert kwargs["stream"] is False


@pytest.mark.django_db
def test_get_completion_stream_true(openai_config):
    """stream=True is forwarded."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}], stream=True)
    _, kwargs = mock_fn.call_args
    assert kwargs["stream"] is True


# ---------------------------------------------------------------------------
# get_embedding
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_embedding_calls_litellm_embedding(openai_config):
    """get_embedding delegates to litellm.embedding."""
    mock_resp = _mock_embedding_response()
    with patch("apps.pkm.services.llm_service.embedding", return_value=mock_resp) as mock_fn:
        result = llm_service.get_embedding(openai_config, ["hello world"])
    assert result is mock_resp
    mock_fn.assert_called_once()


@pytest.mark.django_db
def test_get_embedding_passes_texts_as_input(openai_config):
    """The texts list is forwarded as the 'input' parameter."""
    texts = ["chunk one", "chunk two"]
    with patch(
        "apps.pkm.services.llm_service.embedding", return_value=_mock_embedding_response()
    ) as mock_fn:
        llm_service.get_embedding(openai_config, texts)
    _, kwargs = mock_fn.call_args
    assert kwargs["input"] == texts


@pytest.mark.django_db
def test_get_embedding_uses_default_embedding_model(openai_config):
    """Uses default_embedding_model from the config (with provider prefix)."""
    with patch(
        "apps.pkm.services.llm_service.embedding", return_value=_mock_embedding_response()
    ) as mock_fn:
        llm_service.get_embedding(openai_config, ["text"])
    _, kwargs = mock_fn.call_args
    assert kwargs["model"] == "openai/text-embedding-3-small"


@pytest.mark.django_db
def test_get_embedding_explicit_model_override(openai_config):
    """When model param is provided, it overrides the config's default."""
    with patch(
        "apps.pkm.services.llm_service.embedding", return_value=_mock_embedding_response()
    ) as mock_fn:
        llm_service.get_embedding(openai_config, ["text"], model="text-embedding-3-large")
    _, kwargs = mock_fn.call_args
    assert kwargs["model"] == "openai/text-embedding-3-large"


@pytest.mark.django_db
def test_get_embedding_passes_api_key(openai_config):
    """Decrypted API key is passed per-call."""
    with patch(
        "apps.pkm.services.llm_service.embedding", return_value=_mock_embedding_response()
    ) as mock_fn:
        llm_service.get_embedding(openai_config, ["text"])
    _, kwargs = mock_fn.call_args
    assert kwargs["api_key"] == "sk-test-openai-key"


@pytest.mark.django_db
def test_get_embedding_ollama_uses_api_base(ollama_config):
    """Ollama embedding passes api_base."""
    with patch(
        "apps.pkm.services.llm_service.embedding", return_value=_mock_embedding_response()
    ) as mock_fn:
        llm_service.get_embedding(ollama_config, ["text"])
    _, kwargs = mock_fn.call_args
    assert kwargs["model"] == "ollama/nomic-embed-text"
    assert kwargs["api_base"] == "http://localhost:11434"


# ---------------------------------------------------------------------------
# get_available_providers
# ---------------------------------------------------------------------------


def test_get_available_providers_returns_list():
    """get_available_providers returns a list of strings."""
    providers = llm_service.get_available_providers()
    assert isinstance(providers, list)
    for p in providers:
        assert isinstance(p, str)


def test_get_available_providers_has_all_six():
    """All 6 supported providers are returned."""
    providers = llm_service.get_available_providers()
    expected = {"openai", "anthropic", "gemini", "groq", "openrouter", "ollama"}
    assert set(providers) == expected


def test_get_available_providers_count():
    """Exactly 6 providers."""
    assert len(llm_service.get_available_providers()) == 6


# ---------------------------------------------------------------------------
# get_provider_models
# ---------------------------------------------------------------------------


def test_get_provider_models_openai():
    """OpenAI models include a chat model and an embedding model."""
    models = llm_service.get_provider_models("openai")
    assert isinstance(models, list)
    assert len(models) > 0
    assert any("gpt" in m.lower() for m in models)


def test_get_provider_models_anthropic():
    """Anthropic models include a Claude model."""
    models = llm_service.get_provider_models("anthropic")
    assert len(models) > 0
    assert any("claude" in m.lower() for m in models)


def test_get_provider_models_gemini():
    """Gemini models include a Gemini model."""
    models = llm_service.get_provider_models("gemini")
    assert len(models) > 0
    assert any("gemini" in m.lower() for m in models)


def test_get_provider_models_groq():
    """Groq models include a model."""
    models = llm_service.get_provider_models("groq")
    assert len(models) > 0


def test_get_provider_models_openrouter():
    """OpenRouter models include a model."""
    models = llm_service.get_provider_models("openrouter")
    assert len(models) > 0


def test_get_provider_models_ollama():
    """Ollama models include a model."""
    models = llm_service.get_provider_models("ollama")
    assert len(models) > 0


def test_get_provider_models_unknown_returns_empty():
    """Unknown provider returns an empty list (not an error)."""
    models = llm_service.get_provider_models("nonexistent")
    assert models == []


# ---------------------------------------------------------------------------
# validate_api_key
# ---------------------------------------------------------------------------


def test_validate_api_key_success():
    """validate_api_key returns True when the test call succeeds."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ):
        result = llm_service.validate_api_key("openai", "sk-valid-key")
    assert result is True


def test_validate_api_key_auth_error():
    """validate_api_key returns False on AuthenticationError."""
    from litellm import AuthenticationError

    with patch(
        "apps.pkm.services.llm_service.completion",
        side_effect=AuthenticationError("bad key", "openai", "openai"),
    ):
        result = llm_service.validate_api_key("openai", "sk-bad-key")
    assert result is False


def test_validate_api_key_unknown_provider():
    """validate_api_key returns False for unknown provider."""
    result = llm_service.validate_api_key("nonexistent", "some-key")
    assert result is False


def test_validate_api_key_passes_api_base():
    """api_base is forwarded to the test call."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.validate_api_key("ollama", "some-key", api_base="http://localhost:11434")
    _, kwargs = mock_fn.call_args
    assert kwargs["api_base"] == "http://localhost:11434"


def test_validate_api_key_uses_cheap_model():
    """Validation uses a minimal test call with max_tokens=1."""
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.validate_api_key("openai", "sk-key")
    _, kwargs = mock_fn.call_args
    assert kwargs.get("max_tokens") == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_completion_raises_llm_error_on_authentication_error(openai_config):
    """get_completion raises LLMError on AuthenticationError."""
    from litellm import AuthenticationError

    with (
        patch(
            "apps.pkm.services.llm_service.completion",
            side_effect=AuthenticationError("bad", "openai", "openai"),
        ),
        pytest.raises(llm_service.LLMError) as exc_info,
    ):
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])
    assert "api key" in str(exc_info.value).lower() or "auth" in str(exc_info.value).lower()


@pytest.mark.django_db
def test_get_completion_raises_llm_error_on_rate_limit(openai_config):
    """get_completion raises LLMError on RateLimitError."""
    from litellm import RateLimitError

    with (
        patch(
            "apps.pkm.services.llm_service.completion",
            side_effect=RateLimitError("rate", "openai", "openai"),
        ),
        pytest.raises(llm_service.LLMError),
    ):
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])


@pytest.mark.django_db
def test_get_completion_raises_llm_error_on_timeout(openai_config):
    """get_completion raises LLMError on Timeout."""
    from litellm import Timeout

    with (
        patch(
            "apps.pkm.services.llm_service.completion",
            side_effect=Timeout("timed out", "openai", "openai"),
        ),
        pytest.raises(llm_service.LLMError),
    ):
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])


@pytest.mark.django_db
def test_get_completion_raises_llm_error_on_api_connection_error(openai_config):
    """get_completion raises LLMError on APIConnectionError."""
    from litellm import APIConnectionError

    with (
        patch(
            "apps.pkm.services.llm_service.completion",
            side_effect=APIConnectionError("conn error", "openai", "openai"),
        ),
        pytest.raises(llm_service.LLMError),
    ):
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])


@pytest.mark.django_db
def test_get_embedding_raises_llm_error_on_authentication_error(openai_config):
    """get_embedding raises LLMError on AuthenticationError."""
    from litellm import AuthenticationError

    with (
        patch(
            "apps.pkm.services.llm_service.embedding",
            side_effect=AuthenticationError("bad", "openai", "openai"),
        ),
        pytest.raises(llm_service.LLMError),
    ):
        llm_service.get_embedding(openai_config, ["text"])


@pytest.mark.django_db
def test_get_embedding_raises_llm_error_on_rate_limit(openai_config):
    """get_embedding raises LLMError on RateLimitError."""
    from litellm import RateLimitError

    with (
        patch(
            "apps.pkm.services.llm_service.embedding",
            side_effect=RateLimitError("rate", "openai", "openai"),
        ),
        pytest.raises(llm_service.LLMError),
    ):
        llm_service.get_embedding(openai_config, ["text"])


@pytest.mark.django_db
def test_get_embedding_raises_llm_error_on_timeout(openai_config):
    """get_embedding raises LLMError on Timeout."""
    from litellm import Timeout

    with (
        patch(
            "apps.pkm.services.llm_service.embedding",
            side_effect=Timeout("timed out", "openai", "openai"),
        ),
        pytest.raises(llm_service.LLMError),
    ):
        llm_service.get_embedding(openai_config, ["text"])


@pytest.mark.django_db
def test_get_embedding_raises_llm_error_on_api_connection_error(openai_config):
    """get_embedding raises LLMError on APIConnectionError."""
    from litellm import APIConnectionError

    with (
        patch(
            "apps.pkm.services.llm_service.embedding",
            side_effect=APIConnectionError("conn error", "openai", "openai"),
        ),
        pytest.raises(llm_service.LLMError),
    ):
        llm_service.get_embedding(openai_config, ["text"])


# ---------------------------------------------------------------------------
# Security: API key never logged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_api_key_never_logged_in_completion(openai_config, caplog):
    """The decrypted API key must never appear in any log record."""
    sensitive_key = "sk-test-openai-key"
    with (
        caplog.at_level(logging.DEBUG, logger="apps.pkm.services.llm_service"),
        patch("apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()),
    ):
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])
    for record in caplog.records:
        assert sensitive_key not in record.getMessage()


@pytest.mark.django_db
def test_api_key_never_logged_in_embedding(openai_config, caplog):
    """The decrypted API key must never appear in logs during embedding calls."""
    sensitive_key = "sk-test-openai-key"
    with (
        caplog.at_level(logging.DEBUG, logger="apps.pkm.services.llm_service"),
        patch("apps.pkm.services.llm_service.embedding", return_value=_mock_embedding_response()),
    ):
        llm_service.get_embedding(openai_config, ["text"])
    for record in caplog.records:
        assert sensitive_key not in record.getMessage()


@pytest.mark.django_db
def test_api_key_never_logged_on_error(openai_config, caplog):
    """API key must not leak into logs even when errors are logged."""
    from litellm import AuthenticationError

    sensitive_key = "sk-test-openai-key"
    with (
        caplog.at_level(logging.DEBUG, logger="apps.pkm.services.llm_service"),
        patch(
            "apps.pkm.services.llm_service.completion",
            side_effect=AuthenticationError("bad", "openai", "openai"),
        ),
        contextlib.suppress(llm_service.LLMError),
    ):
        llm_service.get_completion(openai_config, [{"role": "user", "content": "Hi"}])
    for record in caplog.records:
        assert sensitive_key not in record.getMessage()


# ---------------------------------------------------------------------------
# Provider prefix formatting (all 6 providers)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_completion_groq_prefix(company, user):
    """Groq uses 'groq/' prefix."""
    from apps.pkm.models import UserLLMConfig

    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="groq",
        api_key_encrypted="",
        default_model="llama-3.3-70b-versatile",
        default_embedding_model="text-embedding-3-small",
    )
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(config, [{"role": "user", "content": "Hi"}])
    _, kwargs = mock_fn.call_args
    assert kwargs["model"] == "groq/llama-3.3-70b-versatile"


@pytest.mark.django_db
def test_completion_gemini_prefix(company, user):
    """Gemini uses 'gemini/' prefix."""
    from apps.pkm.models import UserLLMConfig

    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="gemini",
        api_key_encrypted="",
        default_model="gemini-2.0-flash",
        default_embedding_model="text-embedding-004",
    )
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(config, [{"role": "user", "content": "Hi"}])
    _, kwargs = mock_fn.call_args
    assert kwargs["model"] == "gemini/gemini-2.0-flash"


@pytest.mark.django_db
def test_completion_openrouter_prefix(company, user):
    """OpenRouter uses 'openrouter/' prefix."""
    from apps.pkm.models import UserLLMConfig

    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openrouter",
        api_key_encrypted="",
        default_model="anthropic/claude-3.5-sonnet",
        default_embedding_model="text-embedding-3-small",
    )
    with patch(
        "apps.pkm.services.llm_service.completion", return_value=_mock_completion_response()
    ) as mock_fn:
        llm_service.get_completion(config, [{"role": "user", "content": "Hi"}])
    _, kwargs = mock_fn.call_args
    assert kwargs["model"] == "openrouter/anthropic/claude-3.5-sonnet"


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


def test_llm_service_exports():
    """The module exports all required public functions."""
    assert hasattr(llm_service, "get_completion")
    assert hasattr(llm_service, "get_embedding")
    assert hasattr(llm_service, "get_available_providers")
    assert hasattr(llm_service, "get_provider_models")
    assert hasattr(llm_service, "validate_api_key")
    assert hasattr(llm_service, "LLMError")
