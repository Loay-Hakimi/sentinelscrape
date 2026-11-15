"""Encryption key storage, creation and rotation.

Keys are never hardcoded. A key is loaded from (in priority order):

1. the ``SENTINEL_KEY`` environment variable (useful for CI/CD), or
2. a key file on disk (default ``.secrets/key.key``, which must be gitignored),
   generated automatically on first run.
"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet


class KeyVault:
    """Loads or creates the Fernet key used to encrypt stored records."""

    def __init__(self, key_path: str = ".secrets/key.key", env_var: str = "SENTINEL_KEY") -> None:
        self.key_path = Path(key_path)
        self.env_var = env_var

    def load_or_create(self) -> bytes:
        """Return the active key, generating and persisting one if needed."""
        env = os.environ.get(self.env_var)
        if env:
            return env.encode("utf-8") if isinstance(env, str) else env

        if self.key_path.exists():
            return self.key_path.read_bytes()

        return self._generate_and_store()

    def _generate_and_store(self) -> bytes:
        key = Fernet.generate_key()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_bytes(key)
        # Best-effort permission tightening (POSIX; a no-op guard on Windows).
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass
        return key

    def rotate(self) -> bytes:
        """Generate a new key, overwriting the stored one, and return it.

        Note: existing ciphertext encrypted under the previous key must be
        re-encrypted separately (see ``security.decryptor``); rotating the key
        alone does not migrate stored data.
        """
        return self._generate_and_store()
