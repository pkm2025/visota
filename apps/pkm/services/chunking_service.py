"""Text chunking and token-counting service for the PKM RAG pipeline.

Splits long documents into overlapping chunks so each chunk fits within an
LLM/embedding context window, and counts tokens so callers can budget API
usage and store ``token_count`` on :class:`~apps.pkm.models.DocumentChunk`.

Design notes:
  - Chunking uses :class:`langchain_text_splitters.RecursiveCharacterTextSplitter`
    with the separator hierarchy ``['\\n\\n', '\\n', '. ', ' ', '']``. The
    splitter tries paragraph breaks first, then line breaks, then sentence
    boundaries, then words, and finally individual characters, which keeps
    semantically related text together whenever possible.
  - ``chunk_size`` and ``chunk_overlap`` are measured in *characters* (the
    convention used by LangChain). Callers that want token-based sizing can
    pass ``chunk_size`` derived from :func:`count_tokens`.
  - Token counting uses :mod:`tiktoken`, the same BPE tokenizer used by OpenAI
    models, so ``count_tokens`` is accurate for the ``gpt-4o`` family. For
    non-OpenAI models we still default to the ``cl100k_base`` encoding, which
    is a close upper-bound approximation for most modern LLMs.

No Django ORM or database access happens here; the functions are pure and safe
to call from async tasks (django-q2) or tests without DB fixtures.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from langchain_text_splitters import RecursiveCharacterTextSplitter

if TYPE_CHECKING:
    import tiktoken

logger = logging.getLogger(__name__)

#: Separator hierarchy used by :func:`split_text`.
#:
#: Ordered from most-preferred (paragraph break) to least-preferred (single
#: character). The recursive splitter uses the first separator that keeps a
#: piece under ``chunk_size``; falling back to the next one only as needed.
SEPARATORS: list[str] = ["\n\n", "\n", ". ", " ", ""]

#: Default chunk size in characters (matches LangChain/RAG convention).
DEFAULT_CHUNK_SIZE: int = 1000

#: Default overlap between consecutive chunks in characters.
DEFAULT_CHUNK_OVERLAP: int = 200

#: Model assumed when ``count_tokens`` is called without an explicit model.
DEFAULT_MODEL: str = "gpt-4o"


def _build_splitter(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    """Construct a configured :class:`RecursiveCharacterTextSplitter`.

    Keeping splitter construction in a helper makes it trivial to unit-test
    the configuration and lets future callers reuse the same settings.
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be a positive integer, got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap must be non-negative, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be smaller than chunk_size "
            f"({chunk_size}) so chunks can make progress."
        )
    return RecursiveCharacterTextSplitter(
        separators=SEPARATORS,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        keep_separator=True,
        strip_whitespace=False,
    )


def split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split ``text`` into overlapping chunks.

    Args:
        text: The document text to split.
        chunk_size: Maximum size of each chunk in characters.
        chunk_overlap: Number of characters of overlap between consecutive
            chunks. Must be smaller than ``chunk_size``.

    Returns:
        A list of chunk strings. An empty input returns an empty list. A
        single chunk is returned when ``text`` fits within ``chunk_size``.

    Raises:
        ValueError: If ``chunk_size`` is not positive, ``chunk_overlap`` is
            negative, or ``chunk_overlap >= chunk_size``.

    The splitter tries to break on paragraph boundaries (``\\n\\n``) first,
    then line breaks, sentence boundaries (``". "``), words, and finally
    characters. ``keep_separator=True`` preserves the leading separator of
    each chunk so context (e.g. a paragraph break) is not lost at the seam.
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not text:
        return []

    splitter = _build_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_text(text)
    logger.debug(
        "Split %d chars into %d chunks (chunk_size=%d, overlap=%d)",
        len(text),
        len(chunks),
        chunk_size,
        chunk_overlap,
    )
    return chunks


@lru_cache(maxsize=32)
def _get_encoding(model: str) -> tiktoken.Encoding:
    """Return (and cache) the tiktoken encoding for ``model``.

    tiktoken's encoding lookup downloads/loads a BPE vocab on first use, so we
    cache the result per model name. If ``model`` is not recognized by
    :func:`tiktoken.encoding_for_model` we fall back to ``cl100k_base``, which
    is a reasonable approximation for most modern chat models.

    The forward reference type avoids importing tiktoken at module load time
    for callers that only need :func:`split_text`.
    """
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        logger.debug("No tiktoken encoding for model %r; falling back to cl100k_base", model)
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """Count the number of tokens in ``text`` for the given ``model``.

    Uses :mod:`tiktoken` (the BPE tokenizer used by OpenAI models). For models
    tiktoken does not know (e.g. Anthropic, Gemini) the ``cl100k_base``
    encoding is used as an approximation, which is an accurate upper bound for
    budgeting purposes.

    Args:
        text: The text to count tokens for.
        model: The model name (e.g. ``"gpt-4o"``, ``"gpt-3.5-turbo"``).
            Defaults to ``"gpt-4o"``.

    Returns:
        The integer token count.

    Raises:
        TypeError: If ``text`` is not a string.
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not text:
        return 0
    encoding = _get_encoding(model)
    return len(encoding.encode(text))


__all__ = [
    "split_text",
    "count_tokens",
    "SEPARATORS",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_MODEL",
]
