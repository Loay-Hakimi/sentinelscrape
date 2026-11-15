"""Hash-based deduplication.

A record's identity is the SHA-256 of its canonical JSON serialization. Two
records with the same field values produce the same hash regardless of key
ordering, so exact duplicates are detected deterministically. The database's
UNIQUE constraint on ``data_hash`` enforces this at insert time.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(record: dict[str, Any]) -> str:
    """Return a stable, key-sorted JSON string for a record."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def record_hash(record: dict[str, Any]) -> str:
    """Return the SHA-256 hex digest uniquely identifying a record's content."""
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()
