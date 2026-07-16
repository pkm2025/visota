"""Unit tests for the PKM PII data masking service (``data_masker``).

Covers each individual mask function plus the convenience ``mask_all``
composition. These tests satisfy the masking contract assertions
VAL-MASK-001 (MST) and VAL-MASK-002 (VND magnitude), and exercise phone and
email masking which are required by the ``pkm-pii-masking`` feature.

These are pure-function tests: no database, no Django settings required
beyond ``django.setup()`` via the ``db`` fixture-less module.
"""

from __future__ import annotations

from apps.pkm.services.data_masker import (
    mask_all,
    mask_email,
    mask_mst,
    mask_phone,
    mask_vnd,
)

# ---------------------------------------------------------------------------
# MST masking  (VAL-MASK-001)
# ---------------------------------------------------------------------------


class TestMaskMst:
    def test_mst_10_digits_masked(self):
        """A 10-digit MST keeps first/last digit, interior masked with *."""
        result = mask_mst("0123456789")
        assert "0123456789" not in result
        assert result.startswith("0")
        assert result.endswith("9")
        # All interior digits should be asterisks (8 of them for a 10-digit MST).
        interior = result[1:-1]
        assert all(ch == "*" for ch in interior)

    def test_mst_14_digits_masked(self):
        """A 14-digit MST is also masked (covers the 10-14 digit range)."""
        result = mask_mst("01234567890123")
        assert "01234567890123" not in result
        assert result.startswith("0")
        assert result.endswith("3")

    def test_mst_with_dashes_preserved(self):
        """MST formatted with dashes still gets its digits masked."""
        result = mask_mst("0123-456-789")
        assert "0123" not in result or "*" in result
        # Shape preserved (dashes remain)
        assert "-" in result

    def test_mst_in_sentence(self):
        """MST embedded in surrounding text is masked, text preserved."""
        text = "Ma so thue 0123456789 cua cong ty."
        result = mask_mst(text)
        assert "0123456789" not in result
        assert "Ma so thue" in result
        assert "cua cong ty" in result

    def test_mst_short_numbers_not_masked(self):
        """Short numbers (under 10 digits) should not be altered."""
        # Year-like and short codes must survive untouched to avoid noise.
        text = "Nam 2026 va ma 12345."
        result = mask_mst(text)
        assert "2026" in result
        assert "12345" in result

    def test_mst_empty_string_returned_unchanged(self):
        assert mask_mst("") == ""

    def test_mst_val_mask_001_contract(self):
        """VAL-MASK-001: '0123456789' becomes a 0...*...9 pattern.

        The contract specifies the first and last digit are preserved and the
        interior is replaced by asterisks (the exact count depends on length).
        """
        result = mask_mst("0123456789")
        # First and last digit preserved, interior fully asterisk-masked.
        assert result.startswith("0")
        assert result.endswith("9")
        interior = result[1:-1]
        assert len(interior) == 8  # 10-digit MST -> 8 interior chars
        assert all(ch == "*" for ch in interior)


# ---------------------------------------------------------------------------
# VND magnitude masking  (VAL-MASK-002)
# ---------------------------------------------------------------------------


class TestMaskVnd:
    def test_vnd_amount_with_commas_masked_to_magnitude(self):
        """'50,000,000 VND' becomes a magnitude like '~50M VND'."""
        result = mask_vnd("50,000,000 VND")
        assert "50,000,000" not in result
        # Must include a magnitude indicator (~50M or similar).
        assert "~50M" in result or "50M" in result

    def test_vnd_amount_with_dots_masked(self):
        """Vietnamese-style '50.000.000 dong' is masked to magnitude."""
        result = mask_vnd("50.000.000 dong")
        assert "50.000.000" not in result
        assert "~50M" in result or "50M" in result

    def test_vnd_amount_in_sentence(self):
        text = "Doanh thu 1,500,000,000 VND nam ngoai."
        result = mask_vnd(text)
        assert "1,500,000,000" not in result
        assert "Doanh thu" in result
        assert "nam ngoai" in result
        # 1.5B magnitude
        assert "~1.5B" in result or "1.5B" in result

    def test_vnd_amount_billions(self):
        result = mask_vnd("2,000,000,000 VND")
        assert "~2B" in result or "2B" in result

    def test_vnd_amount_thousands(self):
        result = mask_vnd("500,000 VND")
        # ~500K
        assert "~500K" in result or "500K" in result

    def test_vnd_empty_string(self):
        assert mask_vnd("") == ""

    def test_vnd_val_mask_002_contract(self):
        """VAL-MASK-002: '50,000,000 VND' contains '~50M' or magnitude."""
        result = mask_vnd("50,000,000 VND")
        assert "~50M" in result


# ---------------------------------------------------------------------------
# Phone masking
# ---------------------------------------------------------------------------


class TestMaskPhone:
    def test_phone_10_digits_masked(self):
        """A 10-digit Vietnamese phone keeps first/last digit, rest masked."""
        result = mask_phone("0901234567")
        assert "0901234567" not in result
        assert result.startswith("0")
        assert result.endswith("7")
        interior = result[1:-1]
        assert all(ch == "*" for ch in interior)

    def test_phone_11_digits_masked(self):
        """An 11-digit phone (landline) is also masked."""
        result = mask_phone("02812345678")
        assert "02812345678" not in result
        assert result.startswith("0")
        assert result.endswith("8")

    def test_phone_in_sentence(self):
        text = "Lien he 0912345678 de biet them."
        result = mask_phone(text)
        assert "0912345678" not in result
        assert "Lien he" in result
        assert "de biet them" in result

    def test_phone_empty_string(self):
        assert mask_phone("") == ""


# ---------------------------------------------------------------------------
# Email masking
# ---------------------------------------------------------------------------


class TestMaskEmail:
    def test_email_user_part_masked(self):
        """Email user part is masked, domain preserved."""
        result = mask_email("user@example.com")
        assert "user" not in result
        assert "example.com" in result
        assert "@" in result
        assert "*" in result

    def test_email_keeps_first_char_of_user(self):
        """First character of the user part is preserved (u***@domain)."""
        result = mask_email("alice@example.com")
        assert result.startswith("a")
        assert "*" in result.split("@")[0]
        assert "example.com" in result

    def test_email_in_sentence(self):
        text = "Email cua toi la john.doe@company.vn ay."
        result = mask_email(text)
        assert "john.doe" not in result
        assert "company.vn" in result
        assert "Email cua toi la" in result

    def test_email_empty_string(self):
        assert mask_email("") == ""


# ---------------------------------------------------------------------------
# mask_all (composition)
# ---------------------------------------------------------------------------


class TestMaskAll:
    def test_mask_all_applies_all_masks(self):
        """mask_all masks MST, VND, phone, and email in one pass."""
        text = (
            "MST 0123456789, doanh thu 50,000,000 VND, lien he 0901234567, email user@example.com."
        )
        result = mask_all(text)
        # None of the sensitive raw values survive.
        assert "0123456789" not in result
        assert "50,000,000" not in result
        assert "0901234567" not in result
        assert "user@example.com" not in result
        # But the magnitude and domain survive.
        assert "50M" in result or "~50M" in result
        assert "example.com" in result

    def test_mask_all_empty_string(self):
        assert mask_all("") == ""

    def test_mask_all_handles_text_without_pii(self):
        """Text with no PII passes through unchanged in shape."""
        text = "Vietnamese accounting regulation TT133."
        result = mask_all(text)
        assert "TT133" in result
        assert "accounting" in result
