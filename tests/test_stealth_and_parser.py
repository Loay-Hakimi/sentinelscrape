import random

from core.parser import Parser
from core.stealth_manager import StealthManager


def test_proxy_round_robin():
    sm = StealthManager(proxies=["p1", "p2", "p3"])
    got = [sm.next_proxy() for _ in range(6)]
    assert got == ["p1", "p2", "p3", "p1", "p2", "p3"]


def test_no_proxy_returns_none():
    sm = StealthManager(proxies=[])
    assert sm.next_proxy() is None
    assert sm.proxies_dict() is None


def test_user_agent_rotation_cycles():
    uas = ["ua1", "ua2"]
    sm = StealthManager(user_agents=uas, rng=random.Random(0))
    seen = {sm.next_user_agent() for _ in range(4)}
    assert seen == {"ua1", "ua2"}


def test_headers_include_user_agent():
    sm = StealthManager(user_agents=["ua-test"])
    headers = sm.headers()
    assert headers["User-Agent"] == "ua-test"
    assert "Accept-Language" in headers


def test_jitter_within_bounds():
    sm = StealthManager(jitter_min_ms=800, jitter_max_ms=3500, rng=random.Random(1))
    for _ in range(1000):
        d = sm.jitter_seconds()
        assert 0.8 <= d <= 3.5


def test_sleep_uses_injected_sleeper():
    slept = []
    sm = StealthManager(jitter_min_ms=10, jitter_max_ms=20, sleeper=slept.append)
    duration = sm.sleep()
    assert slept and abs(slept[0] - duration) < 1e-9


HTML = """
<html><body>
  <article class="product_pod">
     <h3><a title="Book One" href="/one">One</a></h3>
     <p class="price_color">£10.00</p>
  </article>
  <article class="product_pod">
     <h3><a title="Book Two" href="/two">Two</a></h3>
     <p class="price_color">£12.00</p>
  </article>
</body></html>
"""


def test_parser_item_mode_extracts_fields_and_attrs():
    parser = Parser(
        {"title": "h3 a@title", "price": "p.price_color", "url": "h3 a@href"},
        item_selector="article.product_pod",
    )
    records = parser.parse(HTML)
    assert records == [
        {"title": "Book One", "price": "£10.00", "url": "/one"},
        {"title": "Book Two", "price": "£12.00", "url": "/two"},
    ]


def test_parser_zip_mode():
    parser = Parser({"title": "h3 a@title", "price": "p.price_color"})
    records = parser.parse(HTML)
    assert len(records) == 2
    assert records[0]["title"] == "Book One"
    assert records[1]["price"] == "£12.00"


def test_parser_missing_field_is_none():
    parser = Parser({"title": "h3 a@title", "missing": "span.nope"}, item_selector="article.product_pod")
    records = parser.parse(HTML)
    assert records[0]["missing"] is None
