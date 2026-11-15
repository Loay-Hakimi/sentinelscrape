"""SQLite persistence for encrypted, deduplicated records."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from storage.deduplicator import record_hash

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class DBManager:
    """Stores encrypted records in SQLite, deduplicating on content hash.

    The manager holds an encryptor so callers work with plain dicts; payloads
    are encrypted on insert and decrypted on read. The ``data_hash`` is computed
    from the *plaintext* record so duplicate detection does not depend on
    (randomized) ciphertext.
    """

    def __init__(self, path: str, encryptor: Any) -> None:
        self.path = path
        self.encryptor = encryptor
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        self._conn.commit()

    def insert(self, session_id: str, source_url: str, record: dict[str, Any]) -> bool:
        """Insert one record. Returns True if stored, False if a duplicate."""
        digest = record_hash(record)
        payload = self.encryptor.encrypt_record(record)
        scraped_at = datetime.now(timezone.utc).isoformat()
        try:
            self._conn.execute(
                "INSERT INTO records (session_id, source_url, data_hash, payload, scraped_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, source_url, digest, payload, scraped_at),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            # UNIQUE(data_hash) violated -> duplicate content.
            return False

    def insert_many(
        self, session_id: str, source_url: str, records: list[dict[str, Any]]
    ) -> tuple[int, int]:
        """Insert many records. Returns (inserted, duplicates)."""
        inserted = 0
        duplicates = 0
        for record in records:
            if self.insert(session_id, source_url, record):
                inserted += 1
            else:
                duplicates += 1
        return inserted, duplicates

    def count(self, session_id: str | None = None) -> int:
        if session_id is None:
            cur = self._conn.execute("SELECT COUNT(*) FROM records")
        else:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM records WHERE session_id = ?", (session_id,)
            )
        return int(cur.fetchone()[0])

    def iter_decrypted(self, session_id: str | None = None) -> Iterator[dict[str, Any]]:
        """Yield decrypted records, optionally filtered by session."""
        if session_id is None:
            cur = self._conn.execute(
                "SELECT source_url, payload, scraped_at FROM records ORDER BY id"
            )
        else:
            cur = self._conn.execute(
                "SELECT source_url, payload, scraped_at FROM records "
                "WHERE session_id = ? ORDER BY id",
                (session_id,),
            )
        for row in cur:
            record = self.encryptor.decrypt_record(row["payload"])
            record.setdefault("_source_url", row["source_url"])
            record.setdefault("_scraped_at", row["scraped_at"])
            yield record

    def fetch_decrypted(self, session_id: str | None = None) -> list[dict[str, Any]]:
        return list(self.iter_decrypted(session_id))

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "DBManager":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
