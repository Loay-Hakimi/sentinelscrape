"""End-to-end offline demo: scrape a bundled mock site, encrypt, store, report.

Runs the *real* pipeline (HTTP via requests, robots.txt compliance, retries,
pagination, Fernet encryption, SQLite dedup, CSV/JSON export, HTML report)
against a localhost mock server serving ``mocksite/`` — no third-party site is
contacted. Used by ``python main.py demo`` and by the test-suite.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from core.mock_server import MockSiteServer
from core.scraper_engine import Pagination, ScraperEngine, Target
from core.stealth_manager import StealthManager
from exporters.csv_exporter import export_csv
from exporters.json_exporter import export_json
from reports.html_report import write_report
from security.encryptor import Encryptor
from storage.db_manager import DBManager

# Selectors matching mocksite/*.html.
MOCK_SELECTORS = {
    "title": "h3 a@title",
    "url": "h3 a@href",
    "price": "p.price_color",
    "availability": "p.availability",
    "category": "p.category",
    "rating": "p.star-rating@data-rating",
}


def run_demo(
    out_dir: str | Path = "demo_output",
    *,
    pages: int = 3,
    encryptor: Any = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Run the offline demo pipeline; returns a summary dict with output paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    encryptor = encryptor or Encryptor(Encryptor.generate_key())  # ephemeral, never written
    db_path = db_path or str(out / "demo.db")

    with MockSiteServer() as base_url:
        target = Target(
            name="mockbooks",
            url=f"{base_url}/index.html",
            selectors=MOCK_SELECTORS,
            item_selector="article.product_pod",
            pagination=Pagination(type="next_button", selector="li.next a", max_pages=pages),
        )
        # Robots respect ON (the mock robots.txt is fetched over HTTP); jitter off
        # so the demo is fast and deterministic.
        stealth = StealthManager(proxies=[], jitter_min_ms=0, jitter_max_ms=0)
        engine = ScraperEngine(stealth, respect_robots=True, max_retries=2)
        records = engine.scrape(target)

    session_id = uuid.uuid4().hex[:12]
    with DBManager(db_path, encryptor) as db:
        inserted, duplicates = db.insert_many(session_id, "mocksite", records)
        decrypted = db.fetch_decrypted()

    csv_path = out / "records.csv"
    json_path = out / "records.json"
    html_path = out / "report.html"
    export_csv(decrypted, str(csv_path))
    export_json(decrypted, str(json_path))
    write_report(decrypted, str(html_path), title="SentinelScrape — MockBooks Demo")

    return {
        "scraped": len(records),
        "inserted": inserted,
        "duplicates": duplicates,
        "db_path": db_path,
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "html_path": str(html_path),
    }
