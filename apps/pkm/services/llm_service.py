"""LiteLLM wrapper service for multi-provider LLM calls.

Wraps :mod:`litellm` to provide a thin, consistent interface for the PKM
module. Each call receives a :class:`~apps.pkm.models.UserLLMConfig` instance,
decrypts the API key in-memory, and passes it **per-call** to litellm. Keys
are never stored in global env vars or logged.

Supported providers (litellm model prefix format):
  - OpenAI       -> ``openai/``
  - Anthropic    -> ``anthropic/``
  - Google Gemini -> ``gemini/``
  - Groq         -> ``groq/``
  - OpenRouter   -> ``openrouter/``
  - Ollama       -> ``ollama/``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from litellm import (
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
    Timeout,
    completion,
    embedding,
)

from apps.pkm.services.encryption_service import decrypt

if TYPE_CHECKING:
    from apps.pkm.models import UserLLMConfig

logger = logging.getLogger(__name__)

__all__ = [
    "LLMError",
    "LLMAuthError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "get_completion",
    "get_embedding",
    "get_available_providers",
    "get_provider_models",
    "validate_api_key",
]


class LLMError(Exception):
    """Raised when an LLM API call fails (auth, rate-limit, timeout, etc.).

    All litellm exceptions are translated to ``LLMError`` so callers only need
    to catch one type. The original message is preserved but never includes
    the decrypted API key.

    Specific subclasses allow the API layer to map errors to appropriate HTTP
    status codes:

    - :class:`LLMAuthError` -> 401 (authentication failed)
    - :class:`LLMRateLimitError` -> 429 (rate limited)
    - :class:`LLMTimeoutError` -> 504 (timeout or connection error)
    """


class LLMAuthError(LLMError):
    """LLM authentication failed (invalid API key)."""


class LLMRateLimitError(LLMError):
    """LLM provider rate limit exceeded."""


class LLMTimeoutError(LLMError):
    """LLM request timed out or could not connect to the provider."""


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

# All 6 supported providers. The key is the canonical provider string stored
# in ``UserLLMConfig.provider``; the value is the litellm model prefix.
_PROVIDER_PREFIXES: dict[str, str] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "groq": "groq",
    "openrouter": "openrouter",
    "ollama": "ollama",
}

# Suggested models per provider. These are used by the UI dropdown and as
# sensible defaults. Updated as of 2025-06.
_PROVIDER_MODELS: dict[str, list[str]] = {
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "text-embedding-3-small",
        "text-embedding-3-large",
    ],
    "anthropic": [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "text-embedding-004",
    ],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    "openrouter": [
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.1-8b-instruct",
    ],
    "ollama": [
        "llama3",
        "llama3.1",
        "mistral",
        "qwen2.5",
        "nomic-embed-text",
    ],
}

# Cheapest model per provider used for API key validation (max_tokens=1).
_VALIDATION_MODELS: dict[str, str] = {
    "openai": "openai/gpt-4o-mini",
    "anthropic": "anthropic/claude-3-5-haiku-20241022",
    "gemini": "gemini/gemini-1.5-flash",
    "groq": "groq/llama-3.1-8b-instant",
    "openrouter": "openrouter/meta-llama/llama-3.1-8b-instruct",
    "ollama": "ollama/llama3",
}


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------


def _format_model(provider: str, model: str) -> str:
    """Prefix a model name with its provider using litellm format.

    If the model already starts with ``"provider/"`` (e.g. OpenRouter models
    like ``anthropic/claude-3.5-sonnet``), the provider prefix is still
    prepended so litellm receives ``openrouter/anthropic/claude-3.5-sonnet``.
    """
    prefix = _PROVIDER_PREFIXES.get(provider)
    if prefix is None:
        # Unknown provider: return as-is and let litellm raise.
        return model
    return f"{prefix}/{model}"


def _get_api_key(user_config: UserLLMConfig) -> str | None:
    """Decrypt the API key from the user config, in-memory only.

    Returns ``None`` if the encrypted field is empty (e.g. Ollama). The
    decrypted value is never logged.
    """
    encrypted = user_config.api_key_encrypted
    if not encrypted:
        return None
    try:
        return decrypt(encrypted)
    except Exception:
        logger.warning("Failed to decrypt API key for provider %s", user_config.provider)
        return None


def _build_call_kwargs(
    user_config: UserLLMConfig,
    *,
    model: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the kwargs dict for a litellm call.

    Includes model (with provider prefix), decrypted api_key (per-call),
    and api_base if present.
    """
    kwargs: dict[str, Any] = {
        "model": _format_model(user_config.provider, model),
    }
    api_key = _get_api_key(user_config)
    if api_key:
        kwargs["api_key"] = api_key
    else:
        kwargs["api_key"] = None

    api_base = getattr(user_config, "api_base", "") or ""
    if api_base:
        kwargs["api_base"] = api_base

    if extra:
        kwargs.update(extra)

    return kwargs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_completion(
    user_config: UserLLMConfig,
    messages: list[dict[str, Any]],
    stream: bool = False,
) -> Any:
    """Call ``litellm.completion`` with the user's decrypted API key.

    The model is formatted as ``provider/model`` per litellm's prefix
    convention. The API key is passed per-call and never stored globally.

    Args:
        user_config: The user's LLM configuration (provider, model, encrypted key).
        messages: Chat messages list (OpenAI format).
        stream: If ``True``, return a streaming iterator.

    Returns:
        The litellm response object (or streaming iterator).

    Raises:
        LLMError: On authentication, rate-limit, timeout, or connection errors.
    """
    kwargs = _build_call_kwargs(
        user_config,
        model=user_config.default_model,
        extra={"messages": messages, "stream": stream},
    )
    try:
        return completion(**kwargs)
    except AuthenticationError as exc:
        raise LLMAuthError("Invalid API key. Please check your configuration.") from exc
    except RateLimitError as exc:
        raise LLMRateLimitError("Rate limit reached. Please try again later.") from exc
    except Timeout as exc:
        raise LLMTimeoutError("Request timed out. Please try again.") from exc
    except APIConnectionError as exc:
        raise LLMTimeoutError(f"Cannot connect to {user_config.provider} API.") from exc


def get_embedding(
    user_config: UserLLMConfig,
    texts: list[str],
    model: str | None = None,
) -> Any:
    """Call ``litellm.embedding`` with the user's decrypted API key.

    Uses ``user_config.default_embedding_model`` unless ``model`` is provided.
    The model is prefixed with the provider (e.g. ``openai/text-embedding-3-small``).

    Args:
        user_config: The user's LLM configuration.
        texts: List of text strings to embed.
        model: Override embedding model name (without provider prefix).

    Returns:
        The litellm embedding response object.

    Raises:
        LLMError: On authentication, rate-limit, timeout, or connection errors.
    """
    embed_model = model or user_config.default_embedding_model
    if not embed_model:
        raise LLMError(f"No embedding model configured for provider '{user_config.provider}'.")
    kwargs = _build_call_kwargs(
        user_config,
        model=embed_model,
        extra={"input": texts},
    )
    try:
        return embedding(**kwargs)
    except AuthenticationError as exc:
        raise LLMAuthError("Invalid API key. Please check your configuration.") from exc
    except RateLimitError as exc:
        raise LLMRateLimitError("Rate limit reached. Please try again later.") from exc
    except Timeout as exc:
        raise LLMTimeoutError("Request timed out. Please try again.") from exc
    except APIConnectionError as exc:
        raise LLMTimeoutError(f"Cannot connect to {user_config.provider} API.") from exc


def get_available_providers() -> list[str]:
    """Return the list of supported provider strings.

    These match the values stored in ``UserLLMConfig.provider`` and the
    litellm model prefix for each provider.
    """
    return list(_PROVIDER_PREFIXES.keys())


def get_provider_models(provider: str) -> list[str]:
    """Return a list of suggested models for the given provider.

    Returns an empty list for unknown providers.
    """
    return list(_PROVIDER_MODELS.get(provider, []))


def validate_api_key(
    provider: str,
    api_key: str,
    api_base: str | None = None,
) -> bool:
    """Validate an API key by making a minimal test call.

    Uses the cheapest available model with ``max_tokens=1`` to minimise cost.
    Does NOT store the key anywhere.

    Args:
        provider: Provider string (openai, anthropic, gemini, groq, openrouter, ollama).
        api_key: Plaintext API key to test.
        api_base: Optional custom API base URL.

    Returns:
        ``True`` if the key is valid, ``False`` otherwise.
    """
    model = _VALIDATION_MODELS.get(provider)
    if not model:
        return False

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": "test"}],
        "api_key": api_key,
        "max_tokens": 1,
    }
    if api_base:
        kwargs["api_base"] = api_base

    try:
        completion(**kwargs)
        return True
    except AuthenticationError:
        return False
    except Exception:
        return False
