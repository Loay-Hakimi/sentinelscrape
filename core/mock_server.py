"""A tiny localhost HTTP server for the bundled mock site.

Lets the demo exercise the *real* HTTP pipeline (requests, robots.txt, retries,
pagination) against bundled static files — without touching any third-party
website. Binds to 127.0.0.1 on an ephemeral port so concurrent runs never clash.
"""

from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MOCKSITE_DIR = Path(__file__).resolve().parent.parent / "mocksite"


class _QuietHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler that doesn't spam stderr with request logs."""

    def log_message(self, *args: object) -> None:  # noqa: D401 - silence logging
        pass


class MockSiteServer:
    """Context manager that serves ``mocksite/`` on 127.0.0.1:<ephemeral>.

    Usage::

        with MockSiteServer() as base_url:
            ...  # base_url is e.g. "http://127.0.0.1:54123"
    """

    def __init__(self, directory: str | Path = MOCKSITE_DIR) -> None:
        self.directory = str(directory)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("server not started")
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> str:
        handler = partial(_QuietHandler, directory=self.directory)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self.base_url

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> str:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()
