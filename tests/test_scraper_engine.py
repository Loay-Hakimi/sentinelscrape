import pytest

from core.scraper_engine import (
    FetchError,
    Pagination,
    RobotsCache,
    RobotsDisallowed,
    ScraperEngine,
    Target,
)
from core.stealth_manager import StealthManager


def no_sleep_stealth():
    # sleeper is a no-op so tests never actually wait.
    return StealthManager(jitter_min_ms=0, jitter_max_ms=0, sleeper=lambda _s: None)


PAGE_1 = """
<html><body>
  <div class="item"><span class="name">Alpha</span></div>
  <div class="item"><span class="name">Beta</span></div>
  <a class="next" href="/page2">next</a>
</body></html>
"""

PAGE_2 = """
<html><body>
  <div class="item"><span class="name">Gamma</span></div>
</body></html>
"""


def test_scrape_follows_pagination():
    pages = {
        "http://site/page1": (200, PAGE_1),
        "http://site/page2": (200, PAGE_2),
    }

    def fetcher(url, **kwargs):
        return pages[url]

    engine = ScraperEngine(no_sleep_stealth(), respect_robots=False, fetcher=fetcher)
    target = Target(
        name="t",
        url="http://site/page1",
        selectors={"name": "span.name"},
        item_selector="div.item",
        pagination=Pagination(type="next_button", selector="a.next", max_pages=5),
    )
    records = engine.scrape(target)
    names = [r["name"] for r in records]
    assert names == ["Alpha", "Beta", "Gamma"]


def test_scrape_respects_max_pages():
    def fetcher(url, **kwargs):
        return 200, PAGE_1  # always has a "next" link

    engine = ScraperEngine(no_sleep_stealth(), respect_robots=False, fetcher=fetcher)
    target = Target(
        name="t",
        url="http://site/page1",
        selectors={"name": "span.name"},
        item_selector="div.item",
        pagination=Pagination(type="next_button", selector="a.next", max_pages=2),
    )
    records = engine.scrape(target)
    assert len(records) == 4  # 2 items/page * 2 pages


def test_retry_then_success():
    calls = {"n": 0}

    def flaky(url, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise FetchError("boom")
        return 200, PAGE_2

    engine = ScraperEngine(
        no_sleep_stealth(),
        respect_robots=False,
        fetcher=flaky,
        max_retries=5,
        backoff_base=0.0,  # no real wait in tests
        backoff_max=0.0,
    )
    html = engine.fetch("http://site/x")
    assert "Gamma" in html
    assert calls["n"] == 3


def test_retry_exhausted_raises():
    def always_500(url, **kwargs):
        return 500, "error"

    engine = ScraperEngine(
        no_sleep_stealth(),
        respect_robots=False,
        fetcher=always_500,
        max_retries=2,
        backoff_base=0.0,
        backoff_max=0.0,
    )
    with pytest.raises(FetchError):
        engine.fetch("http://site/x")


def test_robots_disallow_blocks_fetch():
    robots_txt = "User-agent: *\nDisallow: /private"

    def fetcher(url, **kwargs):
        if url.endswith("/robots.txt"):
            return 200, robots_txt
        return 200, PAGE_2

    engine = ScraperEngine(no_sleep_stealth(), respect_robots=True, fetcher=fetcher)
    with pytest.raises(RobotsDisallowed):
        engine.fetch("http://site/private/data")


def test_robots_allows_permitted_path():
    robots_txt = "User-agent: *\nDisallow: /private"

    def fetcher(url, **kwargs):
        if url.endswith("/robots.txt"):
            return 200, robots_txt
        return 200, PAGE_2

    engine = ScraperEngine(no_sleep_stealth(), respect_robots=True, fetcher=fetcher)
    html = engine.fetch("http://site/public/data")
    assert "Gamma" in html


def test_missing_robots_allows_all():
    def fetcher(url, **kwargs):
        if url.endswith("/robots.txt"):
            return 404, ""
        return 200, PAGE_2

    engine = ScraperEngine(no_sleep_stealth(), respect_robots=True, fetcher=fetcher)
    assert "Gamma" in engine.fetch("http://site/anything")
