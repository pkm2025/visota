"""PII data masking service for the PKM module (Karpathy LLM Wiki + security).

Masks sensitive data **before** it is sent to an external LLM provider:

  - ``mask_mst``  -- Vietnamese tax IDs (10-14 digits) -> ``0*******9``
  - ``mask_vnd``  -- VND amounts -> magnitude form like ``~50M``
  - ``mask_phone`` -- Vietnamese phone numbers -> ``0xxx...xxx9``
  - ``mask_email`` -- Email addresses -> ``u***@domain.com``
  - ``mask_all``  -- Apply all masks in one pass

The module provides five public functions covering MST tax IDs, VND amounts,
phone numbers, emails, and a convenience ``mask_all`` that applies all of them
in one pass. ``qa_service.build_prompt`` and ``wiki_ingest_service`` call
``mask_all`` (or accept a ``mask=`` flag) so that no sensitive data ever
leaves the process for an external LLM provider.

Security principle: masking is the default.  Only the user can opt out (via
``UserLLMConfig.disable_masking=True``, e.g. for local Ollama models).
"""

from __future__ import annotations

import re

__all__ = [
    "mask_mst",
    "mask_vnd",
    "mask_phone",
    "mask_email",
    "mask_all",
]


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

#: Vietnamese MST / tax code: 10 to 14 consecutive digits (optionally space/dash
#: separated).  We only mask runs of 10-14 digits to avoid touching short
#: numbers like years or account codes.
_MST_PATTERN = re.compile(r"\b\d[\d\s-]{8,17}\d\b")
_MST_DIGITS_ONLY = re.compile(r"\d")

#: VND amount: a number followed by optional thousands separators and the
#: suffix ``VND`` or ``dong``.  e.g. ``50,000,000 VND``, ``50.000.000 d``.
#: Accepts both ASCII and Vietnamese diacritic variants (``dong``, ``đồng``,
#: ``đ``, ``d``, ``vnd``, ``vnđ``) plus magnitude words ``triệu`` / ``tỷ``.
_VND_PATTERN = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})+|\d{4,})\s*"
    r"(tri[eê]u|t[yỷ]u?|ty|d(?:o?ng)?|đ(?:o?ng)?|vnd|vn[dđ])",
    flags=re.IGNORECASE,
)

#: Vietnamese phone: ``0`` followed by 9-10 digits, optional spaces/dashes.
_PHONE_PATTERN = re.compile(r"\b0\d[\d\s-]{7,12}\d\b")

#: Email address (simple, RFC-5322-lite).
_EMAIL_PATTERN = re.compile(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_middle(text: str) -> str:
    """Replace all interior digits with ``*``, keeping the first and last char.

    Used for MST and phone masking so the shape (length) is preserved but the
    numeric value is unreadable.
    """
    chars = list(text)
    digit_indices = [i for i, c in enumerate(chars) if c.isdigit()]
    if len(digit_indices) <= 2:
        # Not enough digits to mask meaningfully; mask everything except shape.
        for i in digit_indices:
            chars[i] = "*"
        return "".join(chars)
    first, last = digit_indices[0], digit_indices[-1]
    for i in digit_indices[1:-1]:
        chars[i] = "*"
    # Keep non-digit interior chars (spaces/dashes) unchanged for readability.
    _ = (first, last)
    return "".join(chars)


def _magnitude_label(value: float) -> str:
    """Format a VND amount as a magnitude label: ``~50M``, ``~1.2B``, ``~900K``.

    - >= 1_000_000_000 -> ``B`` (billion / ti)
    - >= 1_000_000     -> ``M`` (million / trieu)
    - >= 1_000         -> ``K`` (thousand)
    - otherwise        -> raw integer
    """
    if value >= 1_000_000_000:
        return f"~{value / 1_000_000_000:.1f}B VND".replace(".0B", "B")
    if value >= 1_000_000:
        return f"~{value / 1_000_000:.1f}M VND".replace(".0M", "M")
    if value >= 1_000:
        return f"~{value / 1_000:.0f}K VND"
    return f"~{int(value)} VND"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def mask_mst(text: str) -> str:
    """Mask Vietnamese tax IDs (MST) in ``text``.

    A 10-14 digit MST like ``0123456789`` becomes ``0*******9`` (interior
    digits replaced with ``*``).  Non-digit separators are preserved.
    """
    if not text:
        return text
    return _MST_PATTERN.sub(lambda m: _mask_middle(m.group(0)), text)


def mask_vnd(text: str) -> str:
    """Mask VND amounts in ``text`` with a magnitude label.

    ``50,000,000 VND`` -> ``~50M VND``.  ``1.500.000 dong`` -> ``~1.5M VND``.
    The original magnitude is retained so the LLM still understands scale
    (useful for tax/accounting questions) while the exact value is hidden.
    """
    if not text:
        return text

    def _replace(match: re.Match[str]) -> str:
        raw = match.group(1)
        numeric = raw.replace(",", "").replace(".", "")
        try:
            value = float(numeric)
        except ValueError:
            return match.group(0)
        return _magnitude_label(value)

    return _VND_PATTERN.sub(_replace, text)


def mask_phone(text: str) -> str:
    """Mask Vietnamese phone numbers: ``0901234567`` -> ``0*******7``."""
    if not text:
        return text
    return _PHONE_PATTERN.sub(lambda m: _mask_middle(m.group(0)), text)


def mask_email(text: str) -> str:
    """Mask email addresses: ``user@example.com`` -> ``u***@example.com``."""
    if not text:
        return text

    def _replace(match: re.Match[str]) -> str:
        user_part = match.group(1)
        domain = match.group(2)
        masked_user = "*" if len(user_part) <= 1 else user_part[0] + "*" * (len(user_part) - 1)
        return f"{masked_user}@{domain}"

    return _EMAIL_PATTERN.sub(_replace, text)


def mask_all(text: str) -> str:
    """Apply all available masks (MST, VND, phone, email) to ``text``.

    This is the convenience entry point used by ``qa_service`` and
    ``wiki_ingest_service`` before every LLM call.  Returns the original text
    unchanged if it is falsy.
    """
    if not text:
        return text
    text = mask_mst(text)
    text = mask_vnd(text)
    text = mask_phone(text)
    return mask_email(text)
