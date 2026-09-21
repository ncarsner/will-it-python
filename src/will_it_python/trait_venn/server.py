"""HTTP server and CLI entry point for the trait Venn app (I/O layer).

Routes:
    ``GET /``                 The page.
    ``GET /static/<file>``    Page assets (fixed allow-list).
    ``GET /api/state``        Page state; query keys ``sel``, ``country``,
                              ``toggle`` (see :mod:`validation`).
"""

from __future__ import annotations

import argparse
import json
import logging
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import ClassVar, Final
from urllib.parse import parse_qs, urlsplit

from will_it_python.trait_venn import population
from will_it_python.trait_venn.state import build_state
from will_it_python.trait_venn.validation import RequestError, parse_query

log = logging.getLogger(__name__)

DEFAULT_HOST: Final = "127.0.0.1"
DEFAULT_PORT: Final = 8765
_FETCH_TIMEOUT: Final = 8.0
# Census responses are refreshed at most this often.
_POPULATION_TTL: Final = 600.0
_USER_AGENT: Final = (
    "will-it-python trait-venn (+https://github.com/ncarsner/will-it-python)"
)

_ASSETS: Final[dict[str, str]] = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "text/javascript; charset=utf-8",
    "app.css": "text/css; charset=utf-8",
}


def read_asset(name: str) -> bytes:
    """Return the bytes of a bundled static asset."""
    return (
        resources.files("will_it_python.trait_venn")
        .joinpath("static", name)
        .read_bytes()
    )


def fetch_json(url: str) -> object | None:
    """Return decoded JSON from ``url``, or ``None`` on any network/decode error."""
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Referer": population.POPCLOCK_PAGE}
    )
    try:
        with urllib.request.urlopen(request, timeout=_FETCH_TIMEOUT) as response:
            data: object = json.loads(response.read())
            return data
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        log.warning("population fetch failed for %s: %s", url, exc)
        return None


class PopulationCache:
    """Thread-safe, time-limited cache of the Census population snapshot."""

    def __init__(self, ttl: float = _POPULATION_TTL) -> None:
        """Create an empty cache whose entries expire after ``ttl`` seconds."""
        self._ttl = ttl
        self._lock = threading.Lock()
        self._value: population.Snapshot | None = None
        self._fetched = 0.0

    def get(self, now: float) -> population.Snapshot:
        """Return the cached snapshot, refreshing it when stale."""
        with self._lock:
            if self._value is None or now - self._fetched >= self._ttl:
                world = fetch_json(population.POPCLOCK_URL.format(scope="world"))
                us = fetch_json(population.POPCLOCK_URL.format(scope="us"))
                self._value = population.snapshot(world, us, now)
                self._fetched = now
            return self._value


class Handler(BaseHTTPRequestHandler):
    """Request handler serving the page, its assets, and the state API."""

    cache: ClassVar[PopulationCache] = PopulationCache()

    def do_GET(self) -> None:
        """Route a GET request."""
        url = urlsplit(self.path)
        if url.path == "/":
            self._send(HTTPStatus.OK, _ASSETS["index.html"], read_asset("index.html"))
        elif url.path.startswith("/static/") and (name := url.path[8:]) in _ASSETS:
            self._send(HTTPStatus.OK, _ASSETS[name], read_asset(name))
        elif url.path == "/api/state":
            self._state(url.query)
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _state(self, query: str) -> None:
        try:
            request = parse_query(parse_qs(query))
        except RequestError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        now = time.time()
        self._json(HTTPStatus.OK, build_state(request, self.cache.get(now), now))

    def _json(self, status: HTTPStatus, body: object) -> None:
        self._send(status, "application/json", json.dumps(body).encode())

    def _send(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Route access logs through :mod:`logging` at debug level."""
        log.debug(format, *args)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the trait Venn web app.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).
    """
    parser = argparse.ArgumentParser(
        prog="trait_venn", description="Estimate how rare a combination of traits is."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="interface to bind")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="port to listen on"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="do not open a browser"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{server.server_address[1]}/"
    log.info("trait_venn serving %s (Ctrl-C to stop)", url)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")
    finally:
        server.server_close()
