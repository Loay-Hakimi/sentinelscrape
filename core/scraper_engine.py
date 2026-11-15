"""Request orchestration: robots.txt compliance, retries, pagination.

The HTTP transport is injectable (the ``fetcher`` argument) so the engine can be
driven entirely offline in tests. The default transport uses a persistent
``requests.Session``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.parser import Parser
from core.stealth_manager import StealthManager

# (status_code | None, body_text). Raising is also allowed for transport errors.
Fetcher = Callable[..., tuple[int | None, str]]


class FetchError(Exception):
    """Raised for a non-success HTTP response; triggers a retry."""


class RobotsDisallowed(Exception):
    """Raised when robots.txt forbids fetching a URL and respect is enabled."""


@dataclass
class Pagination:
    type: str = "none"  # "none" | "next_button"
    selector: str | None = None
    max_pages: int = 1


@dataclass
class Target:
    name: str
    url: str
    selectors: dict[str, str]
    item_selector: str | None = None
    pagination: Pagination = field(default_factory=Pagination)


class RobotsCache:
    """Per-host robots.txt cache. Missing/unreachable robots.txt allows all."""

    def __init__(self, fetch_text: Callable[[str], str | None]) -> None:
        self._fetch_text = fetch_text
        self._parsers: dict[str, RobotFileParser] = {}

    def allowed(self, url: str, user_agent: str) -> bool:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        rp = self._parsers.get(base)
        if rp is None:
            rp = RobotFileParser()
            try:
                text = self._fetch_text(base + "/robots.txt")
            except Exception:
                text = None
            rp.parse(text.splitlines() if text else [])
            self._parsers[base] = rp
        return rp.can_fetch(user_agent, url)


class ScraperEngine:
    """Fetches and parses targets with stealth, retries and robots compliance."""

    def __init__(
        self,
        stealth: StealthManager,
        *,
        respect_robots: bool = True,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        backoff_max: float = 8.0,
        timeout: float = 15.0,
        session: Any = None,
        fetcher: Fetcher | None = None,
        robots_cache: RobotsCache | None = None,
    ) -> None:
        self.stealth = stealth
        self.respect_robots = respect_robots
        self.max_retries = max(1, max_retries)
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.timeout = timeout
        self._session = session
        self.fetcher = fetcher or self._requests_fetcher
        self.robots = robots_cache or RobotsCache(self._fetch_text_for_robots)

    # -- transport -----------------------------------------------------------

    @property
    def session(self) -> Any:
        if self._session is None:
            import requests

            self._session = requests.Session()
        return self._session

    def _requests_fetcher(self, url: str, **kwargs: Any) -> tuple[int | None, str]:
        resp = self.session.get(
            url,
            headers=kwargs.get("headers"),
            proxies=kwargs.get("proxies"),
            timeout=kwargs.get("timeout", self.timeout),
            allow_redirects=True,
        )
        return resp.status_code, resp.text

    def _fetch_text_for_robots(self, url: str) -> str | None:
        try:
            status, text = self.fetcher(url, headers=self.stealth.headers(), proxies=None, timeout=self.timeout)
        except Exception:
            return None
        if status is None or status >= 400:
            return None
        return text

    # -- fetching ------------------------------------------------------------

    def _fetch_once(self, url: str) -> str:
        headers = self.stealth.headers()
        proxies = self.stealth.proxies_dict()
        status, text = self.fetcher(url, headers=headers, proxies=proxies, timeout=self.timeout)
        if status is None or status >= 400:
            raise FetchError(f"HTTP {status} for {url}")
        return text

    def fetch(self, url: str) -> str:
        """Fetch a URL with robots compliance, jitter and retry/backoff."""
        if self.respect_robots and not self.robots.allowed(url, self.stealth.user_agents[0]):
            raise RobotsDisallowed(url)

        self.stealth.sleep()  # human-like delay (no-op sleeper in tests)

        retryer = Retrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=self.backoff_base, max=self.backoff_max),
            retry=retry_if_exception_type((FetchError, ConnectionError, TimeoutError)),
            reraise=True,
        )
        return retryer(self._fetch_once, url)

    # -- scraping ------------------------------------------------------------

    def scrape(self, target: Target) -> list[dict[str, Any]]:
        """Scrape a target across its configured pages."""
        parser = Parser(target.selectors, target.item_selector)
        results: list[dict[str, Any]] = []
        url = target.url
        pages = max(1, target.pagination.max_pages)

        for _ in range(pages):
            html = self.fetch(url)
            results.extend(parser.parse(html))
            next_url = self._next_url(html, url, target.pagination)
            if not next_url:
                break
            url = next_url
        return results

    @staticmethod
    def _next_url(html: str, current_url: str, pagination: Pagination) -> str | None:
        if pagination.type != "next_button" or not pagination.selector:
            return None
        soup = BeautifulSoup(html, "html.parser")
        el = soup.select_one(pagination.selector)
        if el is None:
            return None
        href = el.get("href")
        if not href:
            return None
        return urljoin(current_url, href)
