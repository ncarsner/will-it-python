"""Builds the JSON-serializable page state for a validated request.

The browser renders this state as-is: all probabilities, odds, percentages,
ordering, and label placement are computed here.
"""

from __future__ import annotations

from typing import Any

from will_it_python.trait_venn import calc, geometry
from will_it_python.trait_venn.population import Clock, Snapshot
from will_it_python.trait_venn.traits import (
    CATEGORIES,
    COUNTRIES,
    COUNTRIES_BY_CODE,
    MAX_SELECTED,
    TRAITS,
    TRAITS_BY_ID,
    US,
    Trait,
)
from will_it_python.trait_venn.validation import Request, can_add

type Json = dict[str, Any]


def _clock(clock: Clock) -> Json:
    return {"base": clock.base, "at": clock.at, "perSecond": clock.per_second}


def ordered_countries() -> list[Json]:
    """Return countries with the United States first, the rest alphabetical."""
    rest = sorted((c for c in COUNTRIES if c.code != US), key=lambda c: c.name)
    return [{"code": c.code, "name": c.name} for c in (COUNTRIES_BY_CODE[US], *rest)]


def _categories(selection: tuple[str, ...], country: str) -> list[Json]:
    """Return categories with traits in display order (see Category.by_prevalence)."""
    result = []
    for category in CATEGORIES:
        members = [t for t in TRAITS if t.category == category.name]
        if category.by_prevalence:
            members.sort(key=lambda t: calc.prevalence(t, country), reverse=True)
        traits = []
        for t in members:
            slot = selection.index(t.id) if t.id in selection else None
            traits.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "short": t.short,
                    "pct": calc.fmt_pct(calc.prevalence(t, country)),
                    "slot": slot,
                    "enabled": slot is not None or can_add(selection, t),
                }
            )
        result.append(
            {
                "name": category.name,
                "side": category.side.value,
                "selectedCount": sum(tr["slot"] is not None for tr in traits),
                "traits": traits,
            }
        )
    return result


def _scope(population: int, p: float) -> Json:
    return {
        "population": population,
        "p": p,
        "odds": calc.ratio(p),
        "pct": calc.fmt_pct(p),
        "count": calc.expected_count(population, p),
    }


def _regions(
    traits: list[Trait], country: str, world_pop: int, nation_pop: int
) -> list[Json]:
    full = (1 << len(traits)) - 1
    regions = []
    for mask in range(1, full + 1):
        slots = [i for i in range(len(traits)) if mask >> i & 1]
        nation = calc.region_probability(traits, mask, country)
        world = calc.region_probability(traits, mask, None)
        regions.append(
            {
                "mask": mask,
                "slots": slots,
                "names": [traits[i].name for i in slots],
                "isCenter": mask == full,
                "nation": _scope(nation_pop, nation.inclusive)
                | {"onlyOdds": calc.ratio(nation.exclusive)},
                "world": _scope(world_pop, world.inclusive),
            }
        )
    return regions


def _diagram(traits: list[Trait], country: str) -> Json | None:
    n = len(traits)
    if not n:
        return None
    anchors = geometry.anchors(n)
    labels = [
        {
            "slot": i,
            "x": anchors[1 << i].x,
            "y": anchors[1 << i].y,
            "name": t.name,
            "pct": calc.fmt_pct(calc.prevalence(t, country)),
        }
        for i, t in enumerate(traits)
    ]
    badge = None
    if n > 1:
        full = (1 << n) - 1
        center = anchors[full]
        k, _, of = calc.badge_ratio(
            calc.region_probability(traits, full, country).inclusive
        ).partition(" in ")
        badge = {
            "x": center.x,
            "y": center.y,
            "r": geometry.badge_radius(n),
            "sets": n,
            "top": f"{k} in" if of else k,
            "bottom": of,
        }
    ellipses = [
        {"cx": e.cx, "cy": e.cy, "rx": e.rx, "ry": e.ry, "rotation": e.rotation}
        for e in geometry.LAYOUTS[n]
    ]
    return {
        "size": geometry.CANVAS,
        "ellipses": ellipses,
        "labels": labels,
        "badge": badge,
    }


def build_state(request: Request, snap: Snapshot, now: float) -> Json:
    """Return the full page state for a request.

    Args:
        request: Validated selection and country.
        snap: Population clocks.
        now: POSIX time used to project populations.

    Returns:
        A JSON-serializable mapping consumed by the browser.
    """
    selection, country = request.selection, request.country
    traits = [TRAITS_BY_ID[i] for i in selection]
    nation = COUNTRIES_BY_CODE[country]
    nation_clock = snap.us if country == US else Clock(nation.population, now, 0.0)
    world_pop, nation_pop = snap.world.now(now), nation_clock.now(now)
    full = (1 << len(traits)) - 1
    world_p = calc.region_probability(traits, full, None).inclusive
    nation_p = calc.region_probability(traits, full, country).inclusive
    return {
        "selection": list(selection),
        "country": country,
        "countryName": nation.name,
        "max": MAX_SELECTED,
        "countries": ordered_countries(),
        "categories": _categories(selection, country),
        "headline": {
            "is": calc.join_phrases([t.is_phrase for t in traits if t.is_phrase]),
            "has": calc.join_phrases([t.has_phrase for t in traits if t.has_phrase]),
            "odds": calc.ratio(world_p),
        },
        "world": _scope(world_pop, world_p),
        "nation": _scope(nation_pop, nation_p),
        "population": {
            "world": _clock(snap.world),
            "nation": _clock(nation_clock),
            "source": snap.source if country == US else "static 2026 estimate",
            "worldSource": snap.source,
        },
        "diagram": _diagram(traits, country),
        "regions": _regions(traits, country, world_pop, nation_pop),
    }
