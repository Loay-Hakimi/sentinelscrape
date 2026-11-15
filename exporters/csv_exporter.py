"""CSV export."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def export_csv(records: list[dict[str, Any]], path: str) -> int:
    """Write records to a CSV file. Returns the number of rows written.

    The column set is the union of all record keys, so heterogeneous records
    still export cleanly (missing fields are left blank).
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames: list[str] = []
    seen = set()
    for record in records:
        for key in record:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)
    return len(records)
