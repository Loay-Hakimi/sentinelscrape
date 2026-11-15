"""HTML parsing with CSS selectors.

Selector values may target an attribute with an ``@attr`` suffix, e.g.
``"a.product-link@href"`` extracts the href rather than the text. When an
``item_selector`` is given, each matching element is treated as one record and
fields are extracted within it. Without an item selector, each field's matches
are zipped positionally into records.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup


def _extract(node: Any, selector: str) -> str | None:
    sel, _, attr = selector.partition("@")
    el = node.select_one(sel.strip())
    if el is None:
        return None
    if attr:
        value = el.get(attr.strip())
        return value if value is not None else None
    return el.get_text(strip=True)


class Parser:
    """Extracts structured records from HTML using CSS selectors."""

    def __init__(self, selectors: dict[str, str], item_selector: str | None = None) -> None:
        if not selectors:
            raise ValueError("at least one field selector is required")
        self.selectors = dict(selectors)
        self.item_selector = item_selector

    def parse(self, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        if self.item_selector:
            return self._parse_items(soup)
        return self._parse_zipped(soup)

    def _parse_items(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        records = []
        for item in soup.select(self.item_selector):
            record = {field: _extract(item, sel) for field, sel in self.selectors.items()}
            if any(v is not None for v in record.values()):
                records.append(record)
        return records

    def _parse_zipped(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        columns: dict[str, list[str | None]] = {}
        for field, selector in self.selectors.items():
            sel, _, attr = selector.partition("@")
            elements = soup.select(sel.strip())
            if attr:
                columns[field] = [el.get(attr.strip()) for el in elements]
            else:
                columns[field] = [el.get_text(strip=True) for el in elements]
        length = max((len(v) for v in columns.values()), default=0)
        records = []
        for i in range(length):
            record = {
                field: (values[i] if i < len(values) else None)
                for field, values in columns.items()
            }
            records.append(record)
        return records
