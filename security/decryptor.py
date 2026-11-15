"""Authorized data retrieval and key-rotation re-encryption helpers.

These utilities operate on an encryptor plus raw ciphertext tokens, so they do
not depend on the storage layer and can be reused for exports, audits, or
migrating data from an old key to a new one.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator


def decrypt_tokens(encryptor: Any, tokens: Iterable[bytes]) -> Iterator[dict[str, Any]]:
    """Decrypt an iterable of ciphertext tokens into record dicts."""
    for token in tokens:
        yield encryptor.decrypt_record(token)


def reencrypt(old_encryptor: Any, new_encryptor: Any, token: bytes) -> bytes:
    """Re-encrypt one token from the old key to the new key (for rotation)."""
    record = old_encryptor.decrypt_record(token)
    return new_encryptor.encrypt_record(record)
