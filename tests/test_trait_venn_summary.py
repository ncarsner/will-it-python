"""Tests for trait_venn text renderings: headline, sources, and summary."""

import pytest

from will_it_python.trait_venn import state, summary
from will_it_python.trait_venn.population import Clock, Snapshot
from will_it_python.trait_venn.validation import Request

NOW = 1_790_000_000.0
SNAP = Snapshot(world=Clock(8_000_000_000, NOW, 0.0), us=Clock(340_000_000, NOW, 0.0))


def build(sel, country="US"):
    return state.build_state(Request(tuple(sel), country), SNAP, NOW)


@pytest.mark.parametrize(
    ("is_text", "has_text", "expected"),
    [
        ("left-handed", "", "Someone who is left-handed is 1 in 10 worldwide."),
        ("", "asthma", "Someone who has asthma is 1 in 10 worldwide."),
        (
            "left-handed",
            "asthma",
            "Someone who is left-handed, and has asthma is 1 in 10 worldwide.",
        ),
        ("", "", summary.EMPTY_HEADLINE),
    ],
)
def test_headline_plain(is_text, has_text, expected):
    assert summary.headline(is_text, has_text, "1 in 10", html=False) == expected


def test_headline_html_emphasizes_and_escapes():
    html = summary.headline("a <b>", "", "1 in 10", html=True)
    assert html == (
        'Someone who is <strong>a &lt;b&gt;</strong> is <span class="odds">1 in 10'
        "</span> worldwide."
    )
    assert summary.headline("", "", "x", html=True) == summary.EMPTY_HEADLINE


def test_sources_us_and_other_nations():
    us = summary.sources("US", "United States", "live", "live")
    assert us.endswith("US & world population: live")
    jp = summary.sources("JP", "Japan", "static", "live")
    assert jp.endswith("Japan population: static · world: live")
    assert "diagram & chips use Japan shares" in jp


def test_summary_lists_traits_and_every_intersection():
    s = build(["female", "left", "hsam"])
    html = s["summaryHtml"]
    assert html.startswith(f"<p>{s['headline']['text']}</p>")
    assert "<li>Female: 50.5% in United States</li>" in html
    assert "<li>Superior autobiographical memory</li>" in html  # below pct floor
    assert html.count('<th scope="row">') == 7  # 2**3 - 1 intersections
    assert html.index("Female + Left-handed + Superior") < html.index(
        '<th scope="row">Female</th>'
    )
    assert "—" in html  # share omitted for the rarest regions
    assert summary.ASSUMPTION in html


def test_summary_for_empty_selection():
    assert build([])["summaryHtml"] == f"<p>{summary.EMPTY_HEADLINE}</p>"
