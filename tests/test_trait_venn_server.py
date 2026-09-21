"""Tests for the trait_venn HTTP server and CLI."""

import errno
import json
import runpy
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import MagicMock, patch

import pytest

from will_it_python.trait_venn import server


@pytest.fixture
def base_url():
    """Run the app on an ephemeral port with Census access disabled."""
    with patch.object(server, "fetch_json", return_value=None):
        server.Handler.cache = server.PopulationCache()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
        httpd.shutdown()
        httpd.server_close()


def get(url):
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, response.headers["Content-Type"], response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers["Content-Type"], exc.read()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def test_index_page(base_url):
    status, ctype, body = get(base_url + "/")
    assert status == 200
    assert ctype.startswith("text/html")
    assert b"Traits assumed independent except where they depend on gender" in body
    assert b"<title>Someone who is female" in body


@pytest.mark.parametrize(
    ("name", "ctype"), [("app.js", "text/javascript"), ("app.css", "text/css")]
)
def test_static_assets(base_url, name, ctype):
    status, content_type, _ = get(f"{base_url}/static/{name}")
    assert status == 200
    assert content_type.startswith(ctype)


@pytest.mark.parametrize(
    "path", ["/static/../server.py", "/static/secret.txt", "/nope"]
)
def test_unknown_paths_404(base_url, path):
    status, _, body = get(base_url + path)
    assert status == 404
    assert json.loads(body) == {"error": "not found"}


def test_api_state(base_url):
    status, ctype, body = get(
        base_url + "/api/state?sel=female,left&country=US&toggle=green"
    )
    data = json.loads(body)
    assert (status, ctype) == (200, "application/json")
    assert data["selection"] == ["female", "left", "green"]
    assert data["population"]["source"].startswith("approximate projection")


def test_api_state_rejects_bad_input(base_url):
    status, _, body = get(base_url + "/api/state?sel=male,female")
    assert status == 400
    assert "exclusive group" in json.loads(body)["error"]


def test_access_log_goes_to_debug_logger(base_url, caplog):
    with caplog.at_level("DEBUG", logger=server.log.name):
        get(base_url + "/")
    assert any("GET / " in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# Population fetching and caching
# ---------------------------------------------------------------------------


def test_fetch_json_success():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"us": 341000000}'
    with patch.object(
        server.urllib.request, "urlopen", return_value=response
    ) as urlopen:
        assert server.fetch_json("https://example.test/x") == {"us": 341000000}
    request = urlopen.call_args.args[0]
    assert request.get_header("User-agent").startswith("will-it-python")


@pytest.mark.parametrize(
    "error", [urllib.error.URLError("blocked"), TimeoutError(), ValueError("bad json")]
)
def test_fetch_json_failure_returns_none(error, caplog):
    with patch.object(server.urllib.request, "urlopen", side_effect=error):
        assert server.fetch_json("https://example.test/x") is None
    assert "population fetch failed" in caplog.text


def test_population_cache_refreshes_only_when_stale():
    cache = server.PopulationCache(ttl=100)
    response = {
        "us": {"population": 400_000_000},
        "world": {"population": 8_000_000_000},
    }
    with patch.object(server, "fetch_json", return_value=response) as fetch:
        first = cache.get(1000.0)
        assert cache.get(1050.0) is first
        assert fetch.call_count == 2
        cache.get(1100.0)
        assert fetch.call_count == 4
    assert first.live_us
    assert first.live_world


def test_read_asset():
    assert server.read_asset("app.js").startswith(b"// Trait Venn")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _fake_server():
    fake = MagicMock()
    fake.server_address = ("127.0.0.1", 9999)
    fake.serve_forever.side_effect = KeyboardInterrupt
    return fake


def test_main_opens_browser_and_shuts_down_cleanly():
    fake = _fake_server()
    with (
        patch.object(server, "ThreadingHTTPServer", return_value=fake) as cls,
        patch.object(server.webbrowser, "open") as browser,
    ):
        server.main(["--port", "9999"])
    cls.assert_called_once_with(("127.0.0.1", 9999), server.Handler)
    browser.assert_called_once_with("http://127.0.0.1:9999/")
    fake.server_close.assert_called_once()


def test_main_no_browser():
    fake = _fake_server()
    with (
        patch.object(server, "ThreadingHTTPServer", return_value=fake),
        patch.object(server.webbrowser, "open") as browser,
    ):
        server.main(["--no-browser", "--host", "0.0.0.0"])
    browser.assert_not_called()


def test_module_entry_point_runs_main():
    with patch.object(server, "main") as main:
        runpy.run_module("will_it_python.trait_venn", run_name="__main__")
    main.assert_called_once_with()


def test_main_port_in_use_exits_with_message(capsys):
    busy = OSError(errno.EADDRINUSE, "Address already in use")
    with (
        patch.object(server, "ThreadingHTTPServer", side_effect=busy),
        pytest.raises(SystemExit) as exit_info,
    ):
        server.main(["--port", "8765", "--no-browser"])
    assert exit_info.value.code == 1
    assert "port 8765 on 127.0.0.1 is already in use" in capsys.readouterr().err


def test_main_other_os_errors_propagate():
    denied = OSError(errno.EACCES, "Permission denied")
    with (
        patch.object(server, "ThreadingHTTPServer", side_effect=denied),
        pytest.raises(OSError, match="Permission denied"),
    ):
        server.main(["--port", "80", "--no-browser"])


def test_stylesheet_hides_collapsed_drill_downs():
    # Regression: `.chips { display: flex }` overrode the [hidden] attribute,
    # so collapsed drill-down categories stayed visible.
    assert b"[hidden] { display: none !important; }" in server.read_asset("app.css")


def test_page_supports_reader_views():
    page = server.read_asset("index.html")
    css = server.read_asset("app.css")
    assert b'<meta name="description"' in page
    assert b'<article class="page">' in page
    assert b'id="summary-body"' in page
    # The summary must be clipped, not display:none, or reader views drop it.
    rule = css.split(b".reader-summary {", 1)[1].split(b"}", 1)[0]
    assert b"clip" in rule
    assert b"display" not in rule


def test_diagram_svg_uses_concrete_colors():
    # Reader views copy the SVG without the stylesheet; CSS variables in SVG
    # paint attributes then resolve to black.
    script = server.read_asset("app.js")
    for pattern in (b'fill="var(--', b'stroke="var(--', b'style="fill:var(--'):
        assert pattern not in script
    assert b"getComputedStyle" in script


def test_text_view_toggle_and_summary_in_stage():
    page = server.read_asset("index.html").decode()
    assert 'id="text-view" aria-pressed="false"' in page
    stage = page.split('<section class="stage"', 1)[1].split("</main>", 1)[0]
    assert 'id="summary-body"' in stage


def test_page_embeds_summary_for_requested_selection(base_url):
    _, _, body = get(base_url + "/?sel=male,left&country=JP")
    page = body.decode()
    assert "<title>Someone who is male and left-handed is 1 in 19 worldwide." in page
    assert '<span class="odds">1 in 19</span>' in page
    assert "<li>Male: 50.4% in Japan</li>" in page


def test_page_without_selection_uses_default(base_url):
    _, _, body = get(base_url + "/")
    assert b"is <strong>female, left-handed and green-eyed</strong>" in body


def test_page_with_invalid_query_is_served_unfilled(base_url):
    status, _, body = get(base_url + "/?sel=nope")
    assert status == 200
    assert b"<title>Trait Venn</title>" in body
    assert b'<div id="summary-body"></div>' in body


def test_api_state_blank_selection_is_empty(base_url):
    _, _, body = get(base_url + "/api/state?sel=&country=US")
    assert json.loads(body)["selection"] == []
