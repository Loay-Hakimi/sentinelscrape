"""Stealth controls: proxy rotation, User-Agent rotation and jitter delays.

These are standard, polite-by-default request-shaping techniques (the same ones
Scrapy/Apify expose) for handling rate limits on public pages — not a means of
bypassing authentication or access controls.
"""

from __future__ import annotations

import random
import time
from typing import Callable

# A small curated pool of real browser User-Agent strings. Kept in-repo so the
# tool needs no network call (and no third-party UA database) to rotate.
DEFAULT_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
)


class StealthManager:
    """Produces rotated request headers/proxies and human-like delays."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        user_agents: list[str] | None = None,
        *,
        jitter_min_ms: int = 800,
        jitter_max_ms: int = 3500,
        rng: random.Random | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if jitter_min_ms < 0 or jitter_max_ms < jitter_min_ms:
            raise ValueError("require 0 <= jitter_min_ms <= jitter_max_ms")
        self.proxies = list(proxies or [])
        self.user_agents = list(user_agents or DEFAULT_USER_AGENTS)
        self.jitter_min = jitter_min_ms / 1000.0
        self.jitter_max = jitter_max_ms / 1000.0
        self._rng = rng or random.Random()
        self._sleeper = sleeper
        self._proxy_idx = 0
        self._ua_idx = self._rng.randrange(len(self.user_agents))

    def next_proxy(self) -> str | None:
        """Round-robin the proxy pool; None when no proxies are configured."""
        if not self.proxies:
            return None
        proxy = self.proxies[self._proxy_idx % len(self.proxies)]
        self._proxy_idx += 1
        return proxy

    def next_user_agent(self) -> str:
        ua = self.user_agents[self._ua_idx % len(self.user_agents)]
        self._ua_idx += 1
        return ua

    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.next_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }

    def proxies_dict(self) -> dict[str, str] | None:
        """Return a requests-style proxies mapping, or None."""
        proxy = self.next_proxy()
        if proxy is None:
            return None
        return {"http": proxy, "https": proxy}

    def jitter_seconds(self) -> float:
        """A human-like delay drawn from a clamped Gaussian over [min, max]."""
        mean = (self.jitter_min + self.jitter_max) / 2.0
        sigma = (self.jitter_max - self.jitter_min) / 6.0 or 0.0
        value = self._rng.gauss(mean, sigma) if sigma else mean
        return max(self.jitter_min, min(self.jitter_max, value))

    def sleep(self) -> float:
        """Sleep for a jittered delay and return the duration slept."""
        delay = self.jitter_seconds()
        self._sleeper(delay)
        return delay
