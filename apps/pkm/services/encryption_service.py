"""Fernet-based encryption service for PKM API keys.

Derives a Fernet key from Django's SECRET_KEY using PBKDF2HMAC + base64url
encoding, then exposes ``encrypt`` / ``decrypt`` for at-rest encryption of
sensitive values (e.g. user LLM API keys).

Security notes:
  - The derived key is NEVER logged or exposed via any public API.
  - ``derive_key`` is an internal helper (prefixed with ``_``) and must not be
    called from outside this module.
  - ``decrypt`` re-raises ``cryptography.fernet.InvalidToken`` on tampered
    ciphertext so callers can handle integrity failures explicitly.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings

logger = logging.getLogger(__name__)

# A fixed, non-secret salt. PBKDF2 only needs the salt to be distinct per
# application; it does not need to be secret. Using a stable hash of the app
# name keeps the salt deterministic across processes without storing extra
# config. Iteration count follows OWASP 2023 guidance for SHA-256 (>=600k).
_SALT = hashlib.sha256(b"visota.pkm.encryption.v1").digest()
_ITERATIONS = 600_000
_KEY_LENGTH = 32  # Fernet requires a 32-byte (256-bit) key


@lru_cache(maxsize=1)
def _derive_key() -> bytes:
    """Derive a Fernet-compatible key from Django's SECRET_KEY.

    Uses PBKDF2HMAC (SHA-256) with a fixed salt, then base64url-encodes the
    32-byte output as required by Fernet. The result is cached per-process so
    repeated encrypt/decrypt calls do not repeat the (expensive) KDF work.

    The key is treated as a secret: it is never returned to callers, never
    logged, and never serialized. Only ``encrypt``/``decrypt`` consume it.
    """
    secret = settings.SECRET_KEY.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LENGTH,
        salt=_SALT,
        iterations=_ITERATIONS,
    )
    raw_key = kdf.derive(secret)
    # Fernet expects a url-safe base64-encoded 32-byte key.
    return base64.urlsafe_b64encode(raw_key)


def _get_fernet() -> Fernet:
    """Build a Fernet instance from the derived key (internal)."""
    return Fernet(_derive_key())


def encrypt(plaintext: str) -> str:
    """Encrypt ``plaintext`` and return the Fernet token as a string.

    The returned string is the standard Fernet token (url-safe base64),
    suitable for storing in a TextField. The same plaintext encrypted twice
    yields different ciphertexts because Fernet embeds a fresh IV + timestamp.
    """
    if not isinstance(plaintext, str):
        raise TypeError("plaintext must be str")
    token = _get_fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token produced by :func:`encrypt`.

    Raises ``cryptography.fernet.InvalidToken`` if ``ciphertext`` is malformed,
    expired, or tampered with. Callers should catch ``InvalidToken`` and treat
    it as an integrity failure (never swallow silently).
    """
    if not isinstance(ciphertext, str):
        raise TypeError("ciphertext must be str")
    # Let InvalidToken propagate to the caller; do not log the ciphertext.
    plaintext_bytes = _get_fernet().decrypt(ciphertext.encode("ascii"))
    return plaintext_bytes.decode("utf-8")


__all__ = ["encrypt", "decrypt", "InvalidToken"]
