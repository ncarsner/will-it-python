"""Text renderings of a page state: headline, sources line, and summary.

The summary is the page's text alternative to the diagram. The server embeds
it in the initial HTML for the requested selection and returns it in every
state response, so browser reader views, screen readers, printing, and the
in-app text view all show the same content.
"""

from __future__ import annotations

from html import escape
from typing import Any, Final

from will_it_python.trait_venn.traits import US

type Json = dict[str, Any]

EMPTY_HEADLINE: Final = "Pick traits on either side to see how rare that person is."
ASSUMPTION: Final = (
    "Traits assumed independent except where they depend on gender "
    "(color blindness, height, migraines)."
)


def headline(is_text: str, has_text: str, odds: str, *, html: bool) -> str:
    """Return the headline sentence.

    Args:
        is_text: Joined "is" phrases, or ``""``.
        has_text: Joined "has" phrases, or ``""``.
        odds: Worldwide odds, e.g. ``"1 in 1,008"``.
        html: Emphasize the phrases and odds with markup (escaped) instead of
            returning plain text.

    Returns:
        The sentence, or a prompt when nothing is selected.
    """
    if not is_text and not has_text:
        return escape(EMPTY_HEADLINE) if html else EMPTY_HEADLINE

    def strong(text: str) -> str:
        return f"<strong>{escape(text)}</strong>" if html else text

    clauses = [
        f"is {strong(is_text)}" if is_text else "",
        f"has {strong(has_text)}" if has_text else "",
    ]
    who = ", and ".join(c for c in clauses if c)
    shown = f'<span class="odds">{escape(odds)}</span>' if html else odds
    return f"Someone who {who} is {shown} worldwide."


def sources(country: str, country_name: str, source: str, world_source: str) -> str:
    """Return the footer line describing interaction and data sources."""
    if country == US:
        populations = f"US & world population: {source}"
    else:
        populations = f"{country_name} population: {source} · world: {world_source}"
    return (
        "Hover the diagram, or focus it and use ← → to explore regions · "
        f"diagram & chips use {country_name} shares, headline is worldwide · "
        f"{populations}"
    )


def summary_html(state: Json) -> str:
    """Return the summary as escaped HTML for a page state.

    Args:
        state: Output of :func:`state.build_state`.

    Returns:
        Paragraphs, a list of selected traits, and a table of every
        intersection with share, odds, and expected people in the selected
        nation.
    """
    text = escape(state["headline"]["text"])
    if not state["selection"]:
        return f"<p>{text}</p>"
    nation, world = state["nation"], state["world"]
    name = escape(state["countryName"])
    chips = sorted(
        (t for c in state["categories"] for t in c["traits"] if t["slot"] is not None),
        key=lambda t: t["slot"],
    )
    traits = "".join(
        f"<li>{escape(t['name'])}"
        + (f": {escape(t['pct'])} in {name}" if t["pct"] else "")
        + "</li>"
        for t in chips
    )
    regions = sorted(state["regions"], key=lambda r: (-len(r["slots"]), r["mask"]))
    rows = "".join(
        f'<tr><th scope="row">{escape(" + ".join(r["names"]))}</th>'
        f"<td>{escape(r['nation']['pct'] or '—')}</td>"
        f"<td>{escape(r['nation']['odds'])}</td>"
        f"<td>{escape(r['nation']['count'])}</td></tr>"
        for r in regions
    )
    return (
        f"<p>{text}</p>"
        f"<p>In {name}: {escape(nation['odds'])}, {escape(nation['count'])}. "
        f"On Earth: {escape(world['count'])} of {world['population']:,}.</p>"
        f"<h3>Selected traits</h3><ul>{traits}</ul>"
        f"<h3>Every intersection in {name}</h3>"
        '<table><thead><tr><th scope="col">Traits</th><th scope="col">Share</th>'
        '<th scope="col">Odds</th><th scope="col">Expected people</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
        f"<p>{escape(state['sourcesText'])}. {escape(ASSUMPTION)}</p>"
    )
