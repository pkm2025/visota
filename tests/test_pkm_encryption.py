"""Unit tests for apps.pkm.services.encryption_service.

Covers round-trip encrypt/decrypt, ciphertext variability, tamper detection,
key determinism from SECRET_KEY, and a guard that the key is never logged.
These tests do NOT require database access (encryption is pure logic), but we
use ``@pytest.mark.django_db`` lightly because settings access is needed.
"""

from __future__ import annotations

import logging

import pytest
from cryptography.fernet import InvalidToken

from apps.pkm.services import encryption_service

# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_encrypt_decrypt_roundtrip_ascii():
    """encrypt then decrypt returns the original plaintext (ASCII)."""
    plaintext = "sk-test-api-key-12345"
    token = encryption_service.encrypt(plaintext)
    assert isinstance(token, str)
    assert encryption_service.decrypt(token) == plaintext


@pytest.mark.django_db
def test_encrypt_decrypt_roundtrip_unicode():
    """Round-trip preserves UTF-8 / emoji content."""
    plaintext = "khoá-mật-🔑-測試"
    token = encryption_service.encrypt(plaintext)
    assert encryption_service.decrypt(token) == plaintext


@pytest.mark.django_db
def test_encrypt_decrypt_roundtrip_empty_string():
    """Empty string round-trips correctly."""
    token = encryption_service.encrypt("")
    assert encryption_service.decrypt(token) == ""


@pytest.mark.django_db
def test_encrypt_decrypt_roundtrip_long_value():
    """A long secret (e.g. a PEM block) round-trips correctly."""
    plaintext = "x" * 10_000
    token = encryption_service.encrypt(plaintext)
    assert encryption_service.decrypt(token) == plaintext


# ---------------------------------------------------------------------------
# Ciphertext variability
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_different_plaintexts_produce_different_ciphertexts():
    """Two distinct plaintexts must not share ciphertext."""
    a = encryption_service.encrypt("alpha")
    b = encryption_service.encrypt("beta")
    assert a != b


@pytest.mark.django_db
def test_same_plaintext_produces_different_ciphertexts():
    """Fernet embeds a fresh IV, so encrypting the same value twice yields
    different tokens (both still decrypt to the same plaintext)."""
    plain = "repeat-me"
    token_a = encryption_service.encrypt(plain)
    token_b = encryption_service.encrypt(plain)
    assert token_a != token_b
    assert encryption_service.decrypt(token_a) == plain
    assert encryption_service.decrypt(token_b) == plain


@pytest.mark.django_db
def test_ciphertext_is_not_plaintext():
    """The ciphertext must not contain the plaintext verbatim."""
    plain = "super-secret-value-xyz"
    token = encryption_service.encrypt(plain)
    assert plain not in token


# ---------------------------------------------------------------------------
# Tamper detection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_decrypt_raises_on_tampered_ciphertext():
    """A modified ciphertext must raise InvalidToken."""
    token = encryption_service.encrypt("secret")
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(InvalidToken):
        encryption_service.decrypt(tampered)


@pytest.mark.django_db
def test_decrypt_raises_on_garbage_input():
    """A non-Fernet string raises InvalidToken."""
    with pytest.raises(InvalidToken):
        encryption_service.decrypt("not-a-real-token")


@pytest.mark.django_db
def test_decrypt_raises_on_empty_input():
    """Empty ciphertext raises InvalidToken (not an empty plaintext)."""
    with pytest.raises(InvalidToken):
        encryption_service.decrypt("")


@pytest.mark.django_db
def test_decrypt_does_not_silently_swallow_invalid_token():
    """InvalidToken must propagate (not be swallowed as a different error)."""
    token = encryption_service.encrypt("ok")
    # Flip one character to break the token.
    flipped = ("B" if token[0] != "B" else "C") + token[1:]
    with pytest.raises(InvalidToken):
        encryption_service.decrypt(flipped)


# ---------------------------------------------------------------------------
# Key derivation determinism
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_derived_key_is_deterministic():
    """The derived key is the same across calls within one SECRET_KEY."""
    encryption_service._derive_key.cache_clear()
    k1 = encryption_service._derive_key()
    k2 = encryption_service._derive_key()
    assert k1 == k2
    # Key must be 44 chars: base64url of 32 bytes.
    assert len(k1) == 44


@pytest.mark.django_db
def test_derived_key_changes_with_secret_key():
    """Different SECRET_KEY values produce different derived keys."""
    from django.test import override_settings

    encryption_service._derive_key.cache_clear()
    key_a = encryption_service._derive_key()

    with override_settings(SECRET_KEY="a-different-secret-for-visota-xyz"):
        encryption_service._derive_key.cache_clear()
        key_b = encryption_service._derive_key()

    encryption_service._derive_key.cache_clear()
    assert key_a != key_b


@pytest.mark.django_db
def test_encrypt_decrypt_survives_secret_key_roundtrip():
    """A token encrypted with one SECRET_KEY cannot be decrypted with another."""
    from django.test import override_settings

    encryption_service._derive_key.cache_clear()
    token = encryption_service.encrypt("owned-by-key-a")

    with override_settings(SECRET_KEY="completely-different-key-b-12345"):
        encryption_service._derive_key.cache_clear()
        with pytest.raises(InvalidToken):
            encryption_service.decrypt(token)

    encryption_service._derive_key.cache_clear()


# ---------------------------------------------------------------------------
# Type safety
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_encrypt_rejects_non_str():
    with pytest.raises(TypeError):
        encryption_service.encrypt(b"bytes-not-allowed")  # type: ignore[arg-type]


@pytest.mark.django_db
def test_decrypt_rejects_non_str():
    with pytest.raises(TypeError):
        encryption_service.decrypt(b"bytes-not-allowed")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Key is never logged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_derived_key_is_never_logged(caplog):
    """The derived key must never appear in any log record."""
    encryption_service._derive_key.cache_clear()
    derived = encryption_service._derive_key()
    # Force a log emission from the encryption module's logger so that even
    # incidental debug logs are captured.
    with caplog.at_level(logging.DEBUG, logger="apps.pkm.services.encryption_service"):
        logging.getLogger("apps.pkm.services.encryption_service").debug("encrypt called")
        encryption_service.encrypt("some-value")
        encryption_service.decrypt(encryption_service.encrypt("some-value"))

    for record in caplog.records:
        assert derived.decode("ascii", errors="replace") not in record.getMessage()
        assert derived not in record.getMessage().encode("utf-8", errors="replace")


@pytest.mark.django_db
def test_plaintext_is_never_logged(caplog):
    """Plaintext input must never leak into logs from the encryption service."""
    sensitive = "do-not-log-this-plaintext"
    with caplog.at_level(logging.DEBUG, logger="apps.pkm.services.encryption_service"):
        token = encryption_service.encrypt(sensitive)
        encryption_service.decrypt(token)

    for record in caplog.records:
        assert sensitive not in record.getMessage()


@pytest.mark.django_db
def test_no_logger_emit_in_encrypt_decrypt(caplog):
    """The encryption service itself must not log anything during normal use.

    This guards against accidental ``logger.info(...)`` calls that might leak
    plaintext or keys in the future.
    """
    with caplog.at_level(logging.DEBUG, logger="apps.pkm.services.encryption_service"):
        token = encryption_service.encrypt("quiet")
        encryption_service.decrypt(token)
    assert caplog.records == []


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


def test_invalid_token_is_re_exported():
    """InvalidToken must be importable from the encryption_service module so
    callers can catch it without importing from cryptography directly."""
    assert encryption_service.InvalidToken is InvalidToken


def test_private_derive_key_is_not_in_all():
    """``_derive_key`` is an internal helper and must not be re-exported."""
    assert "_derive_key" not in encryption_service.__all__
    assert "derive_key" not in encryption_service.__all__


# ---------------------------------------------------------------------------
# Cross-check: matches a manually constructed Fernet with the same key
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_decrypt_works_with_manually_constructed_fernet():
    """A token built directly with Fernet + our derived key decrypts fine,
    confirming our key derivation is standard-compliant."""
    from cryptography.fernet import Fernet

    encryption_service._derive_key.cache_clear()
    key = encryption_service._derive_key()
    f = Fernet(key)
    token = f.encrypt("interop-test".encode("utf-8")).decode("ascii")
    assert encryption_service.decrypt(token) == "interop-test"


@pytest.mark.django_db
def test_encrypt_token_decryptable_by_manual_fernet():
    """Reverse interop: a token from our ``encrypt`` is readable by a Fernet
    constructed with the same derived key."""
    from cryptography.fernet import Fernet

    encryption_service._derive_key.cache_clear()
    token = encryption_service.encrypt("reverse-interop")
    f = Fernet(encryption_service._derive_key())
    assert f.decrypt(token.encode("ascii")).decode("utf-8") == "reverse-interop"
