"""Unit tests for apps.pkm.services.chunking_service.

Covers :func:`split_text` (chunk count scales with length, chunks within size
range, overlap present, edge cases) and :func:`count_tokens` (token counting
works for known strings, scales with length, handles model fallback).

No database access is required (pure text-processing logic). We import
``tiktoken`` directly in a couple of tests to cross-check the service output
against the library, so the test would catch a regression in our wrapper.
"""

from __future__ import annotations

import pytest

from apps.pkm.services import chunking_service
from apps.pkm.services.chunking_service import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    SEPARATORS,
    count_tokens,
    split_text,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _paragraph(words: int) -> str:
    """Return a paragraph of approximately ``words`` words."""
    return " ".join(f"word{i}" for i in range(words))


def _long_text(chars: int) -> str:
    """Return deterministic text of approximately ``chars`` characters."""
    base = "The quick brown fox jumps over the lazy dog. "
    repeats = max(1, chars // len(base) + 1)
    return (base * repeats)[:chars]


# ---------------------------------------------------------------------------
# split_text - basic behavior
# ---------------------------------------------------------------------------


def test_empty_string_returns_empty_list():
    assert split_text("") == []


def test_short_text_returns_single_chunk():
    text = "A short sentence."
    chunks = split_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_returns_list_of_strings():
    text = _long_text(5000)
    chunks = split_text(text)
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)
    assert len(chunks) > 1


def test_round_trip_preserves_content():
    """Concatenating chunks should cover the original text content."""
    text = _long_text(3000)
    chunks = split_text(text, chunk_size=500, chunk_overlap=50)
    # Every word from the original text must appear in at least one chunk.
    for word in text.split():
        assert any(word in chunk for chunk in chunks)


# ---------------------------------------------------------------------------
# split_text - chunk count scales with text length
# ---------------------------------------------------------------------------


def test_chunk_count_scales_with_text_length():
    short = _long_text(500)
    long_text = _long_text(5000)
    short_chunks = split_text(short, chunk_size=200, chunk_overlap=20)
    long_chunks = split_text(long_text, chunk_size=200, chunk_overlap=20)
    assert len(long_chunks) > len(short_chunks)


def test_longer_text_produces_more_chunks():
    text_2k = _long_text(2000)
    text_5k = _long_text(5000)
    chunks_2k = split_text(text_2k)
    chunks_5k = split_text(text_5k)
    assert len(chunks_5k) > len(chunks_2k)


# ---------------------------------------------------------------------------
# split_text - chunks within size range
# ---------------------------------------------------------------------------


def test_chunks_within_chunk_size():
    chunk_size = 300
    text = _long_text(5000)
    chunks = split_text(text, chunk_size=chunk_size, chunk_overlap=50)
    for chunk in chunks:
        # RecursiveCharacterTextSplitter keeps each chunk <= chunk_size, but
        # separators may slightly exceed; allow a small tolerance.
        assert len(chunk) <= chunk_size + len("\n\n")


def test_chunks_with_small_size_stay_small():
    chunk_size = 100
    text = _long_text(2000)
    chunks = split_text(text, chunk_size=chunk_size, chunk_overlap=10)
    for chunk in chunks:
        assert len(chunk) <= chunk_size + len("\n\n")


def test_chunks_are_non_empty():
    text = _long_text(2000)
    chunks = split_text(text, chunk_size=500, chunk_overlap=50)
    for chunk in chunks:
        assert chunk.strip() != ""


# ---------------------------------------------------------------------------
# split_text - overlap present
# ---------------------------------------------------------------------------


def test_overlap_present_between_consecutive_chunks():
    """Consecutive chunks should share overlapping content.

    LangChain's RecursiveCharacterTextSplitter splits at separator boundaries,
    so the overlap is not a strict character-suffix match. Instead we verify
    that a word sequence from the end of chunk[i] reappears near the start of
    chunk[i+1], which is the practical guarantee overlap provides: no content
    is lost at the seam between chunks.
    """
    chunk_size = 300
    chunk_overlap = 100
    # Use text without newlines so the splitter falls through to word/char
    # separators, producing predictable overlap.
    text = _long_text(3000).replace("\n", " ")
    chunks = split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    assert len(chunks) >= 2

    # Verify that the last few words of chunk[i] appear at the start of
    # chunk[i+1] (the overlap region).
    overlap_found = 0
    for i in range(len(chunks) - 1):
        tail_words = chunks[i].split()[-5:]
        next_words = chunks[i + 1].split()[:10]
        # Check that at least one tail word appears early in the next chunk.
        if any(w in next_words for w in tail_words):
            overlap_found += 1
    assert overlap_found > 0, "Expected overlapping content between consecutive chunks"


def test_overlap_with_explicit_paragraphs():
    """Even with paragraph separators, overlapping content should appear."""
    paragraphs = [_paragraph(80) for _ in range(10)]
    text = "\n\n".join(paragraphs)
    chunks = split_text(text, chunk_size=400, chunk_overlap=100)
    assert len(chunks) > 1
    # Each word should appear in at least one chunk (round-trip sanity).
    all_text = " ".join(chunks)
    for word in paragraphs[len(paragraphs) // 2].split():
        assert word in all_text


# ---------------------------------------------------------------------------
# split_text - parameter validation
# ---------------------------------------------------------------------------


def test_chunk_overlap_zero_allowed():
    text = _long_text(1000)
    chunks = split_text(text, chunk_size=200, chunk_overlap=0)
    assert len(chunks) > 1


def test_chunk_size_must_be_positive():
    with pytest.raises(ValueError, match="chunk_size"):
        split_text("hello", chunk_size=0)


def test_negative_chunk_size_rejected():
    with pytest.raises(ValueError, match="chunk_size"):
        split_text("hello", chunk_size=-100)


def test_negative_overlap_rejected():
    with pytest.raises(ValueError, match="chunk_overlap"):
        split_text("hello", chunk_size=100, chunk_overlap=-1)


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError, match="smaller than chunk_size"):
        split_text("hello", chunk_size=100, chunk_overlap=100)


def test_overlap_larger_than_size_rejected():
    with pytest.raises(ValueError, match="smaller than chunk_size"):
        split_text("hello", chunk_size=50, chunk_overlap=200)


def test_non_string_text_rejected():
    with pytest.raises(TypeError):
        split_text(123)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# split_text - separator behavior
# ---------------------------------------------------------------------------


def test_separators_constant_is_expected_hierarchy():
    assert SEPARATORS == ["\n\n", "\n", ". ", " ", ""]


def test_prefers_paragraph_breaks():
    """The splitter should respect paragraph boundaries when possible."""
    para_a = _paragraph(40)
    para_b = _paragraph(40)
    text = para_a + "\n\n" + para_b
    chunks = split_text(text, chunk_size=100, chunk_overlap=10)
    # Each paragraph should fit in its own chunk (or be preserved together).
    assert any(para_a.split()[0] in c for c in chunks)
    assert any(para_b.split()[0] in c for c in chunks)


# ---------------------------------------------------------------------------
# count_tokens - basic behavior
# ---------------------------------------------------------------------------


def test_count_tokens_empty_string():
    assert count_tokens("") == 0


def test_count_tokens_simple_word():
    assert count_tokens("hello") >= 1


def test_count_tokens_known_value():
    """Cross-check against tiktoken directly for gpt-4o."""
    import tiktoken

    text = "The quick brown fox jumps over the lazy dog."
    enc = tiktoken.encoding_for_model("gpt-4o")
    expected = len(enc.encode(text))
    assert count_tokens(text, model="gpt-4o") == expected


def test_count_tokens_default_model_is_gpt4o():
    """Calling without a model should use gpt-4o and match direct tiktoken."""
    import tiktoken

    text = "A Vietnamese accounting ERP built with Django."
    enc = tiktoken.encoding_for_model("gpt-4o")
    assert count_tokens(text) == len(enc.encode(text))


def test_count_tokens_unicode():
    text = "Tiêu đề ghi chú - 测试 - 🔑"
    tokens = count_tokens(text)
    assert tokens >= 1


# ---------------------------------------------------------------------------
# count_tokens - scales with length
# ---------------------------------------------------------------------------


def test_count_tokens_scales_with_length():
    short = "hello"
    long_text = " ".join(["hello"] * 1000)
    assert count_tokens(long_text) > count_tokens(short)


def test_count_tokens_proportional_to_text():
    """Doubling the text should roughly double the token count."""
    base = "The quick brown fox jumps over the lazy dog. "
    text_100 = base * 100
    text_200 = base * 200
    tokens_100 = count_tokens(text_100)
    tokens_200 = count_tokens(text_200)
    assert tokens_200 > tokens_100
    # Should be roughly 2x (allow some tolerance for BPE boundaries).
    ratio = tokens_200 / tokens_100
    assert 1.8 <= ratio <= 2.2


# ---------------------------------------------------------------------------
# count_tokens - model fallback
# ---------------------------------------------------------------------------


def test_count_tokens_unknown_model_falls_back():
    """Unknown model names should not crash; they fall back to cl100k_base."""
    tokens = count_tokens("hello world", model="some-fake-model-xyz")
    assert tokens >= 1


def test_count_tokens_non_string_rejected():
    with pytest.raises(TypeError):
        count_tokens(123)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Integration of split_text + count_tokens
# ---------------------------------------------------------------------------


def test_each_chunk_token_count_within_budget():
    """Chunks should each have a bounded token count for a gpt-4o budget."""
    text = _long_text(5000)
    chunks = split_text(text, chunk_size=1000, chunk_overlap=200)
    # 1000 chars is well within gpt-4o's 128k context; each chunk should be
    # a few hundred tokens at most.
    for chunk in chunks:
        assert count_tokens(chunk, model="gpt-4o") < 500


def test_default_constants_reasonable():
    assert DEFAULT_CHUNK_SIZE == 1000
    assert DEFAULT_CHUNK_OVERLAP == 200


# ---------------------------------------------------------------------------
# __all__ export sanity
# ---------------------------------------------------------------------------


def test_public_api_exports():
    assert "split_text" in chunking_service.__all__
    assert "count_tokens" in chunking_service.__all__
