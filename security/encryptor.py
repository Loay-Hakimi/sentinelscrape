"""Record encryption.

The default engine is Fernet (AES-128-CBC + HMAC-SHA256, authenticated). An
optional AES-256-GCM engine is provided for callers that require a 256-bit
cipher. Both authenticate ciphertext, so tampering is detected on decrypt.
"""

from __future__ import annotations

import json
import os
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class Encryptor:
    """Fernet-based encryptor (AES-128-CBC + HMAC-SHA256)."""

    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    @staticmethod
    def generate_key() -> bytes:
        return Fernet.generate_key()

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, token: bytes) -> str:
        return self._fernet.decrypt(token).decode("utf-8")

    def encrypt_record(self, record: dict[str, Any]) -> bytes:
        """Encrypt a record dict as canonical JSON."""
        return self.encrypt(json.dumps(record, sort_keys=True, ensure_ascii=False))

    def decrypt_record(self, token: bytes) -> dict[str, Any]:
        return json.loads(self.decrypt(token))


class AESGCMEncryptor:
    """Optional AES-256-GCM engine. Ciphertext is ``nonce(12) || ciphertext``."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("AES-256-GCM requires a 32-byte key")
        self._key = key

    @staticmethod
    def generate_key() -> bytes:
        return AESGCM.generate_key(bit_length=256)

    def encrypt(self, plaintext: str) -> bytes:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext.encode("utf-8"), None)
        return nonce + ciphertext

    def decrypt(self, token: bytes) -> str:
        nonce, ciphertext = token[:12], token[12:]
        return AESGCM(self._key).decrypt(nonce, ciphertext, None).decode("utf-8")

    def encrypt_record(self, record: dict[str, Any]) -> bytes:
        return self.encrypt(json.dumps(record, sort_keys=True, ensure_ascii=False))

    def decrypt_record(self, token: bytes) -> dict[str, Any]:
        return json.loads(self.decrypt(token))
