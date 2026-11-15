"""JSON export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_json(records: list[dict[str, Any]], path: str) -> int:
    """Write records to a JSON array file. Returns the number of records."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
    return len(records)
