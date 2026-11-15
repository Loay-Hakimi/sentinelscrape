import csv
import json

from core.scraper_engine import Pagination, ScraperEngine, Target
from core.stealth_manager import StealthManager
from exporters.csv_exporter import export_csv
from exporters.json_exporter import export_json
from security.encryptor import Encryptor
from storage.db_manager import DBManager


def test_export_csv(tmp_path):
    records = [{"a": 1, "b": 2}, {"a": 3, "c": 4}]
    path = tmp_path / "out.csv"
    n = export_csv(records, str(path))
    assert n == 2
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["a"] == "1"
    assert set(rows[0].keys()) == {"a", "b", "c"}  # union of keys


def test_export_json(tmp_path):
    records = [{"a": 1}, {"a": 2}]
    path = tmp_path / "out.json"
    export_json(records, str(path))
    assert json.loads(path.read_text(encoding="utf-8")) == records


PAGE = """
<html><body>
  <div class="item"><span class="name">Alpha</span><span class="price">1</span></div>
  <div class="item"><span class="name">Beta</span><span class="price">2</span></div>
</body></html>
"""


def test_end_to_end_scrape_store_export(tmp_path):
    # Scrape (offline) -> encrypt+store -> export decrypted, all without network.
    def fetcher(url, **kwargs):
        return 200, PAGE

    stealth = StealthManager(jitter_min_ms=0, jitter_max_ms=0, sleeper=lambda _s: None)
    engine = ScraperEngine(stealth, respect_robots=False, fetcher=fetcher)
    target = Target(
        name="t",
        url="http://site/p1",
        selectors={"name": "span.name", "price": "span.price"},
        item_selector="div.item",
        pagination=Pagination(max_pages=1),
    )
    records = engine.scrape(target)
    assert len(records) == 2

    db_path = str(tmp_path / "pipe.db")
    enc = Encryptor(Encryptor.generate_key())
    with DBManager(db_path, enc) as db:
        inserted, duplicates = db.insert_many("sess", target.url, records)
        assert (inserted, duplicates) == (2, 0)
        out = db.fetch_decrypted("sess")

    names = sorted(r["name"] for r in out)
    assert names == ["Alpha", "Beta"]

    csv_path = tmp_path / "pipe.csv"
    assert export_csv(out, str(csv_path)) == 2
    assert csv_path.exists()
